# G3-v3 Decision — Internal Statistical Viability Screening

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING_V3`
**Decision:** `REJECT_STATISTICAL_VIABILITY`

**Scope limitation:** Internal clock only; no absolute UTC/session/event alignment.

---

## Frozen gate evaluation

| Check | Result | Key statistic |
|---|---|---|
| C1 snapshot hash verification | **PASS** | `B372EF5B…1448` matches |
| C2 intersection/exclusion rules followed | **PASS** | T = 48,184; labels ordinal `NOT_UTC` |
| C3 validation residual ADF p < 0.05 | **FAIL** | ADF −1.688, p = **0.4375** |
| C3 sealed residual ADF p < 0.05 | **FAIL** | ADF −2.642, p = **0.0847** |
| C4 Johansen rank ≥ 1 (val & sealed) | **FAIL** | rank val = **0**, sealed = 2, train = 1 |
| C5 pre-sealed rolling pass rate ≥ 60% | **FAIL** | **3.03%** (1/33 blocks) |
| C6 validation AR(1) b<0, p<0.05, finite HL | **FAIL** | b = −0.000709, p = **0.0662**, HL 977.4 bars |
| C6 sealed AR(1) b<0, p<0.05, finite HL | **PASS** | b = −0.001312, p = 0.0031, HL 527.9 bars |
| C7 ≥2 of 4 VR horizons mean-reversion-compatible (val) | **PASS** | val VR compatible |
| C7 ≥2 of 4 VR horizons mean-reversion-compatible (sealed) | **PASS** | sealed VR compatible |
| C8 ≥2 of 3 subperiods pass ADF & b<0 (val) | **FAIL** | **0/3** |
| C8 ≥2 of 3 subperiods pass ADF & b<0 (sealed) | **FAIL** | **0/3** |
| C9 bootstrap AR(1) b 95% CI below 0 (val) | **FAIL** | CI [−0.001486, **+0.0000054**] (includes 0) |
| C9 bootstrap AR(1) b 95% CI below 0 (sealed) | **PASS** | CI [−0.002432, −0.000360] |
| C10 no prohibited feature/calculation | **PASS** | — |

**Supporting statistics:** TRAIN hedge `alpha = −0.1033`, `beta = 0.8561`, `R² = 0.7756`. Primary
pre-sealed rolling pass rate 3.03% (W=4,000: 2.94%; W=6,000: 3.13%); sealed rolling 0/4 = 0%.
Bootstrap uses "stationary-bootstrap resampling of aligned AR(1) observations" (1,000 resamples,
avg block 24, seed 42).

## Key reasons

Multiple mandatory rejection conditions are met: the validation and sealed residual spreads are **not
stationary at 5%** under the TRAIN-fixed hedge ratio (p = 0.4375 and 0.0847); the validation AR(1)
coefficient is not significant (p = 0.0662); the **pre-sealed rolling pass rate is 3.03% (< 40%**);
**0 of 3** subperiods pass in both validation and sealed; the validation bootstrap b CI includes
zero; and the validation Johansen rank is 0. The relationship does **not** exhibit stable,
mean-reverting statistical viability out of sample.

## Interpretation

`REJECT_STATISTICAL_VIABILITY` means the frozen statistical relationship is **not** viable as a
mean-reverting candidate. It does **not** assert an economic or trading conclusion, and it does
**not** authorize any economic test.

## Authorization consequence

**REJECT → no G2/G4/G5/G6 work.** The statistical hypothesis is closed; only a **materially
distinct, newly pre-registered hypothesis** could reopen research. No approval to proceed to
cost-aware economic testing.

## Declaration

No costs, spreads, slippage, swaps, PnL, returns, signals, entries/exits, sizing, portfolio
construction, ML/LLM, backtest, order, execution, MT5, broker, credentials, network, API, external
data, calendar/session interpretation, or live/demo/shadow trading occurred. `statistical_only:
true`; `not_economic_or_tradable: true`. No parameter was tuned after inspecting results; the
single frozen run is final for this phase.

## Artifacts

- `g3_internal_statistical_viability_v3.py`
- `G3_INTERNAL_RESULTS_V3.json`
- `G3_INTERNAL_DECISION_V3.md`
- `RUN_LOG.md` (appended)
