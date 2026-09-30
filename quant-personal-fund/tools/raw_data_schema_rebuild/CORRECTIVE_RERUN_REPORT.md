# Corrective Rerun Report — safe_h1_csv_rebuild

**Stage:** `USDJPY_SAFE_REBUILD_UTILITY_CORRECTIVE_RERUN`
**Date:** 2026-09-29
**Result:** **PASS — 16 tests, 16 passed (0 failed, 0 errored).**

---

## 1. Stage identity and permitted scope

Narrow corrective stage for the offline H1 CSV schema-rebuild utility. Permitted reads/writes were
limited to:

```text
quant-personal-fund/tools/raw_data_schema_rebuild/safe_h1_csv_rebuild.py
quant-personal-fund/tools/raw_data_schema_rebuild/test_safe_h1_csv_rebuild.py
quant-personal-fund/tools/raw_data_schema_rebuild/SYNTHETIC_VALIDATION_REPORT.md
```

and creation of exactly one new file (`CORRECTIVE_RERUN_REPORT.md`). `README.md` was **not** modified
(no objectively false statement existed: it already states “no null/duplicate datetime” validation,
which remains true).

## 2. Two defects repaired

1. **Utility — null datetime validation.** `read_and_normalize` applied `astype(str)` before the null
   check, turning an empty datetime (`NaN`) into the literal `"nan"` and bypassing the guard.
   **Correction:** new `_assert_valid_datetime_labels()` rejects null/NaN, empty string,
   whitespace-only, and literal `"nan"`/`"NaN"` (after stripping), and is called **before** any
   `astype(str)` in `read_and_normalize` and in the merge normalized copy; `validate_canonical_frame`
   uses the same check. Opaque non-empty labels remain untouched (no parsing/localization/inference).
2. **Test — simulated candidate validation failure.** The test patched `read_and_normalize` across its
   own setup call, raising before the intended reread point. **Correction:** the synthetic frame is
   built **before** `mock.patch`, so the failure occurs only inside `write_candidate_atomic` at the
   candidate re-read/validation step; the test asserts the expected error is raised, the original
   content **and** SHA256 are unchanged, no backup is created, no `.tmp` remains, and all paths stay
   inside the temporary test directory.

## 3. Test command and result

```text
python -m unittest -v test_safe_h1_csv_rebuild.py
```

Total tests: **16**. Final result: **OK — 16 passed, 0 failed, 0 errored.** Cases 10 (null datetime)
and 15 (simulated write-validation failure) now **PASS**.

## 4. Changes limited to permitted files

Changes were limited to the two permitted source/test files (`safe_h1_csv_rebuild.py`,
`test_safe_h1_csv_rebuild.py`) and the two reports (`SYNTHETIC_VALIDATION_REPORT.md` appended;
`CORRECTIVE_RERUN_REPORT.md` created). No canonical columns, accepted schemas, merge rules, atomic
replacement design, backup semantics, or test-path isolation design were changed; no new public APIs,
schemas, path behaviors, automatic execution, production paths, symbols, downloader integration,
refresh logic, or analytics were added.

## 5. No production or external activity

No production CSV or raw-data path was accessed/read/hashed/copied/modified; no experiment directory
was inspected; no downloader, MetaTrader5, broker, credentials, `.env`, network/API, terminal
settings, external source, calendar, news, account, orders, positions, fills, demo/shadow/live system
was accessed; the utility was **not** run on any real path; no H5 run or snapshot creation occurred.
No market computation, PnL, strategy, backtest, or trading action occurred. All fixtures were
synthetic and temporary only.

## 6. Status

```text
SYNTHETICALLY_VALIDATED_PENDING_SEPARATE_PRODUCTION_USE_AUTHORIZATION
```

## 7. Exact next authorization consequence

```text
The utility is synthetically validated. A separate explicit authorization is
required before any review or use against a real USDJPY source. That future
stage must remain limited to read-only historical retrieval, canonical
full-file rebuild, immutable backup, hash verification, and subsequent
independent snapshot freeze. No H5 statistical screen is authorized.
```
