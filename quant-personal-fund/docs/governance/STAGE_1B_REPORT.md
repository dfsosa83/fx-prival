# Stage 1B Report — Transparent Portfolio-Baseline Construction and Audit

**Project:** quant-personal-fund  
**Milestone:** Stage 1B  
**Date:** 2026-09-25  
**Label:** Every result below is **PORTFOLIO BASELINE — NOT ALPHA EVIDENCE**

---

## 1. Decision Gate Verdict

### **HOLD**

The three baselines compute and the accounting is internally consistent, **but** the frozen design spec has an internal tension that prevents one pre-defined deliverable (the COVID stress-period evaluation) from being satisfied. Per the spec's own no-post-result-revision rule, this cannot be silently patched.

**Finding:** §3 of the frozen spec sets the portfolio start at **2020-02-28** (to enable the COVID stress period), but §5's minimum-history requirement (60 days) means the earliest investable rebalance is **2020-05-29**. As a result:

- All three baselines hold **zero positions from 2020-02-28 to 2020-05-28** (65 days, including the entire COVID crash window).
- The COVID stress-period evaluation returns **flat (0.0)** because the portfolio is not invested during it — it does not test the intended stress.
- The 2022 rate-hike stress period IS investable and evaluated normally.

**Consequence per the decision gate:** this is a **specification/implementation gap** (start date vs. minimum-history), not an accounting-engine defect. The gate definition says HOLD applies when "data/cost/specification gaps prevent reliable baseline construction" — the COVID stress deliverable is not reliable as constructed.

**No GO is issued.** No STOP is issued (the accounting engine itself is sound; the issue is the frozen window spec).

---

## 2. What Was Built and Verified

| Deliverable | Status |
|---|---|
| Frozen Stage 1B design spec | `docs/governance/STAGE_1B_DESIGN_SPEC.md` |
| Risk-parity (ERC) weight module | `portfolio/risk_parity.py` (coordinate descent, tol 1e-6, init equal, fallback documented) |
| Three baselines (equal / inverse-vol / risk-parity) | Computed, monthly primary |
| Time-varying economic accounting runner | Correct (drift-tracked, entry cost once, next-return-interval) |
| Robustness checks (quarterly, cost stress, top-removal, asset-class, bootstrap) | Computed |
| Reproducibility manifest | `data/processed/stage1b/STAGE1B_REPRODUCIBILITY.json` |

## 3. Baseline Results (monthly rebalance, net of cost; 2020-05-29 → 2026-09-22)

| Metric | Equal-weight | Inverse-vol | Risk-parity |
|---|---|---|---|
| Annualized return | +5.50% | +3.03% | +1.88% |
| Annualized vol | 6.37% | 3.89% | 2.59% |
| Sharpe | 0.872 | 0.786 | 0.731 |
| Sortino | 1.111 | 1.052 | 0.953 |
| Calmar | 0.352 | 0.285 | 0.423 |
| Max drawdown | −15.6% | −10.6% | **−4.4%** |
| Drawdown duration | 185d | 483d | 322d |
| Turnover (annualized) | 1.58× | 2.13× | 13.34× |
| Cost/gross PnL | 15.9% | 17.2% | 17.8% |
| Cumulative return | +43.8% | +22.5% | +13.4% |
| Weight concentration (HHI) | 0.062 | 0.075 | 0.101 |

**Observations (not conclusions):**
- Equal-weight has the highest return and Sharpe; risk-parity the lowest drawdown and highest Calmar.
- Risk-parity turnover (13.3×) is high because ERC weights shift monthly with covariance — an honest cost finding.
- Cost/gross ~16–18% across baselines — the accounting is charging costs correctly and net < gross.

## 4. Robustness Check Results

### Quarterly rebalancing (confirmatory)
| Baseline | Sharpe (quarterly) |
|---|---|
| Equal | 0.822 |
| Inverse-vol | 0.762 |
| Risk-parity | 0.691 |

Monthly vs quarterly Sharpe differences are small (0.03–0.05) — the construction is not frequency-fragile.

### Cost stress (risk-parity, monthly)
| Scenario | Sharpe | Total cost |
|---|---|---|
| Base | 0.731 | 0.0278 |
| 2× spread | 0.700 | 0.0332 |
| 2× slippage | 0.700 | 0.0332 |
| Combined | 0.668 | 0.0387 |

