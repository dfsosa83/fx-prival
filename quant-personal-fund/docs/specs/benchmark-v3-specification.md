# Benchmark v3 Specification (Execution-Aware)

**Status:** SPECIFICATION — no implementation. Benchmark v3 is a separate execution-aware specification; Benchmark B remains the frozen historical research comparator.

---

## 1. Decision (governing policy)

- **Portfolio base currency:** USD.
- **Benchmark B stays frozen** as the historical research comparator for all sleeve evaluation.
- **Benchmark v3 is a separate spec**, accepted on instrument/data/cost/accounting integrity — **never** on similarity to Benchmark B. Any comparison to B is diagnostic only and explicitly labeled non-binding.
- FX spot-price returns remain **research-only**; FX carry is explicitly marked `unavailable`; **no FX execution vehicle is selected** until a venue and the required carry/funding data are confirmed.
- Commodity signals use a **back-adjusted continuous series** (S1); Benchmark v3 performance uses **contract-by-contract realized PnL** (S2).
- Roll yield is part of economic futures return; only roll **transaction** costs are charged separately.
- Equity exposure uses **cash-funded ETFs** with financing = 0 and TER/distributions documented.
- Rates/bonds remain **excluded** pending a homogeneous instrument/data solution (ADR-003 Option 4 confirmed).

## 2. Vehicle Assignment (per ADR-004)

| Asset class | Vehicle (direction) | Status |
|---|---|---|
| FX | UNDECIDED (B1–B5 candidates) | Pending venue + data |
| Equities | Cash-funded ETF | Pending ETF ticker selection |
| Commodities | Futures, contract-by-contract | Pending contract calendar |
| Rates/bonds | EXCLUDED | Pending homogeneous solution |

## 3. Return Construction (per ADR-005/006/007)

- **USD conversion:** all non-USD returns converted via `core/fx.py` convention (direct/inverse pairs, EURJPY cross, missing-FX policy).
- **FX:** per selected vehicle (interest/forward/swap/futures basis) — TBD pending data. Research proxy carries `carry: unavailable`.
- **Equities:** ETF returns = price change + distributions − TER; financing = 0.
- **Commodities:** contract-by-contract PnL (S2); roll yield inside return; roll txn costs separate; back-adjusted series (S1) for signals only.
- **Rates/bonds:** excluded.

## 4. Cost Ledger (per ADR-005)

- Explicit per-instrument `carry/funding/roll` record: `none`, `unavailable`, or modeled value with source.
- Cash-funded vehicles: financing = 0.
- Futures: margin financing explicit; roll txn costs (commission/bid-ask/slippage) separate from roll yield.
- No assumed financing rates (prior SPX 5% etc. removed from v3).

## 5. Accounting (per EXP-2026-04A foundation)

- Reuses `portfolio/accounting_v2.py` conventions (drift-tracked, explicit trades, entry cost once, next-return-interval timing) — accounting code is frozen; v3 configures it, does not modify it.

## 6. Benchmark v3 Acceptance Criteria (no reference to Benchmark B)

| # | Criterion | Evidence |
|---|---|---|
| 1 | Instrument-level execution-vehicle definitions | Vehicle + venue per instrument; FX vehicle selected with data confirmed |
| 2 | Consistent USD return construction | Documented per-vehicle convention; direct/inverse/cross tests |
| 3 | Explicit carry/funding/roll/cost treatment | Per-instrument record with `unavailable` state; no silent defaults |
| 4 | Data provenance and reproducibility | Hashes, manifest, seeds, environment, byte-identical rerun |
| 5 | Broker/venue-confirmed costs where required | Confirmed for every execution vehicle; else not execution-ready |
| 6 | Accounting and instrument-contract tests | Contract PnL, roll-yield, roll-cost, USD-conversion, negative-price tests |
| 7 | Clear separation: signal prices vs realized PnL | S1 never feeds NAV; S2 only NAV input (test-verified) |

## 7. Required Data (per docs/specs/data-requirements-and-venue-checklist.md)

- FX: per selected vehicle — O/N rates, forward points, tom/next swaps, or broker table.
- Equity: ETF ticker → index mapping; TER; distribution yield.
- Commodity: contract calendar; front/next-month price series; broker fee table; negative-price registry.
- Rates/bonds: none (excluded).

## 8. Required Tests

Per ADR-004/005/006/007 test sections — vehicle assignment integrity, carry/funding explicit-state, roll-yield-inclusive return, roll-cost-once, financing=0 for cash-funded, negative-price floor, USD conversion, S1/S2 separation, reproducibility.

## 9. Risks and Limitations

- FX leg cannot be built until venue + data confirmed.
- ETF historical backfill shorter than price-index research history (v3 period may truncate).
- Removing assumed financing changes cost levels vs B — expected; diagnostic only.
- Contract calendar accuracy venue-dependent.

## 10. Implementation Prerequisites

1. Broker venue + FX carry/funding data confirmed.
2. ETF ticker selection + TER/distribution sourced.
3. Commodity contract calendar + broker fee table confirmed.
4. Decision register entries complete (docs/specs/phase-5-6-decision-register.md).

## 11. Non-Goals

- No alpha experiments, strategy tuning, model training.
- No paper trading, Phase 6, live trading, new data download in this phase.
- No change to Benchmark B, the active 15-instrument universe, or any strategy/signal.
- No FX vehicle, broker, ETF ticker, contract calendar, or universe selection in this phase.