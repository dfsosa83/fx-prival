# A1 XAUUSD Orders-Disabled Forward-Observation Start Report

**Stage:** `A1_MT5_OBSERVATION_ONLY_FORWARD_START`
**Experiment:** `QPF-RV-2027-12-A1-XAUUSD-ORDERS-DISABLED-FORWARD-OBSERVATION`
**Session:** `a1_xauusd_observ_20260930`
**Date:** 2026-09-30
**Result:** `A1_ORDERS_DISABLED_FORWARD_OBSERVATION_STARTED`

---

## 1. Scope

Start a controlled, orders-disabled forward observation session for the frozen A1 Gold Rules Engine
using current XAUUSD demo-market data (H1/M30/M15 bars + tick) through the validated read-only MT5
demo feed and the orders-disabled observation runtime. One bounded invocation: preflight + exactly
one first evaluation cycle.

## 2. Permitted components and bound rule version

| Artifact | SHA256 |
|---|---|
| `frival/gold_rules/engine.py` | `9653AE906D30583493A49A478CA123B6A190AC16B93B3FD4F9A2CCDD4B2357E8` |
| `frival/gold_rules/bias.py` | `106999937CFC810C88E58DCCF9476EC63FF998D2CDF08A4BFE43DCD259F8362F` |
| `frival/gold_rules/levels.py` | `63442EBBADAF059B816E49F9FDB28D71471CA4E7C5C98C8C3FE997674E0E49D5` |
| `quant-personal-fund/tools/a1_offline_runner/a1_offline_runner.py` | `36E80FC2C85B9BE52C762C215AD58397D9CB13F472033F690C2A876171979FA3` |
| `.../QPF-RV-2027-10.../A1_OBSERVATION_ONLY_RUNTIME.py` | `766FFC8CDA37A80B4F73FAA985AC34F8DDA74670159D50A5E89FE74E92CA8160` |
| `.../QPF-RV-2027-11.../a1_mt5_demo_observation_environment.py` | `0AD8FCD2F7DD82ABA06508489ABE821D5CEE8F31D53B07A41DC347865BAC9F9B` |

The A1 module hashes equal the frozen offline-reproducibility V2 hashes, so the frozen rule version
is bound.

## 3. Preflight result

- Static scan over the orchestrator and all direct imports → **CLEAN** (AST-based; no prohibited
  import/call/identifier; the read-only feed is the only file permitted the terminal package).
- No execution/order component imported → **confirmed**.
- Mode `OBSERVATION_ONLY` and explicit orders-disabled attestation → **confirmed**.
- Source hashes recorded in `session_state.json`.

## 4. MT5 demo verification and feed status (redacted)

- demo identity verified: **true** (`trade_mode == 0`).
- XAUUSD available: **true**.
- feed: **`XAUUSD_H1_M30_M15_TICK_OK`**; latest closed bar labels M15 `2026-09-30 19:00:00`,
  M30 `2026-09-30 18:30:00`, H1 `2026-09-30 18:00:00`; tick epoch `1790796098`.
- No server name, login, account identifier, balance, equity, margin or leverage was stored.

## 5. Collision check (count-only)

- existing positions count: **0**; existing orders count: **0**; `external_demo_activity`: **false**.

## 6. First-cycle result

- cycle number: **1**; engine state `WATCH_ZONE -> WATCH_ZONE`; rule action `NONE`.
- observation lifecycle status: **`NO_SETUP`** (a bias-consistent swing_high level armed and watched).
- observation event records emitted: **1** (sequence_id 1); heartbeats emitted: **1**.
- no pending entry was emitted on this cycle; pending/expiry handling is active for later cycles.
- `observation_window.status`: **`OBSERVATION_WINDOW_INCOMPLETE`** (0 / 30 days; 1 / 50 cycles).

## 7. Validation

- event record validated against `A1_OBSERVATION_STORAGE_SCHEMA.yaml`: all required fields present,
  no prohibited execution/account fields, lifecycle status in the allowed set, reserved states absent.
- event and heartbeat `sequence_id` monotonic and gap-free.

## 8. Decision

```text
decision: A1_ORDERS_DISABLED_FORWARD_OBSERVATION_STARTED
```

## 9. Attestation

Orders disabled by construction. **No order/position was created, submitted, modified, cancelled or
closed; no virtual fill, PnL, return, cost, drawdown, Sharpe, performance/trading result or trading
instruction was produced.** MT5 demo access was read-only; the connection was shut down after the
cycle. No raw CSV, H6 snapshot or historical result file was read. No FX observation was run.

## 10. Next action consequence

The observation window remains **30 calendar days AND 50 completed cycles**. A separately authorized
monitoring/close stage (`A1_ORDERS_DISABLED_FORWARD_OBSERVATION_MONITOR_AND_CLOSE`) is required later.
No PnL, cost or trading conclusion exists.
