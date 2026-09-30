"""
Currency exposure decomposition for multi-asset portfolios.

Decomposes portfolio weights into per-currency net exposures using
FX pair conventions. Non-FX instruments are treated as local-currency
exposures.
"""

from typing import Dict

import pandas as pd


# FX pair currency decomposition: (base, quote)
# Long EURUSD = +EUR, -USD
# Short EURUSD = -EUR, +USD
FX_PAIRS: Dict[str, tuple] = {
    "EURUSD": ("EUR", "USD"),
    "USDJPY": ("USD", "JPY"),
    "GBPUSD": ("GBP", "USD"),
    "AUDUSD": ("AUD", "USD"),
    "USDCAD": ("USD", "CAD"),
    "USDCHF": ("USD", "CHF"),
    "NZDUSD": ("NZD", "USD"),
    "EURJPY": ("EUR", "JPY"),
}


def decompose_currency_exposure(
    positions: pd.DataFrame,
    instrument_master,  # InstrumentMaster instance
) -> pd.DataFrame:
    """
    Decompose portfolio weights into per-currency net exposures.

    For FX instruments:
        Long EURUSD (positive weight) → +1 EUR exposure, -1 USD exposure.
        Short EURUSD (negative weight) → -1 EUR exposure, +1 USD exposure.
        Long USDJPY → +1 USD, -1 JPY.
        The weight represents the fraction of NAV allocated to the pair.

    For non-FX instruments (equity indices, bonds, commodities):
        Treated as exposure to the instrument's local currency.
        SPX (currency=USD) → +weight USD exposure.

    Args:
        positions: DataFrame (dates × tickers) of portfolio weights.
        instrument_master: InstrumentMaster instance.

    Returns:
        DataFrame (dates × currencies) of net currency exposures.
        Positive = long the currency, negative = short.
    """
    currency_exposures: Dict[str, pd.Series] = {}

    for ticker in positions.columns:
        if ticker not in positions.columns:
            continue

        weight_series = positions[ticker]
        asset_class = instrument_master.asset_class(ticker)

        if asset_class == "fx":
            pair = FX_PAIRS.get(ticker)
            if pair is None:
                # Try to derive from instrument master
                base = instrument_master.get(ticker).get("base_currency")
                quote = instrument_master.get(ticker).get("quote_currency")
                if base and quote:
                    pair = (base, quote)
                else:
                    continue

            base_ccy, quote_ccy = pair
            # Long the pair = long base, short quote
            base_exposure = currency_exposures.setdefault(
                base_ccy, pd.Series(0.0, index=positions.index)
            )
            quote_exposure = currency_exposures.setdefault(
                quote_ccy, pd.Series(0.0, index=positions.index)
            )
            currency_exposures[base_ccy] = base_exposure + weight_series.fillna(0.0)
            currency_exposures[quote_ccy] = quote_exposure - weight_series.fillna(0.0)
        else:
            # Non-FX: treat as local currency exposure
            ccy = instrument_master.get(ticker).get("currency", "USD")
            exposure = currency_exposures.setdefault(
                ccy, pd.Series(0.0, index=positions.index)
            )
            currency_exposures[ccy] = exposure + weight_series.fillna(0.0)

    return pd.DataFrame(currency_exposures).sort_index(axis=1)


def detect_concentration(
    currency_exposures: pd.DataFrame,
    threshold: float = 0.50,
) -> pd.DataFrame:
    """
    Detect dates where a single currency exposure exceeds a threshold.

    Args:
        currency_exposures: DataFrame from decompose_currency_exposure.
        threshold: Warning threshold for absolute currency exposure.

    Returns:
        DataFrame of dates where concentration is detected, with
        the currency and exposure value.
    """
    max_abs = currency_exposures.abs().max(axis=1)
    concentrated = max_abs[max_abs > threshold]

    if len(concentrated) == 0:
        return pd.DataFrame()

    max_ccy = currency_exposures.abs().idxmax(axis=1)
    result = pd.DataFrame({
        "max_exposure": concentrated,
        "currency": max_ccy.loc[concentrated.index],
    })
    return result