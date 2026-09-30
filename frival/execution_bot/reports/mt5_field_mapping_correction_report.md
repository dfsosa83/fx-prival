# EXEC-D1 MT5 Field-Mapping Correction Report (offline)

**Date:** 2026-09-28 (offline correction task following the failed metadata
validation). **No MT5 runtime call, terminal connection, credential retry, or
order action occurred in this task.** A new, separate explicit authorization is
required before any further terminal connection.

## 1. API method correction (verified offline)

- Interface facts verified by **module-level introspection of the installed
  SDK `MetaTrader5 5.0.4874`** (import `MetaTrader5`, `dir()`/`hasattr()` only;
  no `initialize()` and no terminal connection):
  - **`mt5.symbol_info(symbol)` EXISTS** → the symbol-metadata function used.
  - `symbol_info_get` does **NOT exist** in this build and the project defines
    no wrapper of that name → nothing in this package references it.
- Corrected code: `core/broker_constraints.symbol_api_name()` resolves the API
  name without connecting; `tools/mt5_metadata_validate.py` now calls
  `mt5.symbol_info(symbol)` and aborts (`FAILED_SYMBOL_API_UNVERIFIED`) if the
  name cannot be verified — no fallback to `symbol_info_get`.

## 2. Field-mapping correction

Per the documented interface, with the five required real names adopted and
verified present on the installed kit's SymbolInfo record (introspection showed
`trade_stops_level`, `trade_freeze_level`, `filling_mode`, `expiration_mode`,
`order_mode` and related `order_gtc_mode` present; `margin_stop`,
`margin_freeze`, `fill_mode` absent):

| Name | Classification | Notes |
|---|---|---|
| `trade_stops_level` | **REAL_SYMBOL_FIELD** | minimum stop/pending order distance — used by the gate |
| `trade_freeze_level` | **REAL_SYMBOL_FIELD** | freeze level — used by the gate (symbol-level; account provider kept as optional secondary source) |
| `filling_mode` | **REAL_SYMBOL_FIELD** | permitted filling modes (recorded, not a gate input) |
| `expiration_mode` | **REAL_SYMBOL_FIELD** | permitted expiration/time-in-force modes (recorded, not a gate input) |
| `order_mode` | **REAL_SYMBOL_FIELD** | permitted order types incl. pending types (recorded, not a gate input) |
| `margin_stop` | **NOT_AN_MT5_FIELD** | absent from the installed SymbolInfo record; **not an internal alias** mapped to a real field; never read |
| `margin_freeze` | **NOT_AN_MT5_FIELD** | absent; freeze is `trade_freeze_level`, not an alias; never read |
| `fill_mode` | **NOT_AN_MT5_FIELD** | absent; filling is `filling_mode`, not an alias; never read |
| `margin_initial` / `margin_maintenance` | REAL but not execution gates | present in kit; documented but unused by the gate |

The gate fails closed on missing, malformed (non-numeric/negative), or
unsupported required metadata: codes
`BROKER_CONSTRAINT_UNVERIFIED` / `BROKER_CONSTRAINT_MALFORMED` /
`FREEZE_UNVERIFIED` / `MIN_STOP_DISTANCE_VIOLATION`. No defaults are invented.
**Synthetic tests verify mapping, ordering and fail-closed behavior only; they
do NOT verify broker-specific runtime values or semantics.**

## 3. Probe artifacts credential audit (no secrets found)

A membership audit searched all EXEC-D1 artifacts written by the validation and
correction phases (`data/mt5_symbolinfo_probe.json`, `tools/mt5_metadata_validate.py`,
`reports/*.md`) for the exact configured login and password values
(boolean-only output). Result: **no artifact contains the full login or the
password** (`ANY_SECRET_PRESENT = False`). No remediation required; masked
account (`74...623`) and the demo server name are the only account-identifying
values present and are not credentials.

## 4. Offline test evidence

`python -m unittest discover -s tests -p "test_exec_delta1.py" -v` →
**Ran 66 tests … OK**. Relevant coverage:
- Real-field classification audit (`TestBrokerRealFieldMap`): the five real
  names classify `REAL_SYMBOL_FIELD`; `margin_stop`/`margin_freeze`/`fill_mode`
  classify `NOT_AN_MT5_FIELD`.
- Gate never reads invalid names: a fixture raising `AttributeError` on
  `margin_stop`/`margin_freeze`/`fill_mode` passes `evaluate()` untouched.
- Missing `trade_stops_level` → `BROKER_CONSTRAINT_UNVERIFIED`; missing
  `trade_freeze_level` → `FREEZE_UNVERIFIED`; malformed (string / negative)
  values → `BROKER_CONSTRAINT_MALFORMED`; min-stop distance violation blocks;
  provider absent/None → `UNVERIFIED`.
- `TestProbeResolver`: `symbol_api_name()` selects `symbol_info` when present
  and never falls back to `symbol_info_get`; probe source references
  `mt5.symbol_info(symbol)` and contains no `.symbol_info_get(` call.
- All prior EXEC-D1 lifecycle tests still pass; full `tests/` directory shows
  only the pre-existing environmental `test_diagnostics` (order_bot →
  `MetaTrader5`) import error, untouched.

## 5. Statements

1. **No MT5 runtime call, terminal/broker/account connection, credential retry,
   or order action occurred during this correction task.** The single `initialize`
   attempt belongs to the previously authorized (and stopped) validation run.
2. The probe was **not** rerun; no alternative connect attempts were made; no
   `.env` values were printed or copied.
3. No watcher/order-bot/scheduler integration; EXEC-Δ1 remains unwired; no
   strategy/model/label/threshold/risk changes.
4. Changes confined to `frival/execution_bot/`: `core/broker_constraints.py`,
   `tools/mt5_metadata_validate.py`, `tests/test_exec_delta1.py`, reports.

## 6. Remaining blockers

- **B-2 (unchanged):** live broker metadata validation is still NOT performed.
  The `SymbolInfo` records for EURUSD/GBPUSD/USDCHF/USDCAD were never read
  because the authorized connection failed. A **new, separate explicit
  authorization** is required before any further terminal connection; the probe
  will then record real values under the corrected field names.
- **B-1 (unchanged):** the discovery-cursor (`watcher_state.json`) must be
  serialized at integration time (single-writer worker).
- **B-3 (unchanged):** Y1 label vs conditional zone-touch execution mismatch
  remains an open research decision.
- **New (from the failed validation):** the `Invalid "login" argument` root
  cause is UNKNOWN and must be resolved by the operator (verify the configured
  credentials/terminal profile) before re-authorizing; the correction task
  explicitly does NOT claim `.env` contains the wrong login based on that error
  code alone.