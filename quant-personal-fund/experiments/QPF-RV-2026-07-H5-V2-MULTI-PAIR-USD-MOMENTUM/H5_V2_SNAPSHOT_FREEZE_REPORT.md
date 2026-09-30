# H5-v2 — Snapshot Freeze Report (PAUSE; no snapshot)

**Experiment:** `QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V1B_USDJPY_HISTORY_COMPLETENESS_REPAIR` · **Date:** 2026-09-29
**Result:** `PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY`

---

## 1. Scope and data-only prohibitions

Data-preparation-only USDJPY completeness repair + intended v2 snapshot freeze. No market statistic,
return, volatility, momentum, signal, outcome, PnL, cost, backtest, ML, or trading/execution was
computed; no account/position/order/execution access.

## 2. USDJPY completeness repair

- Before: `USDJPY_H1.csv`, schema `open,high,low,close,volume,datetime`, 47,152 rows, label range
  `2019-01-02 00:00:00` → `2026-07-30 14:00:00`, SHA256
  `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC`, validation PASS.
- Downloader: `ml-signal-service/steps/01_download/mt5_downloader.py` (historical H1 only).
- **Blocker (fail-closed):** the downloader appends rows ordered
  `datetime,open,high,low,close,volume` with no header for an existing file, while the existing USDJPY
  file is ordered `open,high,low,close,volume,datetime`; invoking it would **misalign/corrupt** USDJPY.
  Therefore the downloader was **not invoked**, USDJPY was **not modified**, and **no v2 snapshot was
  built**.
- After: **no update** (no new hash/rows/range). Completeness threshold `2026-09-24 18:00:00`: **NOT
  MET**.

## 3. Raw-hash reference (unchanged)

No raw file was modified. EURUSD/GBPUSD/USDCHF/USDCAD/AUDUSD/NZDUSD were not read or altered in this
stage beyond the frozen v1 provenance already recorded; v1 snapshot artifacts are untouched.

## 4. Strict seven-way freeze

**Not performed** — aborted at the completeness gate (fail-closed).

## 5. v2 snapshot

**Not created.** `h5_v2_multiseries_h1_internal_snapshot.csv` and its `.sha256` do not exist.

## 6. Clock

`NOT_UTC` (ordinal internal labels only) — unchanged.

## 7. Prohibited work not performed

No price transformation, statistics, costs, PnL, signals, ML, backtest, execution, MT5 account state,
orders, positions, or external/calendar/news access; no instrument added/removed/substituted; no H5
protocol change; no raw file rewritten other than the permitted (never-attempted) USDJPY update; no
v1 snapshot artifact modified.

## 8. Recommendation

```text
PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY
```
