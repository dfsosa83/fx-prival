# XAUUSD Real Refresh & Canonical Rebuild — Audit

**Stage:** `XAUUSD_H6_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD`
**Experiment audit dir:** `quant-personal-fund/experiments/QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH/`
**Date:** 2026-09-30
**Result:** `XAUUSD_REAL_REFRESH_COMPLETE_PENDING_H6_DATA_REAUDIT`

---

## 1. Authorization and scope

Narrowly authorized real-data repair of the H6 gold stratum: refresh **only** XAUUSD raw H1 history via
read-only historical retrieval, then rebuild the complete XAUUSD raw CSV into the canonical schema
using the synthetically validated safe utility. Data integrity/completeness only; no H6 breakout,
invalidation, returns, outcomes, costs, PnL, signals, or trading.

## 2. Preflight (passed before any MT5 access)

| Field | Verified |
|---|---|
| Path | `ml-signal-service/data/raw/mt5/H1/XAUUSD_H1.csv` |
| SHA256 | `A36F2E2331B38E72A6D2874B625DB981AED92220499204D18E8CE58D71332CFA` (matches H6 audit) |
| Schema | `open,high,low,close,volume,datetime` (matches) |
| Rows | 45,077 (matches) |
| First/final label | `2019-01-02 01:00:00` / `2026-08-17 16:00:00` (match) |
| Integrity | no null/duplicate labels; strictly ascending; finite numeric OHLCV; close > 0 — PASS |

## 3. Immutable backup

- Backup (byte-for-byte copy, same H1 directory):
  `ml-signal-service/data/raw/mt5/H1/XAUUSD_H1.pre_h6_refresh_20260930.csv`
- Backup SHA256 equals the pre-stage source SHA256 (`A36F2E23…332CFA`) — equality **verified**.
- Recorded in `XAUUSD_H1_PRE_REBUILD_BACKUP.sha256`.

## 4. Read-only retrieval

- Repository tool: the **retrieval logic only** of `ml-signal-service/steps/01_download/mt5_downloader.py`
  (`connect_mt5` + `get_rates_with_retry`), invoked **in memory**; `download_pair` was **not** called,
  so the downloader never appended to the legacy raw file.
- Retrieval was **XAUUSD H1 historical bars only**; downloader stdout/stderr suppressed.
- **No account/balance/equity/margin/positions/orders/deals/executions/fills/transactions/history was
  queried or reported.**
- Retrieved: 732 bars, `2026-08-17 17:00:00` → `2026-09-30 14:00:00`.

## 5. Old vs new

| | Old (legacy) | New (canonical) |
|---|---|---|
| Schema | `open,high,low,close,volume,datetime` | `datetime,open,high,low,close,volume` |
| Rows | 45,077 | 45,809 |
| First label | `2019-01-02 01:00:00` | `2019-01-02 01:00:00` |
| Final label | `2026-08-17 16:00:00` | `2026-09-30 14:00:00` |
| SHA256 | `A36F2E23…332CFA` | `6DB76DE379FCF0EF65E60597B1A14AC3DD5E3466E01216D7386702CB14FB7F36` |

- Newly added labels: **732**.
- Identical overlapping rows: **0**; conflicts: **none**.
- Candidate re-read/revalidation: PASS; atomic replacement: PASS; post-replacement SHA256 equals the
  candidate SHA256. Recorded in `XAUUSD_H1_POST_REBUILD.sha256`.

## 6. Completeness threshold

Required final label ≥ `2026-09-24 18:00:00`; achieved `2026-09-30 14:00:00` → **threshold MET**.

## 7. No price values / statistics reported

No price values, log prices, returns, volatility, ranges, breakout/invalidation, outcomes, costs, PnL,
backtests, ML, or trading metrics were computed or reported. Labels are opaque ordinals (`NOT_UTC`).

## 8. Prohibited activities not performed

No other symbol modified/read-for-analysis/rebuilt; no downloader/utility/config/credential/`.env`/
terminal/protocol/snapshot/manifest/registry modified; no account/execution state accessed; no orders;
no macro/calendar/news/external/network beyond the limited read-only MT5 history retrieval; no H6
snapshot or H6 screen.
