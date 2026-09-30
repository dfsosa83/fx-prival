"""
Portfolio weight construction.

Converts strategy signals into dated portfolio weights that feed directly
into portfolio.accounting.compute_portfolio().

Phase 3+ implements weight generation from trend, carry, and value signals.
"""

from typing import Optional

import numpy as np
import pandas as pd


def equal_weight(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Generate equal-weight portfolio across all instruments.

    Simplest possible allocation — used as a diagnostic baseline.

    Args:
        prices: DataFrame (dates × tickers) of prices.

    Returns:
        DataFrame (dates × tickers) of equal weights (1/N each).
    """
    tickers = prices.columns.tolist()
    n = len(tickers)
    weights = pd.DataFrame(1.0 / n, index=prices.index, columns=tickers)
    return weights


def inverse_volatility_weight(
    returns: pd.DataFrame,
    vol_halflife: int = 60,
) -> pd.DataFrame:
    """
    Generate inverse-volatility weighted portfolio.

    Each instrument's weight is proportional to 1/volatility.
    This is a simple risk-based allocation with no directional signal.

    Args:
        returns: DataFrame (dates × tickers) of daily returns.
        vol_halflife: EWMA halflife for volatility estimation.

    Returns:
        DataFrame (dates × tickers) of inverse-vol weights (all positive).
    """
    tickers = returns.columns.tolist()
    weights = pd.DataFrame(0.0, index=returns.index, columns=tickers)

    for ticker in tickers:
        ret = returns[ticker].dropna()
        vol = ret.pow(2).ewm(halflife=vol_halflife, min_periods=20).mean().pow(0.5)
        vol = vol.reindex(returns.index)
        inv_vol = 1.0 / vol.replace(0.0, np.nan)
        weights[ticker] = inv_vol.fillna(0.0)

    # Normalize
    row_sum = weights.sum(axis=1)
    row_sum_safe = row_sum.replace(0.0, np.nan)
    for ticker in tickers:
        weights[ticker] = weights[ticker] / row_sum_safe
    return weights.fillna(0.0)


def fx_carry_value_weights(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    fx_tickers: list,
    carry_weight: float = 0.5,
    value_weight: float = 0.5,
    vol_target: float = 0.15,
    vol_halflife: int = 60,
    long_only: bool = True,
    rebalance_freq: str = "M",
) -> pd.DataFrame:
    """
    Generate FX carry + value sleeve weights.

    Combines carry and value signals for FX pairs into portfolio weights:
        composite_score = carry_weight * carry_norm + value_weight * value_norm

    The composite score is then scaled by inverse volatility and normalized.

    Args:
        prices: DataFrame (dates × tickers) of daily prices (all instruments).
        returns: DataFrame (dates × tickers) of daily returns.
        fx_tickers: List of FX tickers to trade.
        carry_weight: Weight of carry signal in composite.
        value_weight: Weight of value signal in composite.
        vol_target: Annualized vol target per unit of signal.
        vol_halflife: EWMA halflife for volatility estimation.
        long_only: If True, only long positions.
        rebalance_freq: Rebalance frequency ('M', 'W', 'B').

    Returns:
        DataFrame (dates × fx_tickers) of FX sleeve weights.
    """
    from signals.carry.signal import compute_carry_signal, normalize_carry_scores
    from signals.value.signal import compute_value_signal

    fx_prices = prices[fx_tickers]
    carry_raw = compute_carry_signal(fx_prices)
    value_raw = compute_value_signal(fx_prices)

    carry_norm = normalize_carry_scores(carry_raw, long_only=long_only)
    value_norm = (value_raw + 1.0) / 2.0 if long_only else value_raw
    if long_only:
        value_norm = value_norm.clip(lower=0.0, upper=1.0)

    composite = carry_weight * carry_norm + value_weight * value_norm
    if long_only:
        composite = composite.clip(lower=0.0)

    # Inverse-vol scaling
    weights = pd.DataFrame(0.0, index=composite.index, columns=fx_tickers)
    for ticker in fx_tickers:
        ret = returns[ticker].dropna()
        vol = ret.pow(2).ewm(halflife=vol_halflife, min_periods=20).mean().pow(0.5) * np.sqrt(252)
        vol = vol.reindex(composite.index)
        vol_safe = vol.replace(0.0, np.nan)
        raw = composite[ticker] * vol_target / vol_safe
        weights[ticker] = raw.fillna(0.0)

    # Normalize to unit gross exposure (FX sleeve only)
    gross = weights.abs().sum(axis=1)
    gross_safe = gross.replace(0.0, np.nan)
    weights = weights.div(gross_safe, axis=0).fillna(0.0)

    # Downsample to rebalance frequency
    if rebalance_freq != "B":
        period_series = pd.Series(weights.index.to_period(rebalance_freq), index=weights.index)
        is_last = period_series != period_series.shift(-1)
        weights = weights.where(is_last, other=pd.NA)
        weights = weights.ffill().fillna(0.0)

    return weights


def trend_weights(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    lookbacks: Optional[list] = None,
    vol_target: float = 0.20,
    vol_halflife: int = 60,
    long_only: bool = True,
    max_position: float = 0.15,
    rebalance_freq: str = "W",
) -> pd.DataFrame:
    """
    Generate trend-following portfolio weights from price data.

    Pipeline:
        1. blend_signals(prices) → trend scores per instrument per date
        2. compute_vol_scaled_positions(scores, returns) → raw weights
        3. Downsample to rebalance frequency → hold weights between dates
        4. Return weights for use in portfolio accounting

    Args:
        prices: DataFrame (dates × tickers) of daily prices.
        returns: DataFrame (dates × tickers) of daily returns.
        lookbacks: Trend lookback periods (default: [21, 63, 126, 189, 252]).
        vol_target: Annualized vol target per unit of signal.
        vol_halflife: EWMA halflife for volatility estimation.
        long_only: If True, only long positions.
        max_position: Max weight per instrument.
        rebalance_freq: Pandas offset string for rebalance frequency.
                        'W' = weekly, 'M' = monthly. 'B' = daily.

    Returns:
        DataFrame (dates × tickers) of portfolio weights, forward-filled
        between rebalance dates.
    """
    from signals.trend.signal import blend_signals
    from signals.trend.scaling import compute_vol_scaled_positions

    scores = blend_signals(prices, lookbacks=lookbacks, long_only=long_only)
    weights = compute_vol_scaled_positions(
        signals=scores,
        returns=returns,
        vol_target=vol_target,
        vol_halflife=vol_halflife,
        long_only=long_only,
        max_position=max_position,
    )

    # Downsample to rebalance frequency
    if rebalance_freq != "B":
        period_series = pd.Series(weights.index.to_period(rebalance_freq), index=weights.index)
        is_last = period_series != period_series.shift(-1)
        weights = weights.where(is_last, other=pd.NA)
        weights = weights.ffill().fillna(0.0)

    return weights