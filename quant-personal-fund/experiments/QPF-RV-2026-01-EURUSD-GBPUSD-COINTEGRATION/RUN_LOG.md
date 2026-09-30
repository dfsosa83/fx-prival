# Run Log — QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION

Append-only. Do not edit or delete prior entries; corrections are new entries.

---

## 2026-09-29 — PRE_REGISTRATION

- **date:** 2026-09-29
- **stage:** `PRE_REGISTRATION`
- **status:** `preregistered`
- **action:** Manifest and documentation created only.
- **actions explicitly NOT performed:**
  - data access / market-data download or reading;
  - MetaTrader 5 access;
  - credential or `.env` access;
  - network or external API access;
  - code implementation (strategy, signal, backtest, statistical test, pipeline, notebook);
  - statistical tests (ADF, Johansen, variance-ratio, half-life, correlation, cointegration);
  - cost calculation;
  - model training;
  - backtesting;
  - signal generation;
  - execution / demo / shadow / live actions.
- **outcome:** Awaiting separate authorization for G0/G1 planning.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/experiment.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/README.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — PHASE_0_7_G0_G1_DESIGN_SPECIFICATION

- **date:** 2026-09-29
- **stage:** `PHASE_0_7_G0_G1_DESIGN_SPECIFICATION`
- **status:** `preregistered`
- **action:** Created design-only G0/G1 specification and blank data-manifest template.
- **actions explicitly NOT performed:**
  - data access / reading / inspection;
  - source selection;
  - data acquisition / download / extraction;
  - MetaTrader 5 access;
  - credential or `.env` access;
  - network or external API access;
  - code implementation (strategy, signal, backtest, statistical test, pipeline, notebook);
  - test execution;
  - data audit;
  - cost evidence collection or calculation;
  - statistical testing (ADF, Engle-Granger, Johansen, variance-ratio, half-life, correlation, cointegration);
  - modeling / ML / LLM validation;
  - backtesting;
  - signal generation;
  - execution / demo / shadow / live actions.
- **outcome:** G0/G1 design frozen; awaiting separate explicit authorization for G0 execution verification and/or G1 data-audit execution.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G0_G1_DESIGN_SPEC.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/DATA_MANIFEST_TEMPLATE.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/experiment.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/README.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION

- **date:** 2026-09-29
- **stage:** `READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION`
- **status:** `preregistered`
- **action:** Documented future read-only MT5/credential/data access policy only.
- **actions explicitly NOT performed:**
  - MT5 access;
  - credential or `.env` access;
  - data access / reading / inspection;
  - network or external API access;
  - test execution;
  - code implementation;
  - statistical work;
  - cost work;
  - backtesting;
  - signal generation;
  - order activity;
  - execution / demo / shadow / live actions.
- **outcome:** Future read-only G1/G2 access may be separately authorized; this authorization alone grants no access.
- **immutable references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G0_G1_DESIGN_SPEC.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/experiment.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **permanent prohibitions:** no order submission/modification/cancellation; no configuration or credential changes; no secret disclosure; no production changes.
- **authorization consequence:** G0 remains a static isolation verification; future G1/G2 may use an isolated read-only adapter only after a separate explicit task-level instruction.

---

## 2026-09-29 — G0_EXECUTION_ISOLATION

- **date:** 2026-09-29
- **stage:** `G0_EXECUTION_ISOLATION`
- **status:** `preregistered`
- **action:** Executed only the two approved static isolation guards.
- **exact command:** `pytest -q tests/system/test_execution_isolation.py tests/system/test_no_lookahead.py`
- **exact result:** `8 passed in 0.83s`
- **outcome:** `G0_PASS`
- **actions explicitly NOT performed:**
  - market-data access / reading / inspection;
  - source selection;
  - data acquisition;
  - data audit;
  - MetaTrader 5 access;
  - broker access;
  - credential or `.env` access;
  - network or external API access;
  - statistical testing;
  - cost work;
  - model / ML / LLM work;
  - backtesting;
  - signal generation;
  - execution / demo / shadow / live actions.
- **authorization consequence:** only a separately approved G1 data-audit execution is now eligible.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G0_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G0_G1_DESIGN_SPEC.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/experiment.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G1_DATA_AUDIT

- **date:** 2026-09-29
- **stage:** `G1_DATA_AUDIT`
- **status:** `preregistered`
- **authorized locations inspected:**
  - `ml-signal-service\data\raw`
  - `ml-signal-service\data\raw\macro`
