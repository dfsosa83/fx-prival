# Run Log — QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — H5_MULTI_PAIR_USD_MOMENTUM_VOLATILITY_DESIGN

- **date:** 2026-09-29
- **stage:** `H5_MULTI_PAIR_USD_MOMENTUM_VOLATILITY_DESIGN`
- **status:** `preregistered`
- **action:** Froze the H5 multi-pair USD momentum / volatility-conditioned directional hypothesis,
  protocol, candidate universe, selection/multiplicity rules, and implementation blueprint.
  Design-only.
- **hypothesis summary:** coordinated USD strength/weakness across major FX pairs, conditional on a
  high-volatility regime, may predict directional continuation over near-future H1 horizons.
  Predictive-**statistical** only; not a trading strategy.
- **fixed USD confirmation basket (USDJPY mandatory):** EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD
- **target panel and expected signs (USD-strength / USD-weakness):**
  - EURUSD: Negative / Positive
  - GBPUSD: Negative / Positive
  - USDJPY: Positive / Negative
  - USDCHF: Positive / Negative
  - USDCAD: Positive / Negative
  - AUDUSD: Negative / Positive
  - NZDUSD: Negative / Positive
- **fixed grid:** `L ∈ {4,8,24,48}`, `H ∈ {4,8,24}`, `V ∈ {24,72}`, `K ∈ {3,4}`, directions = {USD
  strength, USD weakness}
- **basket treatments:** target-**excluded** = primary selection/multiplicity; target-**included** =
  secondary diagnostic only (never selects)
- **snapshot requirement:** hash-verified immutable strict multiseries H1 intersection of
  `EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`; exclude exactly the maximum common label;
  no imputation/resampling/transformation; `NOT_UTC`
- **splits/embargo:** 60/20/20 chronological with 30-bar embargoes; outcomes must not cross segments
  or embargoes
- **selection/multiplicity/escalation:** validation-only survivor gate (paired strength/weakness);
  BH FDR `q=0.10` across the 672 target-excluded primary tests; **max three** bound configurations
  to sealed; sealed evaluated once
- **actions explicitly NOT performed:** any market-data read/download/parse/hash; any log prices,
  returns, volatility, correlations, momentum, signal values, outcomes, regressions, statistical
  tests, or descriptive market statistics; costs / PnL / drawdown / Sharpe; strategy / orders /
  execution / demo / shadow / live; MT5 / broker / credentials / network / API / calendar / news /
  external data; modification of any existing file, experiment, snapshot, manifest, registry, source,
  code, or prior decision
- **authorization consequence / next permitted action:**
  ```text
  A separate authorization may create a hash-verified immutable H1 multiseries
  snapshot containing EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, and
  NZDUSD, then run exactly one H5-v1 statistical screen under this unchanged
  protocol.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM/H5_RESEARCH_QUESTION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM/H5_CANDIDATE_UNIVERSE.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM/H5_PROTOCOL.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM/H5_SELECTION_AND_MULTIPLICITY.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM/H5_IMPLEMENTATION_BLUEPRINT.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM/RUN_LOG.md`
