# Stage 1B Design Specification — REVISION v1.1 (evaluation start date only)

**Project:** quant-personal-fund  
**Milestone:** Stage 1B — transparent portfolio-baseline construction and audit  
**Date:** 2026-09-25  
**Status:** VERSIONED REVISION. The original frozen spec (`STAGE_1B_DESIGN_SPEC.md`, SHA-256 `deb2d694b0c0d08615c47e5fa9faf852a4cb40622609b16ffa4f7e0ffdd871c3`) is **unchanged and preserved**. This revision changes **only** the evaluable start date.

---

## 1. Scope of Change (single change)

| Item | Original (v1.0) | Revision (v1.1) |
|---|---|---|
| **Evaluation start date** | 2020-02-28 | **2020-05-29** |

**Rationale (explicit):** 2020-05-29 is the **first investable rebalance date** because the frozen **60-calendar-day minimum-history requirement** must be satisfied before volatility and covariance estimates are valid. The 60-day minimum is **not reduced**. No warm-start estimator, backfill, pre-sample data, or other mechanism is introduced to include the COVID stress window.

**COVID stress period:** labeled **outside the evaluable sample** for this baseline version. It is not reported as a portfolio outcome.

## 2. Everything Else Unchanged (frozen)

- **Universe:** exact 15 active instruments (8 FX, 4 equity, 3 commodity).
- **Weights:** long-only, sum-to-one, no caps, no leverage, no cash.
- **Return:** daily log returns, ×√252 annualization.
- **FX conversion:** USD base via `core/fx.py` (direct/inverse/cross).
- **Cost:** Stage 1A cost model; bar-spread proxy `S = points × point`; `L = 0.5×S`; swap = 0 (no rollover); stress 2× spread / 2× slippage / combined.
- **Calendar/rebalancing:** monthly primary, quarterly confirmatory (last trading day).
- **Volatility:** EWMA halflife 60, min-history 60.
- **Covariance:** EWMA halflife 60, Ledoit-style shrinkage δ=0.2, PSD fallback.
- **Risk-parity solver:** ERC coordinate descent, tol 1e-6, init equal, max_iter 2000, documented fallback.
- **Missing data:** no imputation; NaN → 0 contribution; common-union alignment.
- **Bootstrap:** block (6h/12h), 10,000 reps, seed 42.
- **Stress periods:** 2022 rate-hike (2021-09→2022-09) and all other valid checks unchanged.
- **Labeling:** every output `PORTFOLIO BASELINE — NOT ALPHA EVIDENCE`.

## 3. Unchanged Deliverables

All original outputs, reports, hashes, and the HOLD verdict are preserved. This revision's rerun produces **new** outputs under a versioned path; the original `data/processed/stage1b/` artifacts remain intact.

---

*This is the only change. No strategy, signal, carry data, hedging, ML, optimization, broker access, orders, or `frival/` changes are introduced.*