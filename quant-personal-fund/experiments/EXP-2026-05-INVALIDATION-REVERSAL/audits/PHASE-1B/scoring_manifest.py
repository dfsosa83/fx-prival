#!/usr/bin/env python
"""Scoring inputs hash + environment manifest."""
import hashlib
import json
import platform
import sys
from pathlib import Path

BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
EXP = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL")

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

files = {
    "v3.5_manifest": EXP / "experiment.v3.5.yaml",
    "ledger_v35": BASE / "reports/episode_ledger_v35.csv",
    "engine_v35": BASE / "engine/engine_v35.py",
    "score_engine": BASE / "scoring/score_engine.py",
    "bootstrap_inference": BASE / "scoring/bootstrap_inference.py",
    "m15_data": BASE / "data/processed/XAUUSD_M15_processed.parquet",
    "h1_data": BASE / "data/processed/XAUUSD_H1_processed.parquet",
}

def rel(p: Path) -> str:
    try:
        return str(p.relative_to(Path("quant-personal-fund")))
    except ValueError:
        return str(p)

manifest = {
    "experiment": "EXP-2026-05-INVALIDATION-REVERSAL",
    "phase": "historical performance scoring",
    "generated_at": "2026-09-24",
    "seeds": {"bootstrap_seed": 42, "n_replications": 10000},
    "software": {
        "python": sys.version.split()[0],
        "numpy": __import__("numpy").__version__,
        "pandas": __import__("pandas").__version__,
        "scipy": __import__("scipy").__version__,
        "platform": platform.platform(),
    },
    "input_hashes": {k: sha(v) for k, v in files.items()},
}

with open(BASE / "scoring_results/SCORING_REPRODUCIBILITY.json", "w") as f:
    json.dump(manifest, f, indent=2)

print(json.dumps({k: v[:16] for k, v in manifest["input_hashes"].items()}, indent=1))