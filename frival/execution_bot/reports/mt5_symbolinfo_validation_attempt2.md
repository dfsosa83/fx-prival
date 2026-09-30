# MT5 SymbolInfo Validation — Attempt 2 (single authorized read-only attempt)

**Date / session:** 2026-09-28T20:38:05Z
**Authorization:** single read-only MT5 SymbolInfo validation using
`frival/execution_bot/config/credentials.env` (operator-confirmed terminal
path, login, password, server), with mandatory stop conditions.
**Nature:** metadata validation only. **This is NOT an order-execution or fill
test.**
**SDK:** `MetaTrader5 5.0.4874` under `C:\Users\david\anaconda3\python.exe`
(3.9.21). Terminal: the explicitly configured path from `credentials.env`
(`MT5_PATH`, an existing `terminal64.exe`) was used; no alternate path was
tried.

## Outcome: `STOPPED_INIT_FAILED`

`mt5.initialize(...)` failed on the **single** attempt. Per the mandatory stop
condition, the probe recorded the sanitized error, called `mt5.shutdown()`, and
stopped. **No retry, no alternate path/server/credential/argument format was
attempted.** `account_info()` and `symbol_info()` were never reached; no symbol
data was read.

## Exactly which MT5 functions were called and how many times

| Function | Count |
|---|---|
| `mt5.initialize(...)` | **1** (the single authorized attempt) |
| `mt5.last_error()` | **1** (only to record the sanitized failure) |
| `mt5.shutdown()` | **1** (after the attempt, per authorization) |
| `mt5.account_info()` | 0 (not reached) |
| `mt5.symbol_info(symbol)` | 0 × 4 symbols (not reached) |

Structured result: `frival/execution_bot/data/mt5_symbolinfo_probe.json`
(sanitized; `calls` verified above).

## Terminal/account verification outcome

**Not verified — connection could not be established.** The probe never reached
the environment-verification step.
- Authorized identity (masked): server `FPMarketsSC-Demo`, account `74...623`.
- Terminal path used: explicit configured `terminal64.exe` from `credentials.env`.
- Sanitized error returned: `(-2, 'Invalid "login" argument')`.

Note: this is the identical rejection observed in the previous authorization's
attempt (`-2`). The root cause remains UNKNOWN. The operator-confirmed
precondition (credentials correspond to the intended demo account) did not
change this result, which indicates the failure originates elsewhere (SDK
argument contract, terminal profile state, or the passed value's interpretation
by build 5.0.4874) — none of which may be concluded from the error code alone.
This report makes **no claim** that the credentials file contains the wrong
login.

## Allowed SymbolInfo fields — presence/value status

**Not obtained.** `trade_stops_level`, `trade_freeze_level`, `filling_mode`,
`expiration_mode`, `order_mode` for EURUSD, GBPUSD, USDCHF, USDCAD were not
queried because the connection was not established.

## B-2 status

**Still blocked.** Live broker metadata validation remains not performed. The
corrected probe (which will call `mt5.symbol_info(symbol)` and record exactly
the five approved fields) is ready and will run only under a **new, separate
explicit authorization**, after the operator resolves the `-2` initialize
failure (SDK/terminal-profile/argument-contract diagnosis; e.g., validate the
terminal profile state and how the numeric login is interpreted by build
5.0.4874).

## Integrity statements (attempt 2)

- No `order_send`; no order/position/deal/history inspection or modification;
  no terminal/account/symbol/chart/Market-Watch/settings mutation.
- No EXEC-D1 / watcher / order-bot / scheduler wiring or activation.
- No credential was printed, persisted, or exposed; identifiers masked.
- No strategy/model/label/threshold/risk changes.
- Files written (inside `frival/execution_bot/`): `data/mt5_symbolinfo_probe.json`
  (corrected call audit), `reports/mt5_symbolinfo_validation_attempt2.md`
  (this report); `tools/mt5_metadata_validate.py` updated for sanitized call
  bookkeeping on early-exit paths (no re-run performed).

## Required next action

A **new, separate explicit authorization** is required before any further
terminal connection. The operator should first diagnose and resolve the
recurring `-2 'Invalid "login" argument'` initialize failure (terminal profile /
SDK 5.0.4874 argument contract), then re-authorize the identical single-attempt
probe.