# Run Log — QPF-RV-2026-09-USDJPY-REAL-REFRESH

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — USDJPY_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD

- **date:** 2026-09-29
- **stage:** `USDJPY_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD`
- **status:** `preregistered`
- **pre hash/range:** `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC`; legacy
  `open,high,low,close,volume,datetime`; 47,152 rows; `2019-01-02 00:00:00` → `2026-07-30 14:00:00`
- **backup path/hash:** `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.pre_h5_refresh_20260929.csv`
  (`BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC`); recorded in
  `USDJPY_H1_PRE_REBUILD_BACKUP.sha256`
- **post hash/range:** `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858`; canonical
  `datetime,open,high,low,close,volume`; 48,191 rows; `2019-01-02 00:00:00` → `2026-09-29 21:00:00`;
  recorded in `USDJPY_H1_POST_REBUILD.sha256`
- **retrieval:** 1,039 USDJPY H1 bars (`2026-07-30 15:00:00` → `2026-09-29 21:00:00`) via the
  repository downloader’s retrieval logic in memory; downloader stdout/stderr suppressed; the
  downloader did **not** append to any raw file
- **rebuild:** added labels 1,039; identical overlap rows 0; no conflicts; candidate revalidated;
  atomic replace OK; post SHA equals candidate SHA
- **completeness threshold** `2026-09-24 18:00:00`: **MET**
- **result:** `USDJPY_REAL_REFRESH_COMPLETE_PENDING_H5_V2_SNAPSHOT`
- **no analytics/trading/account activity:** no log prices/returns/volatility/momentum/correlations/
  signals/outcomes/regressions/statistical tests/costs/PnL/backtests/ML/trading metrics; no
  account/balance/equity/margin/positions/orders/deals/executions/fills/transactions/history; no
  orders; no macro/calendar/news/external/network beyond limited MT5 read-only history retrieval; no
  other symbol touched; no H5 snapshot or H5 screen
- **next authorization consequence:**
  ```text
  A separate authorization is required to create a new seven-series H5-v2
  snapshot freeze using all sources under the unchanged H5 protocol. No H5
  statistical screen is authorized by this stage.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-09-USDJPY-REAL-REFRESH/refresh_and_rebuild_usdjpy.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-09-USDJPY-REAL-REFRESH/USDJPY_REAL_REFRESH_AUDIT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-09-USDJPY-REAL-REFRESH/USDJPY_REAL_REFRESH_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-09-USDJPY-REAL-REFRESH/USDJPY_H1_PRE_REBUILD_BACKUP.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2026-09-USDJPY-REAL-REFRESH/USDJPY_H1_POST_REBUILD.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2026-09-USDJPY-REAL-REFRESH/USDJPY_REAL_REFRESH_RUN_LOG.md`
