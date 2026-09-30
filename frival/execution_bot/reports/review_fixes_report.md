# EXEC-D1 Review Fixes Report — C-1 / M-1 / M-2 / M-3 / Fix-5

**Date:** 2026-09-28 (follow-up implementation after the independent read-only review)
**Scope:** changes restricted to `frival/execution_bot/`. No wiring, no processes
started/stopped, no MT5/account/broker access, no orders, no strategy/label/
threshold/TP-SL/risk/cooldown changes, nothing under `quant-personal-fund/`.

## Fixes implemented and their test evidence

| Review finding | Fix | Evidence (tests) |
|---|---|---|
| **C-1** — no cross-process idempotency | `LifecycleStore` now provides exclusive `O_EXCL` claims (`claims/` dir) with TTL-based stale-claim recovery (`lifecycle_store.py`: `claimed()`, `_try_claim()`, `_prune_stale_claims()`), plus `refresh()` which re-reads the event log inside the claim. `LifecycleEngine.process()` wraps the full read-check-decide-write sequence (signal claim → refresh → SIGNAL_RECEIVED → slot claim → refresh → `acquires()` → decision). `has_signal()` is keyed to the SIGNAL_RECEIVED reconstruction record so an audit-only DUPLICATE_SKIPPED row cannot masquerade as "already processed" (this exact race was reproduced and fixed). Event-log header creation is claim-guarded. | `TestConcurrentProcesses.test_two_processes_same_signal_no_duplicate`, `.test_two_processes_different_signals_same_slot_no_duplicate`, `.test_stale_claim_recovery_on_restart`; stable 12/12 under repetition |
| **M-1** — fill crash window | `VIRTUAL_OPEN` is now the **single authoritative fill+open event** carrying fill/trigger quotes, gap diagnostics, frozen SL/TP, effective R:R and risk (`lifecycle.py:_fill_open`). Replay derives the open position only from `VIRTUAL_OPEN`; legacy `MARKET_FILLED`/`PENDING_TRIGGERED` rows remain readable and never create a position. | `TestCrashFillRecovery` (after-fill replay = exactly one open; before-fill crash = pending recovered, no open, then advanceable; legacy rows never open) |
| **M-2** — pending across successive quotes | New `LifecycleEngine.advance_pending(signal_id, quote)` fills a persisted pending from a later fresh quote (executable side, zone, D-2/no-chase, conservative adverse gaps, actual-fill accounting, frozen SL/TP preserved). Quotes are watermark-guarded (`last_quote_ts`, persisted via `PENDING_UPDATED` events): stale/duplicate quotes are ignored, quotes after `t_exp` never fill, boundary `ts == t_exp` qualifies. | `TestAdvancePending` (8 tests) |
| **M-3** — automatic startup recovery | `LifecycleStore.__init__` now auto-runs `reconcile()` after replay: expired pendings are expired at construction; valid pendings survive and remain advanceable; restart after an open/close preserves the close. | `TestAutoReconcile` (3 tests); `TestPersistenceRestart.test_reconcile_expires_stale_pending_on_restart` updated to the automatic behavior |
| **Fix-5** — MT5 property mapping | `broker_constraints.py` audits the SymbolInfo field names: `margin_stop` classified **REAL_SYMBOL_FIELD**; `margin_freeze`, `fill_mode`, `expiration_mode` classified **NOT_AN_MT5_FIELD** (never read as attributes — a guard test uses a fixture raising AttributeError on `margin_freeze`). `field_classification()`, `REAL_SYMBOL_INFO_FIELDS`, `INVALID_ASSUMED_FIELDS` and `documented_property_map()` are the authoritative references. The gate still fails closed on missing/malformed metadata. | `TestBrokerRealFieldMap` (4 tests); existing `TestBrokerGate` (6 tests) |

## watcher_state pointer race (review note)

`watcher_state.json` and its handler live inside `frival/execution_bot/`
(`data/watcher_state.json`, `signal_watcher.py`), so its handling WAS updated:
`save_state()` is now an **atomic** write (temp file + `os.replace` + fsync). The
residual **read-modify-write of the discovery cursor `last_signal_id`** (two
simultaneous `--once` processes can both read the same cursor) is NOT fixed by
atomicity alone. Serializing the cursor advance belongs to the integration
layer (a single-writer worker). This is reported explicitly as the remaining
**integration blocker**; the lifecycle store's claims do not and must not
replace it.

## Evidence counts

- `python -m unittest discover -s tests -p "test_exec_delta1.py" -v` → **Ran 63 tests … OK**
- Concurrency class re-run 12/12 times → OK
- Full `tests/` directory: 71 collected; the only error remains the **pre-existing
  `tests/test_diagnostics.py`** import failure (`order_bot.py` → `MetaTrader5`,
  module absent in this offline environment). Untouched, unrelated.

## Integrity statements (valid for this phase)

1. **No orders placed; no MT5 `initialize()`/`login()`; no account/broker/terminal
   access occurred.** The broker probe only checks package importability.
2. **No watcher/order-bot/scheduler integration and no operational activation
   occurred.** The lifecycle remains unwired; `advance_pending()`/claims are
   library APIs exercised only by offline tests.
3. **No strategy/model/label/threshold/TP-SL/risk/cooldown/LLM behavior changed.**
   Signal, agent and model files untouched.
4. **No changes outside `frival/execution_bot/` were made.**
5. `signal_watcher.py` was modified **only** for the atomic `save_state` (file is
   inside the approved scope); its execution path was not rewired.
6. **No full MT5/broker validation is claimed** — the property names are
   documented from the pinned `MetaTrader5>=5.0.45` public API and marked for
   runtime introspection in an MT5-capable environment.

## Remaining blockers before integration

- **B-1 (integration-time):** serialize the discovery-cursor advance
  (`watcher_state.json` `last_signal_id`) behind the single-writer worker, or
  apply the same O_EXCL claim at the cursor level. Atomic write mitigates
  corruption but not double-advance.
- **B-2 (broker-metadata phase):** validate the REAL SymbolInfo field names
  (incl. `margin_stop`) and freeze-level semantics against a live
  `symbol_info_get()` in an MT5-capable environment; until then the gate runs
  `enabled=False` (demo) and everything fails closed.
- **B-3 (policy):** the Y1 label vs conditional zone-touch execution mismatch
  remains an open research decision (documented, not resolved here).