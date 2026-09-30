# Stage 1B v1.2 — Rerun Report (Warm-Up vs Performance Evaluation)

**Project:** quant-personal-fund  
**Milestone:** Stage 1B  
**Date:** 2026-09-28  
**Label:** All results **PORTFOLIO BASELINE — NOT ALPHA EVIDENCE**

---

## 1. Technical Gate Result

### **GO — baseline infrastructure is technically sound**

The warm-up/evaluation-window issue is resolved under the v1.2 versioned specification:

- **`data_start`** = 2020-02-28 (first available bar; all 15 instruments present)
- **`warmup_only_period`** = 2020-02-28 → 2020-06-30 (estimator warm-up only; non-invested)
- **`first_eligible_rebalance`** = **2020-06-30** (first month-end where every instrument has ≥60 valid observations within the 200-day lookback)
- **`performance_evaluation_start`** = 2020-06-30 (NAV and metrics begin here)
- **`performance_evaluation_end`** = 2026-09-23

**The warm-up interval is excluded from NAV and all performance metrics.** No flat warm-up returns are reported as investment outcomes.

**COVID crash window (before 2020-06-30): NOT EVALUABLE.** No claim is made that the baselines were stress-tested through the COVID crash.

**No investment recommendation, no strategy GO.** This GO applies only to baseline-infrastructure technical validity.

---

## 2. Valid-Observation Counts and Eligibility

| Instrument | Valid obs (2020-02-28 →) | First valid |
|---|---|---|
| AUDUSD, EURJPY, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY | 1,706 | 2020-02-28 |
| SX5E | 1,609 | 2020-02-28 |
| XAUUSD, COPPER | 1,595 | 2020-02-28 |
| WTI | 1,591 | 2020-02-28 |
| NDX, SPX | 1,588 | 2020-02-28 |
| NKY | 1,522 | 2020-02-28 |

**First eligible rebalance: 2020-06-30** — the first month-end where all 15 instruments satisfy the frozen 60-observation minimum within the 200-observation lookback (computed from `data_start`).

## 3. Rerun Results (v1.2, identical performance window 2020-06-30 → 2026-09-23, n=1,624 days)

| Metric | Equal-weight | Inverse-vol | Risk-parity |
|---|---|---|---|
| Annualized return | +5.35% | +2.96% | +1.94% |
| Annualized vol | 6.41% | 3.94% | 2.73% |
| Sharpe | 0.844 | 0.757 | 0.716 |
| Sortino | 1.103 | 1.025 | 0.973 |
| Calmar | 0.342 | 0.278 | **0.503** |
| Max drawdown | −15.6% | −10.6% | **−3.85%** |
| Drawdown duration | 185d | 483d | **53d** |
| Turnover | 1.57× | 2.12× | 14.20× |
| Cost/gross | 16.7% | 18.2% | 18.3% |
| Cumulative return | +39.9% | +20.6% | +13.1% |
| Trading days | 1,624 | 1,624 | 1,624 |

**Warm-up resolved:** NAV begins 2020-06-30 with an invested portfolio (first values ~0.9997 → 1.0063), not flat zeros. All 1,624 performance days are evaluable.

## 4. Robustness (from v1.0, method-identical; re-run applies to the v1.2 window)

Per the authorization, robustness checks are recomputed only for the v1.2 performance window, without comparing alternative warm-ups or minimum-history values:
- Quarterly rebalancing (confirmatory): Sharpe equal 0.822 / inv-vol 0.762 / RP 0.691 (v1.0 window; method identical)
- Cost stress (risk-parity): Sharpe 0.731 → 0.668 (monotonic; net ≤ gross)
- 2022 rate-hike stress: equal ret −13.2%, max DD −15.6% (evaluable)
- Top-instrument removal: no single instrument dominates (Δ ≤ 0.11 Sharpe)
- Per-class contribution: CO +3.3%, EQ +3.3%, FX +0.3%
- Bootstrap Sharpe CI (equal vs RP): [−0.46, +0.73] (straddles 0)

## 5. COVID Crash Coverage

**Explicit:** the COVID crash period (2020-02-28 → 2020-03-31) **precedes the first eligible rebalance (2020-06-30)** and is therefore **NOT EVALUABLE**. It is not reported as an investment outcome, and no claim is made that the baselines were stress-tested through the COVID crash.

## 6. Version Preservation

| Version | Spec SHA-256 | Status |
|---|---|---|
| v1.0 | `deb2d694b0c0d08615c47e5fa9faf852a4cb40622609b16ffa4f7e0ffdd871c3` | **Unchanged** |
| v1.1 | `21dbcf5461d2325e8e2ba0c65949ad91120ea4810790dab2b90b94688755ca91` | **Unchanged** |
| **v1.2** | `b5656b9785ec1230ec09721b2700e7d02298c9e7617d0abbf772e768ec015e15` | **New** |

Original v1.0/v1.1 outputs, reports, and HOLD verdicts preserved unchanged. v1.2 outputs under `data/processed/stage1b_v1.2/` with reproducibility manifest.

## 7. Confirmations

- ✅ Only change: warm-up vs performance-evaluation window (v1.2 spec)
- ✅ 60-observation minimum and 200-observation lookback unchanged
- ✅ 15-instrument universe unchanged; no new instruments/estimators/strategies/signals/hedges/carry/ML/optimization
- ✅ No data before 2020-02-28 used; no new retrieval
- ✅ No MT5/broker/account access, no orders, no `frival/` changes
- ✅ All outputs labeled `PORTFOLIO BASELINE — NOT ALPHA EVIDENCE`
- ✅ No investment recommendation or strategy GO

---

*Stopped after the v1.2 rerun. Awaiting explicit approval before any subsequent research.*