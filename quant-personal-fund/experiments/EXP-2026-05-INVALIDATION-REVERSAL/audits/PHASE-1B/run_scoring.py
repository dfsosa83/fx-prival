#!/usr/bin/env python
"""Historical performance scoring — EXP-2026-05 (v3.5 ledger).

Runs 4 cost scenarios x (development, research_grade_oos), computes per-episode
delta_R, cluster-aware block bootstrap (6h/3h/12h), and all required diagnostics.
No strategy GO. No MT5. No orders.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
sys.path.insert(0, str(BASE))
REPORTS = BASE / "reports"
SCORE_OUT = BASE / "scoring_results"
SCORE_OUT.mkdir(parents=True, exist_ok=True)

from scoring.score_engine import score_ledger  # noqa: E402
from scoring.bootstrap_inference import (  # noqa: E402
    block_bootstrap_deltaR,
    iid_diagnostic_only,
)

LEDGER = pd.read_csv(REPORTS / "episode_ledger_v35.csv")
BARS = pd.read_parquet(BASE / "data/processed/XAUUSD_M15_processed.parquet")
BARS["time_utc"] = pd.to_datetime(BARS["time_utc"], utc=True)

SCENARIOS = ["base", "2x_spread", "2x_slippage", "combined"]
BLOCKS = [3, 6, 12]
SEED = 42
N_REPS = 10000

report = {"scenarios": {}, "seeds": {"bootstrap_seed": SEED, "n_replications": N_REPS}}

for scen in SCENARIOS:
    scored = score_ledger(LEDGER, BARS, scen)
    scen_report = {"windows": {}}
    for w in ["development", "research_grade_oos"]:
        sub = scored[scored["window"] == w].copy()
        n = len(sub)
        c1 = (sub["reason"] == "c1_triggered").sum()
        nc1 = (sub["reason"] == "no_c1").sum()
        roll = (sub["reason"] == "rollover_ineligible").sum()

        dr = sub["delta_R"]
        mean_dr = float(dr.mean())
        med_dr = float(dr.median())
        pos_pct = float((dr > 0).mean() * 100)
        avg_pos = float(dr[dr > 0].mean()) if (dr > 0).any() else 0.0
        avg_neg = float(dr[dr < 0].mean()) if (dr < 0).any() else 0.0
        # Profit factor (diagnostic only): sum(pos) / abs(sum(neg))
        pos_sum = float(dr[dr > 0].sum())
        neg_sum = float(abs(dr[dr < 0].sum()))
        pf = pos_sum / neg_sum if neg_sum > 0 else float("inf")

        # Bootstrap
        boot6 = block_bootstrap_deltaR(sub, block_hours=6, n_reps=N_REPS, seed=SEED)
        boot3 = block_bootstrap_deltaR(sub, block_hours=3, n_reps=N_REPS, seed=SEED)
        boot12 = block_bootstrap_deltaR(sub, block_hours=12, n_reps=N_REPS, seed=SEED)
        iid = iid_diagnostic_only(sub)

        # Largest contributions
        top5pos = sub.nlargest(5, "delta_R")[["idx", "delta_R", "entry_time"]].to_dict("records")
        top5neg = sub.nsmallest(5, "delta_R")[["idx", "delta_R", "entry_time"]].to_dict("records")

        # Max drawdown contribution (diagnostic, from cumulative delta R sorted by time)
        sub_sorted = sub.sort_values("entry_time")
        cum = sub_sorted["delta_R"].cumsum()
        dd = float(cum.min() - 0)  # relative to 0 start

        scen_report["windows"][w] = {
            "n_eligible_denominator": n,
            "c1_triggered": int(c1),
            "no_c1": int(nc1),
            "rollover_ineligible": int(roll),
            "mean_delta_R": mean_dr,
            "median_delta_R": med_dr,
            "pct_positive": pos_pct,
            "avg_positive_delta_R": avg_pos,
            "avg_negative_delta_R": avg_neg,
            "profit_factor_diagnostic": pf,
            "max_drawdown_contribution": dd,
            "top5_positive": top5pos,
            "top5_negative": top5neg,
            "bootstrap_6h": boot6,
            "bootstrap_3h": boot3,
            "bootstrap_12h": boot12,
            "iid_diagnostic_only": iid,
        }
        # per-window per-scenario CSV
        sub.to_csv(SCORE_OUT / f"scored_{scen}_{w}.csv", index=False)
    report["scenarios"][scen] = scen_report

with open(SCORE_OUT / "SCORING_RESULTS.json", "w") as f:
    json.dump(report, f, indent=2, default=str)

print(json.dumps({s: {w: {k: report["scenarios"][s]["windows"][w][k]
      for k in ("n_eligible_denominator", "c1_triggered", "no_c1", "rollover_ineligible",
                "mean_delta_R", "median_delta_R", "pct_positive",
                "profit_factor_diagnostic")} for w in
      ("development", "research_grade_oos")} for s in SCENARIOS}, indent=1, default=str))