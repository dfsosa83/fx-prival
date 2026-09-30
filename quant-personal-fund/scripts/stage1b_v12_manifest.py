"""Stage 1B v1.2 — reproducibility manifest + prior-version hash verification."""
import hashlib
import json
import platform
import sys
from pathlib import Path

EXP = Path("quant-personal-fund")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# Verify prior versions unchanged
specs = {
    "v1.0": EXP / "docs/governance/STAGE_1B_DESIGN_SPEC.md",
    "v1.1": EXP / "docs/governance/STAGE_1B_DESIGN_SPEC_v1.1.md",
    "v1.2": EXP / "docs/governance/STAGE_1B_DESIGN_SPEC_v1.2.md",
}
print("=== Spec hashes ===")
for v, p in specs.items():
    print(f"  {v}: {sha(p)}")

files = {
    "spec_v1.2": specs["v1.2"],
    "universe": EXP / "config/universe.yaml",
    "cost_model": EXP / "config/cost_model.yaml",
    "risk_parity": EXP / "portfolio/risk_parity.py",
    "rerun_v1.2": EXP / "scripts/stage1b_v12_rerun.py",
    "eligibility": EXP / "scripts/stage1b_v12_eligibility.py",
    "accounting_v2": EXP / "portfolio/accounting_v2.py",
}

DATA = EXP / "data/raw/yahoo/daily"
data_hashes = {f.name: sha(f) for f in sorted(DATA.glob("*.parquet"))}

manifest = {
    "experiment": "STAGE-1B-v1.2",
    "label": "PORTFOLIO BASELINE — NOT ALPHA EVIDENCE",
    "generated_at": "2026-09-28",
    "periods": {
        "data_start": "2020-02-28",
        "warmup_only_period": "2020-02-28 to 2020-06-30",
        "first_eligible_rebalance": "2020-06-30",
        "performance_evaluation_start": "2020-06-30",
        "performance_evaluation_end": "2026-09-23",
    },
    "frozen_parameters": {
        "min_history_observations": 60,
        "lookback_max_observations": 200,
        "universe": "15 active instruments",
        "rebalance": "monthly",
        "vol_estimator": "ewma_halflife_60",
        "cov_estimator": "ewma_halflife_60_shrinkage_0.2",
        "cost": "bar_spread_proxy_L_0.5S_swap_0_no_rollover",
    },
    "input_hashes": {k: sha(v) for k, v in files.items()},
    "data_hashes": data_hashes,
    "software": {
        "python": sys.version.split()[0],
        "numpy": __import__("numpy").__version__,
        "pandas": __import__("pandas").__version__,
        "scipy": __import__("scipy").__version__,
    },
}

out = EXP / "data/processed/stage1b_v1.2/STAGE1B_v1.2_REPRODUCIBILITY.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"\nmanifest written: {out}")
print(f"data files hashed: {len(data_hashes)}")