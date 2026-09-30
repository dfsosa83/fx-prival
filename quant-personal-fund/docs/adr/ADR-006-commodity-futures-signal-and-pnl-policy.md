# ADR-006: Commodity Futures Signal and PnL Policy

**Status:** ACCEPTED (Phase 5.6 — documentation/specification only; no implementation)  
**Date:** 2026-09-23

---

## Decision

Benchmark v3 separates **three distinct commodity series** that must never be conflated:

| Series | Purpose | Construction | Use |
|---|---|---|---|
| **S1 — Back-adjusted continuous price** | Signal generation only (trend, volatility, regime) | Front-month series with contract switch adjusted out (jump-free) | `signals/` inputs; **never** portfolio performance |
| **S2 — Contract-by-contract realized PnL** | Portfolio performance (Benchmark v3 NAV) | Hold contract A from entry to its last tradable day: `PnL_A = P_A(T) − P_A(t0)`; at roll close A and open B | NAV/return/attribution |
| **S3 — Roll transaction costs** | Cost ledger | Commission + bid-ask + slippage on the rolled notional | `txn_cost` at roll date |

**Economic roll yield (contango/backwardation):**
- The contract basis `(P_B − P_A)` at the roll boundary reflects the term structure. For a long position in contango (P_B > P_A) it is a real holding cost; in backwardation it is a credit.
- **It is part of the economic futures return and must appear in S2 exactly once** — through the realized PnL of closing A and opening B at the boundary.
- **It must NOT** be (a) removed by back-adjustment in the performance series, or (b) additionally charged as a separate "roll cost." Either would double-count or erase it. Back-adjustment exists only in S1 (signals).

**Collateral return:** If total-return futures are ever modeled, the return on posted margin is a **separate, documented term**. Benchmark v3 default is **excess-return (price-only)**; collateral return is out of scope unless explicitly adopted.

**Negative prices:** any close ≤ 0 (e.g., WTI April 2020) is excluded from returns with an explicit data flag — never log-transformed, never zero-filled. A documented price-floor policy applies.

## Rationale

1. The prior design (Phase 5.6 v1) treated the contract spread at roll as an automatic "roll cost" deducted from a back-adjusted series — that double-counts or erases the roll yield. The correction separates economic return (S2) from execution cost (S3).
2. Back-adjustment is a signal-generation convenience; it would distort realized PnL if used for performance.
3. Contract-by-contract PnL is the only convention that prices the real economics of holding futures.

## Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Single back-adjusted series for both signal and performance | Roll yield removed from performance; double-count risk |
| Back-adjusted series + separate roll "cost" = contract spread | Double-counts the basis (spread is the yield, not a fee) |
| Single-contract (no adjustment) for signals | Embeds roll jumps that inflate volatility |

## Scope

- Commodity legs of Benchmark v3 only.
- Does not change Benchmark B or research signals.

## Dependencies

- ADR-004 (vehicle policy)
- ADR-005 (cost taxonomy)
- Venue contract calendar (pending)

## Required Data

- Front-month and next-month contract price series per commodity.
- Venue contract calendar (first/last tradable days, first notice day).
- Broker fee table: commission, bid-ask, slippage at roll.
- Negative-price registry (which dates, why).

## Required Tests

- Roll-yield-inclusive return: a contango roll produces the expected negative carry inside S2; backwardation the credit.
- Roll transaction cost charged exactly once per roll, additive to S2 (no double-count).
- S1 back-adjusted series is jump-free at each roll (measured jump ≈ 0).
- Negative-price floor: close ≤ 0 → NaN with registry entry; never log-transformed.

## Risks and Limitations

- Contract-by-contract PnL changes the commodity return history vs the current continuous series — expected; Benchmark B frozen (diagnostic only).
- Contract calendar accuracy depends on the venue source.

## Implementation Prerequisites

- Venue contract calendar confirmed.
- Broker fee table confirmed.
- Instrument master v3 `vehicle: futures` + contract metadata.

## Acceptance Criteria

- S1 never feeds performance; S2 is the only NAV input (test-verified).
- Roll yield present exactly once; roll transaction costs separate.
- No negative-price return enters the series un-flagged.