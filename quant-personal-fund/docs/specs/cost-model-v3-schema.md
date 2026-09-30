# Cost Model v3 Schema (Execution-Aware)

**Status:** SCHEMA SPECIFICATION — no implementation.

---

## Purpose

Defines the cost-ledger schema for Benchmark v3, replacing the current `config/cost_model.yaml` per-instrument record with an explicit vehicle-aware taxonomy (ADR-005). The current file and its values are preserved unchanged for Benchmark B.

## Cost Record per Instrument (v3)

| Field | Type | Allowed values | Required |
|---|---|---|---|
| `ticker` | string | current | yes |
| `vehicle` | enum | matches instrument master v3 `vehicle` | yes |
| `spread_pips` / `commission_pct` | float | per vehicle | as applicable |
| `slippage` | object | pips (FX) / pct (ETF/futures) | yes |
| `one_way_cost` | float | derived from spread+commission+slippage (symmetric research assumption, documented) | yes |
| `carry` | enum | `none` / `unavailable` / `modeled` | yes |
| `carry_value` | object | interest rates / forward points / swap points / futures basis | if modeled |
| `funding` | enum | `none` / `modeled` | yes |
| `funding_value` | object | margin rate, interest schedule | if modeled |
| `roll` | enum | `none` / `n/a` / `contract_by_contract` | futures |
| `roll_yield_in_return` | bool | `true` — roll yield is economic return, never a separate charge | futures |
| `roll_txn_cost` | object | commission + bid-ask + slippage at roll | futures |
| `ter_pct` | float | ETF TER | equity_etf |
| `distribution_pct` | float | ETF distribution yield | equity_etf |
| `source` | string | broker/factsheet/measurement date | yes |
| `source_class` | enum | `broker_confirmed` / `factsheet` / `assumed` / `unavailable` | yes |
| `execution_ready` | bool | derived: all required confirmations present | yes |

## Vehicle Cost Rules (binding)

| Vehicle | Financing | Carry | Roll | Notes |
|---|---|---|---|---|
| FX research proxy | none (research) | `unavailable` | n/a | not execution-ready |
| FX execution (B1–B5) | per convention | per convention | n/a | pending venue + data |
| Equity ETF (cash-funded) | **0.0** | n/a | n/a | TER/distribution documented |
| Commodity futures | margin financing explicit | n/a | yield in return; txn costs separate | contract calendar needed |
| Rates/bonds | excluded | — | — | ADR-003 Option 4 |

## Prior-Assumption Correction

- The current `financing_annual_pct` values (SPX 5%, NDX 5%, SX5E 4%, NKY 2%) are **assumed leveraged charges, inconsistent with cash-funded ETF semantics**.
- **v3 removes them** (financing = 0 for cash-funded). Opportunity cost of cash is tracked separately (rf), not as financing.
- The current `config/cost_model.yaml` is **not modified** — Benchmark B stays frozen; v3 uses a new ledger.

## Required Tests

- Cash-funded vehicles: `financing == 0.0` (assertion).
- `source_class == assumed` instruments are never `execution_ready`.
- Roll yield never appears as a transaction-cost line; roll txn costs appear exactly once per roll.
- Financing monotonicity across sensitivity scenarios (A ≤ C ≤ B ≤ D) for any modeled funding.

## Risks

- Removing financing changes absolute cost vs Benchmark B — expected, diagnostic only.
- Broker confirmation is required before any instrument is execution-ready.