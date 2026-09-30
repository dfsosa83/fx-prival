#!/usr/bin/env python
"""Gap characterization for the conservative exclusion rule (Phase 1B)."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
PROC = BASE / "data/processed"

m15 = pd.read_parquet(PROC / "XAUUSD_M15_processed.parquet")
m15 = m15.sort_values("time_utc").reset_index(drop=True)

gaps = m15["time_utc"].diff().dropna()
gap_df = pd.DataFrame({"gap_s": gaps.dt.total_seconds(), "to_utc": m15["time_utc"][1:].values})
gap_df["from_utc"] = pd.to_datetime(gap_df["to_utc"], utc=True) - pd.to_timedelta(gap_df["gap_s"], unit="s")

# Classify
# expected M15 interval = 15 min. Weekend = spans Sat 00:00 UTC. Daily window = 1.25h.
daily = gap_df[(gap_df["gap_s"] > 22.5*60) & (gap_df["gap_s"] < 2*3600)]
weekend = gap_df[gap_df["gap_s"] >= 2*3600]

print(f"Total gaps > 22.5min: {len(gap_df[gap_df['gap_s'] > 22.5*60])}")
print(f"  daily-window range (22.5min-2h): {len(daily)}")
print(f"  long gaps >= 2h: {len(weekend)}")

# Daily window distribution (hour of day UTC of gap start)
if len(daily):
    start_utc = pd.to_datetime(daily["from_utc"], utc=True)
    hrs = start_utc.dt.hour.value_counts().sort_index()
    print("\n=== Daily maintenance gap start hour (UTC) ===")
    print(hrs.to_string())

# Long gaps by duration bucket
if len(weekend):
    hbins = (weekend["gap_s"]/3600).value_counts(bins=[2, 10, 20, 30, 40, 50, 70, 100]).sort_index()
    print("\n=== Long gap duration buckets (hours) ===")
    print(hbins.to_string())

# Identify the maintenance window precisely from gap start-hour
mode_hour = start_utc.dt.hour.mode().iloc[0] if len(daily) else None
mode_min = start_utc.dt.minute.mode().iloc[0] if len(daily) else None
print(f"\nModal maintenance gap start: {mode_hour:02d}:{mode_min:02d} UTC (from {len(daily)} daily gaps)")

(BASE / "GAP_ANALYSIS.json").write_text(json.dumps({
    "total_gaps_over_22min": int(len(gap_df[gap_df["gap_s"] > 22.5*60])),
    "daily_window_count": int(len(daily)),
    "weekend_long_gap_count": int(len(weekend)),
    "modal_maintenance_start_utc": f"{mode_hour:02d}:{mode_min:02d}" if mode_hour is not None else None,
}, indent=2), encoding="utf-8")