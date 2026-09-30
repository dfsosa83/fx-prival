# Next Authorized Action

## Action ID

```text
A1_BOUNDED_OBSERVATION_ROUTINE
```

## Objective

Run a bounded routine of observation cycles for the active A1 orders-disabled XAUUSD session
(`a1_xauusd_observ_20260930`, `QPF-RV-2027-12`) until the observation window is met. Operational
observation authorization only.

## Scope

- XAUUSD A1 observation only; MT5 demo read-only; orders disabled; append-only records.

## Required Controls

- Maximum one cycle per newly closed M15 bar; minimum 15 minutes between successful cycle starts; no
  catch-up cycles; no loop faster than M15.
- Fixed scope per cycle: XAUUSD only; H1, M30, M15 and one tick only; verified MT5 demo read-only
  feed; frozen A1 modules; `OBSERVATION_ONLY`; orders disabled.
- Validate active state and source hashes, and validate append-only integrity, before each cycle.
- Acquire an exclusive lock; read count-only positions/orders; run A1 observation-only once; write
  event and heartbeat records; atomically update session state; shut down MT5 in `finally`; release
  the lock; exit.
- Run a separate read-only health check every 10 completed cycles, immediately after any
  `OBSERVATION_ERROR`, immediately after any lifecycle state other than `NO_SETUP`, `RULE_REJECTED`,
  `NO_VALID_PENDING` or `EXPIRED_UNFILLED`, and immediately upon window completion.

## Prohibited Work

No-promotion rule: a routine cycle must not enable orders; create demo/paper/shadow/live orders;
create virtual fills; calculate PnL, returns, costs or performance; activate A3 execution code; change
A1 parameters; add instruments/timeframes; start FX observation; or initiate an economic test. No
demo order, virtual fill, PnL, cost analysis or trading is authorized.

## Expected Artifacts

- append-only event and heartbeat records under the active session directory;
- a session state reflecting the observation-window status;
- a read-only health-check report on the required cadence;
- an observation-close decision after the window expires.

## Stop Conditions

Stop with `PAUSE_A1_OBSERVATION_ROUTINE_CYCLE` (no auto-repair, no retry) if: session state is not
`ACTIVE`; the window is complete; source hashes no longer match; previous records fail structural
integrity; a reserved execution state or prohibited order/fill/PnL/account field appears; the previous
cycle did not shut down MT5 cleanly; a lock/concurrent session is detected; the account is not
verified demo; required XAUUSD timeframe data is unavailable or invalid; a forbidden MT5 operation is
detected; or a runtime/observation error is unresolved. The policy expires automatically once 30
calendar days and 50 completed cycles are both met (state `OBSERVATION_WINDOW_COMPLETE`; a separate
observation-close review is then required).

## Authorization Status

This is an **operational observation authorization only** — status
**`ACTIVE_UNTIL_WINDOW_COMPLETE_OR_PAUSE`**. It authorizes no order, virtual fill, PnL, cost analysis,
performance metric or trading operation, and does not change the frozen A1 version, the observation
runtime, the read-only feed, the storage schema or existing session records.
