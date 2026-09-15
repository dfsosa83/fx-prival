# -*- coding: utf-8 -*-
"""H1 bias filter — design doc §2.1.1.

Deterministic, pure function of closed H1 bars. No MT5 dependency (works on any
OHLCV DataFrame with columns: time/datetime, open, high, low, close).

Bias rule (from the design contract):
    ema_fast > ema_slow and close > ema_slow  -> BULLISH (arms BUY only)
    ema_fast < ema_slow and close < ema_slow  -> BEARISH (arms SELL only)
    else                                       -> FLAT (nothing armed)

EMA(20/50) on H1 is an OPERATIONAL DEFINITION, documented as such in §2.1.1
(the manual transcript never states numeric EMA periods).
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

BULLISH = "BULLISH"
BEARISH = "BEARISH"
FLAT = "FLAT"


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average via pandas (wilders=False, standard EMA)."""
    return series.ewm(span=span, adjust=False).mean()


def compute_h1_bias(
    h1_df: pd.DataFrame,
    ema_fast: int = 20,
    ema_slow: int = 50,
) -> str:
    """Return BULLISH / BEARISH / FLAT for the most recently COMPLETED H1 bar.

    The caller must pass only closed bars (design G1: never the forming bar).
    Returns FLAT if there is not enough history to compute both EMAs.

    Parameters
    ----------
    h1_df : DataFrame
        Closed, oldest->newest H1 bars. Must include 'close'.
    ema_fast, ema_slow : int
        EMA periods from config.yaml (bias.ema_fast / ema_slow).
    """
    if h1_df is None or len(h1_df) < ema_slow:
        return FLAT

    close = h1_df["close"].astype(float)
    ema_f = ema(close, ema_fast)
    ema_s = ema(close, ema_slow)

    last_close = float(close.iloc[-1])
    last_f = float(ema_f.iloc[-1])
    last_s = float(ema_slow_value := ema_s.iloc[-1])

    if last_f > last_s and last_close > last_s:
        return BULLISH
    if last_f < last_s and last_close < last_s:
        return BEARISH
    return FLAT


def series_h1_bias(h1_df: pd.DataFrame, ema_fast: int = 20, ema_slow: int = 50) -> pd.Series:
    """Vectorized bias per completed H1 bar (for backtests / unit tests).

    Returns a boolean/str Series aligned to h1_df; first `ema_slow` entries are
    NA (warm-up), which callers must never treat as a tradable state.
    """
    if h1_df is None or len(h1_df) < ema_slow:
        return pd.Series(dtype="object")

    close = h1_df["close"].astype(float)
    ema_f = ema(close, ema_fast)
    ema_s = ema(close, ema_slow)

    bull = (ema_f > ema_s) & (close > ema_s)
    bear = (ema_f < ema_s) & (close < ema_s)
    result = pd.Series(FLAT, index=h1_df.index, dtype="object")
    result[bull] = BULLISH
    result[bear] = BEARISH
    result.iloc[: ema_slow - 1] = pd.NA
    return result