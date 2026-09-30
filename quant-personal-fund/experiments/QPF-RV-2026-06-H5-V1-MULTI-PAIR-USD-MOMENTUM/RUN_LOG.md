# Run Log — QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — H5_V1_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE

- **date:** 2026-09-29
- **stage:** `H5_V1_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE`
- **status:** `preregistered`
- **parent protocol:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM`
- **mandatory symbols (all present & valid):** EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD
- **raw paths/hashes:**
  - EURUSD `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` — `8161B866D6CFE233B5361A51DE09ACFE9E9B8926D400EE09751DA8E65CA6550B` (48,186)
  - GBPUSD `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` — `984C014AFA960A66ACB4BF855DD3DB1AFB81A685929B257396A6DC1D52798D09` (48,191)
  - USDJPY `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.csv` — `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC` (47,152; ends `2026-07-30 14:00:00`)
  - USDCHF `ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv` — `A25CBF3D0BF96C0A16FF41E9B157BBFFB1F94D8F268A16E5DD797D98F7134DFB` (48,191)
  - USDCAD `ml-signal-service/data/raw/mt5/H1/USDCAD_H1.csv` — `EF32C40422F4F45687E7A7E876E0F5F3F7E17F2CF2FF728D25D17DDA31BF2F31` (48,162)
  - AUDUSD `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv` — `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` (48,116)
  - NZDUSD `ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv` — `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` (48,087)
- **intersection/unmatched/excluded:** strict seven-way intersection 47,065; unmatched EURUSD 1,121 / GBPUSD 1,126 / USDJPY 87 / USDCHF 1,126 / USDCAD 1,097 / AUDUSD 1,051 / NZDUSD 1,022; excluded maximum common label `2026-07-30 14:00:00` (count 1)
- **snapshot hash/rows/range:** `h5_v1_multiseries_h1_internal_snapshot.csv` — `F0B6DBB5EFB67F74DD12C626B117124904E739C86F5DC29C41514EC2CB6E59C8` — 47,064 rows (`2019-01-02 07:00:00` → `2026-07-30 13:00:00`); `h5_v1_multiseries_h1_internal_snapshot.sha256`
- **clock:** `NOT_UTC` (ordinal internal labels only)
- **actions explicitly NOT performed:** price transformation; market statistics; returns / volatility / momentum / confirmation counts / signals / outcomes / correlations / regressions / ADF / AR-OU / variance ratios / bootstrap; costs / PnL; strategy; orders; backtest; ML; MT5 / broker / credentials / network / API / calendar / news / external data; execution / demo / shadow / live; modification of any raw data, parent design, snapshot, manifest, registry, template, experiment, or audit
- **authorization consequence (next action):**
  ```text
  Only one separately authorized H5-v1 statistical screen using the verified
  immutable seven-series snapshot and unchanged parent H5 protocol may proceed.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/experiment.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/H5_V1_DESIGN_BINDING.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/H5_V1_MULTISERIES_DATA_AUDIT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/data_manifest_v1.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/H5_V1_SNAPSHOT_FREEZE_REPORT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/H5_V1_SNAPSHOT_FREEZE_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/h5_v1_multiseries_h1_internal_snapshot.csv`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/h5_v1_multiseries_h1_internal_snapshot.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/freeze_h5_v1_multiseries_snapshot.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM/RUN_LOG.md`
