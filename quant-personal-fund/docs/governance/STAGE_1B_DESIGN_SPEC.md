# Stage 1B Design Specification (FROZEN)

**Project:** quant-personal-fund  
**Milestone:** Stage 1B — transparent portfolio-baseline construction and audit  
**Date:** 2026-09-25  
**Status:** FROZEN before calculation. No parameter may be revised after results are visible.

---

## 1. Purpose

Build three reproducible, transparent portfolio baselines (equal-weight, inverse-volatility, risk-parity) on the validated 15-instrument local dataset. The purpose is portfolio construction and risk measurement, **not alpha**, not selecting the historically best portfolio, and not an investment recommendation.

## 2. Fixed Universe (15 active instruments)

| Asset class | Instruments | Base/quote | Note |
|---|---|---|---|
| FX | EURUSD, USDJPY, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, EURJPY | USD-quoted (or cross) | FX pairs; EURJPY cross |
| Equity index | SPX, NDX, SX5E, NKY | USD/EUR/JPY | SX5E EUR, NKY JPY |
| Commodity | XAUUSD, WTI, COPPER | USD | futures proxies |

Excluded (fixed): US10Y, BUND, JGB (bond leg excluded per ADR-003).

## 3. Return Convention

- **Frequency:** daily (EOD closes).
- **Convention:** log returns for time-series; annualization ×√252.
- **Base currency:** USD.
- **FX conversion:** non-USD assets (SX5E EUR, NKY JPY) converted to USD via the tested `core/fx.py` convention (log-additive; direct/inverse/cross). EURJPY cross handled per `core/fx.py`.
- **Data start/end:** 2020-02-28 (earliest common start across the 15 active instruments) through 2026-09-23 (last available). Instruments with shorter history are aligned to the common union; the portfolio starts when all 15 have data.

## 4. Rebalancing

- **Primary:** monthly (last trading day of month), per the existing `_rebalance_dates` convention.
- **Confirmatory sensitivity:** quarterly (last trading day of quarter).

## 5. Volatility Estimator

- **Estimator:** EWMA volatility, halflife 60 days, annualized ×√252, min_periods 20.
- **Lookback:** 60-day halflife (fixed).
- **Minimum history:** 60 days required before an instrument enters the inverse-vol/risk-parity weight.

## 6. Covariance Estimator

- **Estimator:** EWMA covariance, halflife 60 days, min_periods 20.
- **Shrinkage:** Ledoit-Wolf-style constant shrinkage δ=0.2 toward the identity (the existing `shrinkage_correlation` applied to the EWMA covariance) to guarantee positive definiteness.
- **Positive-definiteness handling:** if the shrunk matrix still has an eigenvalue < 0, add `|min_eig| + ε` to the diagonal (documented fallback).

## 7. Risk-Parity Definition (fixed)

- **Objective:** equal risk contribution (ERC): each instrument's marginal risk contribution equals total risk / N.
- **Solver:** iterative coordinate-descent (cyclic), convergence tolerance 1e-6 on the maximum |RC_i − target| difference.
- **Initialization:** equal weights (1/N).
- **Fallback if not converged in 2000 iterations:** return the last iterate with a convergence-flag warning (documented; never silently accepted).
- **Long-only, fully invested** (weights sum to 1), no leverage, no cash.

## 8. Weight Constraints (all three baselines)

- **Long-only:** all weights ≥ 0.
- **Fully invested:** weights sum to 1.0 per rebalance date.
- **Weight caps:** none (fixed; no cap tuning).
- **Unavailable instruments:** excluded from the weight computation for that rebalance if they lack the required 60-day history; weights renormalized over the available set.

## 9. Missing-Data Policy

- Prices are aligned on the common union index; instruments with missing observations at a given date are excluded from that date's return contribution (NaN return → 0 contribution, documented).
- The portfolio starts when all 15 active instruments have data (2020-02-28).
- No imputation of missing prices.

## 10. Cost and Financing Assumptions (from Stage 1A cost model only)

| Item | Assumption |
|---|---|
| Spread | Historical bar-spread proxy: `spread_price = spread_points × point`, per instrument (Stage 1A measured). |
| Commission | From `config/cost_model.yaml` per instrument class. |
| Slippage | `L = 0.5 × S` (frozen base). Stress: 2× spread, 2× slippage, combined. |
| Swap/financing | **0.0 — no rollover crossing** (monthly rebalance; no overnight carry modeled). Documented, not a proxy for carry. |
| Forward roll | N/A (no forward-based instruments). |
| Futures roll | Not modeled in Stage 1B (documented limitation; WTI/COPPER/XAUUSD front-month continuous series used as-is). |
| Dividend/corporate-action | Yahoo `adj_close` used for equity indices (documented proxy). |

## 11. Accounting Convention

- Reuses `portfolio/accounting_v2.py` (drift-tracked holdings, explicit trades, entry cost once, next-return-interval timing).
- Net returns = gross returns − transaction costs − holding costs (holding cost = 0 here since swap/financing = 0).
- Costs are charged only when weights change; no same-close fills.

## 12. Frozen Stress Periods (pre-defined)

| Period | Label |
|---|---|
| 2020-02-28 → 2020-03-31 | COVID crash |
| 2021-09-01 → 2022-09-30 | 2022 rate-hike / inflation shock |
| 2015–2016 (not in sample — sample starts 2020) | N/A — not evaluated |

Since the sample starts 2020-02-28, only two pre-defined stress periods are evaluable: COVID crash (2020) and the 2022 rate-hike/inflation shock. Both are fixed before calculation.

## 13. Robustness Checks (frozen; no additions after results)

1. Equal-weight vs inverse-vol vs risk-parity comparison.
2. Cost stress: base / 2× spread / 2× slippage / combined.
3. Rebalancing frequency: monthly (primary) vs quarterly (confirmatory).
4. Stress-period performance (COVID 2020, 2022 shock).
5. Top-instrument removal (remove largest single weight at each rebalance; recompute).
6. Per-asset-class contribution analysis.

## 14. Metrics (per baseline, per scenario)

Annualized return, annualized volatility, Sharpe, Sortino, Calmar, max drawdown, drawdown duration, turnover, net-vs-gross cost attribution. Plus: time-varying weights, weight concentration (HHI), risk contribution by instrument/class, currency exposure decomposition + concentration, pairwise return correlation, drawdown correlation, stress-period returns, year-by-year, block-bootstrap CIs (6h/12h blocks, 10k reps, fixed seed).

## 15. Reproducibility

Input data hashes, code/config hashes, fixed seeds, software versions, reproducibility instructions — recorded in the Stage 1B reproducibility manifest.

## 16. Decision Gate (infrastructure only)

- **GO:** results reproducible; accounting internally consistent; net returns never above gross solely due to costs; weights/constraints respected; risk attribution reconciles.
- **HOLD:** data/cost/specification gaps prevent reliable baseline construction.
- **STOP:** a deterministic accounting, data, or risk-engine defect invalidates the baseline.

**This gate determines only whether the baseline infrastructure is technically sound. It is not a strategy GO, portfolio recommendation, investment recommendation, or alpha claim.**

## 17. Frozen — No Post-Result Revision

No weight caps, optimizer, universe, leverage, rebalancing frequency, stress period, or parameter may be changed after inspecting outputs.

---

*This specification is fixed before calculation. Every output is labeled `PORTFOLIO BASELINE — NOT ALPHA EVIDENCE`.*