"""Stage 1B v1.1 vs v1.0 numerical diff."""
import json
import hashlib
from pathlib import Path

import pandas as pd

S1 = Path("quant-personal-fund/data/processed/stage1b")
S2 = Path("quant-personal-fund/data/processed/stage1b_v1.1")

# Load metrics
m1 = json.load(open(S1 / "baselines_metrics.json", encoding="utf-8"))["baselines"]
m2 = json.load(open(S2 / "baselines_metrics_v1.1.json", encoding="utf-8"))["baselines"]

print("=== Metric diff (v1.1 - v1.0) per baseline ===")
for method in ["equal", "inverse_vol", "risk_parity"]:
    a = m1[method]["metrics"]
    b = m2[method]["metrics"]
    print(f"\n{method}:")
    for k in ["annualized_return", "annualized_volatility", "sharpe", "sortino",
              "max_drawdown", "turnover", "total_cost", "gross_pnl", "cost_to_gross",
              "cumulative_return"]:
        d = b[k] - a[k]
        print(f"  {k}: v1.0={a[k]:.4f} v1.1={b[k]:.4f} diff={d:+.4f}")

# Verify original hashes unchanged
spec = hashlib.sha256(Path("quant-personal-fund/docs/governance/STAGE_1B_DESIGN_SPEC.md").read_bytes()).hexdigest()
print("\n=== Original artifacts unchanged ===")
print("spec v1.0 sha256:", spec, spec == "deb2d694b0c0d08615c47e5fa9faf852a4cb40622609b16ffa4f7e0ffdd871c3")

# v1.1 spec hash
spec2 = hashlib.sha256(Path("quant-personal-fund/docs/governance/STAGE_1B_DESIGN_SPEC_v1.1.md").read_bytes()).hexdigest()
print("spec v1.1 sha256:", spec2)