- **MT5 used:** `false`
- **artifacts created:**
  - `data_audit_report.md`
  - `data_quality_checks.csv`
  - `data_manifest_v1.yaml`
  - `G1_DECISION.md`
- **outcome:** `G1_PAUSE`
- **actions explicitly NOT performed:**
  - MetaTrader 5 access;
  - credential or `.env` access;
  - network or external API access;
  - cost calculation;
  - returns / correlation / cointegration / ADF / Engle-Granger / Johansen / hedge-ratio calculations;
  - model / ML / LLM work;
  - signal generation;
  - backtesting;
  - shadow / demo / live actions;
  - order activity.
- **authorization consequence:** only a separately authorized G1-R metadata/provenance remediation may proceed.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_audit_report.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_quality_checks.csv`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G0_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G0_G1_DESIGN_SPEC.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/DATA_MANIFEST_TEMPLATE.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G1R_MT5_METADATA_PROVENANCE_REMEDIATION

- **date:** 2026-09-29
- **stage:** `G1R_MT5_METADATA_PROVENANCE_REMEDIATION`
- **status:** `preregistered`
- **MT5 used:** `true` (read-only only)
- **adapter path:** `quant-personal-fund/audits/mt5_readonly/g1r_mt5_metadata_audit.py`
- **redacted symbol mapping outcome:** EURUSD -> `EURUSD` and GBPUSD -> `GBPUSD`; both `CONFIRMED_FOR_CURRENT_MT5_SAMPLE`; no suffix/alias.
- **bounded artifact paths created:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/audit_mt5_run_summary_redacted.json`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/audit_mt5_symbol_metadata_redacted.json`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/audit_mt5_h1_sample_EURUSD.csv`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/audit_mt5_h1_sample_GBPUSD.csv`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/audit_mt5_tick_sample_redacted.csv`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R_MT5_METADATA_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R_DECISION.md`
- **result:** `G1_PAUSE` (timezone/UTC-offset evidence remains `UNRESOLVED`)
- **actions explicitly NOT performed:**
  - returns / correlation / cointegration / ADF / Engle-Granger / Johansen / hedge-ratio calculations;
  - variance-ratio / Hurst / half-life calculations;
  - cost calculation;
  - model / ML / LLM work;
  - signal generation;
  - backtesting;
  - order activity;
  - execution / demo / shadow / live actions;
  - configuration, credential, or production changes.
- **authorization consequence:** G1_PAUSE; no G2-G6 work is authorized. Only a separately authorized remediation of the outstanding timezone/UTC-offset evidence (or a formally documented export procedure) may proceed.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R_MT5_METADATA_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `quant-personal-fund/audits/mt5_readonly/g1r_mt5_metadata_audit.py`
  - `quant-personal-fund/audits/mt5_readonly/README.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G1R2_TIMEZONE_PROVENANCE_RESOLUTION

- **date:** 2026-09-29
- **stage:** `G1R2_TIMEZONE_PROVENANCE_RESOLUTION`
- **status:** `preregistered`
- **evidence tiers inspected:** Tier 1 (repo export code) / Tier 2 (local docs + config) / Tier 3 (official public documentation)
- **official public documentation used:** `true` (MQL5 `copy_rates_from` doc; FP Markets page returned HTTP 403)
- **result:** `G1_PAUSE`
- **artifacts created/updated:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_TIMEZONE_PROVENANCE_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_PUBLIC_TIMEZONE_EVIDENCE.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml` (updated)
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md` (this entry)
- **key finding:** the original exporter was identified (`ml-signal-service/steps/01_download/mt5_downloader.py`: raw MT5 bar-open epoch -> `pd.to_datetime(unit="s", utc=True)` -> `strftime` tz-strip, no offset shift). Broker/server UTC offset and DST remain `UNRESOLVED`; the vendor "UTC" statement conflicts with the empirical bar-label observation.
- **actions explicitly NOT performed:**
  - MT5 trading / order activity;
  - new market-data retrieval;
  - cost calculation;
  - returns / correlation / cointegration / ADF / Engle-Granger / Johansen / hedge-ratio calculations;
  - variance-ratio / Hurst / half-life calculations;
  - model / ML / LLM work;
  - signal generation;
  - backtesting;
  - shadow / demo / live actions.
