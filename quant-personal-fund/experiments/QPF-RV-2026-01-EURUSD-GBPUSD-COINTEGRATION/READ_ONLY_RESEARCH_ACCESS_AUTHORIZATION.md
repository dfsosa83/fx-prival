# Read-Only Research Access Authorization

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Authorization status:** `APPROVED_READ_ONLY_ACCESS`

This document records a **governance-only, additive** policy decision by the experiment owner. It
grants a future, strictly **read-only**, research access authorization. **It does not itself
authorize any data access or MT5 access today.** Every G1/G2 action still requires a separate
explicit task-level instruction.

---

## Scope

- Applies **only** to future, explicitly authorized **G1** (data audit) and **G2** (cost-evidence)
  research tasks for this experiment.
- Every such task requires its **own separate task-level authorization** before it begins.
- The authorization is strictly **read-only**. It never authorizes trading or state mutation.

## Allowed read-only categories

Subject to a separate task-level instruction, future G1/G2 tasks may read:

- locally stored credentials, solely to authenticate a read-only MT5 session;
- MetaTrader 5 terminal/account metadata;
- account information for audit context;
- symbol specifications, symbol visibility, tick data, historical bars, historical ticks, order
  history, deal history, open-position snapshots, and pending-order snapshots;
- broker-provided spread, contract, swap/rollover, commission, margin, point, digit, lot-size, and
  execution-condition metadata;
- locally available historical files, and later explicitly approved external data sources.

## Permanent prohibitions

This authorization does **not** permit, under any circumstance:

- `order_send`, `order_check`, or any order submission;
- opening, closing, modifying, cancelling, or deleting market/pending orders;
- modifying SL, TP, positions, account settings, terminal settings, broker configuration,
  production configuration, or credentials;
- invoking `TRADE_ACTION_DEAL`, `TRADE_ACTION_PENDING`, `TRADE_ACTION_SLTP`,
  `TRADE_ACTION_REMOVE`, or any equivalent trading action;
- moving or modifying any file under `frival/` or `ml-signal-service/`;
- printing, logging, storing, copying, or exposing credentials, tokens, passwords, account
  secrets, or full account identifiers;
- treating account metadata or positions as trade instructions;
- any shadow, demo, or live trading action.

## Credential-handling policy

- Credentials may be read **locally only as needed** to authenticate a read-only data session.
- Credentials must **never** be printed, logged, copied, serialized, committed, or included in
  experiment artifacts.
- Only the read-only session mechanics may consume them; no credential value may appear in any
  report, manifest, log, CSV, or decision document.

## MT5 safety policy

- Use **only read-only query methods** (for example, terminal/account/symbol metadata reads and
  historical bar/tick retrieval).
- **No order or trade-action functions** may be called.
- No terminal, account, or broker setting may be changed.

## Architecture policy

- Any MT5 integration must remain in an **explicitly isolated audit/acquisition adapter**.
- That adapter must **never** be imported by `core/`, `signals/`, `portfolio/`, `risk/`,
  `backtest/`, `llm_tools/`, or `monitoring/`.
- Research-library code must not gain execution or broker reachability; the isolation guards in
  `tests/system/test_execution_isolation.py` and `tests/system/test_no_lookahead.py` remain in force.

## Logging policy

- Reports may identify the broker/server at a **high level**.
- Account identifiers and all secrets must be **redacted** in every artifact.

## Revocation policy

- This authorization may be **revoked** by an explicit later governance decision, recorded as an
  append-only RUN_LOG entry.

## Boundary statement

This document does **not** authorize data access, credential access, or MT5 access today. It
records the approved future **read-only** policy only. Every G1/G2 action requires a separate,
explicit, task-level instruction, and all permanent prohibitions above apply at all times.
