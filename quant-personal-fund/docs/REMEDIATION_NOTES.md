# Remediation Notes — EXP-2026-04A

**Scope:** Temporary research assumptions introduced or clarified by the EXP-2026-04A benchmark foundation. These are documented so that no assumption is mistaken for an empirical fact.

---

## 1. One-Way Transaction-Cost Symmetry (TEMPORARY ASSUMPTION)

- `one_way_transaction_cost = entry_transaction_cost = exit_transaction_cost = 0.5 * round_trip_cost_pct` for all 15 active instruments.
- **This is a temporary research assumption based on table symmetry.** Real venues have asymmetric entry/exit costs (market impact, rebates, position-specific fees).
- The API (`core/costs.py::entry_transaction_cost` / `exit_transaction_cost` / `one_way_transaction_cost`) is built to accept asymmetric values without changing call sites.
- **Status: ASSUMPTION (not measured).**

## 2. Financing Location (CORRECTION)

- Financing is charged **ONLY** through `daily_holding_cost_pct` in the daily holding-cost term.
- It is **excluded from every transaction-cost function**. This corrects the confirmed H1 double-charge from the Phase 5.5 audit.
- **Status: VERIFIED (code + test).**

## 3. Daily Next-Observation / Next-Return-Interval Convention

- At close[D]: signals and target weights are formed using only information available through D.
- Target becomes effective for the next return interval, r[D+1].
- Transaction costs are booked on D+1 as the modeled entry/rebalance cost for that next-observation position.
- This is a **research convention**, NOT execution-grade close-to-close fill simulation.
- Execution-grade timing, bid/ask fills, and intraday session alignment are **OUT OF SCOPE**.
- **Status: VERIFIED (code + mandated integration test).**

## 4. FX Conversion (RESEARCH-RETURN CONVENTION)

- USD conversion uses **log-additive** return compounding: `R_usd = R_local + r_fx_leg`.
- Direct pairs (EURUSD, GBPUSD, AUDUSD, NZDUSD): leg = pair log return.
- Inverse pairs (USDJPY, USDCAD, USDCHF): leg = -pair log return (USD per unit = 1/pair).
- EURJPY cross: `R_usd = r_EURJPY - r_USDJPY`.
- Missing FX: forward-fill ≤ 5 days, else NaN (never zero-filled). No look-ahead.
- **Distinction documented:** this is a RESEARCH-RETURN FX convention. Execution-grade FX PnL accounting (exact multiplicative fills, bid/ask, session alignment) is OUT OF SCOPE.
- **Status: VERIFIED (code + unit tests) for research use; execution-grade deferred.**

## 5. Benchmark Definition (CORRECTION)

- Prior benchmark: constant-target-weight free-rebalancing approximation (zero turnover, cost = holding only). Audit classified it as convention C.
- Benchmark A (04A): USD buy-and-hold after one initial allocation. Drift tracked.
- Benchmark B (04A, PRIMARY): USD monthly-rebalanced with economically tracked drift, explicit rebalance trades, entry cost, and transaction costs.
- **Status: VERIFIED (code + tests).**

## 6. Cash Weight Semantics (CORRECTION)

- `cash_weight` is an **explicit allocation**, never derived as `1 - net_exposure`.
- `net_exposure = sum(holdings_w)` (signed), `gross_exposure = sum(|holdings_w|)`.
- For benchmarks A/B: cash = 0, net = gross = 1 after entry (asserted).
- `collateral_margin` reserved (None) for future long/short sleeves.
- **Status: VERIFIED (code + tests).**