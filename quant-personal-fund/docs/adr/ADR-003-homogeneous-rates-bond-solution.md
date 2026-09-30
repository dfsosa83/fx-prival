# ADR-003: Future Homogeneous Rates/Bond Data Solution (PROPOSAL ONLY)

**Status:** PROPOSED — NOT ADOPTED. No replacement bond data is sourced in EXP-2026-04A.
**Date:** 2026-09-23
**Decision context:** AUDIT-2026-09-23-PHASE-5-5 finding H3 (heterogeneous bond leg) + user decision to exclude US10Y, BUND, JGB from the active universe.

---

## Problem Statement

The pre-04A bond leg was economically heterogeneous:

| Instrument | Representation | Issue |
|---|---|---|
| US10Y (`^TNX`) | Yield series → constant-duration zero-coupon proxy | Duration approximation, no coupon/roll-down |
| BUND (`IGLT.L`) | iShares Euro Govt Bond 7–10yr ETF | Management fee, tracking error, EUR |
| JGB (`1343.T`) | NEXT FUNDS REIT ETF | **Not a government bond at all** (REIT) |

These three instruments were combined under one `govt_bond` asset class with one 1/18 weight each — economically incompatible exposures.

## Decision

**Proposed:** Define a single, homogeneous rates/bond data convention before any bond exposure re-enters the active universe. Options to be evaluated:

### Option 1 — All-ETF (price-based)
Use comparable-maturity government-bond ETFs for US (e.g., 7–10yr Treasury ETF), Euro (IGLT.L), and Japan (real JGB ETF, not REIT).
- **Pros:** price-based returns consistent with equity/commodity pipeline; no yield conversion.
- **Cons:** ETF management fees; tracking error; ETF availability for JGB is poor.

### Option 2 — All-yield-proxy (zero-coupon)
Use each sovereign's 10Y yield series (US `^TNX`, Germany, Japan) converted by `yield_to_price(maturity=10)`.
- **Pros:** homogeneous method; no ETF fees; directly comparable across countries.
- **Cons:** zero-coupon proxy ignores coupon income and roll-down; requires reliable non-US yield series (the failing `^GDBR10` / `^JGB10Y` tickers were the original problem).

### Option 3 — Direct sovereign futures/ETFs via licensed data
Source government-bond futures (e.g., bund/UST futures) or a licensed data vendor.
- **Pros:** decision-grade.
- **Cons:** cost; new data pipeline; out of scope for 04A.

### Option 4 — Exclude bonds indefinitely
Keep the 15-instrument universe bond-free.
- **Pros:** simplest; avoids proxy risk.
- **Cons:** loses the defensive bond exposure (audit LACO showed removing Bonds *improved* benchmark Sharpe, so the immediate research cost is modest).

## Recommendation (proposal only)

Evaluate **Option 2 (all-yield-proxy)** first, because it is the only option that (a) is homogeneous across the three sovereigns, (b) requires no ETF fee assumptions, and (c) uses the existing `yield_to_price` machinery. If reliable non-US yield series cannot be sourced, fall back to **Option 1 (all-ETF)** with fee documentation, or **Option 4** (exclude) depending on data availability.

## Constraints

- This ADR is a **proposal only** for EXP-2026-04A. No bond data is sourced or added in 04A.
- Bond exposure remains EXCLUDED from the active benchmark until this ADR is resolved by a future decision.
- Historical bond-inclusive results (pre-04A) are preserved append-only and are not re-run.

---

## Append-only Update — Phase 5.6 (2026-09-23): Confirmed Temporary Decision

**Status update:** The Phase 5.6 decision register confirms **Option 4 (exclude rates/bonds)** as the temporary decision for Benchmark v3.

- **Decision:** Rates/bonds remain **excluded** from Benchmark v3 pending a homogeneous instrument/data solution.
- **Rationale:** the three ADR-003 alternatives each carry material unresolved issues — Option 1 (all-ETF) has poor JGB ETF availability and fee assumptions; Option 2 (all-yield-proxy) failed on non-US yield tickers (`^GDBR10`, `^JGB10Y`); Option 3 (sovereign futures) requires licensed data not yet costed.
- **Revisit trigger:** if a licensed sovereign-futures data source (Option 3) is priced and the economics are acceptable, re-open this ADR. Until then, rates/bonds are OUT of Benchmark v3.
- **No universe change, no strategy change, no Benchmark B change** results from this update. Benchmark B remains the frozen 15-instrument research comparator.

*This entry is append-only. The original proposal text above is preserved unchanged.*