# Offline Runner Validation Report — A1

**Stage:** `A1_OFFLINE_RUNNER_IMPLEMENTATION_AND_SYNTHETIC_VALIDATION`
**Tool:** `quant-personal-fund/tools/a1_offline_runner/`
**Date:** 2026-09-30
**Result:** **PASS — 10/10 tests passed.**

---

## 1. Scope and safety boundary

Architecture correction only: implement an isolated offline runner binding the existing pure A1 modules
to local XAUUSD fixtures and validate it. It changes no A1 rule/parameter/logic. It does **not** run the
formal two-run reproducibility stage, does not use production data, and computes no PnL/performance.

## 2. Files created

- `a1_offline_runner.py`
- `test_a1_offline_runner.py`
- `OFFLINE_RUNNER_INTERFACE.md`
- `OFFLINE_RUNNER_VALIDATION_REPORT.md` (this file)
- `README.md`

No other permanent file created; no existing file modified.

## 3. Allowed implementation inputs

- Pure modules: `frival/gold_rules/engine.py`, `bias.py`, `levels.py`.
- Fixtures: `frival/gold_rules/tests/fixtures/XAUUSD_M15.csv` (907 rows), `XAUUSD_M30.csv` (454),
  `XAUUSD_H1.csv` (228).

## 4. Imported pure-module path graph

`a1_offline_runner.py` → (`hashlib`, `importlib`, `json`, `sys`, `pathlib`, `typing`, `pandas`) +
`bias.py`, `levels.py`, `engine.py`. `engine.py` → `bias`, `levels`, `pandas`, stdlib. No prohibited
modules anywhere in the graph.

## 5. Forbidden-import guard result

AST-based `forbidden_import_scan()` over the runner and its direct pure-module imports → **no hits**
(prohibited roots: MT5/MetaTrader5, broker, execution, order, demo-ledger, network, subprocess, env).
The guard inspects AST import nodes (docstrings/comments cannot trigger false positives).

## 6. Fixture preservation / hash result

XAUUSD M15/M30/H1 fixture SHA256 values were identical **before and after** runner use → read-only
preservation confirmed.

## 7. Test count and pass/fail

Command (from `quant-personal-fund/tools/a1_offline_runner/`):
`python -m unittest -v test_a1_offline_runner.py` → **Ran 10 tests — OK.**

Coverage: (1) no prohibited imports; (2) fixture hashes unchanged; (3) schema validate/fail;
(4) real module paths+hashes; (5) all required event fields present; (6) no execution/PnL fields;
(7) deterministic serialization within a run; (8) two runs identical (excluding run metadata);
(9) temp outputs inside temp dir + cleaned; (10) no broker/MT5/network/exec/env access.

## 8. Event-schema completeness and determinism

- Each cycle emits one record with all 21 schema fields present (explicit `null` where absent);
  `mode = "OFFLINE_REPLAY"`, instrument `XAUUSD`, timeframe `M15`.
- Serialization is deterministic (UTF-8, `\n`, canonical JSON, sorted keys).
- Two runs over the same fixtures produced **identical** canonical records (only the run-specific
  `event_id` prefix differs, excluded by design).

## 9. Statements

- This is **not** the formal A1 two-run reproducibility check; it is a unit-level validation of the new
  runner and issues **no** `REPLAY_REPRODUCIBILITY_PASS`.
- **No** MT5/broker/network/orders/virtual fills/PnL/performance/trading activity occurred.
- Research-control files were **not** modified (the reproducibility decision remains unresolved).

## 10. Next action

Separate authorization for the original `A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK`, now using
this runner (fixture-only, MT5-free) to perform the formal two-run comparison.
