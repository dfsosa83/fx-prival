"""
EXP-2026-05-INVALIDATION-REVERSAL — isolated research engine (Phase 1B).

Implements the frozen v3.3 rules EXACTLY. No performance scoring, no
trading decisions. Produces episode ledgers + rule traces only.

Engine outputs (per run):
  - episodes: list of Episode records (ledger)
  - traces:  rule-trace samples for manual audit
  - counters: reason-code and exclusion counts
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ── Constants (frozen v3.3) ────────────────────────────────────────────────
LOOKBACK_M15 = 20
SOLID_BODY_MIN_FRACTION = 0.30
ATR_N = 14
TIME_EXIT_BARS = 12
BASE_SLIPPAGE_MULT = 0.5
MAINT_START_UTC = pd.Timestamp("22:30", tz="UTC")      # conservative window
MAINT_END_UTC = pd.Timestamp("02:00", tz="UTC") + pd.Timedelta(days=1)  # 02:00 next day
MAX_EXPECTED_GAP_M15 = pd.Timedelta(minutes=22.5)
REASON_CODES = ["c1_triggered", "no_c1", "rollover_ineligible",
                "holiday_early_close", "missing_bar", "other_pre_registered"]
SESSION_EXCLUSION_LABEL = "conservative_observed_window_exclusion_not_broker_confirmed"


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def wilder_atr_m15(df: pd.DataFrame) -> np.ndarray:
    """Continuous Wilder ATR(14) series (v3.3)."""
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


def fill_price(mid: float, spread_points: float, point: float, side: str,
               slippage_mult: float = BASE_SLIPPAGE_MULT) -> float:
    """v3.3 fill: buy/cover = P + S/2 + L; sell/short = P - S/2 - L; L=0.5*S.
    S = spread_points * point (price units)."""
    s = spread_points * point
    l = slippage_mult * s
    return mid + s / 2 + l if side in ("buy", "cover") else mid - s / 2 - l


def is_solid_body(row) -> bool:
    rng = row["high"] - row["low"]
    if rng <= 0:
        return False
    return abs(row["close"] - row["open"]) / rng >= SOLID_BODY_MIN_FRACTION


def touches_maintenance_window(ts: pd.Timestamp, max_span: pd.Timedelta) -> bool:
    """True if [ts, ts+max_span] intersects 22:30-02:00 UTC."""
    # normalize: window is 22:30 today -> 02:00 tomorrow
    day = ts.normalize()
    w_start = day + pd.Timedelta(hours=22, minutes=30)
    w_end = day + pd.Timedelta(days=1, hours=2)
    return ts < w_end and (ts + max_span) > w_start


class Episode:
    __slots__ = ("idx", "entry_signal_idx", "entry_fill_idx", "entry_fill_price",
                 "support", "resistance", "h1_bullish_at_entry", "invalidation_idx",
                 "exit_fill_price", "c1_idx", "short_entry_idx", "short_entry_price",
                 "short_stop", "short_exit_idx", "short_exit_price", "reason",
                 "excluded", "exclusion_reason", "traces")

    def __init__(self, idx):
        self.idx = idx
        self.traces = []
        self.entry_signal_idx = None
        self.entry_fill_idx = None
        self.entry_fill_price = None
        self.support = None
        self.resistance = None
        self.h1_bullish_at_entry = None
        self.invalidation_idx = None
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
        return {k: getattr(self, k, None) for k in self.__slots__ if not k.startswith("_")}


def run_engine(m15: pd.DataFrame, h1: pd.DataFrame, point: float = 0.01,
               sample_traces: int = 5) -> dict:
    """Run the frozen v3.3 episode state machine.

    m15: DataFrame with time_utc, open, high, low, close, spread (points)
    h1:  DataFrame with time_utc, open, high, low, close
    """
    m15 = m15.sort_values("time_utc").reset_index(drop=True)
    h1 = h1.sort_values("time_utc").reset_index(drop=True)

    # H1 bias series (completed H1 only)
    h1_close = h1.set_index("time_utc")["close"]
    h1_ema20 = ema(h1_close, 20)
    h1_ema50 = ema(h1_close, 50)
    h1_bullish = (h1_ema20 > h1_ema50) & (h1_close > h1_ema50)
    h1_bullish.index = pd.to_datetime(h1_bullish.index, utc=True)
    h1_bullish_sorted = h1_bullish.sort_index()

    atr = wilder_atr_m15(m15)
    bars = m15
    n = len(bars)
    times = pd.to_datetime(bars["time_utc"], utc=True)

    # Missing-bar mask: gap > 22.5 min (non-weekend) or missing expected bar
    gaps = times.diff().dt.total_seconds()
    missing_bar = pd.Series(False, index=range(n))
    missing_bar.iloc[1:] = gaps.iloc[1:] > MAX_EXPECTED_GAP_M15.total_seconds()

    episodes = []
    counters = {c: 0 for c in REASON_CODES}
    excluded_count = 0
    excl_reason_counts = {}

    i = LOOKBACK_M15  # need 20 prior completed bars
    while i < n - 1:  # need at least entry + next bar
        # H1 bullish at entry signal bar time (nearest completed H1 <= bar time)
        t_sig = times.iloc[i]
        h1_prior = h1_bullish_sorted[h1_bullish_sorted.index <= t_sig]
        if len(h1_prior) == 0 or not h1_prior.iloc[-1]:
            i += 1
            continue

        # support/resistance from preceding 20 completed bars (excl signal bar)
        prior = bars.iloc[i - LOOKBACK_M15:i]
        support = prior["low"].min()
        resistance = prior["high"].max()

        # long signal: bullish solid-body close above frozen resistance
        sig = bars.iloc[i]
        if not is_solid_body(sig) or sig["close"] <= resistance:
            i += 1
            continue
        if sig["close"] <= sig["open"]:  # must be bullish body
            i += 1
            continue

        # Long entry at next bar open with adverse cost
        entry_idx = i + 1
        if entry_idx >= n:
            break
        ep = Episode(len(episodes))
        ep.entry_signal_idx = i
        ep.entry_fill_idx = entry_idx
        ep.support = float(support)
        ep.resistance = float(resistance)
        ep.h1_bullish_at_entry = True
        spread_sig = float(bars["spread"].iloc[i])
        ep.entry_fill_price = fill_price(
            float(bars["open"].iloc[entry_idx]), spread_sig, point, "buy")

        # Conservative session exclusion: entry touches 22:30-02:00 window
        max_span = pd.Timedelta(hours=3)  # 12 M15 bars
        if touches_maintenance_window(times.iloc[entry_idx], max_span):
            ep.reason = SESSION_EXCLUSION_LABEL
            ep.excluded = True
            ep.exclusion_reason = "entry_touches_observed_window"
            excluded_count += 1
            excl_reason_counts["entry_window"] = excl_reason_counts.get("entry_window", 0) + 1
            episodes.append(ep)
            i += 1
            continue

        # scan forward for invalidation: later solid-body close below frozen support
        inv_idx = None
        j = entry_idx + 1
        while j < n:
            r = bars.iloc[j]
            if is_solid_body(r) and r["close"] < support:
                inv_idx = j
                break
            j += 1
            if j - entry_idx > 500:  # safety cap (no future info; just loop guard)
                break
        if inv_idx is None:
            # no invalidation within scan: episode ends (no A/B action)
            ep.reason = "other_pre_registered"
            ep.excluded = True
            ep.exclusion_reason = "no_invalidation_in_scan_window"
            episodes.append(ep)
            i += 1
            continue
        ep.invalidation_idx = inv_idx

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
            ep.excluded = False  # remains in denominator, flat
            counters["no_c1"] += 1
            episodes.append(ep)
            i += 1
            continue
        ep.c1_idx = c1_idx

        # Short entry at next bar open after C1 (eligible if window-not-touched)
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

        # Short stop = max(high_inv, high_conf) + 0.5 * Wilder_ATR(14) at close before entry
        inv_high = float(bars["high"].iloc[inv_idx])
        conf_high = float(bars["high"].iloc[c1_idx])
        atr_entry = float(atr[short_idx - 1])  # value at close of short_idx-1
        short_stop = max(inv_high, conf_high) + 0.5 * atr_entry
        ep.short_stop = short_stop

        ep.short_entry_idx = short_idx
        ep.short_entry_price = fill_price(
            float(bars["open"].iloc[short_idx]),
            float(bars["spread"].iloc[c1_idx]), point, "sell")

        # Short exit: stop / time-exit (12 bars) / forced pre-window — whichever first
        short_exit_idx = None
        short_exit_price = None
        for k in range(1, TIME_EXIT_BARS + 1):
            idx = short_idx + k
            if idx >= n:
                break
            bar = bars.iloc[idx]
            # gap beyond stop -> adverse open
            if bar["low"] <= short_stop:
                # intrabar stop: execute at adverse stop price
                short_exit_idx = idx
                short_exit_price = fill_price(
                    min(float(bar["open"]), short_stop),  # adverse for short
                    float(bars["spread"].iloc[idx - 1]), point, "cover")
                break
            # forced pre-maintenance exit
            if touches_maintenance_window(times.iloc[idx], pd.Timedelta(minutes=0)):
                short_exit_idx = idx
                short_exit_price = fill_price(
                    float(bar["close"]), float(bars["spread"].iloc[idx - 1]), point, "cover")
                break
        if short_exit_idx is None:
            # time exit at bar short_idx + TIME_EXIT_BARS
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

        # rule trace (a few samples)
        if len(episodes) <= sample_traces:
            ep.traces = [
                {"i": i, "sig_close": float(sig["close"]), "resistance": float(resistance)},
                {"inv": inv_idx, "inv_low": float(bars["low"].iloc[inv_idx]), "support": float(support)},
                {"c1": c1_idx, "c1_close": float(bars["close"].iloc[c1_idx])},
                {"short_entry": short_idx, "stop": float(short_stop),
                 "atr_pre_entry": float(atr_entry)},
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