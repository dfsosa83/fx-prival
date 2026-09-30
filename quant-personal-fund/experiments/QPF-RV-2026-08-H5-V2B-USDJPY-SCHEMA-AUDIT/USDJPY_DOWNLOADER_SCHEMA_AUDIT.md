# USDJPY Downloader Schema Compatibility Audit

**Experiment context:** H5-v2 pause (`QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM`)
**Stage:** `H5_V2B_USDJPY_DOWNLOADER_SCHEMA_COMPATIBILITY_AUDIT`
**Date:** 2026-09-29 · **Nature:** read-only code/schema audit

---

## 1. Exact schema / header status of each authorized raw H1 CSV

All seven files have **6 columns** and a **header row**. Two schemas are present:

| Instrument | Header (exact) | datetime column position | Schema family |
|---|---|---|---|
| USDJPY | `open,high,low,close,volume,datetime` | 5 (last) | legacy (datetime-last) |
| EURUSD | `open,high,low,close,volume,datetime` | 5 (last) | legacy (datetime-last) |
| GBPUSD | `open,high,low,close,volume,datetime` | 5 (last) | legacy (datetime-last) |
| USDCHF | `open,high,low,close,volume,datetime` | 5 (last) | legacy (datetime-last) |
| USDCAD | `open,high,low,close,volume,datetime` | 5 (last) | legacy (datetime-last) |
| AUDUSD | `datetime,open,high,low,close,volume` | 0 (first) | canonical (download output) |
| NZDUSD | `datetime,open,high,low,close,volume` | 0 (first) | canonical (download output) |

Delimiter: comma. Header present in all seven.

## 2. First/last row structural formats (values redacted)

For every file the **first** and **last** data rows are **structurally consistent with their
header**: 6 comma-separated fields; the datetime-shaped token (`YYYY-MM-DD HH:MM:SS`) sits at the
datetime column position identified above (5 for the legacy files, 0 for AUDUSD/NZDUSD) in both the
first and last rows. No numerical price values are reported here.

## 3. Canonical schema vs. outlier

The repository’s **documented canonical schema** (downloader docstring, lines 7–8, and
`CANONICAL_COLS`, line 47) is:

```text
datetime, open, high, low, close, volume
```

- **AUDUSD, NZDUSD** match canonical (produced by the repo MT5 downloader).
- **USDJPY, EURUSD, GBPUSD, USDCHF, USDCAD** use the legacy `open,high,low,close,volume,datetime`.

**Conclusion:** USDJPY is **not** a lone outlier — it shares the legacy schema with four other
required files. The mismatch is a **legacy-file vs downloader-canonical split**, not a USDJPY-specific
defect.

## 4. Downloader code path (with line references)

File: `ml-signal-service/steps/01_download/mt5_downloader.py`.

| Concern | Location | Behavior |
|---|---|---|
| Canonical columns | line 47 | `CANONICAL_COLS = ["datetime","open","high","low","close","volume"]` (datetime first) |
| Retrieval | line 132 | `mt5.copy_rates_range(symbol, mt5_tf, from_dt, to_dt)` (via `get_rates_with_retry`, 123–137) |
| Dataframe construction | 162–164 | `pd.DataFrame(rates)`, `time`→`datetime`, `tick_volume`→`volume` |
| Column ordering | 165 | `df = df[CANONICAL_COLS]` → **datetime first** |
| Datetime formatting | 166 | `strftime("%Y-%m-%d %H:%M:%S")` (naive string) |
| Resume point | 109–120 (`get_from_date`) | if file exists: read `datetime` column, resume at last bar + 1 increment |
| Header handling | 168–169 | `file_exists = path exists and size>0`; `to_csv(..., mode="a", header=not file_exists, index=False)` → **header written only for a new/empty file** |
| Append/overwrite | 169 | **append only** (`mode="a"`); **no overwrite or full-rebuild path exists** |
| Duplicate prevention | 118 | relies solely on the `last + increment` resume point; no de-duplication of appended rows |
| Sorting | — | none explicit; relies on MT5 returning ascending bars |
| Filename resolution | 103–106 (`get_output_path`) | `ROOT/settings.paths.raw_mt5/{TF}/{symbol}_{TF}.csv` (`mkdir` if needed) |
| Pair/download loop | 191–198 (`run`) | iterates configured pairs (`pairs.yaml`); supports `--pair/--tf` |
| Credentials | 78–100 (`connect_mt5`) | loads `.env` or the frival credentials fallback; **initializes MT5 + logs in** (not invoked in this audit) |

## 5. Scope of the inconsistency

- **Not only USDJPY:** five legacy files (USDJPY, EURUSD, GBPUSD, USDCHF, USDCAD) use
  `open,high,low,close,volume,datetime`.
- **Not a general downloader design flaw per se:** the downloader is internally consistent with its
  **documented canonical schema** and with the two files it created (AUDUSD, NZDUSD).
- **Not an incorrect conclusion from the previous stage:** H5-v2 correctly detected that an append
  would misalign USDJPY. The real issue is that the pre-existing legacy files were produced by a
  **different writer convention** (datetime-last) than the current downloader (datetime-first).

## 6. Why direct append is unsafe

`download_pair` appends rows ordered `datetime,open,high,low,close,volume` with **no header** into an
existing file (line 169, `header=False`). Appending those rows under the legacy USDJPY header
(`open,high,low,close,volume,datetime`) writes the datetime string into the `open` column and shifts
every value — silently corrupting the file with no exception raised.

## 7. Existing safe overwrite/full-rebuild mode

**None.** The downloader has **only an append path** and never re-fetches full history (it resumes at
`last + 1` bar). There is no overwrite, truncate, rebuild, normalization, schema-conversion, or
backup mode.

## 8. Can the downloader output be made canonical without breaking compatible files?

The **downloader is already canonical** per its documented standard; the **legacy files deviate**.
Therefore the safe direction is **not** to change the downloader’s output order (which would break the
AUDUSD/NZDUSD canonical convention), but to perform a **schema-normalization + full rebuild** for a
legacy file (like USDJPY) when a refresh is needed. Any such change requires separate authorization.

## 9. Material conclusions and their source references

- Canonical schema is datetime-first — downloader docstring lines 7–8; `CANONICAL_COLS` line 47.
- Downloader appends datetime-first, header only when new — lines 168–169.
- Resume-at-last-bar, no dedup — lines 109–120, 118.
- No overwrite/rebuild mode — line 169 (`mode="a"`).
- Legacy files datetime-last — observed headers (§1).
- Append would misalign USDJPY — combination of §1 and line 169.

## 10. Activity statement

**No downloader execution, no import that would initialize MT5, no MT5 initialization/login, no
network/API/broker/account access, no data modification, and no market statistic or price-derived
analysis occurred.** Only code reading and header/row-structure inspection of the eight authorized
files were performed.
