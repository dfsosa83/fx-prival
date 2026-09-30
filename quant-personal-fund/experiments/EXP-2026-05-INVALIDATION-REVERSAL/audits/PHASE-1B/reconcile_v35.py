"""Read-only v3.5 ledger reconciliation — direct from CSV. No modifications."""
import json
from pathlib import Path

import pandas as pd

BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/reports")
ledger = pd.read_csv(BASE / "episode_ledger_v35.csv")

ELIGIBLE = ["c1_triggered", "no_c1", "rollover_ineligible"]

out = {"csv_rows": len(ledger)}

# 1. rows + unique ids overall and by window
out["overall"] = {
    "rows": len(ledger),
    "unique_idx": int(ledger["idx"].nunique()),
    "rows_minus_unique_idx": len(ledger) - ledger["idx"].nunique(),
    "windows": ledger["assignment_window"].value_counts().to_dict(),
}

# 2. every original entry appears exactly once (idx unique per window? idx resets)
for w in ["development", "research_grade_oos"]:
    sub = ledger[ledger["assignment_window"] == w]
    out[w] = {
        "rows": len(sub),
        "unique_idx": int(sub["idx"].nunique()),
        "duplicate_idx_within_window": int(sub["idx"].duplicated().sum()),
        "rows_minus_unique": len(sub) - sub["idx"].nunique(),
    }

# 3. every row has exactly one reason; missing/unclassified
out["reason"] = {
    "null_reason_rows": int(ledger["reason"].isna().sum()),
    "value_counts": ledger["reason"].value_counts().to_dict(),
    "reason_not_in_frozen_set": ledger[~ledger["reason"].isin(
        ELIGIBLE + ["no_invalidation_within_observation_window",
                    "conservative_observed_window_exclusion_not_broker_confirmed",
                    "missing_bar", "right_censored_at_data_end"])]["reason"].unique().tolist(),
}

# 4-5. eligible + exclusions per window
for w in ["development", "research_grade_oos"]:
    sub = ledger[ledger["assignment_window"] == w]
    reasons = sub["reason"].value_counts().to_dict()
    eligible = sum(reasons.get(r, 0) for r in ELIGIBLE)
    out[w]["reason_counts"] = reasons
    out[w]["eligible_avsb"] = eligible
    out[w]["eligible_components"] = {
        r: reasons.get(r, 0) for r in ELIGIBLE
    }
    out[w]["exclusions"] = {
        k: v for k, v in reasons.items() if k not in ELIGIBLE
    }
    out[w]["sum_reason_counts"] = sum(reasons.values())
    out[w]["reconciles"] = sum(reasons.values()) == len(sub)

# 6. combined reconciliation
combined_eligible = sum(out[w]["eligible_avsb"] for w in ["development", "research_grade_oos"])
out["combined"] = {
    "dev_plus_oos_rows": out["development"]["rows"] + out["research_grade_oos"]["rows"],
    "csv_rows": len(ledger),
    "matches": (out["development"]["rows"] + out["research_grade_oos"]["rows"]) == len(ledger),
    "combined_eligible_avsb": combined_eligible,
}

with open(BASE / "V35_RECONCILIATION_REVIEW.json", "w") as f:
    json.dump(out, f, indent=2, default=str)

print(json.dumps(out, indent=2, default=str))