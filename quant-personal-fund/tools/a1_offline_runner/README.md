# a1_offline_runner

An **isolated, fixture-only offline runner** for the existing A1 Gold Rules Engine.

## What it is for

It makes the A1 rule observable reproducibly from **already-existing local XAUUSD fixture CSVs**
without touching the live runtime. It binds the pure A1 modules (`engine.py`, `bias.py`, `levels.py`)
and emits normalized event records for the A1 reproducibility check.

## How it avoids live runtime code

- Imports only the pure A1 modules plus standard library + pandas.
- **Never** imports or references MT5/MetaTrader5, broker, execution, order, demo-ledger, network,
  subprocess, or environment code (enforced by an AST-based safety guard).
- Takes caller-supplied fixture paths; embeds **no** real repository paths as defaults and does **no**
  work at import time.

## Safety restrictions

- Fixture-only and caller-path-driven; read-only on inputs.
- Timestamp labels stay opaque (naive, no timezone; no UTC conversion).
- Cannot place orders, fetch data, calculate PnL, or connect to MT5/broker/network.
- Emits only the frozen evaluation-schema fields; produced single **rule/decision** records —
  **not** performance, PnL, or trade outcomes.

## What it is not

It is a **technical adapter**, not a new trading rule. It does not change A1 rules, parameters,
state-machine logic, signal logic, structural-level logic, stop/target logic, risk caps or decision
semantics.

## Usage (illustrative)

```python
import a1_offline_runner as r
res = r.run_a1_offline(m15_path, m30_path, h1_path, a1_module_dir, warmup_m15=100, run_id="x")
r.write_event_records(res["records"], out_path)
```

## Authorization

Production/demo use is **prohibited** without a future explicit authorization. The formal
two-run reproducibility check remains a separate authorized stage.
