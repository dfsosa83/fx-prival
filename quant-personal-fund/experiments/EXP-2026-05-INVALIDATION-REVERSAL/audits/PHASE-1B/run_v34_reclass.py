#!/usr/bin/env python
"""v3.4 ledger reclassification on stored Phase 1B bars (data-free; no new retrieval).
No PnL/EV/PF/win-rate/drawdown/CI computation — counts only."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
sys.path.insert(0, str(BASE))
REPORTS = BASE / "reports"

from engine.engine_v34 import run_engine_v34  # noqa: E402

m15 = pd.read_parquet(BASE / "data/processed/XAUUSD_M15_processed.parquet")
h1 = pd.read_parquet(BASE / "data/processed/XAUUSD_H1_processed.parquet")
m15["time_utc"] = pd.to_datetime(m15["time_utc"], utc=True)
h1["time_utc"] = pd.to_datetime(h1["time_utc"], utc=True)

DEV = ("2020-01-01", "2023-12-31")
OOS = ("2024-01-01", "2026-09-23")

summary = {}
ledger_all = []
for wname, (s0, s1) in [("development", DEV), ("research_grade_oos", OOS)]:
    m = m15[(m15["time_utc"] >= s0) & (m15["time_utc"] <= s1)].reset_index(drop=True)
    h = h1[(h1["time_utc"] >= s0) & (h1["time_utc"] <= s1)].reset_index(drop=True)
    out = run_engine_v34(m, h)
    eps = out["episodes"]
    rows = [ep.as_dict() for ep in eps]
    ledger = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not ledger.empty:
        ledger.insert(0, "window", wname)
    ledger_all.append(ledger)

    from collections import Counter
    reasons = Counter(ep.reason for ep in eps)
    total = len(eps)
    avsb_eligible = sum(1 for ep in eps if ep.reason in ("c1_triggered", "no_c1", "rollover_ineligible"))
    c1 = reasons.get("c1_triggered", 0)
    no_c1 = reasons.get("no_c1", 0)
    no_inv = reasons.get("no_invalidation_within_observation_window", 0)
    sess = reasons.get(SESSION_EXCLUSION_LABEL := "conservative_observed_window_exclusion_not_broker_confirmed", 0)
    missing = reasons.get("missing_bar_calendar_exclusion", 0)
    roll = reasons.get("rollover_ineligible", 0)
    other = reasons.get("other_pre_registered", 0)

    summary[wname] = {
        "total_original_long_entries": total,
        "avsb_eligible_invalidated": avsb_eligible,
        "c1_triggered_short": c1,
        "no_c1": no_c1,
        "no_invalidation_within_observation_window": no_inv,
        "conservative_session_exclusions": sess,
        "missing_bar_calendar_exclusions": missing,
        "rollover_ineligible": roll,
        "other_pre_registered": other,
        "reason_distribution": dict(reasons),
    }

all_ledger = pd.concat(ledger_all, ignore_index=True) if ledger_all else pd.DataFrame()
all_ledger.to_csv(REPORTS / "episode_ledger_v34.csv", index=False)

with open(REPORTS / "LEDGER_V34_SUMMARY.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))