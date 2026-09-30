#!/usr/bin/env python
"""Run the frozen engine on development and OOS windows; produce episode ledgers
and feasibility counts. NO performance scoring."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
sys.path.insert(0, str(BASE))
PROC = BASE / "data/processed"
REPORTS = BASE / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

from engine.engine import run_engine  # noqa: E402

m15 = pd.read_parquet(PROC / "XAUUSD_M15_processed.parquet")
h1 = pd.read_parquet(PROC / "XAUUSD_H1_processed.parquet")
m15["time_utc"] = pd.to_datetime(m15["time_utc"], utc=True)
h1["time_utc"] = pd.to_datetime(h1["time_utc"], utc=True)

DEV_START, DEV_END = "2020-01-01", "2023-12-31"
OOS_START, OOS_END = "2024-01-01", "2026-09-23"

windows = {
    "development": (DEV_START, DEV_END),
    "research_grade_oos": (OOS_START, OOS_END),
}

summary = {}
ledger_all = []
for wname, (s0, s1) in windows.items():
    m = m15[(m15["time_utc"] >= s0) & (m15["time_utc"] <= s1)].reset_index(drop=True)
    h = h1[(h1["time_utc"] >= s0) & (h1["time_utc"] <= s1)].reset_index(drop=True)
    out = run_engine(m, h)
    eps = out["episodes"]
    # Build ledger DataFrame
    rows = [ep.as_dict() for ep in eps]
    ledger = pd.DataFrame(rows) if rows else pd.DataFrame()
    if not ledger.empty:
        ledger.insert(0, "window", wname)
    ledger_all.append(ledger)

    # Reason-code distribution (mutually exclusive + exclusion label)
    from collections import Counter
    reasons = Counter(ep.reason for ep in eps)
    excluded = sum(1 for ep in eps if ep.excluded)
    summary[wname] = {
        "m15_bars": int(len(m)),
        "h1_bars": int(len(h)),
        "total_episodes": out["total_episodes"],
        "reason_distribution": dict(reasons),
        "excluded_count": excluded,
        "non_excluded_denominator_episodes": int(
            sum(1 for ep in eps if not ep.excluded and ep.reason in
                ("c1_triggered", "no_c1", "rollover_ineligible"))),
        "c1_triggered": int(out["counters"].get("c1_triggered", 0)),
        "no_c1": int(out["counters"].get("no_c1", 0)),
        "rollover_ineligible": int(out["counters"].get("rollover_ineligible", 0)),
        "session_exclusion": int(sum(
            1 for ep in eps
            if ep.reason == "conservative_observed_window_exclusion_not_broker_confirmed")),
    }

all_ledger = pd.concat(ledger_all, ignore_index=True) if ledger_all else pd.DataFrame()
all_ledger.to_csv(REPORTS / "episode_ledger.csv", index=False)

# Rule-trace samples (first few episodes per window)
traces = []
for wname, (s0, s1) in windows.items():
    m = m15[(m15["time_utc"] >= s0) & (m15["time_utc"] <= s1)].reset_index(drop=True)
    h = h1[(h1["time_utc"] >= s0) & (h1["time_utc"] <= s1)].reset_index(drop=True)
    out = run_engine(m, h)
    for ep in out["episodes"][:5]:
        traces.append({"window": wname, "episode": ep.idx, "reason": ep.reason,
                       "trace": ep.traces})
with open(REPORTS / "rule_traces.json", "w") as f:
    json.dump(traces, f, indent=2, default=str)

# Feasibility verdict
dev = summary.get("development", {})
oos = summary.get("research_grade_oos", {})
dev_eps = dev.get("non_excluded_denominator_episodes", 0)
oos_eps = oos.get("non_excluded_denominator_episodes", 0)

if dev_eps >= 100:
    verdict = "GO (sample sufficient for feasibility)"
elif dev_eps >= 1:
    verdict = "HOLD (sample insufficient; N<100 development)"
else:
    verdict = "NEEDS DATA (zero episodes in development)"

summary["_feasibility_verdict"] = {
    "verdict": verdict,
    "dev_non_excluded_episodes": dev_eps,
    "oos_non_excluded_episodes": oos_eps,
    "note": "Feasibility verdict ONLY — no performance scoring performed.",
}

with open(REPORTS / "FEASIBILITY_SUMMARY.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)

print(json.dumps(summary, indent=2, default=str))