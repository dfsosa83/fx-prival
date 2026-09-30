# ADR-007: Equity Return and ETF Policy

**Status:** ACCEPTED (Phase 5.6 — documentation/specification only; no implementation)  
**Date:** 2026-09-23

---

## Decision

Benchmark v3 equity exposure uses **cash-funded ETFs** as the recommended vehicle direction, with **financing set to zero** and **TER/distributions documented**.

| Convention | Return includes | Cost model | Verdict |
|---|---|---|---|
| Price index (`^GSPC`) | price appreciation only | — | Rejected (misses dividends ≈2%/yr) |
| Adjusted-close index (Yahoo `adj_close`) | Yahoo synthetic dividend adjustment | no explicit TER | Current research state; inconsistent for execution |
| **ETF (cash-funded) — RECOMMENDED** | ETF price ≈ index + distributions − TER | spread + commission + documented TER/distribution | **Adopt for v3 (direction)** |
| Total-return index | full TR return | data required | Deferred; only if ETF mapping fails |

**Financing:** cash-funded ETF holders do not borrow. `financing == 0.0` for all equity ETFs in v3. The opportunity cost of cash is tracked separately (rf), not as a financing charge.

**Specific ETF tickers are NOT selected in this ADR** — that is a user/venue decision pending data.

## Rationale

1. Cash-funded ETF is the only option that is simultaneously (a) executable, (b) cash-funded (no leveraged financing), and (c) has a documented fee/distribution structure.
2. The prior `financing_annual_pct` on equity indices (SPX 5%, etc.) was an assumed leveraged charge — inconsistent with cash-funded semantics and corrected here.
3. Price-index and adjusted-close conventions do not map to an executable instrument.

## Alternatives Considered

| Alternative | Rejected because |
|---|---|
| Price index | Misses dividends; not executable |
| Adjusted-close index | Yahoo synthetic adjustment; no TER; inconsistent |
| Index CFD | Reintroduces leveraged financing |
| Index futures | Roll machinery + contract granularity; not needed if ETF exists |

## Scope

- Equity legs of Benchmark v3.
- Does not change Benchmark B or research signals.

## Dependencies

- ADR-004 (vehicle policy)
- ADR-005 (cost taxonomy)
- ETF ticker mapping (pending user/venue decision)

## Required Data

- ETF ticker → index mapping.
- ETF TER (prospectus) and distribution yield.
- Broker commission/spread for the selected ETFs.

## Required Tests

- Equity ETF financing == 0.0 (assertion).
- TER/distribution fields present and sourced for every v3 equity ETF.
- USD conversion consistent for non-USD-listed ETFs (EUR/JPY).

## Risks and Limitations

- ETF tracking error vs index (documented, small for liquid ETFs).
- Historical backfill for ETFs is shorter than the price-index history — v3 period may be truncated vs research.
- ETF ticker availability varies by venue.

## Implementation Prerequisites

- ETF ticker selection (user/venue).
- TER/distribution data sourced.

## Acceptance Criteria

- Every v3 equity instrument is an ETF with documented TER/distribution.
- Financing == 0.0.
- ETF return series is USD-consistent and executable (venue confirmed).