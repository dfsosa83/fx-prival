# Cost-Model Schema (Stage 1A)

**Status:** Stage 1A schema specification  
**Date:** 2026-09-25  
**Note:** This is the target schema for cost records. The current `config/cost_model.yaml` is a partial implementation; unknown fields are marked unresolved, never filled with arbitrary estimates.

---

## Per-Instrument Cost Record

```yaml
instrument: EURUSD
cost_fields:
  spread:
    value_points: 12
    value_price: 0.00012          # points × point
    source: "mt5_symbol_info"
    source_date: "2026-09-24"
    measurement_type: "measured"   # measured | quoted | derived | assumed | unresolved
    confidence: "high"
    timestamp: "2026-09-24T18:00:00Z"
    missing_status: "available"
    revision_policy: "per-session"
    notes: "points convention; price = points × point (verified vs live tick)"

  commission:
    value: 0.0
    source: "broker schedule"
    measurement_type: "quoted"
    confidence: "medium"
    missing_status: "available"

  slippage_assumption:
    value_multiplier: 0.5         # L = 0.5 × S (frozen base)
    source: "research assumption (conservative)"
    measurement_type: "assumed"
    confidence: "low"
    missing_status: "partial"     # becomes measured only via fills (shadow/paper)

  swap_financing:
    swap_long: -6.47
    swap_short: +2.83
    swap_mode: "points_per_lot_per_day"
    source: "mt5_symbol_info (current)"
    measurement_type: "quoted"
    confidence: "medium"
    missing_status: "available_current_only"
    notes: "current values only; not a historical series"

  forward_roll:
    value: null
    source: null
    measurement_type: "unresolved"
    confidence: "low"
    missing_status: "unavailable"
    notes: "forward points not obtained; FRED policy rates are NOT a substitute"

  futures_roll:
    value: null
    source: null
    measurement_type: "unresolved"
    missing_status: "unavailable"
    notes: "N/A for spot/CFD; required only for futures sleeves"

  dividend_adjustment:
    value: null
    source: null
    measurement_type: "unresolved"
    missing_status: "unavailable"
    notes: "N/A for FX; required for equity/ETF sleeves"

  contract_specs:
    contract_size: null           # FX unconfirmed; XAUUSD 100 oz/lot verified
    tick_size: 0.00001
    volume_min: 0.01
    volume_step: 0.01
    measurement_type: "quoted"
    missing_status: "partial"
    notes: "FX contract size unconfirmed via terminal API; broker confirmation required"
```

## Rules

1. Every field carries: `source`, `source_date`, `measurement_type`, `confidence`, `timestamp`, `missing_status`, `revision_policy`.
2. `measurement_type: unresolved` or `missing_status: unavailable` → **leave value null**. Never populate with an arbitrary estimate.
3. `source_date` distinguishes current-from-historical: a current value never implies a historical series.
4. The base `L = 0.5 × S` slippage is `assumed` until fills measure it (shadow/paper phase).
5. Contract specs that are unconfirmed (FX sizes) stay `unresolved` until broker confirmation.

## Existing Implementation

`config/cost_model.yaml` currently carries: spread (points + source), commission, swap long/short, and per-class notes. It does **not** yet carry the full provenance block. The schema above is the target; migration is a Stage 1B activity (not performed here).