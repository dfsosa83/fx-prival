# USDJPY Refresh — Safe Implementation Plan (Design Only)

**Experiment context:** `QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V2B_USDJPY_DOWNLOADER_SCHEMA_COMPATIBILITY_AUDIT`
**Status:** design proposal only — **not implemented**; requires separate authorization.

---

## 1. Canonical raw H1 schema to freeze

```text
datetime, open, high, low, close, volume
```

Rationale: this is the **repository-documented canonical schema** (downloader docstring
`ml-signal-service/steps/01_download/mt5_downloader.py` lines 7–8; `CANONICAL_COLS` line 47) and
matches the two files the downloader already produced (AUDUSD, NZDUSD). Freezing this schema keeps a
single repository standard; the five **legacy datetime-last files** are the divergence.

## 2. Retrieval step (read-only, in memory)

- A future authorized stage would call `mt5.copy_rates_range(symbol, TIMEFRAME_H1, from_dt, to_dt)`
  for USDJPY over the **maximum available** history (from the configured start date), retrieving bars
  **into memory** — no direct writes to the raw CSV.
- No account-balance/equity/position/order/fill/execution query; historical bars only.

## 3. Normalization before persistence

- Build a DataFrame in memory and reorder to the canonical schema **before** any write:
  `datetime, open, high, low, close, volume`, with `datetime` formatted `YYYY-MM-DD HH:MM:SS`
  (naive string, `NOT_UTC` internal-label convention).

## 4. Full-file rebuild (no append) when schema differs

- If the existing file’s header **equals** the canonical schema, a normal incremental append is
  schema-safe and may be used.
- If the existing header **differs** (legacy datetime-last, as with USDJPY), the writer must perform a
  **full-file rebuild** — never an append — producing the canonical schema from scratch.

## 5. Temporary file in the same directory

- Write the rebuilt content to a temporary file **in the same directory**
  (`ml-signal-service/data/raw/mt5/H1/`) so the final step can be an atomic replace on the same
  volume.

## 6. Validation before replacement (fail-closed)

Validate the candidate file before replacing the target:

- exact header/column order equals the canonical schema;
- no null `datetime`;
- no duplicate `datetime`;
- strictly lexicographic ascending `datetime` labels;
- `close` finite and **strictly positive**;
- row count ≥ expected minimum.

## 7. Hashing

- Record the **source/input hash** (existing raw file) before update.
- Record the **candidate output hash** before replacement, and re-verify it after the atomic replace.

## 8. Atomic replace only after validation

- Replace the target **only** if every validation passes, via an atomic rename/replace of the
  temporary file onto `USDJPY_H1.csv`.

## 9. Backup / immutable-copy policy

- Retain an immutable copy of the pre-update USDJPY file (e.g. under an audit/backup location)
  together with its recorded SHA256, so the previous state is recoverable and auditable.

## 10. Fail-closed behavior

If retrieval, normalization, validation, hashing, or atomic replacement fails at any step: **abort**,
leave the existing raw CSV untouched, delete the temporary file, and record a PAUSE with the exact
error.

## 11. Compatibility for already-canonical files

- Files whose header already equals the canonical schema keep incremental append behavior (no change).
- Legacy files are rebuilt to canonical on refresh; no other instrument is modified without its own
  explicit authorization.

## 12. Synthetic local test plan (never invokes MT5)

Offline tests using **synthetic local fixtures only** (no MT5, no network, no production CSVs):

1. **Canonical append/rebuild works** — a canonical-schema fixture appends/rebuilds correctly and
   validates.
2. **Legacy rebuild** — a legacy-schema fixture (datetime-last) is correctly rebuilt into the canonical
   schema with values preserved by logical column name.
3. **Fail-closed cases** — fixtures with malformed rows, duplicate labels, or non-ascending labels are
   **rejected** and the target is left unchanged.
4. **Production isolation** — test mode writes only to temporary/test paths and **cannot touch any raw
   production CSV** (asserted by path allow-listing).

## 13. Authorization statement

**Any implementation of this plan and any USDJPY refresh require separate, explicit authorization
after this audit.** This document implements nothing and does not authorize H5 screening.
