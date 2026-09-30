#!/usr/bin/env python
"""Enrich the 36-cell coverage table with OBSERVED local H1/M5 stats.

Local-only. No MT5. Records observed local coverage, duplicates, gaps.
All MT5-dependent fields remain marked 'MT5 QUERY NOT RUN'.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
OUT = Path("quant-personal-fund/audits/PHASE-0-5-DATA-AUDIT")

cov = pd.read_csv(OUT / "instrument_timeframe_coverage.csv")

H1_DIR = Path("ml-signal-service/data/raw/mt5/H1")
M5_GOLD = Path("ml-signal-service/experiments/EXP-2026-10-GOLD-EXIT-MANAGEMENT/data/xauusd_m5.csv")

for idx, row in cov.iterrows():
    inst, tf = row["instrument"], row["timeframe"]
    if tf == "H1":
        f = H1_DIR / f"{inst}_H1.csv"
        if f.exists():
            df = pd.read_csv(f, parse_dates=["datetime"]).dropna()
            ts = df["datetime"]
            n = len(df)
            dups = int(ts.duplicated().sum())
            gaps = ts.diff().dropna()
            big = int((gaps > pd.Timedelta(hours=2)).sum())
            span_days = (ts.max() - ts.min()).days
            cov.loc[idx, "local_rows"] = n
            cov.loc[idx, "local_first_ts"] = str(ts.min())
            cov.loc[idx, "local_last_ts"] = str(ts.max())
            cov.loc[idx, "duplicate_timestamps"] = dups
            cov.loc[idx, "unexplained_missing"] = big
            cov.loc[idx, "tz_convention"] = "UNVERIFIED (local cache; server tz not confirmed)"
            cov.loc[idx, "fields_available"] = "open,high,low,close,volume(tick)"
            cov.loc[idx, "calendar_assumption"] = "PARTIAL (weekend gaps expected FX; gold halt not mapped)"
            cov.loc[idx, "notes"] = f"LOCAL ONLY: {n} H1 rows over {span_days}d, {dups} dups, {big} gaps>2h. MT5 envelope NOT queried."
    if inst == "XAUUSD" and tf == "M5":
        if M5_GOLD.exists():
            df = pd.read_csv(M5_GOLD, parse_dates=["time"]).dropna()
            n = len(df)
            ts = df["time"]
            dups = int(ts.duplicated().sum())
            cov.loc[idx, "local_rows"] = n
            cov.loc[idx, "local_first_ts"] = str(ts.min())
            cov.loc[idx, "local_last_ts"] = str(ts.max())
            cov.loc[idx, "duplicate_timestamps"] = dups
            cov.loc[idx, "fields_available"] = "open,high,low,close"
            cov.loc[idx, "notes"] = "LOCAL ONLY: ~4-week XAUUSD M5 (2026-08-25 to 2026-09-18). MT5 envelope NOT queried."

cov.to_csv(OUT / "instrument_timeframe_coverage.csv", index=False)
print("instrument_timeframe_coverage.csv enriched")
print(cov[["instrument", "timeframe", "local_rows", "local_first_ts", "local_last_ts",
           "duplicate_timestamps", "unexplained_missing", "adequacy"]].to_string(index=False))