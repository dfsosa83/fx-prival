"""
USD base-currency conversion for the EXP-2026-04A active universe.

Research convention (log-additive), documented in docs/REMEDIATION_NOTES.md:

    R_usd[t] = R_local[t] + r_fx_leg[t]

where r_fx_leg is the log change in the USD-per-unit exchange rate.

Direct pairs (USD quoted):   EUR -> EURUSD, GBP -> GBPUSD, AUD -> AUDUSD, NZD -> NZDUSD
Inverse pairs (USD base):    JPY -> -ln(USDJPY), CAD -> -ln(USDCAD), CHF -> -ln(USDCHF)

Cross-pair EURJPY (JPY per EUR):
    USD per EUR = (JPY per EUR) / (JPY per USD) = EURJPY / USDJPY
    R_usd(EURJPY position) = r_EURJPY - r_USDJPY

Missing-FX policy:
    - Forward-fill up to `max_ffill_days` (default 5).
    - If still missing, the instrument's return is NaN for that date
      (excluded from portfolio return; never zero-filled).
    - No look-ahead: conversion at date t uses FX at date t only.

Distinction (documented): this is a RESEARCH-RETURN FX convention.
Execution-grade FX PnL accounting (exact multiplicative fills, bid/ask,
intraday session alignment) is OUT OF SCOPE for 04A.
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd


# Currency -> (pair_ticker, orientation)
# orientation "direct"  : USD per unit = pair (quote is USD)
# orientation "inverse" : USD per unit = 1 / pair (base is USD)
FX_USD_PER_UNIT: Dict[str, tuple] = {
    "EUR": ("EURUSD", "direct"),
    "GBP": ("GBPUSD", "direct"),
    "AUD": ("AUDUSD", "direct"),
    "NZD": ("NZDUSD", "direct"),
    "JPY": ("USDJPY", "inverse"),
    "CAD": ("USDCAD", "inverse"),
    "CHF": ("USDCHF", "inverse"),
}


def fx_leg_log_return(
    fx_prices: pd.DataFrame,
    currency: str,
) -> pd.Series:
    """
    Log return of the USD-per-unit FX leg for a currency.

    Args:
        fx_prices: DataFrame (dates × FX tickers) of FX prices (level).
        currency: ISO currency code (EUR, GBP, AUD, NZD, JPY, CAD, CHF).

    Returns:
        Series of daily log returns of USD-per-unit, aligned to fx_prices.index.
    """
    if currency not in FX_USD_PER_UNIT:
        raise ValueError(f"No USD conversion defined for currency '{currency}'")

    pair, orientation = FX_USD_PER_UNIT[currency]
    if pair not in fx_prices.columns:
        raise KeyError(f"FX pair '{pair}' required for {currency} conversion not present")

    pair_levels = fx_prices[pair]
    pair_log_ret = np.log(pair_levels / pair_levels.shift(1))

    if orientation == "direct":
        return pair_log_ret
    else:  # inverse: USD per unit = 1/pair
        return -pair_log_ret


def convert_local_to_usd(
    returns_local: pd.Series,
    fx_prices: pd.DataFrame,
    currency: str,
    max_ffill_days: int = 5,
) -> pd.Series:
    """
    Convert a local-currency log return series to USD log returns.

    R_usd[t] = R_local[t] + fx_leg[t]

    Missing-FX policy: forward-fill the FX LEVEL (assuming no FX move
    while unobserved -> leg = 0) up to max_ffill_days; beyond that, the
    converted return is NaN (never zero-filled). This is the conservative
    economic interpretation: an unobserved rate is assumed unchanged.

    Args:
        returns_local: Series of local-currency log returns (indexed by date).
        fx_prices: DataFrame (dates × FX tickers) of FX price levels.
        currency: Local currency of the asset.
        max_ffill_days: Maximum forward-fill days for a missing FX rate.

    Returns:
        Series of USD log returns aligned to returns_local.index.
    """
    if currency not in FX_USD_PER_UNIT:
        raise ValueError(f"No USD conversion defined for currency '{currency}'")
    pair, orientation = FX_USD_PER_UNIT[currency]
    if pair not in fx_prices.columns:
        raise KeyError(f"FX pair '{pair}' required for {currency} conversion not present")

    levels = fx_prices[pair]
    # Union index so FX history immediately before the local series start is
    # available for the first leg; then restrict back to the local dates.
    union = returns_local.index.union(levels.index)
    levels_u = levels.reindex(union)
    levels_ff = levels_u.ffill(limit=max_ffill_days)

    # Leg from forward-filled levels: unchanged level -> leg 0.
    fx_leg = np.log(levels_ff / levels_ff.shift(1))
    if orientation == "inverse":
        fx_leg = -fx_leg
    fx_leg = fx_leg.reindex(returns_local.index)

    converted = returns_local + fx_leg
    # Where FX is still missing beyond ffill limit -> NaN (never zero-filled)
    converted = converted.where(levels_ff.reindex(returns_local.index).notna(), np.nan)
    converted.name = returns_local.name
    return converted


def convert_panel_to_usd(
    returns_panel: pd.DataFrame,
    fx_prices: pd.DataFrame,
    local_currency_map: Dict[str, str],
    max_ffill_days: int = 5,
) -> pd.DataFrame:
    """
    Convert a multi-asset returns panel to USD.

    For each ticker:
        - If the ticker is an FX pair already quoted against USD (quote==USD
          or base==USD), the pair's log return is the position's USD return
          under the research convention -> returned as-is.
        - If the ticker is a non-FX asset with a defined local currency,
          converted via convert_local_to_usd.
        - Otherwise returned as-is (assumed USD-denominated).

    EURJPY (cross pair) is handled by the caller via convert_cross_eurjpy.

    Args:
        returns_panel: DataFrame (dates × tickers) of log returns.
        fx_prices: DataFrame (dates × FX tickers) of FX price levels.
        local_currency_map: ticker -> local currency for non-FX assets.
        max_ffill_days: Forward-fill limit for missing FX.

    Returns:
        DataFrame (dates × tickers) of USD-converted log returns.
    """
    result = returns_panel.copy()
    for ticker in returns_panel.columns:
        if ticker in local_currency_map:
            ccy = local_currency_map[ticker]
            result[ticker] = convert_local_to_usd(
                returns_panel[ticker], fx_prices, ccy, max_ffill_days
            )
        # else: FX pairs quoted against USD or USD assets -> unchanged
    return result


def convert_cross_eurjpy(
    eurjpy_returns: pd.Series,
    usdjpy_prices: pd.Series,
    max_ffill_days: int = 5,
) -> pd.Series:
    """
    Convert EURJPY (cross) returns to USD returns for a USD-based investor.

    USD per EUR = EURJPY / USDJPY  (both JPY per unit)
    R_usd = r_EURJPY - r_USDJPY

    Missing-FX policy: forward-fill the USDJPY LEVEL (assume no JPY/USD
    move while unobserved -> leg 0) up to max_ffill_days; beyond that NaN.

    Args:
        eurjpy_returns: Series of EURJPY log returns.
        usdjpy_prices: Series of USDJPY price levels (JPY per USD).
        max_ffill_days: Forward-fill limit for missing USDJPY.

    Returns:
        Series of USD log returns for the EURJPY position.
    """
    levels = usdjpy_prices
    union = eurjpy_returns.index.union(levels.index)
    levels_u = levels.reindex(union)
    levels_ff = levels_u.ffill(limit=max_ffill_days)
    usdjpy_ret = np.log(levels_ff / levels_ff.shift(1)).reindex(eurjpy_returns.index)
    converted = eurjpy_returns - usdjpy_ret
    converted = converted.where(levels_ff.reindex(eurjpy_returns.index).notna(), np.nan)
    converted.name = eurjpy_returns.name
    return converted