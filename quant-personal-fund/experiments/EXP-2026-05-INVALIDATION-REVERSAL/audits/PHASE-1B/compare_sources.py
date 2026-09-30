"""Compare CSV-derived figures vs summary JSON vs report claims."""
import json
from pathlib import Path

import pandas as pd

BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/reports")

ledger = pd.read_csv(BASE / "episode_ledger_v35.csv")
summary = json.load(open(BASE / "LEDGER_V35_SUMMARY.json", encoding="utf-8"))

print("=== 1. Summary JSON claims ===")
print(json.dumps(summary, indent=1))

print("\n=== 2. CSV-derived (truth) ===")
for w in ["development", "research_grade_oos"]:
    sub = ledger[ledger["assignment_window"] == w]
    rc = sub["reason"].value_counts().to_dict()
    eligible = sum(rc.get(r, 0) for r in ["c1_triggered", "no_c1", "rollover_ineligible"])
    print(f"{w}: rows={len(sub)} eligible={eligible} "
          f"c1={rc.get('c1_triggered',0)} no_c1={rc.get('no_c1',0)} "
          f"rollover={rc.get('rollover_ineligible',0)} "
          f"no_inv={rc.get('no_invalidation_within_observation_window',0)} "
          f"session={rc.get('conservative_observed_window_exclusion_not_broker_confirmed',0)} "
          f"missing={rc.get('missing_bar',0)} right_censored={rc.get('right_censored_at_data_end',0)}")

print("\n=== 3. Discrepancy: summary JSON vs CSV ===")
for w in ["development", "research_grade_oos"]:
    sw = summary["windows"][w]
    sub = ledger[ledger["assignment_window"] == w]
    rc = sub["reason"].value_counts().to_dict()
    diffs = {}
    for k in ["n_episodes", "avsb_eligible", "c1_triggered", "no_c1",
              "rollover_ineligible", "no_invalidation_within_observation_window",
              "conservative_observed_window_exclusion_not_broker_confirmed",
              "missing_bar_calendar_exclusions", "right_censored_at_data_end",
              "fully_observed"]:
        if k in sw:
            # map summary key to CSV field
            key = {"c1_triggered": "c1_triggered", "no_c1": "no_c1",
                   "rollover_ineligible": "rollover_ineligible",
                   "avsb_eligible": "eligible", "n_episodes": "rows"}.get(k, k)
            csvv = None
            if key == "eligible":
                csvv = sum(rc.get(r, 0) for r in ["c1_triggered", "no_c1", "rollover_ineligible"])
            elif key == "rows":
                csvv = len(sub)
            elif key in rc:
                csvv = rc[key]
            elif key == "missing_bar_calendar_exclusions":
                csvv = rc.get("missing_bar", 0)
            elif key == "right_censored_at_data_end":
                csvv = rc.get("right_censored_at_data_end", 0)
            if csvv is not None and sw[k] != csvv:
                diffs[k] = {"summary": sw[k], "csv": csvv}
    print(f"{w}: {json.dumps(diffs)}")

print("\n=== 4. Report claims (from V35_RECONSTRUCTION_REPORT.md) ===")
print("Report said: dev eligible 1863, c1 359, no_c1 1446, rollover 42, no_inv 446, session 324, missing 23")
print("Report said: OOS eligible 1692, c1 382, no_c1 1270, rollover 40, no_inv 562, session 281, missing 19, right_censored 21")
print("CSV actual:  dev c1 359, no_c1 1462, rollover 42 -> eligible 1863; no_inv 446, session 324, missing 17")
print("CSV actual:  OOS c1 382, no_c1 1270, rollover 40 -> eligible 1692; no_inv 562, session 281, missing 19, right_censored 21")