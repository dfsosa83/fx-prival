"""
Multi-asset time-series trend following signals.

Computes trend strength for each instrument using a blended multi-lookback
approach. The signal is the sign of the blended return across multiple
time horizons, representing the directional trend.

Design:
    - Lookbacks: 1M (21d), 3M (63d), 6M (126d), 9M (189d), 12M (252d)
    - Blend: equal-weighted average of normalized returns at each lookback
    - Signal: sign of blended return (+1 = long, -1 = short, 0 = flat)
    - Long-only by default; short positions require explicit opt-in

This is a transparent, non-optimized baseline. The economic mechanism is
well-documented in academic literature: persistence in asset returns at
intermediate horizons due to slow information diffusion, behavioral biases,
and risk premium cycles.
"""

from typing import List, Optional

import numpy as np
import pandas as pd


# Standard trend lookbacks in trading days
DEFAULT_LOOKBACKS = [21, 63, 126, 189, 252]

# Human-readable labels
LOOKBACK_LABELS = {
    21: "1M",
    63: "3M",
    126: "6M",
    189: "9M",
    252: "12M",
}


def compute_trend_signal(
    prices: pd.DataFrame,
    lookbacks: Optional[List[int]] = None,
    method: str = "log_return",
) -> pd.DataFrame:
    """
    Compute trend signals for all instruments across multiple lookbacks.

    For each instrument and each lookback period L:
        return_L[t] = log(price[t] / price[t-L])
        signal_L[t] = sign(return_L[t])

    If method="log_return", uses the raw log return (continuous signal).
    If method="sign", uses only the sign (+1, -1, 0).

    Args:
        prices: DataFrame (dates × tickers) of prices.
        lookbacks: List of lookback periods in trading days.
        method: 'log_return' for continuous signal, 'sign' for discrete.

    Returns:
        If method='sign': DataFrame (dates × tickers) with values in {-1, 0, 1}.
        If method='log_return': DataFrame (dates × tickers) of raw log returns.
    """
    if lookbacks is None:
        lookbacks = DEFAULT_LOOKBACKS

    results = {}
    for lb in lookbacks:
        # Return over lookback period
        ret = np.log(prices / prices.shift(lb))
        if method == "sign":
            results[lb] = np.sign(ret).where(ret.notna(), 0.0)
        else:
            results[lb] = ret
        results[lb].name = LOOKBACK_LABELS.get(lb, str(lb))

    # Build labeled results
    labeled_results = {}
    for lb in lookbacks:
        label = LOOKBACK_LABELS.get(lb, str(lb))
        labeled_results[label] = results[lb]

    return pd.concat(labeled_results, axis=1)


def _standardize_returns(returns: pd.Series, window: int = 252) -> pd.Series:
    """
    Z-score returns over a rolling window for cross-lookback comparability.

    z_t = (r_t - rolling_mean(r, w)) / rolling_std(r, w)

    Args:
        returns: Series of returns at a single lookback for a single instrument.
        window: Rolling window for normalization.

    Returns:
        Series of z-scored returns.
    """
    mean = returns.rolling(window, min_periods=60).mean()
    std = returns.rolling(window, min_periods=60).std()
    std = std.replace(0.0, np.nan)
    return (returns - mean) / std


def blend_signals(
    prices: pd.DataFrame,
    lookbacks: Optional[List[int]] = None,
    normalize_window: int = 252,
    long_only: bool = True,
) -> pd.DataFrame:
    """
    Blend trend signals across multiple lookbacks into a single score.

    Algorithm:
        1. Compute log return at each lookback for each instrument.
        2. Z-score each return series over a rolling window to make
           lookbacks comparable (a 1M return of +2% and a 12M return
           of +8% both become z-scores reflecting recent relative strength).
        3. Average the z-scores across lookbacks for each instrument.
        4. If long_only, clip negative scores to 0.0.

    Args:
        prices: DataFrame (dates × tickers) of daily prices.
        lookbacks: List of lookback periods.
        normalize_window: Rolling window for z-score normalization.
        long_only: If True, negative scores are clipped to 0.0.

    Returns:
        DataFrame (dates × tickers) of blended trend scores.
        Positive = bullish trend. Negative = bearish trend.
    """
    if lookbacks is None:
        lookbacks = DEFAULT_LOOKBACKS

    tickers = prices.columns.tolist()
    blended = pd.DataFrame(0.0, index=prices.index, columns=tickers)

    for ticker in tickers:
        pr = prices[ticker].dropna()
        z_scores = []

        for lb in lookbacks:
            ret_lb = np.log(pr / pr.shift(lb))
            z = _standardize_returns(ret_lb, window=normalize_window)
            z.name = LOOKBACK_LABELS.get(lb, str(lb))
            z_scores.append(z)

        # Average z-scores across lookbacks
        if z_scores:
            avg_z = pd.concat(z_scores, axis=1).mean(axis=1)
            avg_z = avg_z.reindex(prices.index)
            if long_only:
                avg_z = avg_z.clip(lower=0.0)
            blended[ticker] = avg_z

    return blended