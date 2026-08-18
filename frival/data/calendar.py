"""
Economic calendar loader and feature builder.

Loads 20-year event calendar (2007-2026), filters by pair currencies,
and builds per-bar features: event counts, deviation surprises, flags.

CRITICAL: No lookahead — forward features use scheduled events only
(Date+Time known in advance). Backward features use only published events.
"""

from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import numpy as np


CALENDAR_DIR = (
    Path(__file__).resolve().parents[2]
    / "ml-signal-service" / "data" / "raw" / "macro"
)

PAIR_CURRENCIES = {
    "EURUSD": ["EUR", "USD"],
    "GBPUSD": ["GBP", "USD"],
    "USDCHF": ["USD", "CHF"],
    "USDJPY": ["USD", "JPY"],
    "XAUUSD": ["USD"],         # gold is USD-denominated → USD events only
    "USDCAD": ["USD", "CAD"],
}

DEV_WINDOW_HOURS = 24
EVENT_WINDOWS = [1, 4, 24]


def load_calendar(pair: str) -> pd.DataFrame:
    """
    Load all calendar data for a given pair's relevant currencies.

    Loads all yearly CSVs (2007-2026), concatenates, parses Date+Time
    into a datetime column, and filters to events for the pair's currencies.

    Returns a DataFrame indexed by event datetime, sorted chronologically.
    """
    currencies = PAIR_CURRENCIES.get(pair.upper())
    if currencies is None:
        raise ValueError(f"Unknown pair: {pair}. Supported: {list(PAIR_CURRENCIES)}")

    files = sorted(CALENDAR_DIR.glob("EconomicCalendarEvents-*.csv"))
    if not files:
        raise FileNotFoundError(f"No calendar files found in {CALENDAR_DIR}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        # Filter to pair's currencies only
        df = df[df["Currency"].isin(currencies)]
        dfs.append(df)

    calendar = pd.concat(dfs, ignore_index=True)

    # Parse datetime
    calendar["Date"] = pd.to_datetime(calendar["Date"])
    calendar["Time"] = calendar["Time"].replace("N/A", "00:00")
    calendar["event_dt"] = pd.to_datetime(
        calendar["Date"].dt.strftime("%Y-%m-%d") + " " + calendar["Time"],
        format="%Y-%m-%d %H:%M",
        errors="coerce",
    )
    calendar.dropna(subset=["event_dt"], inplace=True)
    calendar.sort_values("event_dt", inplace=True)
    calendar.reset_index(drop=True, inplace=True)

    # Parse numeric Deviation
    calendar["Deviation"] = pd.to_numeric(calendar["Deviation"], errors="coerce")

    # Impact weight for scoring
    impact_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
    calendar["impact_weight"] = calendar["Impact"].map(impact_map).fillna(0)

    # Binary impact flags
    calendar["is_high"] = calendar["Impact"] == "HIGH"
    calendar["is_medium"] = calendar["Impact"].isin(["HIGH", "MEDIUM"])

    print(f"[calendar] Loaded {len(calendar):,} events for {pair} "
          f"({calendar['event_dt'].min().date()} -> {calendar['event_dt'].max().date()})")
    print(f"  HIGH: {calendar['is_high'].sum():,}  MED+: {calendar['is_medium'].sum():,}  "
          f"Dev loaded: {calendar['Deviation'].notna().sum():,}")

    return calendar


def compute_calendar_features(
    bar_datetimes: pd.DatetimeIndex,
    pair: str,
    calendar: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    if calendar is None:
        calendar = load_calendar(pair)

    event_times = calendar["event_dt"].values
    n_bars = len(bar_datetimes)
    bar_ts = bar_datetimes.values
    bar_ts_sorted = np.sort(bar_ts)

    result = pd.DataFrame(index=bar_datetimes)

    # ── Forward event counts (vectorized with searchsorted) ─────────────
    for w in EVENT_WINDOWS:
        delta = np.timedelta64(w, "h")
        # For each bar, count events with event_time in (bar, bar+delta]
        counts = np.searchsorted(event_times, bar_ts_sorted + delta, side="right") - \
                 np.searchsorted(event_times, bar_ts_sorted, side="right")
        result[f"high_events_next_{w}h"] = _map_back(counts, bar_ts, bar_ts_sorted)
        result[f"med_events_next_{w}h"] = _map_back(counts, bar_ts, bar_ts_sorted)
    result["any_event_next_1h"] = result["med_events_next_1h"] > 0

    # ── Backward deviation sum (vectorized) ─────────────────────────────
    dev = calendar["Deviation"].fillna(0).values
    weight = calendar["impact_weight"].values
    weighted_dev = dev * weight

    dev_sum = np.zeros(n_bars, dtype=float)
    for i in range(n_bars):
        start = np.searchsorted(event_times, bar_ts[i] - np.timedelta64(DEV_WINDOW_HOURS, "h"))
        end = np.searchsorted(event_times, bar_ts[i], side="right")
        dev_sum[i] = weighted_dev[start:end].sum()
    result[f"deviation_sum_{DEV_WINDOW_HOURS}h"] = dev_sum

    # ── Hours since last HIGH event ─────────────────────────────────────
    high_idx = np.where(calendar["is_high"].values)[0]
    high_times = event_times[high_idx]
    hours_since = np.full(n_bars, 999.0, dtype=float)
    if len(high_times) > 0:
        # For each bar, find the last HIGH event before it
        for i in range(n_bars):
            idx = np.searchsorted(high_times, bar_ts[i], side="right") - 1
            if idx >= 0:
                diff_ns = bar_ts[i].astype("datetime64[ns]").astype(np.int64) - \
                          high_times[idx].astype("datetime64[ns]").astype(np.int64)
                hours_since[i] = diff_ns / 3.6e12
    result["hours_since_last_high"] = hours_since

    # ── Flags (vectorized) ──────────────────────────────────────────────
    cb_keywords = {
        "is_fomc_day": ["FOMC", "Fed Interest Rate", "Federal Open Market"],
        "is_ecb_day": ["ECB Interest Rate", "European Central Bank", "Main Refinancing"],
        "is_boe_day": ["BoE Interest Rate", "Bank of England", "MPC", "Official Bank Rate"],
        "is_snb_day": ["SNB Interest Rate", "Swiss National Bank", "Libor Target"],
        "is_nfp_day": ["Nonfarm Payrolls", "NFP Change"],
    }

    for flag_name, keywords in cb_keywords.items():
        mask = np.zeros(len(calendar), dtype=bool)
        for kw in keywords:
            mask |= calendar["Name"].str.contains(kw, case=False, na=False).values
        flag_dates = set(calendar.loc[mask, "Date"].dt.date)
        bar_dates = pd.DatetimeIndex(bar_ts).date
        result[flag_name] = [d in flag_dates for d in bar_dates]

    return result


def _map_back(values: np.ndarray, bar_ts: np.ndarray, sorted_ts: np.ndarray) -> np.ndarray:
    """Map sorted values back to original bar order."""
    idx = np.searchsorted(sorted_ts, bar_ts)
    return values[idx]