# A1 XAUUSD Orders-Disabled Forward-Observation Continuation Policy

**Stage:** `A1_ORDERS_DISABLED_FORWARD_OBSERVATION_CONTINUATION_POLICY`
**Session:** `a1_xauusd_observ_20260930`
**Experiment:** `QPF-RV-2027-12-A1-XAUUSD-ORDERS-DISABLED-FORWARD-OBSERVATION`
**Date:** 2026-09-30
**Status:** operational observation authorization only.

This policy authorizes repeated **bounded** observation cycles for the already-active A1 XAUUSD
session, so routine cycles do not each require a new design-stage authorization. It authorizes no
order, virtual fill, PnL, cost, performance or trading operation.

---

## 1. Cycle frequency

```text
Maximum one cycle per newly closed M15 bar.
Minimum spacing: 15 minutes between successful cycle starts.
No catch-up cycles.
No loop faster than M15.
```

A cycle may be manually launched or invoked by an approved local scheduler, but any scheduler must be
created and started under a separate stage — **not** by this policy.

## 2. Fixed scope (every cycle)

```text
XAUUSD only
H1, M30, M15 and one tick only
verified MT5 demo read-only feed
A1 frozen modules (unchanged hashes)
OBSERVATION_ONLY
orders disabled
```

## 3. Pre-cycle stop conditions

A routine cycle must not run if any of the following applies:

- session state is not `ACTIVE`;
- the observation window is already complete;
- source hashes no longer match the session state;
- previous event/heartbeat records fail structural integrity;
- a lifecycle record contains a reserved execution state;
- a prohibited order/fill/PnL/account field is detected;
- the previous cycle did not shut down MT5 cleanly;
- a lock exists or a concurrent session is detected;
- the account cannot be verified as demo;
- required XAUUSD timeframe data is unavailable or structurally invalid;
- any forbidden MT5 operation is detected;
- a runtime/observation error is unresolved.

On any such condition the outcome is:

```text
PAUSE_A1_OBSERVATION_ROUTINE_CYCLE
```

Do not auto-repair or retry.

## 4. Per-cycle mandatory sequence

```text
1. Validate active state and source hashes.
2. Validate existing append-only integrity.
3. Acquire exclusive lock.
4. Initialize MT5 demo.
5. Verify demo status.
6. Read count-only positions/orders.
7. Read XAUUSD H1/M30/M15 and one tick.
8. Run A1 observation-only once.
9. Validate/append event record(s).
10. Append one heartbeat.
11. Atomically update session state.
12. Shutdown MT5 in finally.
13. Release/remove lock.
14. Exit.
```

## 5. No-promotion rule

A routine cycle must not:

- enable orders;
- create demo/paper/shadow/live orders;
- create virtual fills;
- calculate PnL, returns, costs or performance;
- activate A3 execution code;
- change A1 parameters;
- add instruments/timeframes;
- start FX observation;
- initiate an economic test.

## 6. Monitoring cadence

A separate read-only health check is required:

```text
Every 10 completed cycles;
immediately after any OBSERVATION_ERROR;
immediately after any lifecycle state other than NO_SETUP, RULE_REJECTED,
NO_VALID_PENDING or EXPIRED_UNFILLED;
immediately upon window completion.
```

## 7. Completion condition

The routine policy expires automatically when both are true:

```text
calendar days elapsed >= 30
completed cycles >= 50
```

Then session state must be `OBSERVATION_WINDOW_COMPLETE` and no new routine cycle is authorized. A
separate observation-close review is required.

## 8. Attestation

This policy is a bounded operational observation authorization only. It does not authorize any order,
virtual fill, PnL, cost analysis, performance metric or trading operation, and it does not modify the
frozen A1 rule version, the observation runtime, the read-only feed, the storage schema or the
existing session records.
