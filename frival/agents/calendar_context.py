"""
Macro context builder for Agent B (Perplexity fundamental).

Builds a structured text summary of economic calendar events
for a given bar, replacing or augmenting web search.
"""

from typing import Optional
import pandas as pd
import numpy as np

from data.calendar import load_calendar


CB_KEYWORDS = {
    "FOMC Decision": ["FOMC", "Fed Interest Rate", "Federal Open Market", "Fed Funds"],
    "ECB Decision": ["ECB Interest Rate", "European Central Bank", "Main Refinancing"],
    "BoE Decision": ["BoE Interest Rate", "Bank of England", "MPC", "Official Bank Rate"],
    "SNB Decision": ["SNB Interest Rate", "Swiss National Bank", "Libor Target"],
    "NFP Day": ["Nonfarm Payrolls", "NFP Change"],
}


def build_macro_context(
    bar_dt: pd.Timestamp,
    pair: str,
    calendar: Optional[pd.DataFrame] = None,
) -> str:
    """
    Build a macro context string for a given H1 bar and pair.

    Returns formatted text with:
    - Recent events (last 24h): Actual vs Consensus
    - Upcoming events (next 24h)
    - Central bank day flags
    - Event density metrics

    Parameters
    ----------
    bar_dt : pd.Timestamp
        The bar datetime to build context for.
    pair : str
        Trading pair (EURUSD, GBPUSD, etc.)
    calendar : pd.DataFrame, optional
        Pre-loaded calendar from load_calendar().

    Returns
    -------
    str — formatted macro summary for Agent B prompt injection.
    """
    if calendar is None:
        calendar = load_calendar(pair)

    event_times = calendar["event_dt"].values
    bar_ts = bar_dt.to_datetime64()

    # ── Last 24h: events in (bar - 24h, bar] ───────────────────────────
    past_start = bar_ts - np.timedelta64(24, "h")
    past_mask = (event_times > past_start) & (event_times <= bar_ts)
    past_events = calendar[past_mask].copy()

    # ── Next 24h: events in (bar, bar + 24h] ───────────────────────────
    future_end = bar_ts + np.timedelta64(24, "h")
    future_mask = (event_times > bar_ts) & (event_times <= future_end)
    future_events = calendar[future_mask].copy()

    # ── CB day flags ────────────────────────────────────────────────────
    bar_date = bar_dt.date()
    flags = []
    for flag_name, keywords in CB_KEYWORDS.items():
        flag_mask = np.zeros(len(calendar), dtype=bool)
        for kw in keywords:
            flag_mask |= calendar["Name"].str.contains(kw, case=False, na=False).values
        flag_dates = calendar.loc[flag_mask, "Date"].dt.date.values
        if bar_date in flag_dates:
            flags.append(flag_name)

    # ── Build the summary ───────────────────────────────────────────────
    lines = [
        f"=== Macro Calendar Context ({bar_dt.strftime('%Y-%m-%d %H:%M')} UTC) ===",
        "",
    ]

    # Recent events
    high_med_past = past_events[past_events["is_medium"]]
    if len(high_med_past) > 0:
        lines.append(f"Last 24 hours ({len(high_med_past)} HIGH/MEDIUM events):")
        for _, ev in high_med_past.head(10).iterrows():
            name = ev["Name"][:60]
            curr = ev.get("Currency", "?")
            dev = ev.get("Deviation")
            actual = ev.get("Actual", "-")
            consensus = ev.get("Consensus", "-")
            if pd.notna(dev) and dev != 0:
                direction = "beat" if dev > 0 else "MISS"
                lines.append(
                    f"  - {curr} {name}: actual {actual} vs consensus {consensus} "
                    f"({dev:+.2f} {direction})"
                )
            else:
                lines.append(f"  - {curr} {name}")
    else:
        lines.append("Last 24 hours: no HIGH/MEDIUM events recorded.")

    lines.append("")

    # Upcoming events
    high_med_future = future_events[future_events["is_medium"]]
    if len(high_med_future) > 0:
        lines.append(f"Upcoming — next 4 hours:")
        next4 = future_events[
            (event_times[future_events.index] > bar_ts)
            & (event_times[future_events.index] <= bar_ts + np.timedelta64(4, "h"))
        ]
        if len(next4) > 0:
            for _, ev in next4.iterrows():
                et = ev["event_dt"]
                lines.append(f"  - {et.strftime('%H:%M')} UTC: {ev['Currency']} {ev['Name'][:50]} ({ev['Impact']})")
        else:
            lines.append("  None.")

        lines.append(f"")
        lines.append(f"Upcoming — next 24 hours: {len(high_med_future)} HIGH/MEDIUM events")
    else:
        lines.append("Upcoming 24 hours: no scheduled HIGH/MEDIUM events.")

    # Flags
    if flags:
        lines.append(f"")
        lines.append(f"Today's flags: {', '.join(flags)}")
    else:
        lines.append(f"")
        lines.append("Today: no central bank decision or NFP day.")

    # Event density
    lines.append(f"Event density: {len(past_events)} recent / {len(future_events)} upcoming")

    return "\n".join(lines)


def get_next_high_event(
    bar_dt: pd.Timestamp,
    pair: str,
    window_minutes: int = 60,
) -> tuple:
    """
    Check if a HIGH-impact economic event is scheduled within window_minutes
    of bar_dt for currencies relevant to the given pair.

    Returns (event_name, minutes_to_event) or (None, None) if no HIGH event.
    event_name is the RAW calendar Name (e.g. "Consumer Price Index (YoY) (Dec) PREL");
    normalisation to the dataset convention happens in macro_event_responder.

    NOTE: bar_dt and calendar["event_dt"] must share the same timezone. The calendar
    files are broker-time (no TZ marker) — the P0 timezone verification is still open.
    """
    try:
        calendar = load_calendar(pair)
    except Exception:
        return None, None

    if calendar is None or len(calendar) == 0:
        return None, None

    window_end = bar_dt + pd.Timedelta(minutes=window_minutes)
    future = calendar[
        (calendar["event_dt"] >= bar_dt) & (calendar["event_dt"] <= window_end)
    ]
    high = future[future["Impact"] == "HIGH"]
    if len(high) == 0:
        return None, None

    nearest = high.iloc[0]
    event_name = str(nearest["Name"])
    minutes_to = int((nearest["event_dt"] - bar_dt).total_seconds() / 60)
    return event_name, minutes_to