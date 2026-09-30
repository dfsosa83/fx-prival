#!/usr/bin/env python
"""Write the v3.4 episode ledger (reclassification, no performance)."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
sys.path.insert(0, str(BASE))
PROC = BASE / "data/processed"
REPORTS = BASE / "reports"

from engine.engine_v34 import run_engine_v34  # noqa: E402

m15 = pd.read_parquet(PROC / "XAUUSD_M15_processed.parquet")
h1 = pd.read_parquet(PROC / "XAUUSD_H1_processed.parquet")
m15["time_utc"] = pd.to_datetime(m15["time_utc"], utc=True)
h1["time_utc"] = pd.to_datetime(h1["time_utc"], utc=True)

windows = {
    "development": ("2020-01-01", "2023-12-31"),
    "research_grade_oos": ("2024-01-01", "2026-09-23"),
}

ledger_all = []
for wname, (s0, s1) in windows.items():
    m = m15[(m15["time_utc"] >= s0) & (m15["time_utc"] <= s1)].reset_index(drop=True)
    h = h1[(h1["time_utc"] >= s0) & (h1["time_utc"] <= s1)].reset_index(drop=True)
    out = run_engine_v34(m, h)
    rows = [ep.as_dict() for ep in out["episodes"]]
    led = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not led.empty:
        led.insert(0, "window", wname)
    ledger_all.append(led)

all_ledger = pd.concat(ledger_all, ignore_index=True) if ledger_all else pd.DataFrame()
# strip any performance-like columns (defensive; engine emits none)
all_ledger.to_csv(REPORTS / "episode_ledger_v34.csv", index=False)
print("episode_ledger_v34.csv written:", len(all_ledger), "rows")
print("reason codes:", sorted(all_ledger["reason"].unique()))
print("no performance columns:", not any(
    c for c in all_ledger.columns if any(k in c.lower() for k in
    ["pnl", "ev_", "profit_factor", "win_rate", "drawdown", "bootstrap", "ci_"])))