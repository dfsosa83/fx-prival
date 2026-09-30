# ADR-004: Execution Vehicle Policy

**Status:** ACCEPTED (Phase 5.6 — documentation/specification only; no implementation)  
**Date:** 2026-09-23  
**Deciders:** Quantitative research lead (user-approved Phase 5.6 scope)

---

## Decision

Benchmark v3 — the future execution-aware benchmark — assigns an execution vehicle per asset class, with **no FX vehicle selected** until a venue and the required carry/funding data are confirmed:

| Asset class | Vehicle | Status |
|---|---|---|
| **FX** | UNDECIDED — candidates: multi-currency cash account; rolling forwards; spot + tom/next swap; FX futures; broker CFD | **No selection until venue + data confirmed** |
| **Equities** | Cash-funded ETF (recommended direction) | Pending ETF ticker selection (user/venue decision) |
| **Commodities** | Futures, contract-by-contract performance | Pending contract calendar (venue decision) |
| **Rates/bonds** | EXCLUDED (ADR-003 Option 4) | Pending homogeneous instrument/data solution |

**Portfolio base currency: USD** (fixed by EXP-2026-04A).

The FX **spot-price research proxy** is retained for research comparison only (Benchmark B) and is **not** an execution vehicle. Its carry is explicitly marked `unavailable`.

## Rationale

1. A spot FX position is economically a two-currency position; its total return depends on the selected implementation convention (cash balances, tom/next swaps, rolling forwards, futures, or broker product). No convention can be claimed "cost-free" in execution terms.
2. The platform has no broker venue and no confirmed interest/swap/forward data — selecting an FX vehicle now would be an unsupported assumption.
3. ETF/spot/futures vehicles differ fundamentally in financing semantics (cash-funded vs leveraged); the cost-model taxonomy (ADR-005) depends on the vehicle.
4. Rates/bonds remain excluded because ADR-003 alternatives all carry unresolved data or proxy issues.

## Alternatives Considered

| Alternative | Rejected because |
|---|---|
| FX spot-price proxy as the v3 FX vehicle | Research-only; no carry/funding; not execution-aware |
| Default to a specific FX vehicle (any B1–B5) | Venue and data unknown — unsupported assumption |
| Include CFDs/forwards/index-CFDs in v3 | Require swap/forward data and leverage semantics not yet available |
| Include rates/bonds in v3 | ADR-003 unresolved (proxy error / data cost) |

## Scope

- Applies to Benchmark v3 only. Benchmark B and all strategy verdicts remain frozen under the existing 15-instrument research universe.
- Does not change the active benchmark, strategies, or signals.

## Dependencies

- ADR-005 (cost-model vehicle taxonomy)
- ADR-003 (rates/bond exclusion)
- Broker venue + FX carry/funding data (pending)

## Required Data

- Per vehicle: spreads, commissions, financing/swap/interest terms, roll schedules, TER/distributions (as applicable).
- Confirmed venue quoting available instruments.

## Required Tests

- Instrument master v3: every active instrument has a vehicle assignment; FX `carry: unavailable` for research proxy.
- No instrument may be marked execution-ready without a broker-confirmed cost record (test-level assertion in a future acceptance suite).

## Risks and Limitations

- No FX vehicle selected until data confirmed — Benchmark v3 FX leg cannot be built yet.
- ETF selection may change the equity leg's historical return profile vs price-index research data (documented, not a correctness issue).
- Venue-dependent terms (margin, session, liquidity) are outside this ADR.

## Implementation Prerequisites

1. Broker venue identified and data confirmed.
2. ADR-005 cost taxonomy adopted.
3. Benchmark v3 specification (docs/specs/benchmark-v3-specification.md) finalized.

## Acceptance Criteria

- Every instrument in Benchmark v3 has an explicit execution vehicle.
- FX research proxy is labeled research-only with `carry: unavailable`.
- No vehicle is selected without venue + data confirmation (recorded in the decision register).