- **authorization consequence:** G1_PAUSE; no G2-G6 work is authorized. Only a separately authorized remediation documenting the broker/server offset history (or a formally validated export procedure) may proceed.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_TIMEZONE_PROVENANCE_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_PUBLIC_TIMEZONE_EVIDENCE.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G1R3_CONTROLLED_EPOCH_TIMESTAMP_PROBE

- **date:** 2026-09-29
- **stage:** `G1R3_CONTROLLED_EPOCH_TIMESTAMP_PROBE`
- **status:** `preregistered`
- **adapter path:** `quant-personal-fund/audits/mt5_readonly/g1r3_epoch_timestamp_probe.py`
- **MT5 used:** `true` (read-only only)
- **controlled probe outcome:** `BROKER_OR_TERMINAL_TIME_ANOMALY_UNRESOLVED`
- **G1 recommendation:** `G1_PAUSE` (UTC not confirmed; evidence against a UTC basis)
- **artifacts created/updated:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_EPOCH_PROBE_REDACTED.json`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_CONTROLLED_EPOCH_PROBE_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml` (updated)
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md` (this entry)
- **key finding:** raw `symbol_info_tick` epochs ~+3h ahead of system UTC and H1 rate epochs on a server-time basis (contradicting the MQL5 "UTC" claim), while `copy_ticks_from` over a UTC window returned UTC-consistent epochs — an unresolved cross-query anomaly (a local clock skew is not excluded).
- **actions explicitly NOT performed:**
  - market-data history retrieval beyond the bounded 2-bar / 50-tick probe;
  - returns / correlation / cointegration / ADF / Engle-Granger / Johansen / hedge-ratio calculations;
  - variance-ratio / Hurst / half-life calculations;
  - cost calculation;
  - model / ML / LLM work;
  - signal generation;
  - backtesting;
  - order activity;
  - execution / demo / shadow / live actions.
- **authorization consequence:** G1_PAUSE; no G2-G6 work is authorized. Only a separately authorized follow-up (independent time reference, or a documented broker server-time rule) may proceed.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_EPOCH_PROBE_REDACTED.json`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_CONTROLLED_EPOCH_PROBE_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `quant-personal-fund/audits/mt5_readonly/g1r3_epoch_timestamp_probe.py`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT

- **date:** 2026-09-29
- **stage:** `INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT`
- **status:** `preregistered`
- **action:** Documented owner-approved conditional internal-clock-only research scope.
- **result:** `APPROVED_FOR_STATISTICAL_SCREENING_ONLY`
- **original G1:** remains `PAUSE` (this is not `G1_PASS`)
- **actions explicitly NOT performed:**
  - data access / processing;
  - MT5 access;
  - credential or `.env` access;
  - network or external API access;
  - test execution;
  - statistical calculations;
  - cost calculations;
  - model / ML / LLM work;
  - signal generation;
  - backtesting;
  - order activity;
  - execution / demo / shadow / live actions.
- **authorization consequence:** the only candidate next phase is `G3-Internal Statistical Viability Screening`, and only after a separately approved task-level prompt. No G2/G4/G5/G6 work is authorized.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R2_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING

- **date:** 2026-09-29
- **stage:** `G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING`
- **status:** `preregistered`
- **input files and hash verification:**
  - `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` — expected `AFC3109108AE64E59800F99D4B87A11B58B26EDE5185DCBD3B132422E4F3DA5F`; observed `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` → **NO MATCH**
  - `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` — expected `11D9D435C1DDBC4A797BDF236ED3F3F13765338D2AD21870268016F76FD24CB7`; observed `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` → **NO MATCH**
  - **fail-closed:** the script returned before parsing any data
- **internal-clock-only constraints:** ordinal `k`; labels `NOT_UTC`; strict EURUSD/GBPUSD timestamp intersection; five unmatched GBPUSD obs and final `2026-09-29 19:00:00` excluded; no external joins/features
- **artifacts created:** `G3_INTERNAL_STATISTICAL_PROTOCOL.md`, `G3_INTERNAL_STATISTICAL_REPORT.md`, `G3_INTERNAL_DECISION.md`, `G3_INTERNAL_RESULTS.json`, `g3_internal_statistical_screening.py`
- **result:** `PAUSE_STATISTICAL_VIABILITY` (input hash precondition failed; no statistical test executed)
- **actions explicitly NOT performed:** cost/PnL/spread/slippage/commission/swap calculation, signals, entries/exits, sizing, portfolio allocation, ML/LLM, backtesting, MT5/broker/credentials/network, order activity, shadow/demo/live
- **authorization consequence:** PAUSE → no G4-G6. Remediation only: re-freeze the exact input files, record their new hashes in a new manifest version, re-verify, then a new explicit task-level run.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_STATISTICAL_PROTOCOL.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_STATISTICAL_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_RESULTS.json`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_statistical_screening.py`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G1R3_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G3R0_IMMUTABLE_INPUT_SNAPSHOT_FREEZE

