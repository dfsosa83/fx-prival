# Run Log — QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — XAUUSD_H6_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD

- **date:** 2026-09-30
- **stage:** `XAUUSD_H6_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD`
- **status:** `preregistered`
- **pre hash/range:** `A36F2E2331B38E72A6D2874B625DB981AED92220499204D18E8CE58D71332CFA`; legacy
  `open,high,low,close,volume,datetime`; 45,077 rows; `2019-01-02 01:00:00` → `2026-08-17 16:00:00`
- **backup path/hash:** `ml-signal-service/data/raw/mt5/H1/XAUUSD_H1.pre_h6_refresh_20260930.csv`
  (`A36F2E2331B38E72A6D2874B625DB981AED92220499204D18E8CE58D71332CFA`); recorded in
  `XAUUSD_H1_PRE_REBUILD_BACKUP.sha256`
- **post hash/range:** `6DB76DE379FCF0EF65E60597B1A14AC3DD5E3466E01216D7386702CB14FB7F36`; canonical
  `datetime,open,high,low,close,volume`; 45,809 rows; `2019-01-02 01:00:00` → `2026-09-30 14:00:00`;
  recorded in `XAUUSD_H1_POST_REBUILD.sha256`
- **retrieval restriction:** XAUUSD H1 historical bars only, in memory via the repository downloader’s
  retrieval logic (`connect_mt5` + `get_rates_with_retry`); `download_pair` not called; downloader
  output suppressed; no account/execution state; the legacy raw file was not written during retrieval
- **retrieval result:** 732 bars (`2026-08-17 17:00:00` → `2026-09-30 14:00:00`); added labels 732;
  identical-overlap rows 0; no conflicts; candidate revalidated; atomic replace OK; post SHA == candidate SHA
- **completeness threshold** `2026-09-24 18:00:00`: **MET**
- **result:** `XAUUSD_REAL_REFRESH_COMPLETE_PENDING_H6_DATA_REAUDIT`
- **prohibition statement:** no log prices / returns / volatility / ranges / breakout or invalidation
  events / correlations / regressions / statistical tests / costs / PnL / backtests / ML / strategy
  metrics; no account/balance/equity/margin/positions/orders/deals/fills/transactions/history; no
  orders; no macro/calendar/news/external/network beyond the limited read-only MT5 history retrieval;
  no other symbol touched; no H6 snapshot or H6 screen
- **next authorization consequence:**
  ```text
  A separate authorization is required to re-audit H6 data availability, then
  freeze XAUUSD independently (as its own stratum) before its H6 screen. No H6
  statistical screen is authorized by this stage.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH/refresh_and_rebuild_xauusd.py`
  - `quant-personal-fund/experiments/QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH/XAUUSD_REAL_REFRESH_AUDIT.md`
  - `quant-personal-fund/experiments/QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH/XAUUSD_REAL_REFRESH_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH/XAUUSD_H1_PRE_REBUILD_BACKUP.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH/XAUUSD_H1_POST_REBUILD.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2027-01-XAUUSD-H6-REAL-REFRESH/XAUUSD_REAL_REFRESH_RUN_LOG.md`
