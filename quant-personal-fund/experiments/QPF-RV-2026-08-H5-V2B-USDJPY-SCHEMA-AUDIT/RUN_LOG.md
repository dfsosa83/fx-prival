# Run Log — QPF-RV-2026-08-H5-V2B-USDJPY-SCHEMA-AUDIT

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — H5_V2B_USDJPY_DOWNLOADER_SCHEMA_COMPATIBILITY_AUDIT

- **date:** 2026-09-29
- **stage:** `H5_V2B_USDJPY_DOWNLOADER_SCHEMA_COMPATIBILITY_AUDIT`
- **status:** `preregistered`
- **blocker audited:** `downloader_schema_incompatible_with_existing_usdjpy_append_would_misalign`
- **scope:** read-only code/schema inspection of `ml-signal-service/steps/01_download/mt5_downloader.py`
  and header/row-structure inspection of the seven authorized H1 CSVs (USDJPY plus the six others); no
  downloader execution, no MT5 initialization/login, no network/API, no data modification
- **key findings:**
  - canonical repository schema (downloader `CANONICAL_COLS`, line 47): `datetime, open, high, low, close, volume`;
  - **AUDUSD, NZDUSD** are canonical (datetime-first); **USDJPY, EURUSD, GBPUSD, USDCHF, USDCAD** are
    legacy (datetime-last) — USDJPY is **not** a lone outlier;
  - downloader appends with `mode="a"`, `header=not file_exists` (lines 168–169): appending
    datetime-first rows into a datetime-last file **misaligns/corrupts** it;
  - **no overwrite/full-rebuild mode exists**; resume-at-last-bar with no de-duplication (lines 109–120, 118);
  - the fix direction is a **schema-normalization + full rebuild**, not a downloader output change.
- **actions explicitly NOT performed:** downloader execution; MT5 initialize/login; broker/account/
  positions/orders/fills; network/API/calendar/external; data modification; price/return/statistic
  computation; any H5 screen
- **no statistical/economic/trading work; no data modification; no downloader/MT5/network activity.**
- **outputs created:**
  - `quant-personal-fund/experiments/QPF-RV-2026-08-H5-V2B-USDJPY-SCHEMA-AUDIT/USDJPY_DOWNLOADER_SCHEMA_AUDIT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-08-H5-V2B-USDJPY-SCHEMA-AUDIT/USDJPY_REFRESH_SAFE_IMPLEMENTATION_PLAN.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-08-H5-V2B-USDJPY-SCHEMA-AUDIT/RUN_LOG.md`
- **next permitted action:**
  ```text
  A separately authorized schema-normalization implementation and synthetic
  offline validation may be proposed; no USDJPY refresh or H5 screen is
  authorized by this audit.
  ```
