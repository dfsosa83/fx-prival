# EXEC-D1 Fix — `no_quote` Race (2026-09-29)

**Status:** fixed, offline-verified.
**Trigger:** the 16:00Z EURUSD SELL FIRED signal never reached the order stage —
it expired 5 ms after processing with `reason: "no_quote"` instead of using its
10-minute entry window.

## Symptom (evidence)

`data/exec_d1_runtime/lifecycle_events.jsonl`:

- `16:01:29.126Z` `SIGNAL_RECEIVED` `EURUSD_H1_SELL_2026-09-29T16:00:00Z`
  (entry 1.13395, zone 1.13375–1.13415, `texp 16:10:00`).
- `16:01:29.131Z` `EXPIRED_UNFILLED` `reason: "no_quote"`, `last_quote: null`.

Runner log `output/logs/2026-09-29_exec_d1.log:31`. No
`data/exec_d1_executions.jsonl` exists → `execute_fill` was never called.

## Root cause

Two coupled defects:

1. **Processing-clock race (engine).** `LifecycleEngine._decide()`
   (`core/lifecycle.py`) selected the decision quote as the first quote with
   `q.ts >= tp`, where `tp = now_fn()` is read *after* the runner already
   fetched the tick. A just-fetched quote therefore always precedes `tp`, so
   the filter rejected it and fell through to the terminal `no_quote` expiry.
2. **Clock-domain mismatch (transport).** `run_exec_d1_terminal._tick_quote`
   timestamped the quote from the broker `tick.time` epoch — **server** time,
   not the UTC clock the EXEC-D1 window (`t0 .. t_exp`) is defined on. Depending
   on the server offset, the quote landed outside `[tp, t_exp]` on either side.

Both are structural (not market-driven): the first in-window signal was the
first to reach this gate, and it could not pass.

## Fix

- `core/lifecycle.py::LifecycleEngine._decide()` — when no quote is at/after
  `tp`, fall back to the **freshest not-yet-expired** quote (`q.ts <= texp`) as
  the current market snapshot. The upper bound stays hard: a post-expiry quote
  never fills. The primary path is unchanged, so the offline replay contract is
  preserved.
- `core/exec_d1_terminal.py` — new pure `tick_to_quote()`: stamps the quote with
  the **local UTC wall clock** at fetch time and returns `None` when bid/ask are
  absent (no fabricated quote).
- `run_exec_d1_terminal.py` — uses `tick_to_quote()` on both the new-signal and
  pending-advance loops and skips the signal when it returns `None`.

## Verification

- `test_exec_delta1.py::TestLiveQuoteRace` (3 tests): a quote stamped *before*
  the processing instant now fills in-zone (`MARKET_FILLED`), arms a pending on
  the stop path (`ENTRY_PENDING`), and never records `no_quote`.
- `test_exec_d1_terminal.py::TestTickToQuote` (2 tests): UTC stamp within ±1 s
  of now while ignoring the broker epoch; `None` on missing price.
- Suites: `test_exec_delta1.py` 85 tests (84 pass; 1 pre-existing environmental
  failure `test_mt5_not_importable_in_this_environment`, which assumes MetaTrader5
  is *not* installed, but MT5 5.0.4874 is installed in `deaf_agent` — unrelated to
  this change). `test_exec_d1_terminal.py` 19/19 pass.

## Residual notes

- A genuinely stale tick (market data not flowing) is now rejected by the
  `TickFreshness` guard; the terminal `deviation=30` + IOC and the executor
  preflight remain additional guards.
- The engine fallback applies the window bounds `t0 .. t_exp`; quotes before the
  signal or after expiry never become the decision/fill quote.

## Review follow-up (both findings fixed)

Independent review flagged two hardening gaps; both are now implemented.

1. **Stale-tick guard (was WARNING).** `core/exec_d1_terminal.py::TickFreshness`
   tracks, per symbol, whether the broker tick time ADVANCES over local wall
   time — no server-offset knowledge required (all symbols share the server
   clock). A symbol whose broker time has not advanced for > `max_stale_seconds`
   (default 90 s) is treated as a frozen feed and skipped. `run_exec_d1_terminal.py`
   primes all four pairs every loop and refuses to `process()` or
   `advance_pending()` on a stale symbol (the signal stays in-window and is
   retried). `tick_to_quote()` now also carries `broker_time` for audit.
2. **Pre-signal quote bound (was SUGGESTION).** `core/lifecycle.py::_decide()`
   fallback is now bounded `esig.t0 <= q.ts <= esig.texp`, so a quote observed
   before the signal can never become the decision/fill quote.

Tests added: `test_exec_d1_terminal.py::TestTickFreshness` (4) and
`TestTickToQuote::test_carries_broker_time_for_audit`;
`test_exec_delta1.py::TestLiveQuoteRace::test_presignal_quote_is_not_used`.

