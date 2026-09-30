# QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION

**Title:** EURUSD–GBPUSD Cointegration Viability Falsification
**Program scope:** `FUTURE_QPF` · **Family:** `RV` (relative value)
**Status:** `preregistered` · **Decision:** NONE

> This is a **viability-falsification** pre-registration only. It is **not** an approved
> strategy, signal, portfolio sleeve, trading system, demo candidate, or live candidate. It
> authorizes **no** data work, computation, code, or execution.

---

## 1. Status and scope

This document pre-registers a single question and the gates that decide whether the question
may even be studied further. It creates no signal, no sleeve, and no executable artifact. The
only permitted next step after this pre-registration is **G0/G1 planning**, and only under a
separate explicit instruction.

## 2. Research question

> Does a hedge-ratio-adjusted EURUSD/GBPUSD log-price spread exhibit out-of-sample stationary and
> mean-reverting behavior that is sufficiently stable and economically large to justify a later
> cost-aware two-leg backtest?

## 3. Mathematical candidate formulation

The candidate spread is:

\[
s_t = \log(P_t^{EURUSD}) - \beta_t \log(P_t^{GBPUSD})
\]

where \(\beta_t\) must be estimated using **only information available before time \(t\)**. In
plain language: at each point in time, the hedge ratio is computed from past prices alone; no
future or contemporaneous-sealed information may enter its estimation. No estimation window,
estimator, or sampling frequency is fixed by this pre-registration.

## 4. Null hypotheses

- **Statistical viability.**
  - H0_1: the spread is not stationary / not cointegrated.
  - H1: the spread is stationary or cointegrated under pre-registered tests.
- **Economic viability (evaluated only in a later phase).**
  - H0_2: net expected value after all two-leg costs is less than or equal to zero.

**Stationarity or cointegration alone must never be represented as tradable edge.** Passing
H1 does not pass H0_2.

## 5. Why this is materially distinct from previous work

- The legacy program closed **directional H1 FX ML** under a triple-barrier hit/miss label and
  **FX crosses as diversification under that same directional label**. This experiment is a
  **two-leg relative-value** study whose target is **spread stationarity and mean reversion**,
  not a directional one-leg classifier, and it does not reuse the triple-barrier label.
- It is **not** a gold rule-engine variation (`EXP-2026-03-RULEENGINE`) and **not** the
  FX rule-engine transfer (`EXP-2026-04-RULEENGINE-FX-BACKTEST`).
- It is **not** a follow-up to `EXP-2026-05-INVALIDATION-REVERSAL`, which is CLOSED/STOP and must
  not be rerun, tuned, deployed, demo-tested, forward-validated, or followed up under the same
  hypothesis.
- Lineage references: `docs/falsification_ledger/no_edge_map.md`,
  `docs/falsification_ledger/LEGACY_INDEX.md`, `experiments/REGISTRY.md`.

Two statements that are frequently conflated and must be kept separate:

- **Correlation is not cointegration.** Two series may be highly correlated in levels or returns
  without any stable long-run equilibrium relationship.
- **Cointegration/stationarity is not proof of a tradable edge.** A statistically stationary
  spread can still be dominated by two-leg transaction costs, funding, and execution frictions.

## 6. Pre-registered gates and allowed transitions

All gates are `NOT_RUN` at pre-registration. Advancement is sequential; a gate that fails with a
`STOP` decision halts the experiment.

| Gate | Purpose (short) | Failure → | Pass authorizes |
|---|---|---|---|
| `G0_EXECUTION_ISOLATION` | Keep research code isolated from broker/MT5/credentials/network | STOP | Data-audit planning only |
| `G1_DATA_AUDIT` | Documented, synchronized EURUSD/GBPUSD data | PAUSE / STOP | Cost-evidence audit only |
| `G2_COST_EVIDENCE` | Measured or documented two-leg cost inputs | PAUSE | Statistical viability tests only |
| `G3_COINTEGRATION_STATIONARITY` | Out-of-sample credible spread relationship | STOP | Mean-reversion diagnostics only |
| `G4_MEAN_REVERSION` | Practically relevant reversion mechanism | STOP | Economic-viability screening only |
| `G5_ECONOMIC_VIABILITY` | Dislocations plausibly exceed two-leg round-trip cost | STOP | A separately approved cost-aware backtest only |
| `G6_COST_AWARE_BACKTEST` | Walk-forward, pre-registered policy, net EV | STOP | No deployment; at most a separate shadow-phase governance decision |

Full gate definitions (purpose, evidence required, pass criterion, failure decision, authorized
next phase) are in `experiment.yaml` under `stage_gates`.

## 7. Required future evidence

- G0: a passing static execution-isolation guard and a review of future code paths.
- G1: a versioned data manifest and audit report covering source, field semantics, timeframe,
  coverage, timezone, missingness, and timestamp alignment.
- G2: two-leg cost evidence — bid/ask or spread evidence, commissions, slippage model,
  swap/rollover convention, and order/execution assumptions — with **no fabricated values**.
- G3: Engle-Granger/ADF and Johansen where the sample design supports it, plus rolling stability
  of beta and stationarity.
- G4: half-life diagnostics, variance-ratio tests, and regime/subperiod stability.
- G5: cost-aware **descriptive** screening only (no optimized strategy, no production backtest).
- G6 (separately authorized): a walk-forward simulation of a fixed, pre-registered policy with
  bid/ask-aware or conservatively modeled fills, both-leg entry/exit costs, commissions,
  slippage, swaps, no look-ahead, chronological train/validation/sealed-test design, robustness
  checks, and net EV results.

Any ML phase requires separate explicit approval and must use the existing EURUSD methodology
contract: chronological train/validation/sealed test, purged temporal CV, recency weighting
inside training folds, synthetic-noise feature controls, PR-AUC, probability calibration,
validation-only threshold selection, and cost-adjusted sealed-test evaluation.

## 8. Explicit non-goals and prohibited actions

This pre-registration does **not** authorize, and the following are prohibited until separately
approved:

- any data download, ingestion, validation, transformation, or computation on market data;
- any Python strategy, signal, backtest, statistical-test, pipeline, cost-model, or notebook code;
- running ADF, Johansen, variance-ratio, half-life, correlation, cointegration, cost, portfolio,
  ML, or backtest calculations;
- parameter search, threshold tuning, or model/ML development;
- adding EURUSD or GBPUSD to any universe or cost configuration;
- any ML or LLM validation;
- any execution, demo, shadow, or live transition;
- any claim of tradability or edge from stationarity/cointegration alone.

The future backtest (if ever authorized) must compare against a **no-trade baseline** and must
not assume stationarity implies profitability. All costs must be treated as **two-leg** costs.

## 9. Artifact inventory

| Artifact | Path |
|---|---|
| Pre-registration manifest | `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/experiment.yaml` |
| Overview (this file) | `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/README.md` |
| Run log | `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/RUN_LOG.md` |
| Registry entry | `experiments/REGISTRY.md`, `experiments/REGISTRY.yaml` |
| Lineage references | `docs/falsification_ledger/no_edge_map.md`, `docs/falsification_ledger/LEGACY_INDEX.md` |
| Decision log (no entry yet) | `docs/decisions/DECISION_LOG.md` |

No data manifest, cost record, code path, notebook, report, or decision exists yet — by design.
