# -*- coding: utf-8 -*-
"""Structural level detection on M30 — design doc §2.1.2.

Pure functions of closed M30/M15 OHLCV bars. No MT5 dependency.
DataFrames must have columns: datetime, open, high, low, close, volume
(oldest -> newest; only COMPLETED bars).

Implements, exactly as specified in the design contract:
  - 5-bar fractal pivot rule, confirmed 2 bars after the pivot (wing=2)
  - level merge when closer than `merge_atr_mult * ATR_M30`
  - level consumption: a solid-body close beyond the level breaks it (§2.1.3)
  - directional watch selection per H1 bias (S4.1), nearest level only
  - swing-above / swing-below helpers used for TP1 (§2.6.1) and invalidation (§2.7)
"""
from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

SOLID_BODY_MIN_FRACTION = 0.30  # design doc §2.1.3 (mirrors signal_gate.py)


def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    """Wilder ATR of the most recent M30 bar (scalar)."""
    if df is None or len(df) < period + 1:
        return float("nan")

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)

    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, adjust=False).mean()
    return float(atr.iloc[-1])


def _is_solid_body(open_, close, high, low, fraction: float = SOLID_BODY_MIN_FRACTION) -> bool:
    rng = high - low
    if rng <= 0:
        return False
    return abs(close - open_) >= fraction * rng


def fractal_swings(df: pd.DataFrame, wing: int = 2) -> pd.DataFrame:
    """Return confirmed fractal swing pivots as a DataFrame.

    Each row: kind ('swing_high'|'swing_low'), price, pivot_idx, pivot_time,
    confirmed_idx, confirmed_time. Only pivots whose confirmation bar has
    fully closed are included (no lookahead — confirmed_time is the bar at
    index pivot_idx+wing).
    """
    n = len(df)
    highs = df["high"].astype(float).to_numpy()
    lows = df["low"].astype(float).to_numpy()
    times = df["datetime"].to_numpy()

    rows: List[Dict] = []
    for i in range(wing, n - wing):
        left_high = highs[i - wing:i].max()
        right_high = highs[i + 1:i + wing + 1].max()
        if highs[i] > left_high and highs[i] > right_high:
            rows.append(
                {
                    "kind": "swing_high",
                    "price": float(highs[i]),
                    "pivot_idx": i,
                    "pivot_time": times[i],
                    "confirmed_idx": i + wing,
                    "confirmed_time": times[i + wing],
                }
            )
        left_low = lows[i - wing:i].min()
        right_low = lows[i + 1:i + wing + 1].min()
        if lows[i] < left_low and lows[i] < right_low:
            rows.append(
                {
                    "kind": "swing_low",
                    "price": float(lows[i]),
                    "pivot_idx": i,
                    "pivot_time": times[i],
                    "confirmed_idx": i + wing,
                    "confirmed_time": times[i + wing],
                }
            )
    return pd.DataFrame(rows)


def _merge_nearby(df: pd.DataFrame, merge_dist: float, kind: str) -> pd.DataFrame:
    """Merge same-kind levels within `merge_dist`, keeping the most recent."""
    if df.empty or merge_dist <= 0:
        return df.copy()
    sub = df[df["kind"] == kind].sort_values("price").copy()
    if len(sub) <= 1:
        return df

    kept_mask = pd.Series(True, index=sub.index)
    prev_price = None
    for idx in sub.index:
        p = sub.at[idx, "price"]
        if prev_price is not None and (p - prev_price) <= merge_dist:
            kept_mask.at[idx] = False
        else:
            prev_price = p

    kept = sub[kept_mask]
    # discard duplicates by pivot_time (keep the most recent in time)
    kept = (
        kept.sort_values("pivot_time", ascending=False)
        .drop_duplicates(subset=["price"], keep="first")
        .sort_values("pivot_time", ascending=True)
    )
    other = df[df["kind"] != kind]
    return pd.concat([other, kept], ignore_index=True)


def build_active_levels(
    df_m30: pd.DataFrame,
    lookback: int = 200,
    atr_period: int = 14,
    merge_atr_mult: float = 0.5,
) -> Dict:
    """Build the current M30 structural level set (design doc §2.1.2).

    Returns {"levels": DataFrame, "atr_m30": float}. Levels carry the
    'confirmed_time' needed by the engine for PENDING_RETEST time-boxing.
    """
    df = df_m30.tail(lookback).reset_index(drop=True)
    atr_m30 = compute_atr(df, atr_period)
    levels = fractal_swings(df, wing=2)

    merge_dist = float(merge_atr_mult * atr_m30) if atr_m30 == atr_m30 else 0.0
    if not levels.empty and merge_dist > 0:
        for kind in ("swing_high", "swing_low"):
            levels = _merge_nearby(levels, merge_dist, kind)

    return {"levels": levels.reset_index(drop=True), "atr_m30": atr_m30}


