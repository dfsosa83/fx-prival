# Stage 1B Design Specification — REVISION v1.2 (warm-up vs performance evaluation)

**Project:** quant-personal-fund  
**Milestone:** Stage 1B  
**Date:** 2026-09-28  
**Status:** VERSIONED REVISION. v1.0 (`deb2d694…`) and v1.1 (`21dbcf54…`) specs and their outputs/hashes/reports are **unchanged and preserved**.

---

## 1. Purpose of Revision

Resolve the warm-up/evaluation-window issue by explicitly distinguishing estimator warm-up data from portfolio performance evaluation. Historical bars before the performance window are used **only** as estimator warm-up — their returns are **not** counted as portfolio performance.

## 2. Defined Periods

| Period | Definition |
|---|---|
| **`data_start`** | 2020-02-28 (earliest available bar in the validated local dataset; 15-instrument universe present) |
| **`warmup_only_period`** | 2020-02-28 → first_eligible_rebalance (inclusive). Used **only** for EWMA vol/cov estimator warm-up; not invested; returns excluded from NAV and metrics |
| **`first_eligible_rebalance`** | **2020-06-30** — the first month-end on which every active instrument has ≥60 valid observations within the 200-observation lookback (frozen min-history satisfied for all 15 instruments) |
| **`performance_evaluation_start`** | 2020-06-30 (first eligible rebalance) — portfolio NAV and performance metrics begin here |
| **`performance_evaluation_end`** | 2026-09-23 (last available bar) |

## 3. Frozen Rules (unchanged)

- **Minimum history:** 60 valid observations (frozen, **not reduced**).
- **Lookback:** 200-observation maximum (frozen, **not changed**).
- **Estimator use:** each rebalance uses only **past** observations (warm-up + prior performance bars). No future data, backfill, or imputation.
- **Missing-data rule:** if the data cannot support a valid weight on a date, follow the frozen missing-data rule (exclude that instrument for that rebalance; renormalize). The 15-instrument universe is **not changed**.
- **Universe, construction, cost model, rebalancing, vol/cov, solver, bootstrap:** all identical to v1.0/v1.1.
- **Warm-up interval:** **non-invested** — excluded from NAV returns and all performance metrics.
- **COVID crash (before 2020-06-30):** **not evaluable** — precedes the first eligible rebalance. **No flat portfolio return is reported as an investment outcome; no claim that baselines were stress-tested through the COVID crash.**

## 4. Scope of Change (single)

| Item | v1.0/v1.1 | v1.2 |
|---|---|---|
| Performance evaluation start | (flat warm-up until first non-zero weight) | **2020-06-30 (first_eligible_rebalance), with warm-up 2020-02-28 → 2020-06-30 used for estimators only** |

**Nothing else changes.** No new instruments, estimators, strategies, signals, hedges, carry, ML, or optimization variants.

## 5. Labeling

All outputs remain labeled **PORTFOLIO BASELINE — NOT ALPHA EVIDENCE**.

---

*This is the versioned warm-up/evaluation clarification. It is not a change to the 60-observation rule, 200-observation lookback, universe, construction, or cost model.*