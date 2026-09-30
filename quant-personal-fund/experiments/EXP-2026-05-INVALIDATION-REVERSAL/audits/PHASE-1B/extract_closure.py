"""Extract v3.6 numbers for the closure report."""
import json
from pathlib import Path

p = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/scoring_results/SCORING_RESULTS_V36.json")
d = json.load(open(p, encoding="utf-8"))

for s in ["base", "2x_spread", "2x_slippage", "combined"]:
    print("===", s)
    for w in ["development", "research_grade_oos"]:
        x = d["scenarios"][s]["windows"][w]
        b = x["bootstrap_6h"]
        b3 = x["bootstrap_3h"]
        b12 = x["bootstrap_12h"]
        line = (f"{w}: mean={x['mean_delta_R']:.4f} "
                f"6h=[{b['ci_lower']:.4f},{b['ci_upper']:.4f}] "
                f"P={b['prob_mean_delta_R_gt_0']:.3f} "
                f"pf={x['profit_factor_diagnostic']:.3f} "
                f"3h=[{b3['ci_lower']:.4f},{b3['ci_upper']:.4f}] "
                f"12h=[{b12['ci_lower']:.4f},{b12['ci_upper']:.4f}]")
        print(line)