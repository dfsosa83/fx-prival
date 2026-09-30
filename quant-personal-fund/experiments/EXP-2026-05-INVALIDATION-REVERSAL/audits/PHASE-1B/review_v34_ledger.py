#!/usr/bin/env python
"""READ-ONLY v3.4 ledger review — four issues.

No performance metrics. No file writes except this analysis output (JSON/CSV
reports under reports/). Computes counts, timestamps, overlap, reconciliation.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
PROC = BASE / "data/processed"
REPORTS = BASE / "reports"

m15 = pd.read_parquet(PROC / "XAUUSD_M15_processed.parquet")
m15["time_utc"] = pd.to_datetime(m15["time_utc"], utc=True)
last_available = m15["time_utc"].max()
first_available = m15["time_utc"].min()

ledger = pd.read_csv(REPORTS / "episode_ledger_v34.csv")
ledger["entry_fill_ts"] = pd.to_datetime(ledger["entry_fill_ts"], utc=True)
ledger["invalidation_ts"] = pd.to_datetime(ledger["invalidation_ts"], utc=True)

WINDOW = pd.Timedelta(days=20)
DEV_END = pd.Timestamp("2023-12-31", tz="UTC")
OOS_END = pd.Timestamp("2026-09-23", tz="UTC")

out = {"data_last_available": str(last_available),
       "data_first_available": str(first_available)}

# ═══════════════════════════════════════════════════════════════════════════
# ISSUE 1 — Right-censoring
# ═══════════════════════════════════════════════════════════════════════════
# For each episode, does a full 20-day window exist after entry within the
# AVAILABLE data (not just within its slice)?
for wname in ["development", "research_grade_oos"]:
    sub = ledger[ledger["window"] == wname].copy()
    # available end for the window: dev uses data through... the engine ran on
    # a slice ending DEV_END for dev, and OOS_END for OOS.
    avail_end = DEV_END if wname == "development" else OOS_END
    sub["window_end_needed"] = sub["entry_fill_ts"] + WINDOW
    sub["fully_observed"] = sub["window_end_needed"] <= avail_end
    # episodes whose scan hit the slice end BEFORE the window would elapse
    # are right-censored if they were classified no_invalidation
    rce = sub[(sub["reason"] == "no_invalidation_within_observation_window") &
              (~sub["fully_observed"])]
    # also: any episode classified no_invalidation but whose entry is near the
    # end of the slice (regardless) — those lack a full window within slice
    no_inv = sub[sub["reason"] == "no_invalidation_within_observation_window"]
    out[wname] = {
        "n_episodes": int(len(sub)),
        "fully_observed_full_window": int(sub["fully_observed"].sum()),
        "right_censored_in_slice": int((~sub["fully_observed"]).sum()),
        "no_invalidation_total": int(len(no_inv)),
        "no_invalidation_fully_observed": int(no_inv["fully_observed"].sum()),
        "no_invalidation_right_censored": int((~no_inv["fully_observed"]).sum()),
        "right_censored_entry_dates": [str(t) for t in
            rce["entry_fill_ts"].sort_values().tolist()[:10]],
        "min_entry_ts": str(sub["entry_fill_ts"].min()),
        "max_entry_ts": str(sub["entry_fill_ts"].max()),
    }

# ═══════════════════════════════════════════════════════════════════════════
# ISSUE 2 — Boundary integrity: entries near 2023-12-31 in dev
# ═══════════════════════════════════════════════════════════════════════════
dev = ledger[ledger["window"] == "development"].copy()
near_boundary = dev[(dev["entry_fill_ts"] > pd.Timestamp("2023-12-01", tz="UTC")) &
                    (dev["entry_fill_ts"] <= DEV_END)]
# Their 20-day window extends into 2024
near_boundary_extends = near_boundary[(near_boundary["entry_fill_ts"] + WINDOW) > DEV_END]
out["boundary_integrity"] = {
    "dev_entries_in_dec_2023": int(len(near_boundary)),
    "dev_entries_whose_20d_window_crosses_into_2024": int(len(near_boundary_extends)),
    "of_those_classified_no_invalidation": int(
        (near_boundary_extends["reason"] == "no_invalidation_within_observation_window").sum()),
    "of_those_with_invalidation": int(near_boundary_extends["invalidation_ts"].notna().sum()),
    "rule": ("Episodes assigned to dev/OOS by the run script's m15 slice filter; "
             "dev run only saw bars <= 2023-12-31, so dev entries near year-end "
             "cannot resolve invalidation/C1 from 2024 bars."),
}

# ═══════════════════════════════════════════════════════════════════════════
# ISSUE 3 — Overlapping episodes
# ═══════════════════════════════════════════════════════════════════════════
# An episode is 'active' from entry_fill_ts until its resolution:
#   - invalidation_ts if present, else entry_fill_ts + 20d
resolved = ledger.copy()
resolved["active_end"] = resolved["invalidation_ts"].fillna(
    resolved["entry_fill_ts"] + WINDOW)

# count overlaps: for each episode, how many others have entry within its
# active interval (or whose active interval covers this entry)
active_starts = resolved["entry_fill_ts"].values
active_ends = resolved["active_end"].values
starts = resolved["entry_fill_ts"].values
n = len(resolved)
overlap_count = 0
overlap_pairs = []
for a in range(n):
    for b in range(a + 1, n):
        # overlap if a's interval intersects b's interval
        s_a, e_a = active_starts[a], active_ends[a]
        s_b, e_b = active_starts[b], active_ends[b]
        if s_a <= e_b and s_b <= e_a:
            overlap_count += 1
            overlap_pairs.append((a, b))
out["overlap"] = {
    "n_episodes": n,
    "n_overlapping_pairs": overlap_count,
    "fraction_pairs_overlapping": round(overlap_count / (n * (n - 1) / 2), 5) if n > 1 else 0.0,
    "note": "Engine does NOT skip ahead after an episode; multiple breakout entries can be open simultaneously.",
}

# ═══════════════════════════════════════════════════════════════════════════
# ISSUE 4 — Denominator reconciliation
# ═══════════════════════════════════════════════════════════════════════════
reason_counts = Counter(ledger["reason"])
tot = len(ledger)
eligible = {k: v for k, v in reason_counts.items()
            if k in ("c1_triggered", "no_c1", "rollover_ineligible")}
excluded = {k: v for k, v in reason_counts.items()
            if k not in ("c1_triggered", "no_c1", "rollover_ineligible")}
out["reconciliation"] = {
    "total_ledger_rows": tot,
    "unique_episode_idx": int(ledger["idx"].nunique()),
    "duplicate_idx_count": int(ledger.duplicated(subset=["window", "idx"]).sum()),
    "sum_reason_counts": sum(reason_counts.values()),
    "eligible_sum": sum(eligible.values()),
    "excluded_sum": sum(excluded.values()),
    "reconciled": (sum(reason_counts.values()) == tot),
    "reason_distribution": dict(reason_counts),
    "eligible_by_period": {
        w: int(ledger[(ledger["window"] == w) & ledger["reason"].isin(
            ["c1_triggered", "no_c1", "rollover_ineligible"])].shape[0])
        for w in ["development", "research_grade_oos"]
    },
}

with open(REPORTS / "V34_LEDGER_REVIEW.json", "w") as f:
    json.dump(out, f, indent=2, default=str)

print(json.dumps(out, indent=2, default=str))