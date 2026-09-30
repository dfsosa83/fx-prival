# Run Log — QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — H5_V2_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE

- **date:** 2026-09-29
- **stage:** `H5_V2_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE`
- **status:** `preregistered`
- **parent protocol:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM` (unchanged)
- **predecessor:** `QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM` (`FROZEN_UNUSED_USDJPY_STALE`)
- **USDJPY assertion:** PASS — SHA256 `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858`; schema `datetime,open,high,low,close,volume`; final label `2026-09-29 21:00:00`
- **raw hashes (all seven):** EURUSD `8161B866…6550B` · GBPUSD `984C014A…798D09` · USDJPY `810F789A…A5858` · USDCHF `A25CBF3D…134DFB` · USDCAD `EF32C404…BF2F31` · AUDUSD `0BF89F68…110A66` · NZDUSD `9707F4D0…7A85E9`
- **intersection / unmatched / excluded:** strict seven-way intersection 48,029; unmatched EURUSD 157 / GBPUSD 162 / USDJPY 162 / USDCHF 162 / USDCAD 133 / AUDUSD 87 / NZDUSD 58; excluded maximum common label `2026-09-24 18:00:00` (count 1)
- **snapshot hash/range:** `h5_v2_multiseries_h1_internal_snapshot.csv` — `751EE1647D54E5402C762141DB8D8B547118C9825BDCBFB988F48F2DDA8B2588` — 48,028 rows (`2019-01-02 07:00:00` → `2026-09-24 17:00:00`); `h5_v2_multiseries_h1_internal_snapshot.sha256`
- **clock:** `NOT_UTC`
- **prohibitions:** no MT5/downloader/broker/account/credentials/`.env`/network/calendar/external access; no raw-source modification; no other symbol touched; no market statistic beyond integrity/label-range/intersection/unmatched/hashes; no H5-v2 screen
- **next authorization consequence:**
  ```text
  Only one separately authorized H5-v2 statistical screen using the verified
  immutable seven-series v2 snapshot (comment line skipped) and the unchanged
  parent H5 protocol may proceed. No PnL/cost/strategy/backtest/trading/execution
  work is authorized, and H5-v1 remains immutable but unused.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/experiment.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_DESIGN_BINDING.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_MULTISERIES_DATA_AUDIT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/data_manifest_v2.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_SNAPSHOT_FREEZE_REPORT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_SNAPSHOT_FREEZE_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/h5_v2_multiseries_h1_internal_snapshot.csv`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/h5_v2_multiseries_h1_internal_snapshot.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/freeze_h5_v2_multiseries_snapshot.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/RUN_LOG.md`

---

## 2026-09-29 — H5_V2_DIRECTIONAL_STATISTICAL_SCREEN

- **date:** 2026-09-29
- **stage:** `H5_V2_DIRECTIONAL_STATISTICAL_SCREEN`
- **status:** `preregistered`
- **input:** `h5_v2_multiseries_h1_internal_snapshot.csv`; SHA256 verified
  `751EE1647D54E5402C762141DB8D8B547118C9825BDCBFB988F48F2DDA8B2588` (match); input validation PASS
- **splits/embargoes:** T = 48,028; train 28,816 [0,28816) · embargo 30 · validation 9,575
  [28846,38421) · embargo 30 · sealed 9,577 [38451,48028)
- **primary validation grid:** 672 target-excluded tests; numeric p-values 672; not-testable 0
- **BH FDR:** q=0.10 over 672 numeric p-values; **2** tests passed BH (both EURUSD); 13 tests had HAC p<0.05
- **targets (primary):** EURUSD BH-pass 2; all other targets 0; favorable-Δ counts EURUSD 53, GBPUSD 32,
  USDJPY 42, USDCHF 73, USDCAD 21, AUDUSD 16, NZDUSD 32
- **secondary diagnostics:** 672 target-included records (descriptive only; not in BH)
- **survivors:** **0**; **selected configurations:** **0**
- **sealed:** intentionally **not evaluated** (no validation configuration qualified)
- **result:** `REJECT_DIRECTIONAL_STATISTICAL_VIABILITY`
- **actions explicitly NOT performed:** PnL / trading/strategy return / equity / drawdown / Sharpe /
  win rate / profit factor / costs / spreads / commissions / slippage / swaps / financing / latency /
  fills / order-book / entries / exits / stops / sizing / portfolio; any new indicator/model/ML/LLM/
  optimization/bootstrap/cointegration test; MT5 / broker / credentials / `.env` / network / API /
  calendar / news / external data; order / execution / demo / shadow / live; no H5-v2 snapshot change,
  no parameter tuning after results
- **authorization consequence:** REJECT → no cost/PnL/economic test, no strategy/backtest/trading.
  Rejection applies only to this H5-v2 target/basket/H1 configuration family; it does not reject FX
  momentum generally, and no retuning is authorized.
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/h5_v2_directional_statistical_screen.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_DIRECTIONAL_RESULTS.json`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/H5_V2_DIRECTIONAL_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/h5_v2_multiseries_h1_internal_snapshot.csv`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/h5_v2_multiseries_h1_internal_snapshot.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM/RUN_LOG.md`
