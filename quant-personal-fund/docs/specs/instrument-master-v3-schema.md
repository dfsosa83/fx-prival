# Instrument Master v3 Schema (Execution-Aware)

**Status:** SCHEMA SPECIFICATION — no implementation.

---

## Purpose

Extends the current instrument master (`config/universe.yaml`, `data/reference/instrument_master.csv`) so every Benchmark v3 instrument carries execution-vehicle, carry/funding/roll, and venue metadata. Research-only proxies are explicitly marked.

## Schema Fields (additive to existing)

| Field | Type | Allowed values | Required |
|---|---|---|---|
| `ticker` | string | current | yes |
| `asset_class` | string | fx / equity_index / commodity / govt_bond | yes |
| `base_currency` / `quote_currency` / `currency` | string (ISO 4217) | current | yes |
| `vehicle` | enum | `fx_spot_research_proxy` / `fx_cash_account` / `fx_forward` / `fx_tom_next` / `fx_futures` / `fx_cfd` / `equity_etf` / `commodity_futures` / `excluded` | yes (v3) |
| `vehicle_status` | enum | `selected` / `candidate` / `pending_venue_data` / `not_selected` | yes (v3) |
| `carry` | enum | `none` / `unavailable` / `modeled` | yes (v3) |
| `carry_detail` | string | e.g., "O/N SOFR − ESTR", "forward points", "swap table", "unavailable: no forward data" | if carry != none |
| `funding` | enum | `none` (cash-funded) / `modeled` (futures margin, FX interest) | yes (v3) |
| `funding_rate_source` | string | e.g., "SOFR/ESTR factsheet", "broker margin schedule" | if funding = modeled |
| `roll` | enum | `none` / `n/a` / `contract_by_contract` | yes (v3, futures) |
| `roll_calendar` | ref | link to contract calendar | futures only |
| `roll_txn_cost` | object | commission + bid-ask + slippage per contract roll | futures only |
| `ter_pct` | float | ETF total expense ratio | equity_etf |
| `distribution_pct` | float | ETF distribution yield | equity_etf |
| `venue` | string | execution venue/broker (pending) | selected vehicles |
| `venue_confirmed` | bool | broker/venue confirmed costs | selected vehicles |
| `data_source` | string | current | yes |
| `execution_ready` | bool | all confirmations present | derived |
| `is_active` | bool | current | yes |
| `deactivation_reason` | string | current | if inactive |

## Research-Only Proxy Rule

- FX research proxies (`vehicle: fx_spot_research_proxy`) MUST have `carry: unavailable`, `funding: none` (research convention), `execution_ready: false`.
- They remain valid for Benchmark B research but are excluded from Benchmark v3 execution.

## Required Tests

- Every active v3 instrument has `vehicle`, `vehicle_status`, `carry`, `funding`, `roll`, `execution_ready`.
- `carry: unavailable` ⇔ `execution_ready: false` (proxies are never execution-ready).
- No instrument is `execution_ready` without `venue_confirmed` costs.
- Equity ETFs have `ter_pct` and `distribution_pct` populated and sourced.

## Risks

- Schema additive — backward compatible with the frozen 15-instrument research universe.
- ETF ticker selection, FX vehicle, and venue remain pending user decisions (never inferred here).