Costs degrade performance monotonically as expected; net ≤ gross maintained.

### Stress periods (equal, monthly)
| Period | Result |
|---|---|
| COVID 2020 (2020-02-28→03-31) | **FLAT (0.0) — portfolio not invested (HOLD finding)** |
| 2022 rate-hike (2021-09→2022-09) | ret −13.2%, max DD −15.6% |

### Top-instrument removal (inverse-vol)
| Removed | Sharpe |
|---|---|
| None | 0.786 |
| XAUUSD | 0.677 |
| SPX | 0.725 |
| NDX | 0.723 |
| WTI | 0.723 |

No single instrument dominates (largest effect: XAUUSD removal −0.11 Sharpe).

### Per-asset-class contribution (equal, monthly)
| Class | Contribution |
|---|---|
| Commodity (CO) | +3.34%/yr |
| Equity (EQ) | +3.35%/yr |
| FX | +0.31%/yr |

### Block-bootstrap Sharpe CIs (equal vs risk-parity, 10k reps)
| Block | Point | 95% CI |
|---|---|---|
| 6h | +0.141 | [−0.461, +0.726] |
| 12h | +0.141 | [−0.472, +0.735] |

The equal-vs-risk-parity Sharpe difference is **not statistically distinguishable from zero** (CI straddles 0).

## 5. Accounting Integrity Checks

- ✅ Net returns never above gross due to costs (cost/gross positive for all baselines).
- ✅ Weights are long-only, sum to 1 (per rebalance), caps none — respected.
- ✅ Entry cost charged once; turnover reconciles with trade weights.
- ✅ Risk attribution (risk contributions) computed; ERC solver converged on all rebalances.
- ✅ Cost stress monotonic; net ≤ gross.
- ✅ Block-bootstrap reproducible (seed 42).

## 6. HOLD Finding Detail

**The frozen spec's start date (2020-02-28) conflicts with the 60-day minimum history (§5).** The earliest investable rebalance is 2020-05-29. This makes the COVID stress period (2020-02-28 → 03-31) non-investable: the baselines hold no positions during it, so its evaluation is flat by construction, not by market outcome.

**Impact:** the COVID stress-period deliverable is not satisfied. The 2022 stress period is valid. All other deliverables are complete and internally consistent.

**Required resolution (not performed — spec is frozen):** the start date must be moved to the earliest investable date (≈2020-05-29), or the COVID stress window re-scoped to the investable sub-period. Either requires a **frozen-spec revision approved by the user** before re-running.

## 7. Reproducibility

- Input hashes: universe, cost model, risk_parity, baseline/robustness drivers, accounting_v2 — in `STAGE1B_REPRODUCIBILITY.json`.
- 19 daily data files hashed.
- Seeds: bootstrap 42, 10,000 reps.
- Software versions recorded (numpy/pandas/scipy/python/platform).

## 8. Unresolved Facts and Impact

| Fact | Impact |
|---|---|
| FX contract sizes unconfirmed | Weight construction is price-return based (no sizing conversion needed for baselines), but any future PnL normalization is provisional |
| Futures roll conventions unconfirmed | WTI/COPPER/XAUUSD front-month series used as-is; roll cost not modeled |
| Bond leg excluded | Baseline is 15-asset; defensive bond exposure absent |
| COVID window non-investable (spec tension) | **HOLD** — requires frozen-spec revision to resolve |

## 9. Recommendation

**HOLD for the full Stage 1B as specified.** The infrastructure is sound and 3 of 4 stress-deliverable components are complete, but the frozen start-date/minimum-history conflict invalidates the COVID stress-period evaluation and the spec prohibits post-result revision.

**Recommended resolution options (require your decision):**
1. Revise the frozen spec start date to 2020-05-29 (earliest investable) and re-run — then the COVID stress window is re-scoped to the investable sub-period or dropped with documentation.
2. Revise the minimum-history requirement to allow earlier investment (e.g., first rebalance at 60 days after start regardless of the 200-day lookback cap).
3. Accept the HOLD and treat the 2022 stress period + all other checks as the Stage 1B evidence, with the COVID period documented as non-evaluable.

**No GO is issued. No alpha, portfolio, or investment recommendation is made. All results are PORTFOLIO BASELINE — NOT ALPHA EVIDENCE.**

---

*Stopped after Stage 1B reporting. Awaiting explicit approval before any subsequent research or a frozen-spec revision.*