# H5-v2 — Snapshot Freeze Report

**Experiment:** `QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V2_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE` · **Date:** 2026-09-29
**Parent protocol:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM`
**Result:** `SNAPSHOT_V2_FROZEN_PENDING_H5_V2_SCREEN`

---

## 1. Scope

Deterministic, data-preparation-only freeze of one immutable internal-clock H1 seven-series snapshot
for H5-v2. No statistical/economic screen; no market statistic; no costs, PnL, strategy, backtest, ML,
or trading/execution.

## 2. Repair provenance

USDJPY was refreshed and canonically rebuilt in the prior authorized stage
(`USDJPY_REAL_REFRESH_COMPLETE_PENDING_H5_V2_SNAPSHOT`): canonical schema now
`datetime,open,high,low,close,volume`, 48,191 rows, ending `2026-09-29 21:00:00`,
SHA256 `810F789A…A5858`. The original legacy file is preserved as an immutable backup.

## 3. Source integrity

All seven mandatory files validated (schema/integrity PASS). **USDJPY assertion PASS** (hash, schema,
final label). See `H5_V2_MULTISERIES_DATA_AUDIT.md` for per-source hashes/rows/ranges.

## 4. Strict seven-way construction

- Raw strict seven-way intersection: **48,029**
- Unmatched: EURUSD 157 · GBPUSD 162 · USDJPY 162 · USDCHF 162 · USDCAD 133 · AUDUSD 87 · NZDUSD 58
- Excluded exactly one label — maximum common label `2026-09-24 18:00:00`.

## 5. Snapshot

| Field | Value |
|---|---|
| File | `h5_v2_multiseries_h1_internal_snapshot.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_7WAY_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Schema | `internal_index_k, timestamp_label_internal, eurusd_close, gbpusd_close, usdjpy_close, usdchf_close, usdcad_close, audusd_close, nzdusd_close` |
| Rows (T) | **48,028** |
| First / last retained label | `2019-01-02 07:00:00` / `2026-09-24 17:00:00` |
| SHA256 | `751EE1647D54E5402C762141DB8D8B547118C9825BDCBFB988F48F2DDA8B2588` |

## 6. Prohibitions respected

No MT5/downloader/broker/account/credentials/`.env`/network/calendar/external access; no raw-source
modification; no other symbol touched; no snapshot omitting USDJPY; no market statistic beyond
integrity/label-range/intersection/unmatched/hashes; no H5-v2 screen.

## 7. Recommendation

```text
SNAPSHOT_V2_FROZEN_PENDING_H5_V2_SCREEN
```
