# Offline Runner Interface — A1 Gold Rules Engine

Fixture-only, caller-path-driven adapter. Binds the existing pure A1 modules
(`engine.py`, `bias.py`, `levels.py`) to local XAUUSD fixture CSVs and emits normalized event records.
No execution at import time; no default repository paths; no MT5/broker/network/execution code.

## Public functions

```python
load_fixture_bars(csv_path) -> pandas.DataFrame
validate_fixture_schema(df) -> None
load_a1_modules(a1_module_dir) -> (bias_mod, levels_mod, engine_mod)
module_hashes(mods) -> dict
build_a1_offline_inputs(m15, m30, h1, warmup_m15=100) -> list
run_a1_offline(m15_path, m30_path, h1_path, a1_module_dir, config=None, warmup_m15=100, run_id=...) -> dict
normalize_a1_event_record(run_id, cycle_index, label, rule_version_id, input_identity,
                          state_before, state_after, dec, risk_caps, error_status) -> dict
write_event_records(records, out_path) -> None
forbidden_import_scan(paths) -> list           # AST-based safety guard
sha256_file(path) -> str
```

## Contracts

- **Inputs:** caller-supplied paths only; local CSVs only; read-only. `datetime` labels are kept as
  strings (`label`) and parsed to **naive** timestamps for engine use — no timezone inference, no UTC
  conversion, no interpolation, no fetching.
- **A1 binding:** the runner calls the real pure module functions (`GoldRulesEngine.evaluate`,
  `Snapshot`, `EngineState`, `Decision`) unchanged; it does not re-implement or simplify rule logic.
  Module paths and SHA256 is reported in the returned metadata (`module_hashes`).
- **Events:** one normalized record per A1 evaluation cycle, with `mode = OFFLINE_REPLAY`; all schema
  fields present or explicit `null`. No `order_id`/`fill_price`/`fill_time`/`realized_pnl`/
  `unrealized_pnl`/`account_balance`/`position_size`/`broker_response`.
- **Serialization:** deterministic (UTF-8, `\n`, canonical JSON, sorted keys).
- **Safety guard:** `forbidden_import_scan()` inspects AST import nodes of the runner and its direct
  pure-module imports; it fails if a prohibited module root (MT5/broker/execution/order/demo-ledger/
  network/subprocess/env) appears.

## Explicit restrictions

- Cannot place orders, fetch data, calculate PnL, or connect to MT5/broker/network.
- Technical adapter only — **not** a new trading rule; A1 rule/params unchanged.
- Production/demo use is prohibited without a future authorization.
