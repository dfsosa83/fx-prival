#!/usr/bin/env python
"""Stage 1B reproducibility manifest — input/code/config hashes, seeds, versions."""
import hashlib
import json
import platform
import sys
from pathlib import Path

EXP = Path("quant-personal-fund")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


files = {
    "stage1b_design_spec": EXP / "docs/governance/STAGE_1B_DESIGN_SPEC.md",
    "universe": EXP / "config/universe.yaml",
    "cost_model": EXP / "config/cost_model.yaml",
    "risk_parity": EXP / "portfolio/risk_parity.py",
    "baseline_driver": EXP / "scripts/stage1b_baselines.py",
    "robustness_driver": EXP / "scripts/stage1b_robustness.py",
    "accounting_v2": EXP / "portfolio/accounting_v2.py",
}

# data hashes for the 15 active instruments' daily parquet
DATA = EXP / "data/raw/yahoo/daily"
data_hashes = {}
for f in sorted(DATA.glob("*.parquet")):
    data_hashes[f.name] = sha(f)

manifest = {
    "experiment": "STAGE-1B",
    "label": "PORTFOLIO BASELINE — NOT ALPHA EVIDENCE",
    "generated_at": "2026-09-25",
    "seeds": {"bootstrap_seed": 42, "n_replications": 10000},
    "software": {
        "python": sys.version.split()[0],
        "numpy": __import__("numpy").__version__,
        "pandas": __import__("pandas").__version__,
        "scipy": __import__("scipy").__version__,
        "platform": platform.platform(),
    },
    "frozen_parameters": {
        "universe": "15 active instruments (8 FX, 4 equity, 3 commodity)",
        "start": "2020-02-28", "end": "2026-09-23",
        "rebalance_primary": "monthly", "rebalance_confirmatory": "quarterly",
        "vol_estimator": "ewma_halflife_60", "vol_min_hist": 60,
        "cov_estimator": "ewma_halflife_60_shrinkage_0.2",
        "risk_parity": "ERC_coordinate_descent_tol_1e-6_init_equal_maxiter_2000",
        "cost": "bar_spread_proxy_L_0.5S_swap_0_no_rollover",
        "long_only": True, "cash_allowed": False, "weight_caps": "none",
    },
    "input_hashes": {k: sha(v) for k, v in files.items()},
    "data_hashes_15_instruments": data_hashes,
}

out = EXP / "data/processed/stage1b/STAGE1B_REPRODUCIBILITY.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"manifest written: {out}")
print(f"data files hashed: {len(data_hashes)}")