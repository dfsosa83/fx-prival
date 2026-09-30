# H5-v2 — USDJPY Completeness Audit

**Experiment:** `QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V1B_USDJPY_HISTORY_COMPLETENESS_REPAIR`
**Date:** 2026-09-29
**Result:** `PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY`

---

## 1. USDJPY before update

| Field | Value |
|---|---|
| Path | `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.csv` |
| Schema | `open,high,low,close,volume,datetime` |
| Rows | 47,152 |
| First label | `2019-01-02 00:00:00` |
| Last label | `2026-07-30 14:00:00` |
| SHA256 | `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC` |
| Validation | PASS (`datetime`+`close` present; no nulls/duplicates; strictly ascending; finite positive closes) |
| Known H5-v1 final label | `2026-07-30 14:00:00` |

## 2. Downloader identity and intended use

- Downloader: `ml-signal-service/steps/01_download/mt5_downloader.py`.
- Intended use: **historical H1 bars only** for USDJPY; would write only `USDJPY_H1.csv`; no account
  state, orders, positions, or execution.
- Downloader append schema (`CANONICAL_COLS`): `datetime,open,high,low,close,volume`, appended with
  `header=not file_exists` (no header for an existing file).

## 3. Blocker (fail-closed)

The existing USDJPY raw file is ordered **`open,high,low,close,volume,datetime`** (datetime **last**),
whereas the downloader appends rows ordered **`datetime,open,high,low,close,volume`** (datetime
**first**) with **no header**. Invoking the downloader would therefore write misaligned rows into
USDJPY (a datetime string into the `open` column, etc.), **corrupting the raw source**.

Per the requirement that the downloader "use the project's established raw CSV schema" and the
prohibition against corrupting raw data, the downloader was **not invoked**; USDJPY was **not
modified**; and **no v2 snapshot was created**.

- `blocker`: `downloader_schema_incompatible_with_existing_usdjpy_append_would_misalign`
- Existing USDJPY schema: `["open","high","low","close","volume","datetime"]`
- Downloader append schema: `["datetime","open","high","low","close","volume"]`

## 4. USDJPY after update

Not updated (no download attempted). New hash/rows/range do not exist. **Extension status: none.**

## 5. Completeness threshold

Target threshold `2026-09-24 18:00:00` — **NOT MET** (no update occurred). Decision:
`PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY`.

## 6. Activity statement

No account, balance, equity, position, order, transaction, fill, execution, cost, or statistical
activity occurred beyond read-only inspection of USDJPY (schema/rows/range/hash). No other symbol was
touched.
