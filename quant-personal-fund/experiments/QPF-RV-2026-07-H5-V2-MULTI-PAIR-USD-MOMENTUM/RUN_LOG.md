# Run Log — QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — H5_V1B_USDJPY_HISTORY_COMPLETENESS_REPAIR

- **date:** 2026-09-29
- **stage:** `H5_V1B_USDJPY_HISTORY_COMPLETENESS_REPAIR`
- **status:** `preregistered`
- **parent protocol:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM` (unchanged)
- **old USDJPY provenance:** `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.csv` — schema
  `open,high,low,close,volume,datetime`; 47,152 rows; `2019-01-02 00:00:00` → `2026-07-30 14:00:00`;
  SHA256 `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC`; validation PASS
- **downloader use:** `ml-signal-service/steps/01_download/mt5_downloader.py` — intended for
  **historical H1 bars only**; **NOT invoked** (fail-closed)
- **blocker:** downloader appends `datetime,open,high,low,close,volume` (no header) into an existing
  file, but USDJPY is `open,high,low,close,volume,datetime`; invoking it would misalign/corrupt USDJPY
- **updated source hash/range:** none — USDJPY was **not modified** (no update)
- **v2 snapshot hash/range:** none — **no v2 snapshot created**
- **completeness threshold** `2026-09-24 18:00:00`: **NOT MET**
- **result:** `PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY`
- **actions explicitly NOT performed:** instrument add/remove/substitute; H5 protocol change; any
  download/update for any symbol other than USDJPY; rewrite/normalize/interpolate/resample of any raw
  file; macro/calendar/news/external access; price transformation / log return / volatility /
  momentum / correlation / signal / outcome / regression / statistical test / cost / PnL / backtest /
  ML / trading metric; MT5 account balance/equity/positions/orders/transactions/fills or execution
  state; order/execution/demo/shadow/live; modification of H5-v1 snapshot artifacts or any parent
  design/manifest/registry/template/experiment
- **next action (failure):**
  ```text
  H5-v1 is paused; no substitution, download, or H5 statistical screen is
  authorized under this stage. A later authorized stage must first reconcile the
  downloader append schema with the existing raw-file schema (or otherwise obtain
  a schema-consistent USDJPY update), then create the v2 snapshot.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/experiment.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_DESIGN_BINDING.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_USDJPY_COMPLETENESS_AUDIT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/data_manifest_v2.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_SNAPSHOT_FREEZE_REPORT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_SNAPSHOT_FREEZE_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/repair_usdjpy_and_freeze_h5_v2.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM/RUN_LOG.md`