def level_is_consumed(
    df: pd.DataFrame,
    level: Dict,
    solid_body_min_fraction: float = SOLID_BODY_MIN_FRACTION,
) -> bool:
    """True if any closed bar after `confirmed_time` closes with solid body
    beyond the level (design doc §2.1.2 rule 3, §2.1.3 body threshold).

    Pass the highest available closed timeframe (M15 or M30) for the check.

    Vectorized (identical logic to the old per-row loop — same outputs, ~100x
    faster). Deterministic: the same bars/levels produce the same boolean.
    """
    if "confirmed_time" not in level:
        return False
    post = df[df["datetime"] > level["confirmed_time"]]
    if post.empty:
        return False
    high = post["high"].astype(float)
    low = post["low"].astype(float)
    opn = post["open"].astype(float)
    cls = post["close"].astype(float)
    rng = high - low
    body = (cls - opn).abs()
    solid = (rng > 0) & (body >= solid_body_min_fraction * rng)
    if level["kind"] == "swing_high":
        beyond = cls > level["price"]
    else:
        beyond = cls < level["price"]
    return bool((solid & beyond).any())


def active_level_status(
    levels: pd.DataFrame,
    df_higher: pd.DataFrame,
    solid_body_min_fraction: float = SOLID_BODY_MIN_FRACTION,
) -> pd.DataFrame:
    """Return a copy of `levels` with a boolean 'consumed' column.

    `df_higher` is the highest closed timeframe available for consumption
    checks (design doc §2.1.2: M15 or M30 solid-body close consumes).
    """
    out = levels.copy()
    out["consumed"] = [
        level_is_consumed(df_higher, row.to_dict(), solid_body_min_fraction)
        for _, row in out.iterrows()
    ]
    return out


def select_watched_level(
    bias: str,
    levels_df: pd.DataFrame,
    current_price: float,
) -> Optional[Dict]:
    """Single armed level per design doc §2.1.2 rules 5–6 (S4.1 directional
    filter + nearest-only). Returns None if nothing qualifies.

    - BULLISH bias -> nearest INTACT swing_low below current price (BUY support)
    - BEARISH bias -> nearest INTACT swing_high above current price (SELL resistance)
    - FLAT -> nothing armed
    """
    if bias not in ("BULLISH", "BEARISH") or levels_df.empty:
        return None

    available = levels_df[levels_df["consumed"] == False]  # noqa: E712
    if available.empty:
        return None

    if bias == "BULLISH":
        cand = available[available["kind"] == "swing_low"]
        cand = cand[cand["price"] < current_price]
    else:
        cand = available[available["kind"] == "swing_high"]
        cand = cand[cand["price"] > current_price]

    if cand.empty:
        return None
    cand = cand.copy()
    cand["_dist"] = (cand["price"] - current_price).abs()
    row = cand.sort_values("_dist").iloc[0]
    return row.drop(labels=["_dist"]).to_dict()


def nearest_swing_above(levels_df: pd.DataFrame, price: float) -> Optional[Dict]:
    """Nearest INTACT swing_high above `price` — TP1 for BUY (§2.6.1) and
    invalidation-reference for SELL (§2.7)."""
    if levels_df is None or levels_df.empty:
        return None
    cand = levels_df[(levels_df["consumed"] == False) & (levels_df["kind"] == "swing_high")]  # noqa: E712
    cand = cand[cand["price"] > price]
    if cand.empty:
        return None
    return cand.sort_values("price").iloc[0].to_dict()


def nearest_swing_below(levels_df: pd.DataFrame, price: float) -> Optional[Dict]:
    """Nearest INTACT swing_low below `price` — SL/invalidation reference for
    BUY (§2.7), TP1 for SELL (§2.6.1)."""
    if levels_df is None or levels_df.empty:
        return None
    cand = levels_df[(levels_df["consumed"] == False) & (levels_df["kind"] == "swing_low")]  # noqa: E712
    cand = cand[cand["price"] < price]
    if cand.empty:
        return None
    return cand.sort_values("price", ascending=False).iloc[0].to_dict()