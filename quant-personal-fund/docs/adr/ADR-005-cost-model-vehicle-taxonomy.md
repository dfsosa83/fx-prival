# ADR-005: Cost-Model Vehicle Taxonomy

**Status:** ACCEPTED (Phase 5.6 — documentation/specification only; no implementation)  
**Date:** 2026-09-23

---

## Decision

Benchmark v3 cost accounting distinguishes **cash-funded vehicles** from **leveraged/futures vehicles**, and requires an **explicit per-instrument carry/funding/roll record** with an `unavailable` state:

| Vehicle class | Financing | Carry/swap | Roll | TER/distributions |
|---|---|---|---|---|
| **FX spot (research proxy)** | n/a (not execution) | `carry: unavailable` | n/a | n/a |
| **FX execution (B1–B5, to be selected)** | Per convention (interest / forward points / swap points / futures basis / broker table) | Per convention | n/a | n/a |
| **Equity ETF (cash-funded)** | **0.0 — cash-funded, no borrowing** | n/a | n/a | **TER + distributions documented** |
| **Commodity futures** | Margin financing only (explicit) | n/a | **Roll yield in return; roll transaction costs charged separately** | n/a |
| **Rates/bonds** | Excluded | — | — | — |

**Critical correction adopted:** the previous model charged `financing_annual_pct` on equity indices as if they were leveraged (SPX 5%, NDX 5%, SX5E 4%, NKY 2%). This is **inconsistent with cash-funded ETF semantics** — a cash-funded ETF holder does not borrow. These assumed rates must be **removed from v3** and replaced by documented TER/distribution data, or 0.0 with opportunity cost of cash tracked separately.

## Rationale

1. Financing semantics are vehicle-dependent: cash-funded ETFs have no financing charge; leveraged CFDs do; futures have margin/roll economics.
2. The Phase 5.5 audit (H1) and the 04B financing-sensitivity analysis showed financing dominates benchmark cost — it must be modeled correctly per vehicle, not via a generic assumed rate.
3. An explicit `carry/funding/roll` record prevents silent defaults (e.g., "zero swap" being mistaken for "no carry effect").

## Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Keep `financing_annual_pct` as a generic per-instrument cost | Assumed, leveraged semantics — inconsistent with cash-funded ETFs |
| Model all vehicles as leveraged | Unrealistic and reintroduces the H1 double-charge class of error |
| Omit carry/funding records | Silent defaults; research proxies would appear carry-free |

## Scope

- Benchmark v3 cost ledger and schema (`docs/specs/cost-model-v3-schema.md`).
- Does not change Benchmark B's cost model (B remains frozen).

## Dependencies

- ADR-004 (vehicle policy)
- Broker/venue-confirmed cost inputs (pending)

## Required Data

- ETF: TER, distribution yield, commission, spread (broker-confirmed).
- FX: per selected convention — O/N interest rates, forward points, tom/next swaps, or broker swap table.
- Futures: commission, bid-ask, slippage, margin terms, roll schedule.

## Required Tests

- Cash-funded instruments have `financing == 0.0` (assertion).
- No instrument carries an assumed financing rate without a source tag.
- Roll-yield-inclusive vs roll-transaction-cost separation (ADR-006 tests).

## Risks and Limitations

- Removing financing changes absolute cost levels vs Benchmark B (expected; B is frozen; comparison is diagnostic).
- ETF TER/distribution data requires a factsheet/prospectus source.

## Implementation Prerequisites

- Instrument master v3 schema with `carry/funding/roll` and `source` fields.
- Broker-confirmed cost inputs.

## Acceptance Criteria

- Every v3 instrument has an explicit carry/funding/roll record: `none`, `unavailable`, or a modeled value with source.
- Cash-funded vehicles carry zero financing.
- No assumed financing rate exists in the v3 ledger.