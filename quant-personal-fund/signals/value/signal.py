"""
FX value (mean-reversion) signal.

Economic mechanism: currencies deviate from long-run equilibrium levels
(PPP, REER, purchasing power parity) and tend to revert over multi-year
horizons. The value trade bets on reversion to a long-run fair value.

Proxy from spot prices only:
    Long-run fair value is approximated by a very long moving average
    (2-5 years). The value signal is positive when spot is significantly
    BELOW its long-run mean (currency is undervalued → long it).

Design:
    value_score[t] = -z(spot - long_ma) / long_ma
    Positive = currency undervalued → long.
"""

from typing import List, Optional

import numpy as np
import pandas as pd


DEFAULT_LONG_WINDOWS = [504, 756, 1008]  # 2y, 3y, 4y (252 days/year)


def compute_value_signal(
    prices: pd.DataFrame,
    long_windows: Optional[List[int]] = None,
    z_threshold: float = 0.5,
) -> pd.DataFrame:
    """
    Compute FX value signals from spot prices.

    For each FX pair, the value score measures the deviation of spot from
    its long-run moving average, z-scored over the same window.

    value_score[t] = -z_score(spot[t] / long_ma[t] - 1)

    Positive value score = currency is below fair value → LONG it.
    Scores are clipped to [-1, 1] by default (only trade strong signals).

    Args:
        prices: DataFrame (dates × FX tickers) of spot prices.
        long_windows: Long-run MA windows in days.
        z_threshold: Minimum z-score to activate a trade.

    Returns:
        DataFrame (dates × tickers) of value scores.
    """
    if long_windows is None:
        long_windows = DEFAULT_LONG_WINDOWS

    results = {}
    for ticker in prices.columns:
        spot = prices[ticker].dropna()
        composite = pd.Series(0.0, index=prices.index)

        for w in long_windows:
            ma = spot.rolling(w, min_periods=w // 2).mean()
            # Deviation of spot from long-run MA
            deviation = (spot - ma) / ma
            # Z-score the deviation over the same window
            z = deviation.rolling(w, min_periods=w // 2).apply(
                lambda x: (x[-1] - x.mean()) / x.std() if x.std() > 0 else 0.0,
                raw=True,
            )
            # Value trade: long the undervalued currency (negative deviation)
            value_component = -z
            value_component = value_component.reindex(prices.index)
            composite += value_component.fillna(0.0)

        composite = composite / len(long_windows)

        # Only trade when |z| exceeds threshold
        composite = composite.where(composite.abs() >= z_threshold, 0.0)
        composite = composite.clip(lower=-1.0, upper=1.0)

        results[ticker] = composite

    return pd.DataFrame(results)