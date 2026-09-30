# Synthetic Validation Report — safe_h1_csv_rebuild

**Stage:** `USDJPY_SAFE_REBUILD_UTILITY_IMPLEMENTATION_AND_SYNTHETIC_VALIDATION`
**Date:** 2026-09-29
**Result:** **NOT PASSED — 14 passed, 1 failure, 1 error (16 tests run).**

---

## 1. Objective and scope

Implement an isolated, path-explicit utility that safely rebuilds a legacy or canonical raw H1 CSV
into the frozen canonical schema, and validate it **exclusively with synthetic local fixtures**.
No MT5, downloader, broker, credentials, network, production raw data, experiment snapshot, or market
statistics were accessed. No production file was read or written (not even read-only).

## 2. Files created

- `quant-personal-fund/tools/raw_data_schema_rebuild/safe_h1_csv_rebuild.py`
- `quant-personal-fund/tools/raw_data_schema_rebuild/test_safe_h1_csv_rebuild.py`
- `quant-personal-fund/tools/raw_data_schema_rebuild/README.md`
- `quant-personal-fund/tools/raw_data_schema_rebuild/SYNTHETIC_VALIDATION_REPORT.md` (this file)

## 3. Canonical schema

```python
CANONICAL_COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]
```

Accepted inputs: canonical `datetime,open,high,low,close,volume` and legacy
`open,high,low,close,volume,datetime` (header-only detection); everything else fail-closed.

## 4. Test matrix (single run; command `python -m unittest -v test_safe_h1_csv_rebuild.py`)

| # | Case | Result |
|---|---|---|
| 1 | Canonical detection & rebuild | ok |
| 2 | Legacy detection & normalization (by name) | ok |
| 3 | Exact output column order & opaque labels | ok |
| 4 | Merge non-overlapping canonical rows | ok |
| 5 | Merge legacy-format new rows after normalization | ok |
| 6 | Identical overlapping datetime deduplicates | ok |
| 7 | Conflicting overlapping datetime fails | ok |
| 8 | Duplicate datetime fails | ok |
| 9 | Out-of-order datetime fails | ok |
| 10 | **Null datetime fails** | **FAIL (ValidationError not raised)** |
| 11 | Non-numeric / non-finite OHLCV fails | ok |
| 12 | Non-positive close fails | ok |
| 13 | Unsupported schema fails | ok |
| 14 | Existing backup path fails closed | ok |
| 15 | **Simulated write-validation failure leaves original unchanged** | **ERROR (mock raised in test setup)** |
| 16 | Every test path inside its own temporary directory | ok |
| 17 | No test path contains production/experiment raw paths | ok |

Ran 16 tests → **14 passed, 1 failure, 1 error.**

## 5. Root causes (identified, NOT fixed in this task)

- **Case 10 (utility defect):** `read_and_normalize` calls `frame["datetime"].astype(str)` **before**
  the null check, so an empty datetime cell (read as `NaN`) becomes the string `"nan"` and bypasses
  the `datetime.isna()` guard. Remedy: check `datetime.isna()` **before** `astype(str)` (also in the
  merge helper’s normalized copy).
- **Case 15 (test defect):** the test patches `read_and_normalize` for the whole method, including its
  own `_frame()` setup call, so the mock raises during setup instead of during the write. Remedy:
  build the candidate frame **before** entering the `mock.patch` context.

## 6. Fixtures / activity statement

All fixtures were **tiny synthetic CSVs** created under a `TemporaryDirectory` and cleaned up at
teardown; every asserted path was verified to be inside its own temp directory and to contain none of
`ml-signal-service/data/raw`, `quant-personal-fund/experiments`, or any production raw path. **No**
production raw data was read/written, and **no** downloader, MT5, broker, network, credentials, market
statistics, strategy, cost, PnL, backtest, or trading activity occurred.

## 7. Limitations

- The utility has **not** been used against any real raw file and has **not** retrieved any historical
  data.
- The suite is **not fully green**: one utility edge-case defect and one test-harness defect remain
  (see §5). The utility is therefore **not yet validated** for production use.

## 8. Recommendation / next permitted action

The synthetic suite did **not** pass; per the stage rule, no further patch/re-run was performed in
this task. The next permitted action is a **separate authorization** to correct the two identified
defects (one utility, one test) and re-run the synthetic suite once.

Only after a fully green suite:

```text
A separate authorization may review the utility and, if accepted, authorize a
narrowly scoped real USDJPY historical refresh using read-only retrieval,
full canonical rebuild, immutable backup, hash verification, and a new H5
multiseries snapshot freeze. No H5 screen is authorized by this stage.
```

---

## Corrective Rerun — 2026-09-29

**Prior result:** 14 passed / 1 failed / 1 errored (16 tests).

### Defects and exact narrow corrections

1. **Utility defect — null datetime validation.** `read_and_normalize` called
   `frame["datetime"].astype(str)` **before** the null check, so an empty datetime cell (read as `NaN`)
   became the literal string `"nan"` and bypassed the guard. **Correction:** added
   `_assert_valid_datetime_labels()` (rejecting null/NaN, empty string, whitespace-only, and literal
   `"nan"`/`"NaN"` after stripping) and call it **before** any `astype(str)` in `read_and_normalize`
   and in the merge helper’s normalized copy; `validate_canonical_frame` now routes through the same
   check. Opaque non-empty labels are untouched (no parsing/localization).
2. **Test defect — simulated candidate validation failure.** The test patched `read_and_normalize`
   across its own `_frame()` setup call. **Correction:** the synthetic frame is now built **before**
   entering the `mock.patch` context, so the failure occurs only at the intended candidate
   re-read/validation step inside `write_candidate_atomic`; the test now also asserts unchanged
   original content and SHA256, absence of a backup, no leftover `.tmp`, and temp-dir path isolation.

### Full-suite result

Command: `python -m unittest -v test_safe_h1_csv_rebuild.py` → **Ran 16 tests — OK (16 passed, 0 failed, 0 errored).**

| # | Case | Status |
|---|---|---|
| 1 | Canonical detection & rebuild | PASS |
| 2 | Legacy detection & normalization (by name) | PASS |
| 3 | Exact output column order & opaque labels | PASS |
| 4 | Merge non-overlapping canonical rows | PASS |
| 5 | Merge legacy-format new rows after normalization | PASS |
| 6 | Identical overlapping datetime deduplicates | PASS |
| 7 | Conflicting overlapping datetime fails | PASS |
| 8 | Duplicate datetime fails | PASS |
| 9 | Out-of-order datetime fails | PASS |
| 10 | Null datetime fails | **PASS** (corrected) |
| 11 | Non-numeric / non-finite OHLCV fails | PASS |
| 12 | Non-positive close fails | PASS |
| 13 | Unsupported schema fails | PASS |
| 14 | Existing backup path fails closed | PASS |
| 15 | Simulated write-validation failure leaves original unchanged | **PASS** (corrected) |
| 16 | Every test path inside its own temporary directory | PASS |
| 17 | No test path contains production/experiment raw paths | PASS |

### Fixtures / activity statement

All fixtures were **synthetic and temporary only** (tiny CSVs under a `TemporaryDirectory`, removed at
teardown), with forbidden-path assertions active. **No** production data, downloader, MT5, broker,
credentials, network, external source, market computation, PnL, strategy, backtest, or trading action
occurred.

### Status

```text
SYNTHETICALLY_VALIDATED_PENDING_SEPARATE_PRODUCTION_USE_AUTHORIZATION
```

