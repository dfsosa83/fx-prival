# A1 + A3 — Forward Observation Design (Orders Disabled)

**Primary rule:** A1 `GOLD_RULES_ENGINE` (unchanged)
**Recording adapter:** A3 `EXEC_D1_TERMINAL` (lifecycle/state persistence and event recording only)
**Stage:** `A1_A3_A8_REPLAY_AND_FORWARD_DEMO_EVALUATION_DESIGN`

> Not authorization to connect, observe MT5, place demo orders, simulate fills, or trade.

---

## Instrument and rule

- Primary instrument: **XAUUSD only**.
- Rule: **exact existing A1 version**, **no parameter changes**.
- Adapter: **A3 only for lifecycle/state persistence and event recording**.

## Default operation mode

```text
OBSERVATION_ONLY
ORDERS_DISABLED
NO_BROKER_CONNECTION_REQUIRED
```

- Any later connection to a live quote feed/MT5 must be **separately authorized**.
- In the initial forward-observation stage **no actual fill, virtual fill, PnL, balance, account,
  position, order, or execution state is observed**.

## Observation window

```text
Minimum 30 calendar days OR 50 completed rule-evaluation cycles, whichever occurs later.
```

This is an **operational-observation requirement**, not a statistical-significance claim.

## Per-cycle capture (required fields)

```text
run_id
rule_version_id
instrument
timeframe
timestamp_label_internal_or_source_timestamp
mode
market-data-input-identity
rule_state_before
rule_state_after
candidate_signal_direction
setup_type
structural_level_fields
entry_zone
stop_level
target_level
risk_cap_fields
pending_entry_status
pending_expiry_time
accept_reject_reason
lifecycle_status
error_status
```

Use `null` where no signal/setup exists; never fabricate an order/fill field.

## State expectations

```text
NO_SETUP
SETUP_DETECTED
SIGNAL_ACCEPTED
ENTRY_PENDING
EXPIRED_UNFILLED
NO_VALID_PENDING
RULE_REJECTED
OBSERVATION_ERROR
```

The following are **reserved future states and are NOT allowed in observation-only mode**:
`MARKET_FILLED`, `PENDING_TRIGGERED`, `VIRTUAL_OPEN`, `CLOSED_TP`, `CLOSED_SL`, `CLOSED_TIMEOUT`.

## Gate after the observation window

```text
FORWARD_OBSERVATION_COMPLETE
```

only if:

- no accidental order/execution path was enabled;
- every rule evaluation has a complete event record or an explicit error;
- lifecycle transitions are internally consistent;
- pending-expiry behavior is recorded correctly;
- no unhandled observation errors remain;
- source/version provenance is preserved.

Failure → `FORWARD_OBSERVATION_PAUSE`.

The next stage after completion is a **separately authorized review of data quality and operational
behavior** — **not** automatic demo-order activation.
