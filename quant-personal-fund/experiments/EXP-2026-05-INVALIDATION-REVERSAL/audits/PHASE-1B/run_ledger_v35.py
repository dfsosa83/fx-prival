#!/usr/bin/env python
"""v3.5 ledger reconstruction — full-history run, entry-timestamp assignment,
explicit right-censoring, dependence metadata. NO performance scoring."""
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
sys.path.insert(0, str(BASE))
PROC = BASE / "data/processed"
REPORTS = BASE / "reports"

from engine.engine_v35 import run_engine_v35  # noqa: E402

m15 = pd.read_parquet(PROC / "XAUUSD_M15_processed.parquet")
h1 = pd.read_parquet(PROC / "XAUUSD_H1_processed.parquet")
m15["time_utc"] = pd.to_datetime(m15["time_utc"], utc=True)
h1["time_utc"] = pd.to_datetime(h1["time_utc"], utc=True)

# FULL HISTORY run (no slicing) — cross-boundary outcome resolution allowed
out = run_engine_v35(m15, h1)
episodes = out["episodes"]

rows = [ep.as_dict() for ep in episodes]
ledger = pd.DataFrame(rows)
ledger.to_csv(REPORTS / "episode_ledger_v35.csv", index=False)

# Per-window counts
summary = {"last_available_bar_time": out["last_available_bar_time"],
           "total_episodes": out["total_episodes"],
           "windows": {}}

for wname in ["development", "research_grade_oos"]:
    sub = [ep for ep in episodes if ep.assignment_window == wname]
    reasons = Counter(ep.reason for ep in sub)
    fully_observed = sum(1 for ep in sub if ep.observation_complete)
    right_censored = sum(1 for ep in sub if ep.reason == "right_censored_at_data_end")
    eligible = sum(1 for ep in sub if ep.reason in ("c1_triggered", "no_c1", "rollover_ineligible"))
    summary["windows"][wname] = {
        "n_episodes": len(sub),
        "reason_distribution": dict(reasons),
        "fully_observed": fully_observed,
        "right_censored_at_data_end": right_censored,
        "avsb_eligible": eligible,
        "min_entry": str(min(ep.entry_time for ep in sub)),
        "max_entry": str(max(ep.entry_time for ep in sub)),
    }

with open(REPORTS / "LEDGER_V35_SUMMARY.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))
print()
print("No performance columns:", not any(
    c for c in ledger.columns if any(k in c.lower() for k in
    ["pnl", "ev_", "profit_factor", "win_rate", "drawdown", "bootstrap", "ci_"])))