- **date:** 2026-09-29
- **stage:** `G3R0_IMMUTABLE_INPUT_SNAPSHOT_FREEZE`
- **status:** `preregistered`
- **raw input paths and current source hashes:**
  - `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` — `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` (48,185 rows)
  - `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` — `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` (48,190 rows)
- **snapshot path and hash:**
  - `g3_internal_clock_snapshot_v2.csv` — `159BE4F9F1A3AD7F1F0B19675C6EB11DC4CFFDED95101898F147D041BEB0BA5D`
  - `g3_internal_clock_snapshot_v2.sha256`
- **snapshot row count and exclusions:** T = 48,184; raw strict intersection 48,185; final label `2026-09-29 19:00:00` excluded (present); 5 GBPUSD-only unmatched labels excluded; 0 EURUSD-only; no imputation/forward-fill/interpolation/resampling
- **protocol v2 artifact:** `G3_INTERNAL_STATISTICAL_PROTOCOL_V2.md`
- **result:** `SNAPSHOT_FROZEN_PENDING_G3_V2`
- **actions explicitly NOT performed:**
  - log-price transformation / returns / spread / correlation / covariance / cointegration;
  - ADF / Johansen / hedge-ratio / AR(1) / half-life / variance-ratio / Hurst / bootstrap;
  - cost / PnL / EV calculation;
  - signals / entries-exits / sizing / portfolio allocation;
  - ML / LLM;
  - backtesting;
  - MT5 / broker / credentials / network;
  - order activity;
  - execution / demo / shadow / live actions.
