# Phase 5.6 Decision Register

**Status:** REGISTER — records approved policies and pending decisions. No implementation.

---

## Approved Decisions (governing)

| # | Decision | Source |
|---|---|---|
| D1 | Portfolio base currency is **USD** | EXP-2026-04A (fixed) |
| D2 | **Benchmark B remains frozen** as the historical research comparator | 04A/04B user approval |
| D3 | **Benchmark v3 is a separate execution-aware specification**, accepted on instrument/data/cost/accounting integrity, **not** similarity to B | Phase 5.6 approval |
| D4 | **FX spot-price returns are research-only**; carry explicitly `unavailable` | ADR-004, Phase 5.6 v2 |
| D5 | **No FX execution vehicle is selected** until venue + carry/funding data confirmed | ADR-004, Phase 5.6 v2 |
| D6 | Commodity **signals use back-adjusted continuous series**; **Benchmark v3 performance uses contract-by-contract realized PnL** | ADR-006 |
| D7 | **Roll yield is part of economic futures return**; only roll transaction costs are charged separately | ADR-006 |
| D8 | Equity exposure uses **cash-funded ETFs**, financing = 0, TER/distributions documented | ADR-007 |
| D9 | **Rates/bonds remain excluded** pending a homogeneous instrument/data solution | ADR-003 Option 4 (confirmed) |
| D10 | Benchmark v3 acceptance is based on instrument, data, cost, and accounting integrity — **not** similarity to Benchmark B | Phase 5.6 approval |

## Cost/Accounting Corrections Confirmed

| # | Correction | Effect |
|---|---|---|
| C1 | Assumed `financing_annual_pct` (SPX 5%, etc.) removed from v3; cash-funded financing = 0 | ADR-005 |
| C2 | FX research proxy carry = `unavailable` (not "zero with no effect") | ADR-004/005 |
| C3 | Roll yield inside futures return; roll txn costs separate; no double-count | ADR-006 |
| C4 | Signal prices (S1) never feed portfolio NAV; contract PnL (S2) is the only NAV input | ADR-006 |

## Pending Decisions (NOT inferred — user/venue)

| # | Pending decision | Required before |
|---|---|---|
| P1 | FX execution vehicle (B1–B5) | Benchmark v3 FX leg |
| P2 | Broker/venue | all execution-ready instruments |
| P3 | Specific ETF tickers | equity leg |
| P4 | Commodity contract calendar | commodity leg |
| P5 | USD O/N funding rate source | opportunity-cost tracking (if adopted) |
| P6 | USDCAD keep/drop | v3 universe |

## References

- ADR-003 (append-only update), ADR-004, ADR-005, ADR-006, ADR-007
- docs/specs/benchmark-v3-specification.md
- docs/specs/instrument-master-v3-schema.md
- docs/specs/cost-model-v3-schema.md
- docs/specs/data-requirements-and-venue-checklist.md