"""
FX carry signal.

Economic mechanism: uncovered interest parity (UIP) deviations. High-yield
currencies tend to carry positive expected excess returns when UIP does not
hold — the "carry" trade is long the high-interest currency, short the
low-interest currency, earning the rate differential plus any appreciation.

Carry proxy from spot prices only:
    Since we lack direct forward points, we approximate carry via the
    interest-rate differential implied by the spot rate's position relative
    to its recent moving average. A cleaner implementation uses actual
    rate differentials when available (Phase 4+ with FRED rate data).

Design:
    For each FX pair (base/quote):
        carry_score[t] = sign-based signal proportional to the deviation
        of the spot from its N-day moving average, rescaled to [-1, 1].
        Positive = go long the pair (long base).
"""

from typing import List, Optional

import numpy as np
import pandas as pd


DEFAULT_MA_WINDOWS = [21, 63, 126, 252]  # 1M, 3M, 6M, 12M


def compute_carry_signal(
    prices: pd.DataFrame,
    ma_windows: Optional[List[int]] = None,
    method: str = "deviation",
) -> pd.DataFrame:
    """
    Compute FX carry signals from spot prices.

    For each FX pair, the carry signal is the normalized deviation of spot
    from its moving average. A positive deviation means the currency is
    strong relative to its recent mean (bearish for carry — you want to be
    short an overvalued currency and long an undervalued high-yield one).

    Uses the inverse: carry is long when spot is BELOW the moving average
    (the high-yield currency is cheap).

    Args:
        prices: DataFrame (dates × FX tickers) of spot prices.
        ma_windows: Moving average windows in days.
        method: 'deviation' for raw deviation, 'sign' for sign only.

    Returns:
        DataFrame (dates × tickers) of carry scores in [-1, 1].
        Positive = long the pair (long base currency).
    """
    if ma_windows is None:
        ma_windows = DEFAULT_MA_WINDOWS

    results = {}
    for ticker in prices.columns:
        spot = prices[ticker].dropna()
        scores = pd.Series(0.0, index=prices.index)

        for w in ma_windows:
            ma = spot.rolling(w, min_periods=w // 2).mean()
            # Deviation of spot from MA. Carry wants to be long the CHEAP pair.
            deviation = (spot - ma) / ma
            # Invert: cheap (deviation < 0) → carry-positive
            carry_component = -deviation
            carry_component = carry_component.reindex(prices.index)
            scores += carry_component.fillna(0.0)

        scores = scores / len(ma_windows)  # average across windows
        if method == "sign":
            scores = np.sign(scores)

        results[ticker] = scores

    return pd.DataFrame(results)


def normalize_carry_scores(
    scores: pd.DataFrame,
    window: int = 252,
    long_only: bool = True,
) -> pd.DataFrame:
    """
    Normalize carry scores to a common scale for portfolio construction.

    Z-scores each pair's carry score over a rolling window, then clips
    to [-1, 1] (or [0, 1] for long-only).

    Args:
        scores: Raw carry scores from compute_carry_signal().
        window: Rolling window for z-score normalization.
        long_only: If True, clip negatives to 0.

    Returns:
        Normalized carry scores.
    """
    result = pd.DataFrame(0.0, index=scores.index, columns=scores.columns)
    for ticker in scores.columns:
        s = scores[ticker].rolling(window, min_periods=60).apply(
            lambda x: (x[-1] - x.mean()) / x.std() if x.std() > 0 else 0.0,
            raw=True,
        )
        if long_only:
            s = s.clip(lower=0.0, upper=1.0)
        else:
            s = s.clip(lower=-1.0, upper=1.0)
        result[ticker] = s.fillna(0.0)
    return result