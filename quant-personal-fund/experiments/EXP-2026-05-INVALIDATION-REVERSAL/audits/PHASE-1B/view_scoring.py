"""View scoring results summary."""
import json
from pathlib import Path

p = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/scoring_results/SCORING_RESULTS.json")
d = json.load(open(p, encoding="utf-8"))

for s in ["base", "2x_spread", "2x_slippage", "combined"]:
    print(f"=== {s} ===")
    for w in ["development", "research_grade_oos"]:
        x = d["scenarios"][s]["windows"][w]
        b = x["bootstrap_6h"]
        b3 = x["bootstrap_3h"]
        b12 = x["bootstrap_12h"]
        iid = x.get("iid_diagnostic_only", {})
        iid_p = iid.get("p_value", "n/a")
        print(f"  {w}: n={x['n_eligible_denominator']} "
              f"c1={x['c1_triggered']} no_c1={x['no_c1']} roll={x['rollover_ineligible']}")
        print(f"     mean_dR={x['mean_delta_R']:.4f} med={x['median_delta_R']:.4f} "
              f"%pos={x['pct_positive']:.1f} pf={x['profit_factor_diagnostic']:.3f}")
        print(f"     6h CI=[{b['ci_lower']:.4f},{b['ci_upper']:.4f}] P(>0)={b['prob_mean_delta_R_gt_0']:.3f}")
        print(f"     3h CI=[{b3['ci_lower']:.4f},{b3['ci_upper']:.4f}] "
              f"12h CI=[{b12['ci_lower']:.4f},{b12['ci_upper']:.4f}] iid_p={iid_p}")