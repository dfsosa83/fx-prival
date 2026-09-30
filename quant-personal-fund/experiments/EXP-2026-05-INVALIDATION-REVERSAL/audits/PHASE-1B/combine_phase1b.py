#!/usr/bin/env python
"""Combine Phase 1B raw chunks into processed M15/H1 datasets + quality checks."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
RAW_M15 = BASE / "data/raw/m15"
RAW_H1 = BASE / "data/raw/h1"
PROC = BASE / "data/processed"
PROC.mkdir(parents=True, exist_ok=True)

q = {}

def load_combine(outdir, tf):
    frames = []
    for f in sorted(outdir.glob(f"XAUUSD_{tf}_*.parquet")):
        frames.append(pd.read_parquet(f))
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values("time_utc").drop_duplicates(subset="time_utc", keep="last").reset_index(drop=True)
    return df

m15 = load_combine(RAW_M15, "M15")
h1 = load_combine(RAW_H1, "H1")

for name, df, tf in [("M15", m15, "M15"), ("H1", h1, "H1")]:
    q[name] = {
        "rows": int(len(df)),
        "first_utc": str(df["time_utc"].min()),
        "last_utc": str(df["time_utc"].max()),
        "duplicates_removed": int(len(df) - df["time_utc"].nunique()),
        "utc_minute_aligned": float(df["time_utc"].dt.minute.isin([0,15,30,45]).mean())
        if tf == "M15" else float(df["time_utc"].dt.minute.isin([0,30]).mean()),
    }
    # intra-session gaps
    expected = pd.Timedelta(minutes=15 if tf == "M15" else 60)
    gaps = df["time_utc"].diff().dropna()
    big = gaps[gaps > expected * 1.5]
    q[name]["gaps_over_1.5x"] = int(len(big))
    q[name]["largest_gap_s"] = float(big.max().total_seconds()) if len(big) else 0.0
    # save processed
    out = PROC / f"XAUUSD_{tf}_processed.parquet"
    df.to_parquet(out, index=False)
    q[name]["processed_file"] = str(out.relative_to(BASE))

print(json.dumps(q, indent=2))

# Spread distributions (M15, points)
print("\n=== M15 spread distribution (points) ===")
print(f"min={m15['spread'].min()} max={m15['spread'].max()} "
      f"mean={m15['spread'].mean():.2f} p50={m15['spread'].median()} "
      f"p99={m15['spread'].quantile(0.99):.1f}")

(BASE / "DATA_QUALITY.json").write_text(json.dumps(q, indent=2), encoding="utf-8")