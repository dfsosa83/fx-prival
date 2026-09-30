# MT5 SymbolInfo Metadata Validation — Result Report (read-only)

**Date / session:** 2026-09-28T20:19:40Z (single attempt)
**Authorization:** read-only MT5 metadata validation (connect, confirm demo
environment, read SymbolInfo for the specified FX symbols, disconnect, report).
**Nature:** metadata-only validation. **This was NOT an order-execution test and
must not be described as one.**
**SDK used:** `MetaTrader5 5.0.4874` under `C:\Users\david\anaconda3\python.exe`
(3.9.21). Terminal binary discovered at
`C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe`. Authorized server from
`frival/config/.env`: `FPMarketsSC-Demo` (account masked `74...623`,
7-digit numeric). No other Python in this environment has the SDK.

## Outcome: STOPPED — `FAILED_TERMINAL` (no metadata was read)

The authorized connection could not be established. Per the authorization's stop
conditions ("if read-only validation cannot be guaranteed, stop and request
further authorization"), the probe stopped immediately after the first failed
`initialize`; no account, terminal, or symbol metadata was read; no alternate
calls, credential variants, or workarounds were attempted.

## Exactly which functions were called and what they returned

| # | Function (recorded in `data/mt5_symbolinfo_probe.json`) | Args | Returned |
|---|---|---|---|
| 1 | `mt5.initialize(path="C:\\Program Files\\FPMarkets MT5 Terminal\\terminal64.exe", login=<masked 74...623>, password=<not displayed>, server="FPMarketsSC-Demo")` | as listed | `False`; `mt5.last_error()` = **`(-2, 'Invalid "login" argument')`** |
| 2 | `mt5.shutdown()` (unguarded error path) | — | executed (no return recorded) |

`account_info()`, `terminal_info()`, and `symbol_info_get(...)` were **not
reached** (initialization gate). Symbols EURUSD, GBPUSD, USDCHF, USDCAD were
**not queried**. The probe deliberately recorded only these two calls.

Evidence file: `frival/execution_bot/data/mt5_symbolinfo_probe.json`
(schema_version 1, status `FAILED_TERMINAL`, all secrets masked).

## Diagnostic (read-only, no reconnection) — root cause UNKNOWN

- The configured login is **syntactically valid** for MT5: 7 characters, digits
  only, no leading zero.
- `MetaTrader5 5.0.4874` rejected it with retcode −2
  (`'Invalid "login" argument'`).
- **The root cause is UNKNOWN.** A rejection with this code can stem from the
  SDK argument contract, the terminal profile state, or the configured
  credentials — none of these was verified, and none may be concluded from the
  error code alone. In particular, **it is NOT asserted that `frival/config/.env`
  contains the wrong login**; that claim would require evidence this task did
  not obtain.
- **API facts verified offline (import-time introspection only, no connection):
  the installed SDK exposes `mt5.symbol_info(symbol)` as the symbol-metadata
  function; `symbol_info_get` does not exist in this build.** Per the offline
  correction task, the probe now uses `mt5.symbol_info`, and the field mapping
  was corrected accordingly (see
  `reports/mt5_field_mapping_correction_report.md`).

## Offline correction task (post-validation, 2026-09-28)

A follow-up OFFLINE task corrected the broker-constraint mapping and the probe
code against the documented/verified interface (`trade_stops_level`,
`trade_freeze_level`, `filling_mode`, `expiration_mode`, `order_mode`;
`mt5.symbol_info`; `margin_stop`/`margin_freeze`/`fill_mode` classified as
invalid assumed names). That task performed **no MT5 runtime call, terminal
connection, credential retry, or order action** and did not rerun this probe.
Details: `reports/mt5_field_mapping_correction_report.md`.

## Integrity statements

1. **No `order_send` / order / position / fill operations occurred** (none exist
   in the probe; the SDK was used for `initialize` and `shutdown` only).
2. **No terminal or account settings changed.** No credentials displayed,
   saved, or reused beyond the authorized `initialize` call (password never
   printed; account masked in all artifacts).
3. **No watcher/order-bot/scheduler integration and no operational activation.**
   EXEC-Δ1 remains unwired.
4. **No strategy/model/label/threshold/risk changes; nothing modified outside
   `frival/execution_bot/`.** Artifacts created: `tools/mt5_metadata_validate.py`,
   `data/mt5_symbolinfo_probe.json`, and this report.
5. The probe script itself is the recorded call transcript (functions called,
   symbols sought, returns) as required.

## Status of the EXEC-D1 broker field mapping (Fix-5,B-2)

**Unchanged and still UNVERIFIED at runtime.** The documented classification
stands as-is: `margin_stop` = REAL MT5 symbol field (per the pinned SDK API);
`margin_freeze` / `fill_mode` / `expiration_mode` = NOT confirmed MT5 symbol
fields (never read by the gate; gate fails closed). This probe could not verify
actual `SymbolInfo._fields` because a connection could not be established.

## Required operator action before any follow-up authorization

1. Verify the account/login credentials configured in `frival/config/.env`
   against the FP Markets demo terminal (confirm the login is the numeric MT5
   **login** accepted by `FPMarketsSC-Demo`, not a different account code), and
   confirm the terminal profile is in a state `MetaTrader5 5.0.4874` can start.
2. Re-authorize the identical read-only probe (or an insertion of the corrected
   credentials) so the `SymbolInfo` fields can be captured; the probe script
   requires no changes and will connect, verify demo/account/server, read the
   four FX symbols, and disconnect.

Until explicit re-authorization, the validation remains stopped. No further MT5
connection was attempted after the single failed `initialize`.