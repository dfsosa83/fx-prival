# Cost Model Policy

## Principle

Costs must be specified before signal search. Spread, commission, slippage, financing, and roll assumptions belong in the initial experiment manifest, not as an optional adjustment after attractive gross results appear.

## Default Cost Structure

Every instrument has a cost record in `config/cost_model.yaml` with the following fields:

| Field | Unit | Description |
|---|---|---|
| `spread_pips` | pips (FX) / price units (other) | Measured or conservatively estimated bid-ask spread |
| `spread_source` | string | Date and method of measurement |
| `slippage_pips` | pips / price units | Conservative slippage buffer |
| `commission_per_lot` | account currency | Per-lot commission (if applicable) |
| `swap_long_points` | points per day | Overnight financing for long positions |
| `swap_short_points` | points per day | Overnight financing for short positions |
| `roll_cost_pct` | percentage | Futures/CFD roll cost as fraction of notional |
| `dividend_adjustment` | string | Description of dividend handling for equity instruments |
| `session_multiplier` | float | Spread multiplier by session (1.0 until measured) |

## Conservative Defaults (Phase 1)

Until empirical measurement data exists, the following conservative defaults apply:

| Instrument class | Default spread assumption | Default slippage |
|---|---|---|
| G10 FX majors | Measured spot spread × 1.5 | 0.5 pips |
| FX crosses | Measured spot spread × 1.5 | 1.0 pips |
| Equity index CFDs | 1.0 index point | 0.5 index points |
| Government bond proxies | 0.1% of price | 0.05% of price |
| Commodities | 0.1% of price | 0.05% of price |

## Session Conditioning

The `session_multiplier` field is 1.0 until session-conditioned measurements exist. Once measured, multipliers should reflect:

- **Asian session:** Typically wider spreads for non-Asian-pair FX.
- **London/NY overlap:** Typically tightest spreads for G10 FX.
- **US equity session:** Relevant for equity index instruments.
- **Weekend/holiday proximity:** Wider spreads near market closes before extended breaks.

## Swap and Financing

- **FX instruments:** Swap is direction-dependent (can be positive or negative). It must be tracked as a separate diagnostic line, not silently netted into EV/R.
- **Equity index CFDs:** Financing is typically direction-independent and always negative (cost). Model as daily rate × notional.
- **Commodities:** Roll cost is the primary financing cost. Model as the difference between front-month and next-month futures prices at roll date.

## Cost Stress Testing

Every positive result must be stress-tested with:

1. **Double spread** — simulate spreads at 2× the assumed value.
2. **Double slippage** — simulate slippage at 2× the assumed value.
3. **Adverse swap** — simulate swap at 2× cost for the worst direction.
4. **Triple-session** — simulate session-conditioned spread at 3× for off-peak sessions.

A result that flips from positive to negative under any cost stress test is classified as cost-fragile and cannot receive a GO without cost-model improvement.

## Measurement Cadence

Cost measurements should be refreshed:
- Monthly for spreads (capture structural changes).
- After every 30 real/paper fills for slippage (log per execution).
- Quarterly for swap/financing rates (capture rate-cycle changes).
- After any broker change or contract specification update.