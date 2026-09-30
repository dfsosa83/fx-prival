"""
Volatility scaling for trend following positions.

Converts raw trend signals into position weights using inverse-volatility
scaling. Each instrument's position is sized to target a fixed risk budget,
so that more volatile instruments receive smaller weights and less volatile
instruments receive larger weights.

This is a standard approach in managed futures / CTA strategies.
"""

from typing import Optional, Tuple

import numpy as np
import pandas as pd


def compute_vol_scaled_positions(
    signals: pd.DataFrame,
    returns: pd.DataFrame,
    vol_target: float = 0.20,
    vol_halflife: int = 60,
    vol_min_periods: int = 20,
    max_position: float = 0.15,
    long_only: bool = True,
    signal_halflife: int = 10,
    rebalance_threshold: float = 0.02,
) -> pd.DataFrame:
    """
    Convert trend signals to inverse-volatility position weights.

    For each instrument i at time t:
        smoothed_signal = EWMA(signal, halflife=signal_halflife)
        raw_position[i,t] = smoothed_signal[i,t] * (vol_target / vol_instrument[i,t])

    Weights are then normalized so sum(abs(weight)) = 1.0. A rebalance
    threshold suppresses weight changes smaller than `rebalance_threshold`,
    reducing turnover from noisy daily signal fluctuations.

    Args:
        signals: DataFrame (dates × tickers) of trend scores from blend_signals().
        returns: DataFrame (dates × tickers) of daily returns for vol estimation.
        vol_target: Annualized volatility target per instrument.
        vol_halflife: EWMA halflife for volatility estimation (days).
        vol_min_periods: Minimum observations before producing a vol estimate.
        max_position: Maximum absolute weight per instrument.
        long_only: If True, negative signals are clipped to 0.
        signal_halflife: EWMA halflife for smoothing signals (days).
        rebalance_threshold: Minimum weight change to trigger rebalance.
                             Smaller changes keep the previous weight.

    Returns:
        DataFrame (dates × tickers) of portfolio weights.
    """
    tickers = signals.columns.tolist()
    n_dates = len(signals)
    weights = pd.DataFrame(0.0, index=signals.index, columns=tickers)

    # Compute EWMA volatility for each instrument
    vol_estimates = pd.DataFrame(np.nan, index=signals.index, columns=tickers)
    for ticker in tickers:
        ret = returns[ticker].dropna()
        vol_annual = ret.pow(2).ewm(
            halflife=vol_halflife,
            min_periods=vol_min_periods,
        ).mean().pow(0.5) * np.sqrt(252)
        vol_estimates[ticker] = vol_annual.reindex(signals.index)

    # Smooth signals
    smoothed = signals.ewm(halflife=signal_halflife, min_periods=5).mean()

    # Compute raw weights
    raw_weights = pd.DataFrame(0.0, index=signals.index, columns=tickers)
    prev_weights = pd.Series(0.0, index=tickers)

    for i in range(n_dates):
        date = signals.index[i]
        sig = smoothed.iloc[i].fillna(0.0)
        if long_only:
            sig = sig.clip(lower=0.0)

        # Raw position: sig * vol_target / instrument_vol
        raw = pd.Series(0.0, index=tickers)
        for ticker in tickers:
            v = vol_estimates.loc[date, ticker]
            if pd.notna(v) and v > 0:
                raw[ticker] = sig[ticker] * vol_target / v

        # Normalize to unit gross exposure
        gross = raw.abs().sum()
        if gross > 0:
            raw = raw / gross

        # Apply per-instrument cap: if any weight exceeds max_position,
        # scale all weights proportionally so the max is exactly max_position
        max_abs = raw.abs().max()
        if max_abs > max_position:
            raw = raw * (max_position / max_abs)

        # Apply rebalance threshold: keep previous weight if change is small
        if i > 0 and rebalance_threshold > 0:
            change = (raw - prev_weights).abs()
            for ticker in tickers:
                if change[ticker] < rebalance_threshold:
                    raw[ticker] = prev_weights[ticker]

            # Apply per-instrument cap: if any weight exceeds max_position,
            # scale all weights proportionally so the max is exactly max_position
            max_abs = raw.abs().max()
            if max_abs > max_position:
                raw = raw * (max_position / max_abs)

            # Re-normalize after threshold
            gross = raw.abs().sum()
            if gross > 0:
                raw = raw / gross

            # Apply cap again after re-normalization (threshold may have distorted it)
            max_abs = raw.abs().max()
            if max_abs > max_position:
                raw = raw * (max_position / max_abs)

        weights.loc[date] = raw
        prev_weights = raw.copy()

    return weights


def forecast_vol_target(
    signals: pd.DataFrame,
    returns: pd.DataFrame,
    vol_lookback: int = 60,
    target_vol: float = 0.15,
) -> pd.Series:
    """
    Compute a portfolio-level volatility forecast for scaling.

    Estimates conditional portfolio volatility from recent returns and
    current target positions to enable portfolio-level volatility targeting.

    Args:
        signals: Raw trend scores (not yet normalized).
        returns: Daily returns DataFrame.
        vol_lookback: Lookback for volatility forecasting.
        target_vol: Target annualized portfolio volatility.

    Returns:
        Series of volatility scaling multipliers (1.0 = no adjustment,
        <1.0 = reduce exposure, >1.0 = increase exposure).
    """
    # Estimate correlation from recent returns
    recent_rets = returns.tail(vol_lookback)
    if len(recent_rets) < vol_lookback // 2:
        return pd.Series(1.0, index=signals.index)

    cov = recent_rets.cov() * 252
    vols = np.sqrt(np.diag(cov.values))

    # Estimate portfolio vol from current signals and covariance
    multipliers = pd.Series(1.0, index=signals.index)
    for i, date in enumerate(signals.index):
        if i < vol_lookback:
            continue
        s = signals.loc[date].fillna(0.0).values
        if np.sum(np.abs(s)) < 1e-10:
            continue
        # Normalize signals to unit gross exposure
        s_norm = s / np.sum(np.abs(s))
        port_vol = np.sqrt(s_norm @ cov @ s_norm)
        if port_vol > 0:
            multipliers.loc[date] = target_vol / port_vol

    return multipliers.clip(lower=0.25, upper=2.0)