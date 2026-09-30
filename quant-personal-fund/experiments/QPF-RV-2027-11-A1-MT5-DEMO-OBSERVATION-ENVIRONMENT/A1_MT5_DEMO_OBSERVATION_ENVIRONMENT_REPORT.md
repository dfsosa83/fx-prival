# A1 MT5-Demo Observation-Environment Report

**Stage:** `A1_MT5_DEMO_OBSERVATION_ENVIRONMENT`
**Experiment:** `QPF-RV-2027-11-A1-MT5-DEMO-OBSERVATION-ENVIRONMENT`
**Date:** 2026-09-30
**Result:** `A1_MT5_DEMO_OBSERVATION_ENVIRONMENT_READY`

---

## 1. Scope

Build and validate a controlled **DEMO-only**, **orders-disabled** environment that can read real
XAUUSD H1/M30/M15 bars and a single tick for observing the frozen A1 Gold Rules Engine. Initialize
MT5, read market data, read count-only positions/orders for collision detection, then shut down
immediately. No order, no fill, no PnL, no trading.

## 2. Architecture / orders-disabled proof

`a1_mt5_demo_observation_environment.py` exposes a `RealMt5Gateway` read-only wrapper over
`MetaTrader5` limited to:
`initialize, shutdown, account_info, terminal_info, symbol_select, symbol_info, symbol_info_tick,
copy_rates_from_pos, copy_rates_range, positions_get, orders_get, last_error`.

- `orders_disabled_guard` requires `ORDERS_DISABLED is True`.
- `validate_mode` requires `mode == OBSERVATION_DEMO`.
- `verify_demo_account` rejects any account where `trade_mode != 0` (live/real).
- `static_scan_forbidden` is a source-text scan that fails if any forbidden order/execution method
  token (assembled from split literals so it never appears verbatim) is present.
- Persisted output is a **redacted** structural attestation only: no account id, login, server,
  balance, equity, margin, leverage, raw bars or price history.

## 3. Static safety result

`static_scan_forbidden([module])` → **no hits** (self-scan passes inside `run_setup`).

## 4. Test count / result

`python -m unittest -v test_a1_mt5_demo_observation_environment.py` → **Ran 12 tests — OK**
(mocks + synthetic payloads only; no MT5, no broker, no market data, no orders).

Covered: live-account rejection, demo acceptance, orders-disabled guard, forbidden-token rejection,
XAUUSD-only, H1/M30/M15-only, redaction, count-only reconciliation, bar/tick payload validation,
immediate shutdown, no persistent price/account storage, no order method invoked.

## 5. Real DEMO validation result (one-shot, read-only)

Terminal: FP Markets MT5 demo terminal. Executed `env.run_setup(RealMt5Gateway(...), cfg)` once.

```json
{
  "mode": "OBSERVATION_DEMO",
  "redacted": true,
  "demo_verified": true,
  "xauusd_available": true,
  "existing_positions_count": 0,
  "existing_orders_count": 0,
  "orders_disabled": true,
  "bars_read_ok": { "H1": true, "M30": true, "M15": true },
  "tick_read_ok": true,
  "source_bar_freshness": "READ_OK",
  "checked_at_utc": "2026-09-30T16:13:07+00:00"
}
```

## 6. Attestation

**No order was sent, modified or cancelled; no position was opened or closed; no virtual fill, PnL
or performance activity occurred.** The connection was shut down immediately after validation. Only
a redacted structural attestation was produced. No existing file was modified.

## 7. Next action consequence

A separate explicit authorization is required to begin A1 orders-disabled forward observation using
this environment. This setup does not authorize any broker order, demo order, virtual fill, PnL
analysis or trading.
