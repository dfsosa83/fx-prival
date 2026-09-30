# Demo Evaluation Readiness

**Stage:** `EXISTING_SIGNAL_AND_BOT_EVIDENCE_INVENTORY`
**Date:** 2026-09-30

Technical measurability only. This is **not** a profitability, edge or production-readiness claim.
No live execution is recommended anywhere in this document. FX and XAUUSD are treated as separate strata.

This document covers the candidates **not** classified `NOT_A_CANDIDATE`: **A1**, **A3**, **A8**.

---

## A1 — `GOLD_RULES_ENGINE` (XAUUSD)

- **Ready for offline replay design:** **yes (scoped).** The decision logic is pure and deterministic
  (`engine.py`, `bias.py`, `levels.py`), and there is an existing replay precedent for the same engine
  (`A8`, `frival/fx_rules_backtest/run_backtest.py`) plus local XAUUSD fixtures
  (`frival/gold_rules/tests/fixtures/XAUUSD_{M15,M30,H1}.csv`). A full-history M15/M30 XAUUSD dataset for a
  long replay is **not verified** to exist beyond the fixtures; the replay scope would begin fixture-bounded.
- **Ready for forward-demo design:** **yes.** The runner already loops every 60s with journaling
  (`journal/*.jsonl`), state persistence (`state/engine_state.json`), a login guard, a `--dry` log-only mode,
  and demo virtual-PnL realization to the shared ledger (`_realize_trade`, verified by
  `tests/test_demo_pnl.py`).
- **Minimum missing evidence / instrumentation:** (i) confirm the current `trading.mode` and that the running
  process matches the current code revision; (ii) pre-declare the measurement fields and window (the
  journal already carries `action,reason,state,levels,gate_results,bid,ask,pnl,ts,utc`); (iii) confirm how
  exit outcomes (SL/TP/invalidation/close) are captured per trade from the demo path.
- **Execution boundary isolated:** **partially.** It reuses the shared `execution_bot` adapter (MT5) with a
  demo branch and a login guard; it is not a dedicated, self-contained adapter. It must not be run in a
  mode that places real orders during this evaluation.
- **Recommended next stage:** **`FORWARD_DEMO_DESIGN`** (optionally preceded by a scope-limited
  `REPLAY_DESIGN` on the local fixtures / `fx_rules_backtest` data).

## A3 — `EXEC_D1_TERMINAL` (pending-entry lifecycle, configurable instruments)

- **Ready for offline replay design:** **yes (lifecycle mechanics only).** `core/lifecycle.py` +
  `core/lifecycle_store.py` are pure and unit-tested (`tests/test_exec_delta1.py`,
  `tests/test_exec_d1_terminal.py`), and an authoritative append-only event log exists
  (`data/exec_d1_runtime/lifecycle_events.jsonl`). Replay would validate *lifecycle mechanics*
  (pending → touch/expiry, close handling), **not** signal quality.
- **Ready for forward-demo design:** **yes.** It is the dedicated real-order path, already guarded by a
  demo-env check (`login` + `trade_mode == 0`), emergency-stop file, idempotency, one-position-per-pair and
  a daily cap; measurement of entry/pending/expiry behaviour is directly feasible from the event log.
- **Minimum missing evidence / instrumentation:** (i) pre-declare the measurement of pending→entry/expiry
  outcomes and close/exit handling; (ii) confirm the demo-only isolation guard remains enforced; (iii)
  specify the analysis unit (per-signal lifecycle outcome) without costs/PnL in this stage.
- **Execution boundary isolated:** **yes** — dedicated adapter with demo guard and explicit safety controls.
- **Recommended next stage:** **`FORWARD_DEMO_DESIGN`**.

## A8 — `FX_RULES_BACKTEST` (offline replay harness)

- **Ready for offline replay design:** **yes.** This is itself a one-pass, deterministic, read-only replay
  harness that executes the unmodified A1 engine over local per-pair M15/M30 CSVs and emits trade ledgers
  and decision logs (`results/*_ledger.csv`, `results/*_decisions.jsonl`).
- **Ready for forward-demo design:** **n/a** — it is an offline tool, not a live/demo engine.
- **Minimum missing evidence / instrumentation:** clarify whether the replay's data-acquisition step is
  reproducible from local files alone (the replay itself is local; `acquire_data.py` may depend on an
  external source for (re)building the CSVs).
- **Execution boundary isolated:** **yes** — no MT5/orders at replay time.
- **Recommended next stage:** **`REPLAY_DESIGN`** (as a supporting harness for A1, not a standalone rule).

---

## Not advanced

- **A2 `FX_SIGNAL_PIPELINE`** — `NOT_A_CANDIDATE`: hybrid ML+LLM, external API dependency, historically
  rejected signal quality; not self-contained offline.
- **A4 `LEGACY_ORDER_BOT`** — `NOT_A_CANDIDATE`: consumer of A2 signals, paper/demo virtual fills; not a
  distinct rule.
- **A5 `GOLD_TESTS_FIXTURES`, A6 `ML_LLM_ARTIFACTS`, A7 `HISTORICAL_LOGS_REPORTS`, A9 `DEMO_LEDGER`,
  A10 `GOLD_RULES_DESIGN_DOC`, A11 `QPF_PLATFORM_LIBRARY`** — supporting evidence/components, not candidates.

No recommendation here authorises demo, paper, shadow or live trading. Any next stage requires **separate
explicit authorisation**, and the next action remains `REQUIRES_SEPARATE_AUTHORIZATION`.
