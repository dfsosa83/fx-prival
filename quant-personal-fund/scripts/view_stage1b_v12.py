"""View v1.2 metrics + verify warm-up handling."""
import json
from pathlib import Path

import pandas as pd

OUT = Path("quant-personal-fund/data/processed/stage1b_v1.2")
d = json.load(open(OUT / "baselines_metrics_v1.2.json", encoding="utf-8"))

for m in ["equal", "inverse_vol", "risk_parity"]:
    mm = d["baselines"][m]["metrics"]
    print(f"=== {m} ===")
    for k in ["annualized_return", "annualized_volatility", "sharpe", "sortino",
              "calmar", "max_drawdown", "drawdown_duration_days", "turnover",
              "total_cost", "gross_pnl", "cost_to_gross", "cumulative_return", "n_days"]:
        v = mm[k]
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

# Verify warm-up handling: NAV starts at 2020-06-30
nav = pd.read_csv(OUT / "equal_nav.csv", index_col=0)
print("\n=== NAV window check ===")
print("nav index min:", nav.index.min(), "| max:", nav.index.max())
print("nav rows:", len(nav))
print("first 3 nav values:", nav["nav_net"].head(3).round(4).tolist())