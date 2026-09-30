# Run Log — QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — H6_FAILED_BREAKOUT_INVALIDATION_DESIGN

- **date:** 2026-09-30
- **stage:** `H6_FAILED_BREAKOUT_INVALIDATION_DESIGN`
- **status:** `preregistered`
- **action:** Froze the H6 failed-breakout invalidation hypothesis, protocol, candidate universe,
  selection/multiplicity rules, and implementation blueprint. Design-only.
- **hypothesis summary:** a breakout beyond a pre-defined trailing high/low that fails and re-enters
  its prior range within a limited number of future H1 bars may contain statistically detectable
  information about subsequent price movement opposite to the original breakout. Predictive-statistical
  event study only.
- **frozen H1 universe:** EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD (evaluated individually);
  **separate XAUUSD stratum** (never pooled with FX, never used to rank FX). H1 only in H6-v1; M15/D1
  only as later separately documented replication designs.
- **event classes:** `FAILED_UPWARD_BREAKOUT`, `FAILED_DOWNWARD_BREAKOUT` (required together).
- **fixed grid:** N ∈ {12, 24, 48}; M ∈ {2, 4, 8}; H ∈ {4, 8, 24} → 54 directional tests per
  instrument.
- **timing:** breakout at t → invalidation k* ∈ [1,M] → **event timestamp e = t+k*** → outcome
  y_e(H) = log(P_{e+H}/P_e) begins strictly after confirmation.
- **controls / selection / multiplicity / sealed:** deterministic same-segment controls matched by
  `(e - segment_start) mod H` phase; **validation-only** selection with BH FDR **q=0.10** across the
  **378** primary tests; survivors need ≥30 events, ≥200 controls and all directional checks in both
  classes; **at most three** bound configurations to sealed, evaluated once.
- **actions explicitly NOT performed:** any market-data read/download/parse/hash; prices / log prices /
  returns / volatility / ranges / highs / lows / breakout or invalidation events / correlations /
  regressions / ADF / statistical tests / costs / PnL / drawdown / Sharpe / signals / entries / exits /
  sizing / portfolio / ML / model outputs; MT5 / broker / credentials / `.env` / terminal / network /
  API / calendar / news / external data; orders / execution / demo / shadow / live; modification of any
  existing artifact
- **next permitted action:**
  ```text
  A separate authorization may audit H1 data availability for the H6 FX universe
  and XAUUSD, then freeze immutable snapshots before any H6 statistical screen.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION/H6_RESEARCH_QUESTION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION/H6_PROTOCOL.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION/H6_CANDIDATE_UNIVERSE.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION/H6_SELECTION_AND_MULTIPLICITY.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION/H6_IMPLEMENTATION_BLUEPRINT.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION/RUN_LOG.md`
