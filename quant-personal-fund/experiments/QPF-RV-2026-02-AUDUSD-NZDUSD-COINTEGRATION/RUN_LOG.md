# Run Log — QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — G1_AUDNZD_IMMUTABLE_SNAPSHOT_FREEZE

- **date:** 2026-09-29
- **stage:** `G1_AUDNZD_IMMUTABLE_SNAPSHOT_FREEZE`
- **status:** `preregistered`
- **raw file paths and hashes:**
  - `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv` — `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` (48,116 rows)
  - `ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv` — `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` (48,087 rows)
- **intersection count:** 48,030
- **excluded maximum common label:** `2026-09-24 18:00:00` (count 1); unmatched AUDUSD-only 86, NZDUSD-only 57
- **snapshot path/hash/row count:** `audnzd_h1_internal_snapshot_v1.csv` — `B4F90F302C5181FBC881318910CC3904E9CB9C95CC400AF3D29FA42218E71BB2` — 48,029 rows (`2019-01-02 07:00:00` → `2026-09-24 17:00:00`); `audnzd_h1_internal_snapshot_v1.sha256`
- **clock:** `NOT_UTC` (ordinal internal labels only)
- **actions explicitly NOT performed:** log prices / returns / spreads / correlations / regressions / hedge ratios / cointegration / ADF / Johansen / AR-OU / half-life / variance ratios / bootstrap / costs / slippage / swaps / PnL / signals / positions / ML / optimization / backtests / MT5 / broker / credentials / network / order / execution / demo / shadow / live
- **authorization consequence:** Only one separately authorized G3 statistical screen on the verified snapshot may proceed.
- **artifact references:**
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/experiment.yaml`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/G0_G1_DESIGN_SPEC.md`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/G1_DATA_AUDIT.md`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/AUDNZD_SNAPSHOT_FREEZE_REPORT.md`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/AUDNZD_SNAPSHOT_FREEZE_DECISION.md`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/audnzd_h1_internal_snapshot_v1.csv`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/audnzd_h1_internal_snapshot_v1.sha256`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/freeze_audnzd_snapshot.py`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/RUN_LOG.md`

---

## 2026-09-29 — G3_AUDNZD_STATISTICAL_VIABILITY_SCREENING

- **date:** 2026-09-29
- **stage:** `G3_AUDNZD_STATISTICAL_VIABILITY_SCREENING`
- **status:** `preregistered`
- **input:** `audnzd_h1_internal_snapshot_v1.csv`; SHA256 verified `B4F90F302C5181FBC881318910CC3904E9CB9C95CC400AF3D29FA42218E71BB2` (match)
- **internal-clock-only:** ordinal labels `NOT_UTC`; T = 48,029; splits train 28,817 / validation 9,575 / sealed 9,577 with 30-bar embargoes
- **train hedge OLS:** alpha = 0.009714, beta = 0.862457, R2 = 0.872321
- **result:** `REJECT_STATISTICAL_VIABILITY`
- **key statistics:** validation residual ADF p = 0.1508; sealed residual ADF p = 0.9503; Johansen rank train/validation/sealed = 0/0/0; pre-sealed primary rolling 6.06% (W4000 2.94%, W6000 6.25%); sealed rolling 0%; AR(1) validation b = -0.001449 p = 0.0078 (HL 478), sealed b = -0.0000291 p = 0.835; variance-ratio compatible (all horizons) in validation and sealed; subperiods 0/3 both; bootstrap b 95% CI validation below 0, sealed includes 0
- **artifacts created:** `g3_audnzd_statistical_viability.py`, `G3_AUDNZD_INTERNAL_RESULTS.json`, `G3_AUDNZD_INTERNAL_DECISION.md`
- **actions explicitly NOT performed:** costs / slippage / swaps / PnL / returns / Sharpe / drawdown; signals / entries / exits / position sizing / portfolios; ML / optimization; backtests; MT5 / broker / credentials / network / API / calendar / external data; order activity; execution / demo / shadow / live; other candidate pairs
- **authorization consequence:** REJECT → no economic/PnL test, no G2/G4/G5/G6, no trading. Only a materially distinct, newly pre-registered hypothesis could reopen research for this pair.
- **artifact references:**
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/g3_audnzd_statistical_viability.py`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/G3_AUDNZD_INTERNAL_RESULTS.json`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/G3_AUDNZD_INTERNAL_DECISION.md`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/audnzd_h1_internal_snapshot_v1.csv`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/audnzd_h1_internal_snapshot_v1.sha256`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/G0_G1_DESIGN_SPEC.md`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION/RUN_LOG.md`
