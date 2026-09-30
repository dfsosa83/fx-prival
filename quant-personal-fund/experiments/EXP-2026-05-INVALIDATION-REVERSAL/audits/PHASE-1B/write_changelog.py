"""v3.3 (500-bar) vs v3.4 (20-day) change log — counts only."""
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
REPORTS = BASE / "reports"

with open(REPORTS / "FEASIBILITY_SUMMARY.json", encoding="utf-8") as f:
    old = json.load(f)
with open(REPORTS / "LEDGER_V34_SUMMARY.json", encoding="utf-8") as f:
    new = json.load(f)

changelog = {}
for w in ["development", "research_grade_oos"]:
    o, n = old[w], new[w]
    new_denominator = n["c1_triggered_short"] + n["no_c1"] + n["rollover_ineligible"]
    old_denominator = o["non_excluded_denominator_episodes"]
    changelog[w] = {
        "old_total_episodes_500bar": o["total_episodes"],
        "new_total_original_long_entries_20day": n["total_original_long_entries"],
        "old_other_pre_registered_500bar_cap": o["reason_distribution"].get("other_pre_registered", 0),
        "new_no_invalidation_within_observation_window": n["no_invalidation_within_observation_window"],
        "old_denominator_avsb": old_denominator,
        "new_denominator_avsb": new_denominator,
        "delta_denominator": new_denominator - old_denominator,
        "old_session_excluded": o["session_exclusion"],
        "new_session_excluded": n["conservative_session_exclusions"],
        "new_missing_bar_calendar_excluded": n["missing_bar_calendar_exclusions"],
        "new_c1_triggered": n["c1_triggered_short"],
        "new_no_c1": n["no_c1"],
        "new_rollover_ineligible": n["rollover_ineligible"],
    }

with open(REPORTS / "V34_CHANGELOG.json", "w") as f:
    json.dump(changelog, f, indent=2)

print(json.dumps(changelog, indent=2))