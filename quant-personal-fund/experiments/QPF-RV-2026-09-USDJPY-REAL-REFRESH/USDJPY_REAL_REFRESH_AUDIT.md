# USDJPY Real Refresh & Canonical Rebuild — Audit

**Stage:** `USDJPY_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD`
**Experiment audit dir:** `quant-personal-fund/experiments/QPF-RV-2026-09-USDJPY-REAL-REFRESH/`
**Date:** 2026-09-29
**Result:** `USDJPY_REAL_REFRESH_COMPLETE_PENDING_H5_V2_SNAPSHOT`

---

## 1. Scope and authorization

One narrowly authorized real-data repair: refresh **only** the USDJPY raw H1 history via the repository
MT5 downloader (read-only historical retrieval) and rebuild the complete USDJPY raw CSV into the
canonical schema using the synthetically validated utility. Data integrity/completeness only — no
statistics, economics, backtest, PnL, strategy, or trading.

## 2. Preflight (passed before any MT5 access)

| Field | Verified |
|---|---|
| Path | `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.csv` |
| SHA256 | `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC` (matches) |
| Schema | `open,high,low,close,volume,datetime` (matches) |
| Rows | 47,152 (matches) |
| First/last label | `2019-01-02 00:00:00` / `2026-07-30 14:00:00` (match) |
| Integrity | no null/duplicate labels; strictly ascending; finite numeric OHLCV; close > 0 — PASS |

## 3. Immutable backup

- Backup (byte-for-byte copy, same raw directory):
  `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.pre_h5_refresh_20260929.csv`
- Backup SHA256 equals the pre-stage source SHA256 (`BF92FF40…A4CBC`) — equality **verified**.
- Recorded in `USDJPY_H1_PRE_REBUILD_BACKUP.sha256` as
  `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC  USDJPY_H1.pre_h5_refresh_20260929.csv`.

## 4. Retrieval method

- Repository tool: `ml-signal-service/steps/01_download/mt5_downloader.py` (its retrieval logic only:
  `connect_mt5` + `get_rates_with_retry`), invoked **in memory** — `download_pair` was **not** called,
  so the downloader never appended to any raw file.
- Retrieval was **USDJPY H1 historical bars only**; the downloader’s stdout/stderr were suppressed.
- **No account/balance/equity/margin/positions/orders/deals/executions/fills/transactions/history was
  queried or reported.**
- Retrieved: 1,039 bars, `2026-07-30 15:00:00` → `2026-09-29 21:00:00`.

## 5. Old vs new

| | Old (legacy) | New (canonical) |
|---|---|---|
| Schema | `open,high,low,close,volume,datetime` | `datetime,open,high,low,close,volume` |
| Rows | 47,152 | 48,191 |
| First label | `2019-01-02 00:00:00` | `2019-01-02 00:00:00` |
| Last label | `2026-07-30 14:00:00` | `2026-09-29 21:00:00` |
| SHA256 | `BF92FF40…A4CBC` | `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858` |

- **Newly added labels:** 1,039.
- **Identical overlapping rows:** 0.
- **Conflict status:** none (no overlapping datetimes).
- Candidate re-read/revalidation: PASS; atomic replace: PASS; post-replacement SHA256 equals the
  candidate SHA256. Recorded in `USDJPY_H1_POST_REBUILD.sha256` as
  `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858  USDJPY_H1.csv`.

## 6. Completeness threshold

Required final label ≥ `2026-09-24 18:00:00`; achieved `2026-09-29 21:00:00` → **threshold MET**.

## 7. No market statistics reported

No log prices, returns, volatility, momentum, correlations, signals, outcomes, regressions,
statistical tests, costs, PnL, backtests, ML results, trading metrics, or portfolio values were
computed or reported.

## 8. Prohibited activities not performed

No other symbol updated/read-for-analysis/rebuild (EURUSD, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD
untouched); no downloader/utility/test/config/credential/`.env`/terminal/registry/protocol/snapshot/
manifest/strategy code modified; no account/execution state accessed; no orders; no macro/news/
calendar/external/network beyond the limited MT5 read-only history retrieval; no H5 screen or H5
snapshot.
