# A1 Orders-Disabled Forward-Observation Setup Report

**Stage:** `A1_ORDERS_DISABLED_FORWARD_OBSERVATION_SETUP`
**Experiment:** `QPF-RV-2027-10-A1-ORDERS-DISABLED-FORWARD-OBSERVATION-SETUP`
**Date:** 2026-09-30
**Result:** `A1_ORDERS_DISABLED_FORWARD_OBSERVATION_SETUP_PASS`

---

## 1. Scope

Build and locally validate an isolated, observation-only runtime for the frozen A1 Gold Rules Engine
that can persist complete lifecycle/event records but is **orders-disabled by construction**. No MT5/
broker/network/quote feed/execution connection; no observation started; no performance evaluation.

## 2. Source inspection paths

- A1 pure modules: `frival/gold_rules/{engine.py,bias.py,levels.py}` (frozen; not modified).
- Offline runner interface: `quant-personal-fund/tools/a1_offline_runner/{a1_offline_runner.py,
  OFFLINE_RUNNER_INTERFACE.md}`.
- A3 concepts: `frival/execution_bot/core/` (lifecycle/event-record vocabulary) — **read only; not
  imported or executed**; used as a documented compatibility target.

## 3. Architecture and orders-disabled proof

`A1_OBSERVATION_ONLY_RUNTIME.py` imports **only the standard library** (`json`, `pathlib`, and `ast`
locally inside the guard). It contains **no** MT5/broker/network/order/fill/client object, **no** A3
executable import, and exposes only pure/local functions: configuration validation, event-schema
validation, lifecycle-transition validation, append-only local persistence, session metadata,
observation-window tracking, and a static safety self-check.

## 4. Static safety result

`static_safety_check([runtime])` → **no hits**. The guard is AST-based: it rejects prohibited import
roots, prohibited function names (`send_`, `place_`, `submit_`, `connect_`, `execute_`, …), `environ`
attribute use, and identifiers containing prohibited substrings (exempting the attested
`orders_disabled` / `observation_only` identifiers).

## 5. Event schema / lifecycle validation

- Only observation-safe states accepted (`NO_SETUP, SETUP_DETECTED, SIGNAL_ACCEPTED, ENTRY_PENDING,
  EXPIRED_UNFILLED, NO_VALID_PENDING, RULE_REJECTED, OBSERVATION_ERROR`); all reserved execution states
  (`MARKET_FILLED, PENDING_TRIGGERED, VIRTUAL_OPEN, CLOSED_TP/SL/TIMEOUT, EXTERNAL_STATE_CONFLICT`)
  are rejected.
- Legal transitions enforced; no transition to an execution state is valid.
- Every event must carry the 21 required fields (explicit `null` allowed); prohibited fields
  (`order_id`, `fill_price`, `fill_time`, `realized_pnl`, `unrealized_pnl`, `account_balance`,
  `position_size`, `broker_response`) are rejected.

## 6. Append-only storage result

JSON Lines only, UTF-8, newline `\n`, to `<caller_root>/<session_id>/events.jsonl`; monotonic
`sequence_id`; existing records never overwritten (append mode); writes outside the caller root refused.

## 7. Test count / result

`python -m unittest -v test_a1_observation_only_runtime.py` → **Ran 15 tests — OK** (synthetic event
dicts + temporary directories only).

## 8. Attestation

**No market data, A1 rule execution, forward observation, broker, MT5, order, virtual fill, PnL or
performance activity occurred.** No existing file modified.

## 9. Next action consequence

A separate explicit authorization is required to begin A1 orders-disabled forward observation using an
approved data-source method. No broker connection, demo order, virtual fill, PnL analysis or trading is
authorized by this setup.
