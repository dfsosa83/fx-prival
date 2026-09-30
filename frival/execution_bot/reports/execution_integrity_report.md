# EXEC-D1 Execution-Integrity Report

**Date:** 2026-09-28 · **Scope:** implementation of the approved EXEC-D1 final
plan (entry-zone / 10-minute expiry execution lifecycle) under
`frival/execution_bot/`, demo/paper only.

## Integrity statements

1. **No orders were placed.** The implementation adds an offline lifecycle
   engine; no order request is ever constructed or sent. The engine records
   lifecycle states only (`ENTRY_PENDING`, `MARKET_FILLED`, `PENDING_TRIGGERED`,
   `VIRTUAL_OPEN`, `EXPIRED_UNFILLED`, closes).
2. **No MT5 login/account/broker action occurred.** No `initialize()`, no
   terminal path, no account, no symbol, no position, no deal, no history
   access. The broker-constraint gate probes the MetaTrader5 Python package
   *presence* only (`import MetaTrader5`); in this environment the package is
   **absent**, so the probe returns `UNAVAILABLE` and the gate stays disabled
   (`enabled=False`, demo mode) — everything fails closed, nothing is invented.
3. **No terminal or process state was changed.** No existing scheduler, ML,
   gold, MT5, or execution-bot process was started, stopped, restarted, or
   reconfigured. No `run.py --once`, no watcher loop, no gold runner was
   invoked. Only ephemeral pytest processes ran the offline test suite against
   `tempfile.mkdtemp()` directories.
4. **No strategy/model/threshold/label/risk logic was modified.**
   - Y1 label, entry rule, thresholds, features, agents, prompts, signals: untouched.
   - TP/SL generation (ATR(14) × 1.0/1.5 anchored at close): untouched.
   - Risk sizing, lot sizing, daily-loss settings: untouched.
   - M15 fail-open, borderline policy, cooldown, LLM behavior: untouched.
   - Existing `main.py`, `signal_gate.py`, `order_bot.py`, `order_manager.py`,
     `signal_watcher.py`, `run.py`, gold engine: **not modified**.
5. **No modifications were made under `quant-personal-fund/`.**
6. **Y1 label/execution mismatch is documented, not resolved.** The lifecycle
   engine's module docstring states that the model probability describes the
   close-entry hypothetical while execution implements a conditional
   market-in-zone or ≤10-minute zone-touch entry; resolution is a separate
   research decision and is explicitly out of scope.

## Files created (all under `frival/execution_bot/`)

| Path | Role |
|---|---|
| `core/lifecycle.py` | EXEC-D1 lifecycle engine: zone rules (D-2/D-3/D-5), conservative stop gaps (D-4), frozen SL/TP + fill-anchored metrics (D-6) |
| `core/lifecycle_store.py` | Append-only `lifecycle_events.jsonl` (fsync write-ahead), derived `pending_entries.jsonl` / `open_positions.jsonl` snapshots (atomic `os.replace`), replay/restart, `reconcile`, idempotency+concurrency guards (D-1/D-7) |
| `core/broker_constraints.py` | Mandatory correction #1: documented MT5 property map (pinned `MetaTrader5>=5.0.45`), `UNVERIFIED` marker, fail-safe gate (block on missing properties; no defaults) |
| `core/invalid_fills.py` | D-9 exclusion contract (`partition`, `is_excluded`, `assert_no_reconstruction`) |
| `data/invalid_signal_ids.json` | Migration manifest: the two 2026-09-28 records → `INVALID_SYNTHETIC_FILL_NO_OUTCOME` |
| `tests/test_exec_delta1.py` | 42 offline tests (adverse gaps, expiry at exactly 10 min, restart recovery, duplicates, concurrency, fill=PnL anchor, external conflict, manifest exclusion, broker fail-safe) |
| `reports/migration_report_2026_09_28.md` | D-9 migration evidence |
| `reports/test_report_exec_delta1.md` | Test evidence (42/42 OK) |

## Implementation-time findings that required no code change here

- `MetaTrader5` is not importable in this environment and `pytz` is absent from
  the legacy `core/__init__` import chain; the EXEC-D1 modules therefore carry a
  documented flat-layout fallback for offline use and never import the broker
  SDK. The 10-minute expiry is enforced by the lifecycle engine (wall-clock
  `t_exp = t0 + 600 s`), replacing the MT5-order-side-only GTC expiration that
  the pre-D1 demo path ignored.

## Follow-up phase (review fixes, 2026-09-28)

A second read-only-safe implementation phase addressed the independent review
findings C-1 / M-1 / M-2 / M-3 / Fix-5. All statements above remain true for the
follow-up: no orders, no MT5/account/broker access, no process started/stopped/
reconfigured, no watcher/order-bot/scheduler integration, no strategy/model/
label/threshold/risk changes, no changes outside `frival/execution_bot/`.
The lifecycle store gained cross-process claims and automatic startup
reconciliation; the engine gained `advance_pending()` and the single
authoritative fill/open event; `signal_watcher.save_state` was made atomic.
Evidence and remaining blockers: `reports/review_fixes_report.md`. Test suite:
63/63 OK (EXEC-D1), concurrency class 12/12 OK.

## Enablement gating

The new lifecycle is **not wired into any running workflow**. Enabling it in
the signal watcher / order bot / MT5 path is a separate, explicit approval step,
per the approved scope ("Stop and wait for explicit approval before enabling the
new lifecycle in any running workflow").