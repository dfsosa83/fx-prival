# EXEC-D1 Test Report — entry-zone / 10-minute expiry lifecycle

**Suite:** `frival/execution_bot/tests/test_exec_delta1.py` (stdlib `unittest`,
fully offline: fake clocks, scripted quote streams, tempfile data dirs, and
offline subprocess workers for the concurrency tests).
**Run command:** `python -m unittest discover -s tests -p "test_exec_delta1.py" -v`
(workdir `frival/execution_bot`).

## Result (post review-fix phase)

```
Ran 63 tests in 1.478s

OK
```

All 63 tests pass. The cross-process concurrency class was additionally
re-run 12/12 times with deterministic single-acceptance assertions. No test
imports or executes MT5; no network; no production data store is touched.

## Review-fix coverage added on top of the original 42

| Test class | Coverage |
|---|---|
| `TestConcurrentProcesses` | two spawned processes, **same signal** → exactly one `VIRTUAL_OPEN` (+ `DUPLICATE_SKIPPED`); two processes, **different signals, same (symbol,direction)** → exactly one open (+ `CONCURRENCY_SKIPPED`); stale-claim TTL recovery (crashed-owner claim reclaimed and reusable) |
| `TestAdvancePending` | normal touch and adverse gap via `advance_pending`; multiple successive quote calls; stale/duplicate (watermarked) quote rejection; boundary fill at exactly `t_exp`; quote after `t_exp` → `EXPIRED_UNFILLED` (never fills); restart-while-pending then fresh-quote fill; restart rejects replayed stale cached quotes |
| `TestCrashFillRecovery` | crash AFTER the authoritative fill → replay yields exactly one open; crash BEFORE the fill (pending write-ahead only) → pending recovered, no open, still advanceable; legacy `PENDING_TRIGGERED` rows replay without creating positions (only `VIRTUAL_OPEN` opens) |
| `TestAutoReconcile` | expired pending auto-reconciled at store construction; valid pending survives startup and stays advanceable; restart after open+SL close preserves the close |
| `TestBrokerRealFieldMap` | `margin_stop` classified REAL; `margin_freeze`/`fill_mode`/`expiration_mode` classified NOT_AN_MT5_FIELD; gate never reads `margin_freeze` (AttributeError-guard fixture); synthetic `SymbolInfo` introspection; missing metadata fails closed |

## Coverage (original 42, retained and updated)

Market in-zone fills (SELL/BUY), inclusive zone boundaries, SELL_STOP/BUY_STOP
normal + adverse-gap fills, no-limit separation, D-2 no-chase, 10-minute expiry
(window semantics, boundary, post-expiry quotes, processed-after-expiry),
pending/open restart survival, append-only events, single-process idempotency
and slot concurrency, fill==eligible-quote accounting, PnL/risk/RR from actual
fill with frozen SL/TP, SL-first closes, 6 h horizon timeout, external-conflict
exclusion (no `CLOSED_MANUAL`), D-9 manifest exclusion + no-reconstruction
guard, fail-safe broker gate (unverified/missing/freeze/min-stop), corrupt-tail
recovery, atomic snapshots, integrity summary, signal validation against the
real 2026-09-28 record.

## Regression note

Full `tests/` directory: 71 collected, 1 module error — **pre-existing and
environmental**: `tests/test_diagnostics.py` imports `order_bot.py` →
`MetaTrader5` (absent in this offline Python 3.12.9). Untouched by EXEC-D1.