- **G3-v1 status:** remains `PAUSE_STATISTICAL_VIABILITY`; no statistical result was observed and no hypothesis conclusion changed.
- **authorization consequence:** only a separately approved one-time G3-v2 run using `g3_internal_clock_snapshot_v2.csv` exactly (hash-verified; comment line skipped) may proceed. No G2/G4/G5/G6 work is authorized.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_STATISTICAL_PROTOCOL.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_STATISTICAL_PROTOCOL_V2.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3R0_SNAPSHOT_FREEZE_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3R0_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v1.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v2.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_clock_snapshot_v2.csv`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_clock_snapshot_v2.sha256`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3r0_snapshot_freeze.py`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G3R0B_COMPLETED_LABEL_BOUNDARY_REPAIR

- **date:** 2026-09-29
- **stage:** `G3R0B_COMPLETED_LABEL_BOUNDARY_REPAIR`
- **status:** `preregistered`
- **result:** `SNAPSHOT_V3_FROZEN_PENDING_G3_V3`
- **rationale:** the v2 fixed-label exclusion removed the named label `2026-09-29 19:00:00` while the strict intersection then ended at `2026-09-29 20:00:00`, so v2 retained the greatest common label; v3 deterministically excludes the **maximum common label**.
- **G3-v1 and G3-v2 were not statistically executed** — no statistical result was observed in either, or in this phase.
- **raw paths and hashes:**
  - `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` — `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` (48,185 rows)
  - `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` — `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` (48,190 rows)
- **v3 snapshot path, hash, row count, first and last retained labels:**
  - `g3_internal_clock_snapshot_v3.csv` — `B372EF5B508E11A244B521C9BD7D475D05682ABEFA8A383C3372D7F56AC81448`
  - rows T = 48,184; first label `2019-01-02 00:00:00`; last retained label `2026-09-29 19:00:00`
  - `g3_internal_clock_snapshot_v3.sha256`
- **raw intersection count / excluded maximum common label / unmatched counts:** intersection 48,185; excluded maximum common label `2026-09-29 20:00:00` (count 1); unmatched EURUSD-only 0; unmatched GBPUSD-only 5
- **references:** `G3R0B_COMPLETED_LABEL_BOUNDARY_AMENDMENT.md`, `g3r0b_snapshot_freeze.py`, `data_manifest_v3.yaml`, `G3R0B_SNAPSHOT_FREEZE_REPORT.md`, `G3R0B_DECISION.md`, `g3_internal_clock_snapshot_v3.csv`, `g3_internal_clock_snapshot_v3.sha256`, `G3_INTERNAL_STATISTICAL_PROTOCOL_V2.md`, `G3R0_DECISION.md`, `G3_INTERNAL_DECISION.md`, `INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT.md`, `data_manifest_v1.yaml`, `data_manifest_v2.yaml`
- **actions explicitly NOT performed:**
  - MT5 / broker / credentials / network / external data / calendars / sessions;
  - log prices / returns / differences / spreads / hedge ratios / correlation / covariance / cointegration;
  - Johansen / ADF / AR(1) / half-life / variance ratio / Hurst / bootstrap;
  - costs / slippage / swaps / PnL / EV / Sharpe;
  - signals / positions / sizing / portfolios;
  - ML / LLM;
  - backtesting;
  - order activity;
  - G3-v2 / G3-v3 / G2 / G4 / G5 / G6 execution;
  - execution / demo / shadow / live actions.
- **authorization consequence:** Only a separately authorized, one-time G3-v3 statistical run using the hash-verified `g3_internal_clock_snapshot_v3.csv` exactly, with its comment line skipped, may proceed. No G2, G4, G5, or G6 work is authorized.
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3R0B_COMPLETED_LABEL_BOUNDARY_AMENDMENT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3r0b_snapshot_freeze.py`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_clock_snapshot_v3.csv`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_clock_snapshot_v3.sha256`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v3.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3R0B_SNAPSHOT_FREEZE_REPORT.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3R0B_DECISION.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`

---

## 2026-09-29 — G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING_V3

- **date:** 2026-09-29
- **stage:** `G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING_V3`
- **status:** `preregistered`
- **input:** `g3_internal_clock_snapshot_v3.csv`; SHA256 verified `B372EF5B508E11A244B521C9BD7D475D05682ABEFA8A383C3372D7F56AC81448` (match)
- **internal-clock-only:** ordinal labels `NOT_UTC`; T = 48,184; no raw EURUSD/GBPUSD CSV read; no external joins; differences of the residual spread used only for AR(1)/VR/bootstrap diagnostics
- **splits:** train 28,910 / validation 9,606 / sealed 9,608; 30-bar embargoes
- **train hedge OLS:** alpha = -0.1033, beta = 0.8561, R2 = 0.7756
- **result:** `REJECT_STATISTICAL_VIABILITY`
- **key statistics:** validation residual ADF p = 0.4375; sealed residual ADF p = 0.0847; Johansen rank train = 1 / validation = 0 / sealed = 2; pre-sealed primary rolling pass rate = 3.03% (W4000 = 2.94%, W6000 = 3.13%); sealed rolling = 0% (0/4); AR(1) validation b = -0.000709 p = 0.0662, sealed b = -0.001312 p = 0.0031; variance-ratio compatible on validation & sealed; subperiods 0/3 (validation) and 0/3 (sealed); bootstrap b 95% CI validation includes 0, sealed below 0
- **artifacts created:** `g3_internal_statistical_viability_v3.py`, `G3_INTERNAL_RESULTS_V3.json`, `G3_INTERNAL_DECISION_V3.md`
- **actions explicitly NOT performed:**
  - costs / spreads / slippage / swaps / PnL / returns / EV / Sharpe;
  - signals / entries-exits / position sizing / portfolio construction;
  - ML / LLM;
  - backtesting / order activity / execution / demo / shadow / live;
  - MT5 / broker / credentials / network / API / external data;
  - calendar/session/absolute-time interpretation;
  - raw EURUSD/GBPUSD CSV access beyond snapshot v3;
  - G2 / G4 / G5 / G6 execution.
- **authorization consequence:** REJECT → no G2/G4/G5/G6. The statistical hypothesis is closed; only a materially distinct, newly pre-registered hypothesis could reopen research. Approval (had it occurred) would have meant only "proceed to cost-aware economic testing".
- **immutable artifact references:**
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_statistical_viability_v3.py`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_RESULTS_V3.json`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_DECISION_V3.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_clock_snapshot_v3.csv`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/g3_internal_clock_snapshot_v3.sha256`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/G3_INTERNAL_STATISTICAL_PROTOCOL_V2.md`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/data_manifest_v3.yaml`
  - `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md`
- **lineage references:**
  - `docs/falsification_ledger/no_edge_map.md`
  - `docs/falsification_ledger/LEGACY_INDEX.md`
  - `experiments/REGISTRY.md`
  - `experiments/REGISTRY.yaml`
