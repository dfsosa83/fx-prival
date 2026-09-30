"""View Stage 1B baseline metrics."""
import json
from pathlib import Path

p = Path("quant-personal-fund/data/processed/stage1b/baselines_metrics.json")
d = json.load(open(p, encoding="utf-8"))

for m in ["equal", "inverse_vol", "risk_parity"]:
    x = d["baselines"][m]
    if "metrics" not in x:
        print(m, "ERROR:", x)
        continue
    mm = x["metrics"]
    print(f"=== {m} ===")
    for k in ["annualized_return", "annualized_volatility", "sharpe", "sortino",
              "calmar", "max_drawdown", "drawdown_duration_days", "turnover",
              "total_cost", "gross_pnl", "cost_to_gross", "cumulative_return"]:
        v = mm[k]
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    print(f"  HHI: {x['weight_concentration_hhi']:.4f}")