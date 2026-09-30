# Phase 0.7 — G0/G1 Design Specification

**Experiment:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV` — status `preregistered`
**Nature:** Design-only, frozen contract. Creates no data, no code, no results.

This document freezes the audit contract for **G0 (execution isolation)** and **G1 (data audit)**
in advance, so that data-quality, timestamp, coverage, source, and cost-evidence rules cannot be
altered after data is inspected. G2–G6 are defined only where needed to bound G0/G1; they are not
authorized here.

---

## Scope and Authorization Boundary

This is a **design-only** phase. It authorizes:

- writing and freezing this specification and the blank data-manifest template;
- pre-defining the G0/G1 pass, pause, and stop rules.

It authorizes **none** of the following: data access; data acquisition; data inspection; market
computation; source selection; model building; signal creation; backtesting; test execution;
broker, MT5, credential, or network interaction.

Any future **G0 or G1 execution requires a separate explicit user instruction.** Nothing in this
design specification constitutes approval to read, fetch, or compute on any data.

## G0 — Execution Isolation Verification Design

G0 verifies that research code cannot reach execution, broker, MT5, credentials, or network side
effects. It uses the existing static guards (do **not** run now):

```text
pytest -q tests/system/test_execution_isolation.py tests/system/test_no_lookahead.py
```

**G0 pass criterion:**

- Both static safety tests pass.
- Any future code introduced for G1 planning/audit is reviewed statically before it is relied upon.
- No research-library module under `core/`, `data/pipelines/`, `signals/`, `portfolio/`,
  `risk/`, `backtest/`, `llm_tools/`, or `monitoring/` imports or references execution, broker,
  MT5, credentials, or prohibited network/runtime dependencies — except the documented existing
  narrow allowlist in `data/pipelines/download.py` for `yfinance` and `fredapi`.
- No experiment artifact will import execution code.

**G0 failure consequences:**

- Any unexplained violation is `STOP`.
- A documented safe exception requires **explicit user approval** before any allowlist change.
- G0 pass authorizes **only** G1 data-audit execution — not G2 or statistical work.

## G1 — Data Audit Design

The later G1 audit is **descriptive and provenance-focused**. It must **not** compute
cointegration, correlation, half-life, variance ratio, hedge ratios, trading signals,
returns-based alpha, costs, or backtests.

G1 is limited to:

- file/source discovery authorized in the later phase;
- schema and field inspection;
- timestamp/timezone inspection;
- date range and coverage inspection;
- missingness, duplicates, ordering, and completeness checks;
- instrument identity and symbol mapping checks;
- cross-instrument timestamp alignment checks;
- price-field semantics checks: bid, ask, mid, OHLC, close, and tick volume;
- market-closure / weekend / holiday handling checks;
- DST / broker-server time issues;
- dataset hashing and manifest creation;
- documentation of limitations and gaps.

## Candidate Data Source Hierarchy

No source is selected now. A hierarchy is pre-registered:

1. **Primary candidate:** broker-native historical export or read-only source that can document
   FP Markets/MT5 symbol semantics, server timezone, bid/ask availability, and extraction coverage.
2. **Secondary candidate:** independent institutional or commercial FX source with documented
   timestamp convention, bid/ask or a defensible mid-price methodology, instrument definition,
   and coverage.
3. **Tertiary candidate:** reputable public/historical source suitable **only** for statistical
   screening if its limitations are documented. It is **not** sufficient by itself for
   execution-cost approval.
4. **Not acceptable alone for G2/G6:** unexplained OHLC-only datasets, screenshots, manually
   copied prices, unknown-timezone data, or sources without provenance.

The later G1 audit may **inventory** candidate sources, but a source must not be selected as
approved until its evidence is recorded in the data manifest and the G1 decision report.

## Canonical Data Contract

Minimum required **dataset-level metadata**:

- manifest_id
- experiment_id
- instrument
- broker_or_vendor
- source_type
- symbol_as_received
- canonical_symbol
- asset_class
- timeframe
- timezone_as_received
- canonical_timezone
- extraction_method
- extraction_timestamp_utc
- requested_date_range
- received_date_range
- field_definitions
- source_file_path_or_uri
- file_format
- checksum_sha256
- row_count
- source_limitations
- access_scope
- created_by
- manifest_version

Required **time-series fields**:

- timestamp
- open
- high
- low
- close
- tick_volume_or_volume
- bid_open, bid_high, bid_low, bid_close — when available
- ask_open, ask_high, ask_low, ask_close — when available
- spread_points_or_spread_price — when available
- source_symbol
- canonical_symbol
- timeframe
- source_timezone
- timestamp_utc
- bar_completion_status or equivalent metadata — when available

Fields unavailable from a source must be explicitly marked `UNAVAILABLE` — never silently
inferred or filled. Price type must be explicit: **bid, ask, mid, last, or unknown**. **Unknown
price semantics fail G1.**

## Timestamp and Timezone Standard

Pre-registered standard:

- Internal canonical timestamp: **timezone-aware UTC**.
- Preserve the raw timestamp and the source timezone in raw metadata.
- Never silently strip timezone information.
- If MT5/broker time is used later, identify server time, UTC-offset history, DST convention,
  and the conversion method.
- Alignment is based on **completed bars only**.
- A bar must not be treated as completed before the next bar boundary or an equivalent explicit
  completion marker.
- Cross-instrument alignment must be performed on canonical UTC timestamps.
- No forward fill across missing bars is permitted for statistical testing without later explicit
  justification and documentation.

## Frequency and Coverage Decision Framework

No final frequency is selected now. Candidate frequency classes are pre-registered:

- **H1:** primary initial candidate — consistent with existing research infrastructure and may
  mitigate intraday microstructure noise.
- **H4:** secondary robustness candidate — lower turnover, fewer observations.
- **M15:** conditional candidate only if data-quality and execution evidence later justify it;
  it must **not** be introduced merely to search for an edge.
- **D1:** contextual robustness candidate — not assumed to be the execution frequency.

Coverage principle:

- Historical coverage must support chronological train, validation, and sealed-test segments,
  multiple market regimes, and rolling stability checks.
- The exact minimum dates, number of bars, and split boundaries must be proposed **after** G1
  descriptive facts are known and **frozen before G3**.
- Coverage must include enough non-overlapping rolling windows to assess stability; a single
  favorable period is insufficient.
- Data with material unexplained gaps, ambiguous timezone, or unknown bar-completion semantics
  cannot advance.

## Required Data Quality Checks

Checks and required audit outputs, for **both EURUSD and GBPUSD**:

- schema validation and field availability;
- UTC conversion validation;
- strict monotonic timestamps;
- duplicate timestamp count and handling proposal;
- missing expected bar count and gap distribution;
- maximum consecutive missing bars;
- weekend / market-close / holiday classification;
- partial/incomplete-bar identification;
- OHLC integrity: non-null, finite, positive; `high >= max(open, close)`;
  `low <= min(open, close)`; `high >= low`;
- bid/ask consistency when present: `bid <= ask` and non-negative spread;
- spread sanity **description** when present, but **no trading-cost calculation in G1**;
- symbol identity and broker suffix/prefix mapping;
- date-range overlap across EURUSD and GBPUSD;
- canonical-UTC timestamp alignment rate;
- price semantic classification: bid/ask/mid/unknown;
- raw-file checksum and reproducible manifest link;
- source limitations and survivorship/data-revision concerns.

Required audit table columns:

- check_name
- instrument
- result
- severity
- evidence_path
- rule_applied
- remediation_needed
- G1_impact

## Data Provenance and Manifest Requirements

The later actual data manifest must be based on `DATA_MANIFEST_TEMPLATE.yaml` (created in this
phase). It must contain:

- all dataset-level fields listed in the canonical contract;
- data quality summary;
- checksums;
- raw source references;
- timezone conversion declaration;
- bar-completion declaration;
- cross-instrument alignment declaration;
- G1 decision recommendation;
- explicit `NOT_RUN` placeholders for G2–G6;
- **no** trading metrics, **no** cointegration metrics, **no** model metrics, and **no** cost values.

A manifest is **immutable** after its related G1 audit starts. Corrections require a new manifest
version and a new hash, with an append-only RUN_LOG entry.

## G2 Cost-Evidence Requirements

Specify only; do **not** execute. G2 will require separately sourced evidence for each leg and
each relevant side/direction:

- spread or bid/ask evidence;
- commission schedule;
- slippage model and its provenance;
- swap/rollover long and short convention;
- rollover-day convention, including any triple-swap treatment;
- contract size, point/pip definition, minimum lot, and margin assumptions;
- order type and fill assumptions;
- session/time-of-day sensitivity;
- any currency conversion required for account-currency PnL;
- entry and exit costs for both legs.

G2 cannot use fabricated values, generic internet assumptions, or costs inherited from a
different broker/symbol/account without documentation. G2 pass is needed before any claim of
economic viability. As defined in the pre-registered experiment gates, G3 statistical testing may
use price-only data **only after** G2 documentation exists.

## Explicitly Deferred Work

Deferred and unauthorized in this phase (and until separately approved):

- source selection or source approval;
- data acquisition, extraction, download, reading, parsing, or storage;
- data cleaning or transformation;
- updating `config/universe.yaml` or `config/cost_model.yaml`;
- EURUSD/GBPUSD additions to any production system;
- ADF, Engle-Granger, Johansen, correlation, hedge-ratio, half-life, variance-ratio, Hurst, or
  regime calculations;
- feature engineering, ML, noise features, calibration, ensembles, threshold selection, LLM
  validation;
- signal generation, trade sizing, risk allocation, portfolio construction;
- cost measurement or cost calculation;
- backtesting, walk-forward testing, sealed-test design execution;
- shadow, demo, or live trading;
- changes to `frival/` or `ml-signal-service/`.

## G0/G1 Decision Rules

- **`G0_PASS`:** both static guards pass and static review finds no disallowed dependency in the
  permitted research-library scope.
- **`G0_STOP`:** any unexplained prohibited dependency, execution reachability, credential access,
  or broker/MT5/network side effect.
- **`G1_PASS`:** manifest and audit report document acceptable source provenance, known price
  semantics, canonical timezone conversion, completed-bar semantics, adequate and aligned
  coverage, and no material unresolved integrity defect.
- **`G1_PAUSE`:** potentially usable data exists but required evidence is missing; coverage is
  insufficient; bid/ask semantics are unavailable; timezone is unresolved; or a remediable
  data-quality issue remains.
- **`G1_STOP`:** fundamentally unusable or irreconcilable data; unknown price semantics; inability
  to align instruments; or defects that prevent a credible later analysis.

Authorization chain:

- `G0_PASS` authorizes **only** the execution of G1 under a new explicit instruction.
- `G1_PASS` authorizes **only** G2 evidence collection under a new explicit instruction.
- **No gate result authorizes G3, G4, G5, G6, shadow, demo, or live action automatically.**

## Required Future Artifacts

Do **not** create these now; they belong to their respective separately authorized phases:

```text
experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/
├── data_audit_report.md                # G1 only
├── data_quality_checks.csv             # G1 only
├── data_manifest_v1.yaml               # G1 only
├── G0_DECISION.md                      # G0 only
├── G1_DECISION.md                      # G1 only
└── reports/
    └── G2_COST_EVIDENCE_SPEC.md        # G2 only
```

## Phase 0.7 Completion Boundary

This phase ends after the design specification, the blank data-manifest template, and one
append-only RUN_LOG entry are written.

The next permitted action is a separately authorized **G0 execution verification and/or G1
data-audit execution**. No source access or computation is authorized by this design
specification itself.
