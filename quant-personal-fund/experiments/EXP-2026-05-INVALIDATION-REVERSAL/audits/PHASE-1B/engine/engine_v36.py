"""
EXP-2026-05 — v3.6 engine variant (short-stop bug fix).

Changes vs v3.5 (ONLY the short-stop condition for shorts):
  v3.5 (BUG):  if bar["low"] <= short_stop:
  v3.6 (FIX):  if bar["high"] >= short_stop:

Gap handling (frozen per authorization):
  - If the bar OPENS at or above the short stop (open >= stop), model the
    stop exit at the ADVERSE OPEN (fill at the open with cover cost).
  - Otherwise, if the bar's high reaches/exceeds the stop, model the stop
    exit AT THE STOP PRICE, with frozen adverse costs.
  - Cost convention applied exactly once per fill.

Preserved exactly from v3.5: stop level, next-bar execution, time exit,
forced-session exit, cost model, episode definitions, sample, reason codes.
NO performance scoring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LOOKBACK_M15 = 20
SOLID_BODY_MIN_FRACTION = 0.30
ATR_N = 14
TIME_EXIT_BARS = 12
BASE_SLIPPAGE_MULT = 0.5
OBSERVATION_WINDOW = pd.Timedelta(days=20)
MAINT_START_UTC = pd.Timestamp("22:30", tz="UTC")
MAINT_END_UTC = pd.Timestamp("02:00", tz="UTC") + pd.Timedelta(days=1)
MAX_EXPECTED_GAP_M15 = pd.Timedelta(minutes=22.5)
SESSION_EXCLUSION_LABEL = "conservative_observed_window_exclusion_not_broker_confirmed"
NO_INVALIDATION_LABEL = "no_invalidation_within_observation_window"
RIGHT_CENSORED_LABEL = "right_censored_at_data_end"
MISSING_BAR_LABEL = "missing_bar"

DEV_START = pd.Timestamp("2020-02-28", tz="UTC")
DEV_END = pd.Timestamp("2023-12-31", tz="UTC")

REASON_CODES_V35 = [
    "c1_triggered",
    "no_c1",
    "rollover_ineligible",
    SESSION_EXCLUSION_LABEL,
    MISSING_BAR_LABEL,
    NO_INVALIDATION_LABEL,
    RIGHT_CENSORED_LABEL,
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


def time_block_id(ts: pd.Timestamp) -> str:
    """Deterministic 24-M15-bar (6h) block: anchor at Unix epoch UTC."""
    return str(int(ts.timestamp()) // (6 * 3600))


class EpisodeV36:
    def __init__(self, idx):
        self.idx = idx
        self.traces = []
        self.entry_signal_idx = None
        self.entry_fill_idx = None
        self.entry_time = None
        self.entry_fill_price = None
        self.support = None
        self.resistance = None
        self.invalidation_idx = None
        self.invalidation_time = None
        self.exit_fill_price = None
        self.c1_idx = None
        self.c1_time = None
        self.short_entry_idx = None
        self.short_entry_price = None
        self.short_stop = None
        self.short_exit_idx = None
        self.short_exit_price = None
        self.reason = None
        self.excluded = False
        self.observation_complete = None
        self.shared_invalidation_cluster_id = None
        self.time_block = None
        self.assignment_window = None

    def as_dict(self):
        return {k: getattr(self, k, None) for k in self.__dict__ if not k.startswith("_")}


def run_engine_v36(m15: pd.DataFrame, h1: pd.DataFrame, point: float = 0.01,
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
    last_available = times.iloc[-1]

    gaps = times.diff().dt.total_seconds()
    missing_bar = pd.Series(False, index=range(n))
    missing_bar.iloc[1:] = gaps.iloc[1:] > MAX_EXPECTED_GAP_M15.total_seconds()

    episodes = []
    counters = {c: 0 for c in REASON_CODES_V35}

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
        ep = EpisodeV36(len(episodes))
        ep.entry_signal_idx = i
        ep.entry_fill_idx = entry_idx
        ep.entry_time = times.iloc[entry_idx]
        ep.support = support
        ep.resistance = resistance
        ep.entry_fill_price = fill_price(
            float(bars["open"].iloc[entry_idx]), float(bars["spread"].iloc[i]), point, "buy")
        ep.time_block = time_block_id(ep.entry_time)
        ep.assignment_window = ("development" if DEV_START <= ep.entry_time <= DEV_END
                                else "research_grade_oos")

        max_span = pd.Timedelta(hours=3)

        # ── RIGHT-CENSOR CHECK (before any other classification) ──────────
        window_end_needed = ep.entry_time + OBSERVATION_WINDOW
        if window_end_needed > last_available:
            ep.reason = RIGHT_CENSORED_LABEL
            ep.excluded = True
            ep.observation_complete = False
            counters[RIGHT_CENSORED_LABEL] += 1
            episodes.append(ep)
            i += 1
            continue

        if touches_maintenance_window(ep.entry_time, max_span):
            ep.reason = SESSION_EXCLUSION_LABEL
            ep.excluded = True
            ep.observation_complete = True
            counters[SESSION_EXCLUSION_LABEL] += 1
            episodes.append(ep)
            i += 1
            continue

        if missing_bar.iloc[entry_idx]:
            ep.reason = MISSING_BAR_LABEL
            ep.excluded = True
            ep.observation_complete = True
            counters[MISSING_BAR_LABEL] += 1
            episodes.append(ep)
            i += 1
            continue

        # ── OBSERVATION: 20 calendar days (full history available) ────────
        window_end_ts = ep.entry_time + OBSERVATION_WINDOW
        inv_idx = None
        j = entry_idx + 1
        while j < n:
            if times.iloc[j] > window_end_ts:
                break
            r = bars.iloc[j]
            if missing_bar.iloc[j]:
                j += 1
                continue
            if is_solid_body(r) and r["close"] < support:
                inv_idx = j
                break
            j += 1

        if inv_idx is None:
            ep.reason = NO_INVALIDATION_LABEL
            ep.excluded = True
            ep.observation_complete = True
            counters[NO_INVALIDATION_LABEL] += 1
            episodes.append(ep)
            i += 1
            continue

        ep.invalidation_idx = inv_idx
        ep.invalidation_time = times.iloc[inv_idx]
        ep.observation_complete = True

        exit_idx = inv_idx + 1
        if exit_idx >= n:
            # Cannot happen for a fully-observed window (exit bar is within window)
            ep.reason = RIGHT_CENSORED_LABEL
            ep.excluded = True
            counters[RIGHT_CENSORED_LABEL] += 1
            episodes.append(ep)
            break
        ep.exit_fill_price = fill_price(
            float(bars["open"].iloc[exit_idx]),
            float(bars["spread"].iloc[inv_idx]), point, "sell")

        c1_idx = inv_idx + 1
        c1_ok = False
        if c1_idx < n:
            c1 = bars.iloc[c1_idx]
            c1_ok = is_solid_body(c1) and c1["close"] < bars["low"].iloc[inv_idx]
        if not c1_ok:
            ep.reason = "no_c1"
            ep.excluded = False
            counters["no_c1"] += 1
            episodes.append(ep)
            i += 1
            continue
        ep.c1_idx = c1_idx
        ep.c1_time = times.iloc[c1_idx]

        short_idx = c1_idx + 1
        if short_idx >= n:
            ep.reason = RIGHT_CENSORED_LABEL
            ep.excluded = True
            counters[RIGHT_CENSORED_LABEL] += 1
            episodes.append(ep)
            break
        if touches_maintenance_window(times.iloc[short_idx], max_span):
            ep.reason = "rollover_ineligible"
            ep.excluded = False
            counters["rollover_ineligible"] += 1
            episodes.append(ep)
            i += 1
            continue
        if missing_bar.iloc[short_idx]:
            ep.reason = MISSING_BAR_LABEL
            ep.excluded = True
            counters[MISSING_BAR_LABEL] += 1
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

        short_exit_idx = None
        short_exit_price = None
        for k in range(1, TIME_EXIT_BARS + 1):
            idx = short_idx + k
            if idx >= n:
                break
            bar = bars.iloc[idx]
            # v3.6 FIX: for a SHORT, the stop is ABOVE entry; the short is
            # stopped when price RISES to the stop (high >= stop).
            #   v3.5 BUG was: bar["low"] <= short_stop  (fires on nearly every bar)
            if bar["high"] >= short_stop:
                short_exit_idx = idx
                if float(bar["open"]) >= short_stop:
                    # Gap handling: bar OPENS at/above the stop -> exit at the
                    # ADVERSE OPEN (cover fill at open).
                    short_exit_price = fill_price(
                        float(bar["open"]),
                        float(bars["spread"].iloc[idx - 1]), point, "cover")
                else:
                    # Otherwise: exit AT THE STOP PRICE with frozen adverse cost.
                    short_exit_price = fill_price(
                        float(short_stop),
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
            # cannot occur for a fully-observed window (12 bars within 20 days)
            ep.reason = RIGHT_CENSORED_LABEL
            ep.excluded = True
            counters[RIGHT_CENSORED_LABEL] += 1

        if len(episodes) <= sample_traces:
            ep.traces = [
                {"i": i, "sig_close": float(sig["close"]), "resistance": resistance},
                {"inv": inv_idx, "inv_low": float(bars["low"].iloc[inv_idx]), "support": support},
                {"c1": c1_idx, "c1_close": float(bars["close"].iloc[c1_idx])},
                {"short_entry": short_idx, "stop": float(short_stop), "atr_pre_entry": float(atr_entry)},
            ]
        episodes.append(ep)
        i += 1

    # ── Dependence metadata: shared invalidation cluster id ────────────────
    inv_map = {}
    for ep in episodes:
        if ep.invalidation_time is not None:
            key = str(ep.invalidation_time)
            if key not in inv_map:
                inv_map[key] = len(inv_map)
            ep.shared_invalidation_cluster_id = inv_map[key]

    return {
        "episodes": episodes,
        "counters": counters,
        "total_episodes": len(episodes),
        "last_available_bar_time": str(last_available),
    }