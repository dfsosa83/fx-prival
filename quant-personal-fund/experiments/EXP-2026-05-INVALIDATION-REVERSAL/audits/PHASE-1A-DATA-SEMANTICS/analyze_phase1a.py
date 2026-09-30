#!/usr/bin/env python
"""Phase 1A analysis: timezone alignment, rollover gaps, calendar evidence."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
OUT = Path(__file__).resolve().parent

SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD"]
results = {}

for sym in SYMBOLS:
    df = pd.read_csv(OUT / f"bars_{sym}.csv", parse_dates=["time_utc"]).sort_values("time_utc")
    mins = df["time_utc"].dt.minute
    aligned = float(mins.isin([0, 15, 30, 45]).mean())

    df["gap_s"] = df["time_utc"].diff().dt.total_seconds()
    big = df[df["gap_s"] > 22.5 * 60].copy()  # >22.5 min
    gaps = []
    for _, r in big.iterrows():
        prev = r["time_utc"] - pd.Timedelta(seconds=r["gap_s"])
        gaps.append({
            "from_utc": str(prev),
            "to_utc": str(r["time_utc"]),
            "gap_hours": round(float(r["gap_s"]) / 3600.0, 3),
        })

    # intra-day vs weekend: gap crossing a UTC Saturday 00:00 boundary is weekend
    weekend_gaps = []
    daily_gaps = []
    for g in gaps:
        start = pd.Timestamp(g["from_utc"])
        # weekend if the gap contains a Sat/Sun daytime period (simplified: start weekday>=5)
        if start.dayofweek >= 5:
            weekend_gaps.append(g)
        else:
            daily_gaps.append(g)

    results[sym] = {
        "bars": int(len(df)),
        "utc_minute_aligned_fraction": aligned,
        "first_time_utc": str(df["time_utc"].min()),
        "last_time_utc": str(df["time_utc"].max()),
        "gaps_over_22min": len(gaps),
        "weekend_gaps": weekend_gaps,
        "daily_gaps": daily_gaps,
    }

print(json.dumps(results, indent=2, default=str))

# Also examine spread field distribution for units confirmation
print("\n=== SPREAD FIELD STATISTICS (points) ===")
for sym in SYMBOLS:
    df = pd.read_csv(OUT / f"bars_{sym}.csv")
    print(f"{sym}: min={df['spread'].min()}, max={df['spread'].max()}, "
          f"mean={df['spread'].mean():.2f}, mode={df['spread'].mode().iloc[0]}")