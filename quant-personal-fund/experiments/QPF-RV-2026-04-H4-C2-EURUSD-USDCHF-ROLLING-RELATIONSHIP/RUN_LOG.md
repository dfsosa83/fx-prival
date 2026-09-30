# Run Log — QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — H4_C2_IMMUTABLE_SNAPSHOT_FREEZE

- **date:** 2026-09-29
- **stage:** `H4_C2_IMMUTABLE_SNAPSHOT_FREEZE`
- **status:** `preregistered`
- **parent protocol ID:** `QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY`
- **candidate / order / orientation:** C2 (first H4 candidate) — `log(EURUSD)` on `log(USDCHF)`
- **raw input paths/hashes:**
  - `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` — `8161B866D6CFE233B5361A51DE09ACFE9E9B8926D400EE09751DA8E65CA6550B` (48,186 rows)
  - `ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv` — `A25CBF3D0BF96C0A16FF41E9B157BBFFB1F94D8F268A16E5DD797D98F7134DFB` (48,191 rows)
- **intersection/unmatched/excluded:** raw strict intersection 48,186; unmatched EURUSD-only 0, USDCHF-only 5; excluded maximum common label `2026-09-29 21:00:00` (count 1)
- **snapshot hash/row count/range:** `eurusd_usdchf_h1_internal_snapshot_v1.csv` — `67590790F8BF0E20A707792D8DE85077C6D1067BD45035B05744D5D235E1DBF6` — 48,185 rows (`2019-01-02 00:00:00` → `2026-09-29 20:00:00`); `eurusd_usdchf_h1_internal_snapshot_v1.sha256`
- **clock:** `NOT_UTC` (ordinal internal labels only)
- **actions explicitly NOT performed:** statistical/economic tests; log prices / changes / returns / spreads / correlations / OLS / hedge ratios / ADF / AR-1 / half-life / Johansen / variance ratios / bootstrap; costs / PnL / drawdown / Sharpe; signals / entries-exits / sizing / portfolios; ML / LLM; backtests; MT5 / broker / credentials / network / API / calendar / external data; order / execution / demo / shadow / live; modification of any raw data, config, credentials, earlier experiment, H4 design file, registry, or template
- **authorization consequence:** Only one separately authorized H4-C2 screen using the verified immutable snapshot and unchanged parent H4 protocol may proceed.
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/experiment.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/H4_C2_DESIGN_BINDING.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/H4_C2_DATA_AUDIT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/data_manifest_v1.yaml`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/H4_C2_SNAPSHOT_FREEZE_REPORT.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/H4_C2_SNAPSHOT_FREEZE_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/eurusd_usdchf_h1_internal_snapshot_v1.csv`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/eurusd_usdchf_h1_internal_snapshot_v1.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/freeze_h4_c2_snapshot.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/RUN_LOG.md`

---

## 2026-09-29 — H4_C2_ROLLING_RELATIONSHIP_SCREEN

- **date:** 2026-09-29
- **stage:** `H4_C2_ROLLING_RELATIONSHIP_SCREEN`
- **status:** `preregistered`
- **input:** `eurusd_usdchf_h1_internal_snapshot_v1.csv`; SHA256 verified `67590790F8BF0E20A707792D8DE85077C6D1067BD45035B05744D5D235E1DBF6` (match); input validation PASS
- **split/embargo:** T = 48,185; train 28,911 [0,28911) · embargo 30 · validation 9,607 [28941,38548) · embargo 30 · sealed 9,607 [38578,48185)
- **validation summaries (W: complete / eligible / elig_rate / passes / pass_rate / eligible-for-selection):**
  - W=1000: 8 / 1 / 0.1250 / 0 / 0.0000 / NO (<3 eligible)
  - W=2000: 7 / 1 / 0.1429 / 0 / 0.0000 / NO (<3 eligible)
  - W=5000: 4 / 1 / 0.2500 / 0 / 0.0000 / NO (<3 eligible)
- **selection:** no W selected (`selected_W = null`); all W failed `eligible_blocks >= 3`
- **sealed:** not evaluated (validation selection failed)
- **result:** `REJECT_ROLLING_STATISTICAL_VIABILITY`
- **failed requirement(s):** `eligible_blocks >= 3` failed for every W (1 eligible block each); consequently ≥2 passes, pass rate ≥60%, and selection all fail
- **actions explicitly NOT performed:** costs / PnL / returns / drawdown / Sharpe; signals / entries / exits / sizing / portfolios; strategy / backtests; ML / LLM; MT5 / broker / credentials / `.env` / network / API / calendar / news / external data; downloader; order / execution / demo / shadow / live; other candidate pairs; no parameter tuning after results
- **authorization consequence:** REJECT → no cost/PnL/economic test, no G2/G4/G5/G6, no trading. Rejection applies only to this C2 orientation / H1 / H4 design; other candidates (C3, C4, C5) remain untested.
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/h4_c2_rolling_relationship_screen.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/H4_C2_ROLLING_RESULTS.json`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/H4_C2_ROLLING_DECISION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/eurusd_usdchf_h1_internal_snapshot_v1.csv`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/eurusd_usdchf_h1_internal_snapshot_v1.sha256`
  - `quant-personal-fund/experiments/QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP/RUN_LOG.md`
