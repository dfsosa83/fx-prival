# Dataset Versioning and SHA-256 Hashing Convention

**Status:** Stage 1A governance standard  
**Date:** 2026-09-25

---

## 1. Purpose

Every dataset used for research or backtesting must be identifiable by a unique version and verifiable by hash. This prevents silent data changes, enables reproducibility, and traces every result to its exact inputs.

## 2. Dataset Identity

Each dataset file is identified by:

| Field | Definition |
|---|---|
| `dataset_id` | Unique ID: `{source}_{instrument_or_universe}_{frequency}_{yyyy-mm-dd_snapshot}` |
| `file_path` | Canonical storage path |
| `sha256` | Full SHA-256 digest of the file bytes |
| `version` | Monotonic integer; 1 = first validated snapshot |
| `acquired_at` | UTC timestamp of acquisition |

## 3. Storage Convention

```
data/raw/{source}/{frequency}/{instrument}_{frequency}_{start}_{end}.parquet
data/raw/{source}/manifests/{dataset_id}.yaml
```

Raw files are **immutable**: a change to the underlying data produces a **new file with a new name** (new end date), never an overwrite. Processed datasets are regenerable from raw + code and are hash-verified against their raw inputs.

## 4. Manifest Format (per dataset)

```yaml
dataset_id: "yahoo_finance_EURUSD_daily_2026-09-25"
version: 1
source: "yahoo_finance"
instrument: "EURUSD"
frequency: "daily"
acquired_at: "2026-09-25T12:00:00Z"
acquired_by: "data/pipelines/download.py"
date_range: {start: "2015-01-01", end: "2026-09-24"}
rows: 3054
columns: [date, open, high, low, close, adj_close, volume]
missing_pct: 0.003
sha256: "<full digest>"
validation: {schema: pass, duplicates: 0, monotonic: pass, ohl_consistency: warnings}
provenance:
  source_url: "https://query1.finance.yahoo.com/..."
  license_notes: "Yahoo Finance terms"
  adjustment: "adj_close includes dividends/splits per Yahoo"
notes: ""
```

## 5. Hashing Rules

- **Raw data:** SHA-256 of the stored file bytes; recomputed on every read and compared to the manifest.
- **Processed data:** SHA-256 of the file bytes; the manifest records the raw-input hashes it was built from.
- **Code/config:** every experiment records SHA-256 of the exact code and config versions used.
- **Inputs-hash for experiments:** SHA-256 of the concatenated, sorted set of (data manifests + code + config hashes) — see the experiment-manifest convention.

## 6. Verification

```python
from core.hashing import hash_file, verify_file_hash
assert verify_file_hash(path, manifest["sha256"]), "dataset changed"
```

Any mismatch → treat the dataset as **unverified**; do not use it in research until re-acquired and re-validated.

## 7. Status Fields

Every dataset carries a status:
- `validated` — passes schema + quality checks, hash verified
- `unverified` — present but hash not yet checked
- `superseded` — replaced by a newer version (kept for provenance)
- `rejected` — failed validation; must not be used

---

*This convention is enforced by the data-pipeline validation and the experiment-manifest workflow.*