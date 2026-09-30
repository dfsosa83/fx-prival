# PHASE-5-6A REVIEW

**Title:** Phase 5.6 review summary — execution-aware benchmark specification  
**Date:** 2026-09-23  
**Status:** SPECIFICATION COMPLETE — no implementation. Benchmark B frozen. Benchmark v3 not built.

---

## 1. Approved Policies (summary)

| # | Policy | Status |
|---|---|---|
| 1 | USD base currency | Approved |
| 2 | Benchmark B frozen as historical research comparator | Approved |
| 3 | Benchmark v3 is a separate execution-aware spec; acceptance on integrity, not similarity to B | Approved |
| 4 | FX spot-price returns research-only; carry `unavailable` | Approved |
| 5 | No FX execution vehicle until venue + carry/funding data confirmed | Approved |
| 6 | Commodity signals = back-adjusted continuous; performance = contract-by-contract PnL | Approved |
| 7 | Roll yield in economic return; only roll txn costs charged separately | Approved |
| 8 | Equity = cash-funded ETFs; financing 0; TER/distributions documented | Approved |
| 9 | Rates/bonds excluded (ADR-003 Option 4 confirmed) | Approved |
| 10 | v3 acceptance on instrument/data/cost/accounting integrity | Approved |

## 2. Cost/Accounting Corrections Approved

- Assumed financing rates removed from v3 (cash-funded = 0).
- FX research proxy carry = `unavailable` (not "zero").
- Roll yield vs roll txn cost separation (no double-count).
- S1 (signal) vs S2 (performance) separation.

## 3. Unresolved Decisions (pending — never inferred)

| # | Unresolved | Owner |
|---|---|---|
| U1 | FX execution vehicle (B1–B5) | user/venue after data |
| U2 | Broker/venue | user/venue |
| U3 | Specific ETF tickers | user/venue after data |
| U4 | Commodity contract calendar | venue |
| U5 | USD O/N funding rate source | user (if adopted) |
| U6 | USDCAD keep/drop | user |

## 4. Exact Decisions Required Before Any Benchmark v3 Implementation

1. **Select an FX execution vehicle (B1–B5)** and confirm the required carry/funding data is available.
2. **Name a broker/venue** and obtain confirmed cost tables (FX spreads, ETF commission, commodity fees).
3. **Select specific ETF tickers** and source TER/distribution data.
4. **Confirm a commodity contract calendar** and broker roll-fee schedule.
5. **Decide on USD O/N funding-rate tracking** (opportunity cost) — in or out of v3 scope.
6. **Decide USDCAD** in the v3 universe.
7. **Approve the v3 acceptance suite** (instrument/data/cost/accounting integrity criteria in the spec) — no reference to Benchmark B.

## 5. What This Phase Did NOT Do (explicit)

- Did not implement Benchmark v3.
- Did not modify code, configs, the active 15-instrument universe, strategies, or signals.
- Did not download data, select an FX vehicle, broker, ETF tickers, contract calendar, or a new universe.
- Did not start paper trading or Phase 6.

## 6. Deliverables

| Doc | Path |
|---|---|
| ADR-004 | docs/adr/ADR-004-execution-vehicle-policy.md |
| ADR-005 | docs/adr/ADR-005-cost-model-vehicle-taxonomy.md |
| ADR-006 | docs/adr/ADR-006-commodity-futures-signal-and-pnl-policy.md |
| ADR-007 | docs/adr/ADR-007-equity-return-and-etf-policy.md |
| ADR-003 update | docs/adr/ADR-003-homogeneous-rates-bond-solution.md (append-only) |
| Spec | docs/specs/benchmark-v3-specification.md |
| Schema | docs/specs/instrument-master-v3-schema.md |
| Schema | docs/specs/cost-model-v3-schema.md |
| Checklist | docs/specs/data-requirements-and-venue-checklist.md |
| Register | docs/specs/phase-5-6-decision-register.md |
| Review | docs/specs/PHASE-5-6A-REVIEW.md (this document) |

---

*End of Phase 5.6A review. Implementation of Benchmark v3 requires the user decisions in §4.*