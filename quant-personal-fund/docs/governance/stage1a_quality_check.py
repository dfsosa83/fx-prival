#!/usr/bin/env python
"""Stage 1A — data-quality validation on existing local datasets + bootstrap
synthetic verification. Read-only; no new data retrieval."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # quant-personal-fund/
import numpy as np
import pandas as pd
from data.pipelines.validate import validate_ohlcv  # noqa: E402
from core.bootstrap import block_bootstrap_ci  # noqa: E402

DATA = Path("quant-personal-fund/data/raw/yahoo/daily")
OUT = Path("quant-personal-fund/docs/governance")

results = []
for f in sorted(DATA.glob("*.parquet")):
    df = pd.read_parquet(f)
    if "date" in df.columns:
        df = df.set_index("date")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")]
    v = validate_ohlcv(df.reset_index(), ticker=f.stem)
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    results.append({
        "file": f.name,
        "rows": len(df),
        "first": str(df.index.min().date()),
        "last": str(df.index.max().date()),
        "valid": v["is_valid"],
        "errors": len(v["errors"]),
        "warnings": len(v["warnings"]),
        "missing_pct": v["missing_pct"],
        "sha256": h[:16],
    })

rdf = pd.DataFrame(results)
rdf.to_csv(OUT / "stage1a_data_quality.csv", index=False)
print(rdf[["file", "rows", "valid", "errors", "warnings", "missing_pct"]].to_string(index=False))

# ── Bootstrap synthetic verification ───────────────────────────────────────
print("\n=== Block-bootstrap synthetic verification ===")
# Case 1: IID data, block=1 should match IID bootstrap
rng = np.random.RandomState(42)
iid = rng.randn(500)
b1 = block_bootstrap_ci(iid, block_length=1, n_resamples=1000, random_seed=7)
print(f"IID data block=1: mean={b1[0]:.4f} CI=[{b1[1]:.4f},{b1[2]:.4f}]")

# Case 2: AR(1) positive autocorrelation -> wider CI with block>1
eps = rng.randn(1000)
ar1 = np.zeros(1000)
ar1[0] = eps[0]
for i in range(1, 1000):
    ar1[i] = 0.5 * ar1[i - 1] + eps[i]
w1 = block_bootstrap_ci(ar1, block_length=1, n_resamples=1000, random_seed=7)
w10 = block_bootstrap_ci(ar1, block_length=10, n_resamples=1000, random_seed=7)
print(f"AR(1) block=1 CI width: {w1[2]-w1[1]:.4f}; block=10 width: {w10[2]-w10[1]:.4f}")
print(f"Block>1 wider than block=1: {(w10[2]-w10[1]) > (w1[2]-w1[1])}")

# Case 3: reproducibility
r1 = block_bootstrap_ci(iid, block_length=5, n_resamples=200, random_seed=99)
r2 = block_bootstrap_ci(iid, block_length=5, n_resamples=200, random_seed=99)
print(f"Reproducible (same seed): {r1 == r2}")

bootstrap_report = {
    "iid_block1": {"mean": b1[0], "ci": [b1[1], b1[2]]},
    "ar1_block1_width": w1[2] - w1[1],
    "ar1_block10_width": w10[2] - w10[1],
    "block_wider_for_autocorrelated": bool((w10[2] - w10[1]) > (w1[2] - w1[1])),
    "reproducible": bool(r1 == r2),
}
with open(OUT / "stage1a_bootstrap_verify.json", "w") as f:
    json.dump(bootstrap_report, f, indent=2)
print("bootstrap verification written")