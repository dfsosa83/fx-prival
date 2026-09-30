"""
EXP-2026-05 — v3.4 engine variant (ledger classification update).

Replaces the v3.3 implementation's 500-bar scan cap with the frozen
20-CALENDAR-DAY observation window, measured from the actual entry
timestamp. NO performance scoring.

Only episode identification and reason-code classification change.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ── Constants (v3.4) ───────────────────────────────────────────────────────
LOOKBACK_M15 = 20
SOLID_BODY_MIN_FRACTION = 0.30
ATR_N = 14
TIME_EXIT_BARS = 12
BASE_SLIPPAGE_MULT = 0.5
OBSERVATION_WINDOW = pd.Timedelta(days=20)          # 20 CALENDAR days from entry ts
MAINT_START_UTC = pd.Timestamp("22:30", tz="UTC")
MAINT_END_UTC = pd.Timestamp("02:00", tz="UTC") + pd.Timedelta(days=1)
MAX_EXPECTED_GAP_M15 = pd.Timedelta(minutes=22.5)
SESSION_EXCLUSION_LABEL = "conservative_observed_window_exclusion_not_broker_confirmed"
NO_INVALIDATION_LABEL = "no_invalidation_within_observation_window"
MISSING_BAR_LABEL = "missing_bar_calendar_exclusion"

REASON_CODES_V34 = [
    "c1_triggered",
    "no_c1",
    NO_INVALIDATION_LABEL,
    SESSION_EXCLUSION_LABEL,
    MISSING_BAR_LABEL,
    "rollover_ineligible",
    "other_pre_registered",
]


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def wilder_atr_m15(df: pd.DataFrame) -> np.ndarray:
    n = len(df)
    tr = np.full(n, np.nan)
    prev_close = df["close"].shift(1)
    for i in range(1, n):
        h, l, cp = df["high"].iloc[i], df["low"].iloc[i], prev_close.iloc[i]
        tr[i] = max(h - l, abs(h - cp), abs(l - cp))
    atr = np.full(n, np.nan)
    valid = np.where(~np.isnan(tr))[0]
    if len(valid) >= ATR_N:
        i0 = valid[ATR_N - 1]
        atr[i0] = np.nanmean(tr[valid[:ATR_N]])
        for i in range(i0 + 1, n):
            atr[i] = (ATR_N - 1) / ATR_N * atr[i - 1] + tr[i] / ATR_N
    return atr


def fill_price(mid, spread_points, point, side, slippage_mult=BASE_SLIPPAGE_MULT):
    s = spread_points * point
    l = slippage_mult * s
    return mid + s / 2 + l if side in ("buy", "cover") else mid - s / 2 - l


def is_solid_body(row) -> bool:
    rng = row["high"] - row["low"]
    if rng <= 0:
        return False
    return bool(abs(row["close"] - row["open"]) / rng >= SOLID_BODY_MIN_FRACTION)


def touches_maintenance_window(ts: pd.Timestamp, max_span: pd.Timedelta) -> bool:
    day = ts.normalize()
    w_start = day + pd.Timedelta(hours=22, minutes=30)
    w_end = day + pd.Timedelta(days=1, hours=2)
    return ts < w_end and (ts + max_span) > w_start


class Episode:
    def __init__(self, idx):
        self.idx = idx
        self.traces = []
        self.entry_signal_idx = None
        self.entry_fill_idx = None
        self.entry_fill_ts = None
        self.entry_fill_price = None
        self.support = None
        self.resistance = None
        self.invalidation_idx = None
        self.invalidation_ts = None
        self.exit_fill_price = None
        self.c1_idx = None
        self.short_entry_idx = None
        self.short_entry_price = None
        self.short_stop = None
        self.short_exit_idx = None
        self.short_exit_price = None
        self.reason = None
        self.excluded = False
        self.exclusion_reason = None

    def as_dict(self):
        return {k: getattr(self, k, None) for k in self.__dict__ if not k.startswith("_")}


def run_engine_v34(m15: pd.DataFrame, h1: pd.DataFrame, point: float = 0.01,
                   sample_traces: int = 5) -> dict:
    m15 = m15.sort_values("time_utc").reset_index(drop=True)
    h1 = h1.sort_values("time_utc").reset_index(drop=True)

    h1_close = h1.set_index("time_utc")["close"]
    h1_bullish = ((ema(h1_close, 20) > ema(h1_close, 50)) &
                  (h1_close > ema(h1_close, 50))).sort_index()

    atr = wilder_atr_m15(m15)
    bars = m15
    n = len(bars)
    times = pd.to_datetime(bars["time_utc"], utc=True)

    # missing-bar mask: gap > 22.5 min (non-weekend) or missing expected bar
    gaps = times.diff().dt.total_seconds()
    missing_bar = pd.Series(False, index=range(n))
    missing_bar.iloc[1:] = gaps.iloc[1:] > MAX_EXPECTED_GAP_M15.total_seconds()

    episodes = []
    counters = {c: 0 for c in REASON_CODES_V34}
    excluded_count = 0
    excl_reason_counts = {}

    i = LOOKBACK_M15
    while i < n - 1:
        t_sig = times.iloc[i]
        h1_prior = h1_bullish[h1_bullish.index <= t_sig]
        if len(h1_prior) == 0 or not h1_prior.iloc[-1]:
            i += 1
            continue

        prior = bars.iloc[i - LOOKBACK_M15:i]
        support = float(prior["low"].min())
        resistance = float(prior["high"].max())

        sig = bars.iloc[i]
        if not is_solid_body(sig) or sig["close"] <= resistance or sig["close"] <= sig["open"]:
            i += 1
            continue

        entry_idx = i + 1
        if entry_idx >= n:
            break
        ep = Episode(len(episodes))
        ep.entry_signal_idx = i
        ep.entry_fill_idx = entry_idx
        ep.entry_fill_ts = times.iloc[entry_idx]
        ep.support = support
        ep.resistance = resistance
        ep.entry_fill_price = fill_price(
            float(bars["open"].iloc[entry_idx]), float(bars["spread"].iloc[i]), point, "buy")

        max_span = pd.Timedelta(hours=3)
        if touches_maintenance_window(ep.entry_fill_ts, max_span):
            ep.reason = SESSION_EXCLUSION_LABEL
            ep.excluded = True
            ep.exclusion_reason = "entry_touches_observed_window"
            excluded_count += 1
            excl_reason_counts["entry_window"] = excl_reason_counts.get("entry_window", 0) + 1
            episodes.append(ep)
            i += 1
            continue

        if missing_bar.iloc[entry_idx]:
            ep.reason = MISSING_BAR_LABEL
            ep.excluded = True
            ep.exclusion_reason = "entry_bar_missing"
            excluded_count += 1
            excl_reason_counts["entry_bar_missing"] = excl_reason_counts.get("entry_bar_missing", 0) + 1
            episodes.append(ep)
            i += 1
            continue

        # ── OBSERVATION WINDOW: 20 CALENDAR DAYS from entry timestamp ──────
        window_end_ts = ep.entry_fill_ts + OBSERVATION_WINDOW

        inv_idx = None
        j = entry_idx + 1
        while j < n:
            # boundary: if this bar's time exceeds the 20-day window, stop scanning
            if times.iloc[j] > window_end_ts:
                break
            r = bars.iloc[j]
            if missing_bar.iloc[j]:
                # missing bar inside window: flag but continue (may still invalidate later)
                j += 1
                continue
            if is_solid_body(r) and r["close"] < support:
                inv_idx = j
                break
            j += 1

        if inv_idx is None:
            # No invalidation within 20 calendar days -> outside A-vs-B population
            ep.reason = NO_INVALIDATION_LABEL
            ep.excluded = True
            ep.exclusion_reason = "no_invalidation_within_20_calendar_days"
            excluded_count += 1
            excl_reason_counts["no_invalidation_20d"] = excl_reason_counts.get("no_invalidation_20d", 0) + 1
            episodes.append(ep)
            i += 1
            continue

        ep.invalidation_idx = inv_idx
        ep.invalidation_ts = times.iloc[inv_idx]

        # Policy A/B identical long exit at next bar open after invalidation
        exit_idx = inv_idx + 1
        if exit_idx >= n:
            ep.reason = "other_pre_registered"
            ep.excluded = True
            ep.exclusion_reason = "exit_bar_out_of_range"
            episodes.append(ep)
            break
        ep.exit_fill_price = fill_price(
            float(bars["open"].iloc[exit_idx]),
            float(bars["spread"].iloc[inv_idx]), point, "sell")

        # C1: immediately next completed solid-body close below invalidation-bar low
        c1_idx = inv_idx + 1
        c1_ok = False
        if c1_idx < n:
            c1 = bars.iloc[c1_idx]
            c1_ok = is_solid_body(c1) and c1["close"] < bars["low"].iloc[inv_idx]
        if not c1_ok:
            ep.reason = "no_c1"
            ep.excluded = False  # in denominator, flat
            counters["no_c1"] += 1
            episodes.append(ep)
            i += 1
            continue
        ep.c1_idx = c1_idx

        # Short entry at next bar open after C1
        short_idx = c1_idx + 1
        if short_idx >= n:
            ep.reason = "other_pre_registered"
            ep.excluded = True
            ep.exclusion_reason = "short_bar_out_of_range"
            episodes.append(ep)
            break
        if touches_maintenance_window(times.iloc[short_idx], max_span):
            ep.reason = "rollover_ineligible"
            ep.excluded = False  # in denominator, flat
            counters["rollover_ineligible"] += 1
            episodes.append(ep)
            i += 1
            continue
        if missing_bar.iloc[short_idx]:
            ep.reason = MISSING_BAR_LABEL
            ep.excluded = True
            ep.exclusion_reason = "short_entry_bar_missing"
            excluded_count += 1
            excl_reason_counts["short_entry_bar_missing"] = excl_reason_counts.get("short_entry_bar_missing", 0) + 1
            episodes.append(ep)
            i += 1
            continue

        inv_high = float(bars["high"].iloc[inv_idx])
        conf_high = float(bars["high"].iloc[c1_idx])
        atr_entry = float(atr[short_idx - 1])
        short_stop = max(inv_high, conf_high) + 0.5 * atr_entry
        ep.short_stop = short_stop

        ep.short_entry_idx = short_idx
        ep.short_entry_price = fill_price(
            float(bars["open"].iloc[short_idx]),
            float(bars["spread"].iloc[c1_idx]), point, "sell")

        # Short exit: stop / time-exit (12 bars) / forced pre-window — first
        short_exit_idx = None
        short_exit_price = None
        for k in range(1, TIME_EXIT_BARS + 1):
            idx = short_idx + k
            if idx >= n:
                break
            bar = bars.iloc[idx]
            if bar["low"] <= short_stop:
                short_exit_idx = idx
                short_exit_price = fill_price(
                    min(float(bar["open"]), short_stop),
                    float(bars["spread"].iloc[idx - 1]), point, "cover")
                break
            if touches_maintenance_window(times.iloc[idx], pd.Timedelta(minutes=0)):
                short_exit_idx = idx
                short_exit_price = fill_price(
                    float(bar["close"]), float(bars["spread"].iloc[idx - 1]), point, "cover")
                break
        if short_exit_idx is None:
            idx = short_idx + TIME_EXIT_BARS
            if idx < n:
                short_exit_idx = idx
                short_exit_price = fill_price(
                    float(bars["close"].iloc[idx]),
                    float(bars["spread"].iloc[idx - 1]), point, "cover")
        if short_exit_idx is not None:
            ep.short_exit_idx = short_exit_idx
            ep.short_exit_price = short_exit_price
            ep.reason = "c1_triggered"
            counters["c1_triggered"] += 1
        else:
            ep.reason = "other_pre_registered"
            ep.excluded = True
            ep.exclusion_reason = "no_exit_within_range"

        if len(episodes) <= sample_traces:
            ep.traces = [
                {"i": i, "sig_close": float(sig["close"]), "resistance": resistance},
                {"inv": inv_idx, "inv_low": float(bars["low"].iloc[inv_idx]), "support": support},
                {"c1": c1_idx, "c1_close": float(bars["close"].iloc[c1_idx])},
                {"short_entry": short_idx, "stop": float(short_stop), "atr_pre_entry": float(atr_entry)},
            ]
        episodes.append(ep)
        i += 1

    return {
        "episodes": episodes,
        "counters": counters,
        "excluded_count": excluded_count,
        "exclusion_reason_counts": excl_reason_counts,
        "total_episodes": len(episodes),
    }