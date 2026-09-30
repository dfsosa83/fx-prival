# Stage 1B v1.1 — Rerun Report

**Project:** quant-personal-fund  
**Milestone:** Stage 1B (versioned rerun)  
**Date:** 2026-09-25  
**Label:** All results **PORTFOLIO BASELINE — NOT ALPHA EVIDENCE**

---

## 1. Verdict

### **HOLD**

The v1.1 single-date correction (2020-02-28 → 2020-05-29) **did not achieve the intended effect**. It relocated the non-investable warmup rather than removing it:

| Version | Evaluation start | First investable rebalance | Flat days |
|---|---|---|---|
| v1.0 | 2020-02-28 | 2020-05-29 | 65 |
| **v1.1** | **2020-05-29** | **2020-08-31** | **66** |

**Mechanism:** the 200-day lookback in `weights_at` is **truncated by the frame start**. With the frame starting 2020-05-29, `ewma_vol`/`ewma_cov` see only ~30 days of data at the June 2020 rebalance — below the frozen `MIN_HIST=60` — so weights cannot be produced until the August 31 rebalance (when the in-frame history first reaches 60 days). Moving the start date later does not fix this; it makes it slightly worse (the pre-frame 200-day lookback is even shorter relative to the new start).

**Per the authorized constraints** ("do not use pre-sample data", "do not reduce the 60-day minimum"), the only genuine fix — letting the lookback use pre-frame history — is **prohibited**. Therefore the v1.1 rerun does not satisfy the goal of an investable-from-day-1 baseline, and the COVID window remains non-evaluable.

**No GO, no STOP.** The accounting engine remains sound; the window/lookback interaction is a specification limitation that the frozen rules cannot resolve within the authorized scope.

---

## 2. What Was Preserved (unchanged)

| Artifact | SHA-256 | Status |
|---|---|---|
| Original spec v1.0 | `deb2d694b0c0d08615c47e5fa9faf852a4cb40622609b16ffa4f7e0ffdd871c3` | **Unchanged** |
| Original manifest | `9e115fabacbf91a63f7dc8a6fde2ea6adfac91adcc61ab8c63715389c14974e3` | **Unchanged** |
| Original v1.0 outputs | `data/processed/stage1b/` | **Unchanged** |
| Original HOLD verdict | `docs/governance/STAGE_1B_REPORT.md` | **Unchanged** |

## 3. What Was Created (versioned, additive)

| Artifact | SHA-256 |
|---|---|
| `docs/governance/STAGE_1B_DESIGN_SPEC_v1.1.md` | `21dbcf5461d2325e8e2ba0c65949ad91120ea4810790dab2b90b94688755ca91` |
| `scripts/stage1b_v11_rerun.py` | — |
| `data/processed/stage1b_v1.1/` | new outputs (nav/returns/weights CSVs, metrics JSON) |

**The only spec change was the evaluation start date.** Universe, weights, costs, rebalancing, vol/cov, solver, bootstrap, labeling all unchanged.

## 4. Recomputed Results (v1.1) and Diff vs v1.0

| Metric | Equal v1.1 (Δ vs v1.0) | Inv-vol v1.1 (Δ) | Risk-parity v1.1 (Δ) |
|---|---|---|---|
| Ann return | +4.41% (−1.08pp) | +2.43% (−0.60pp) | +1.78% (−0.10pp) |
| Sharpe | 0.715 (−0.157) | 0.633 (−0.153) | 0.692 (−0.039) |
| Sortino | 0.915 (−0.196) | 0.841 (−0.211) | 0.902 (−0.051) |
| Max DD | −15.6% (0.00) | −10.6% (0.00) | −4.4% (0.00) |
| Turnover | 1.54× (−0.04) | 2.09× (−0.04) | 13.19× (−0.15) |
| Cost/gross | 18.8% (+2.9pp) | 20.7% (+3.6pp) | 18.6% (+0.9pp) |
| Cum return | +32.6% (−11.2pp) | +17.0% (−5.5pp) | +12.2% (−1.2pp) |

**Interpretation:** removing the first ~3 months (which included the COVID recovery, a positive period) lowers all return metrics; max DD is unchanged (the 2022 drawdown dominates); cost/gross rises slightly (fewer days to amortize the entry cost). These are coherent consequences of the later start, **but they do not reflect an investable-from-day-1 baseline** because the warmup persisted (66 flat days to 2020-08-31).

## 5. COVID Window

**The COVID stress window is NOT reported as a portfolio outcome.** It remains **outside the evaluable sample** in both v1.0 and v1.1 because the portfolio is not invested during it. This is stated, not hidden.

## 6. Robustness (v1.1 window)

Not re-run as a separate deliverable because the baseline itself is not investable-from-day-1; the v1.0 robustness results (quarterly, cost stress, 2022 stress, top-removal, asset-class, bootstrap) remain valid as **infrastructure** evidence and are unchanged in method. They are reported in `STAGE_1B_REPORT.md` (v1.0).

## 7. Updated Verdict

**HOLD for baseline-infrastructure validity.**

The infrastructure is sound (accounting consistent, net ≤ gross, weights constrained, ERC converges, reproducible). The blocker is a **specification limitation**: within the authorized scope (no pre-sample data, no min-history reduction), a 60-day-min-history baseline with a frame-truncated 200-day lookback **cannot be invested from its stated start date**. The COVID stress window is therefore non-evaluable regardless of start-date choice.

**No GO is issued.** No alpha, portfolio, or investment recommendation. No strategies, signals, carry data, hedging, ML, optimization, broker/MT5 access, orders, or `frival/` changes.

---

*Stopped after the v1.1 rerun. Awaiting explicit approval.*