#!/usr/bin/env python
"""v3.6 scoring reproducibility manifest (hashes)."""
import hashlib
import json
import platform
import sys
from pathlib import Path

EXP = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL")
BASE = EXP / "audits/PHASE-1B"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


files = {
    "v3.5_manifest": EXP / "experiment.v3.5.yaml",
    "v3.6_manifest": EXP / "experiment.v3.6.yaml",
    "v3.5_ledger": BASE / "reports/episode_ledger_v35.csv",
    "engine_v36": BASE / "engine/engine_v36.py",
    "score_engine": BASE / "scoring/score_engine.py",
    "bootstrap_inference": BASE / "scoring/bootstrap_inference.py",
    "m15_data": BASE / "data/processed/XAUUSD_M15_processed.parquet",
    "h1_data": BASE / "data/processed/XAUUSD_H1_processed.parquet",
}

manifest = {
    "experiment": "EXP-2026-05-INVALIDATION-REVERSAL",
    "phase": "v3.6 short-stop fix + re-scoring",
    "generated_at": "2026-09-25",
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

out = BASE / "scoring_results/SCORING_REPRODUCIBILITY_V36.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(json.dumps({k: v[:16] for k, v in manifest["input_hashes"].items()}, indent=1))