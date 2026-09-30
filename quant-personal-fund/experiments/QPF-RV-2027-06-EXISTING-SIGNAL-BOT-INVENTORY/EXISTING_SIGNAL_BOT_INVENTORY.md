# Existing Signal and Bot Inventory

**Stage:** `EXISTING_SIGNAL_AND_BOT_EVIDENCE_INVENTORY`
**Experiment:** `QPF-RV-2027-06-EXISTING-SIGNAL-BOT-INVENTORY`
**Date:** 2026-09-30
**Mode:** read-only inspection of repository source, docs, tests, config templates and stored logs.

> No code, test, bot, watcher, replay, simulator or backtest was executed. No market data was parsed or
> analysed. No MT5/broker/network/credential/account/order activity. H6 and the prior families
> (G3-v3, G3-AUDNZD, H4-C2, H5-v2) remain rejected in their frozen formulations. Nothing here grants
> demo, paper, shadow or live trading, and nothing here is a profitability claim.

---

## Scope and Safety Boundary

This inventory identifies **already-implemented** signals, bots, lifecycle handling, logs, tests and
execution adapters, and judges whether any concrete existing rule can be evaluated in a controlled
demo/replay workflow **without inventing a new signal** and **without enabling live trading**.

Governance reads (authoritative): `research_control/PROJECT_HANDOFF.md`, `NEXT_ACTION.md`,
`RESEARCH_LEDGER.yaml`, `CONTINUITY_PROTOCOL.md`; plus the single H6 decision artifact
`experiments/QPF-RV-2027-05-H6-FAILED-BREAKOUT-STATISTICAL-SCREEN/H6_FAILED_BREAKOUT_DECISION.md`
(confirming `REJECT_H6_FX_STATISTICAL_VIABILITY` and `REJECT_H6_XAUUSD_STATISTICAL_VIABILITY`).

Evidence labelling used throughout: **VERIFIED** (read directly from source/doc/test/log),
**INFERRED** (from source structure only), **UNKNOWN** (not determinable from repository evidence).

## Repository Areas Inspected

- `frival/` — `gold_rules/` (+`tests/`, `tests/fixtures/`, `config/`, `journal/`, `state/`),
  `execution_bot/` (+`core/`, `tests/`, `config/`, `tools/`, `reports/`, `data/`), `agents/` (+`prompts/`),
  `model/`, `fx_rules_backtest/` (+`data/`, `results/`), `output/{logs,signals,reports}/`, and top-level
  orchestration (`main.py`, `signal_gate.py`, `run_daily_scheduler.py`, `live_logger.py`, `.bat` launchers).
- `ml-signal-service/` — `notebooks/` (per-symbol + MERG), `models_bin/`, `steps/`, `config/`, `docs/`
  (incl. `docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md` and `docs/experiments/ROADMAPS/`).
- `quant-personal-fund/` — `research_control/`, `experiments/` (registry + experiment folders),
  `signals/` (trend/carry/value/ml_overlays), `core/`, `portfolio/`, `risk/`, `backtest/`, `execution/`,
  `monitoring/`, `docs/`.

## Asset Register

| ID | Name | Path(s) | Category (primary) | Instrument | TF | Rule vs model | Exec isolated | MT5/network | Evidence basis |
|---|---|---|---|---|---|---|---|---|---|
| A1 | `GOLD_RULES_ENGINE` | `frival/gold_rules/{engine,bias,levels,run_gold_rules,status}.py`, `frival/gold_rules/config.yaml` | `IMPLEMENTED_SIGNAL_RULE` | XAUUSD | M15/M30/H1 | deterministic rule (no ML/LLM) | reuses `execution_bot` adapter; has `--dry` | MT5 (broker) | VERIFIED |
| A2 | `FX_SIGNAL_PIPELINE` | `frival/main.py`, `frival/signal_gate.py`, `frival/agents/*`, `frival/model/{features,ensemble}.py`, `frival/run_daily_scheduler.py` | `SIGNAL_ORCHESTRATOR` | EURUSD, GBPUSD, USDCHF, USDCAD (+EURUSD_AGNOSTIC shadow) | H1 | hybrid ML + LLM | signals only (no order call in `main.py`) | LLM APIs + MT5 data | VERIFIED |
| A3 | `EXEC_D1_TERMINAL` | `frival/execution_bot/run_exec_d1_terminal.py`, `core/{exec_d1_terminal,lifecycle,lifecycle_store}.py` | `PENDING_ENTRY_LIFECYCLE` (+`EXECUTION_ADAPTER`) | configurable | H1 | deterministic lifecycle | dedicated adapter; demo-env guard | MT5 (demo) | VERIFIED |
| A4 | `LEGACY_ORDER_BOT` | `frival/execution_bot/{run.py,order_bot.py,signal_watcher.py}`, `core/{order_manager,demo_ledger,broker_constraints,config_manager}.py` | `DEMO_OR_PAPER_COMPONENT` | configurable | H1 | deterministic; demo virtual fill | partial (demo branch) | MT5 | VERIFIED |
| A5 | `GOLD_TESTS_FIXTURES` | `frival/gold_rules/tests/{test_rules,test_engine,test_breakout,test_demo_pnl,sanity_walk}.py`, `tests/fixtures/XAUUSD_{M15,M30,H1}.csv` | `TEST_FIXTURE_OR_TEST_EVIDENCE` | XAUUSD | M15/M30/H1 | local fixtures | n/a (offline) | none | VERIFIED |
| A6 | `ML_LLM_ARTIFACTS` | `ml-signal-service/notebooks/**`, `models_bin/*.joblib`, `steps/**`, `experiments/**` | `ML_LLM_COMPONENT` | multiple (+US30, XAUUSD) | H1/S/D | trained models / notebooks | n/a | yes (training/data steps) | VERIFIED (files); performance UNKNOWN-by-design |
| A7 | `HISTORICAL_LOGS_REPORTS` | `frival/output/logs/`, `frival/output/signals/`, `frival/output/reports/`, `frival/execution_bot/data/`, `frival/gold_rules/journal/`, `frival/execution_bot/reports/` | `HISTORICAL_LOG_OR_REPORT` | FX + XAUUSD | H1/M15 | n/a (data) | n/a | none (stored) | VERIFIED |
| A8 | `FX_RULES_BACKTEST` | `frival/fx_rules_backtest/{run_backtest,acquire_data,report}.py`, `data/*_M15.csv`,`data/*_M30.csv`, `results/*_ledger.csv`,`results/*_decisions.jsonl` | `SIMULATOR_OR_REPLAY_COMPONENT` | EURUSD, GBPUSD, USDCAD, USDJPY | M15/M30/H1 | deterministic replay of A1 engine | offline (no MT5 at replay) | data source script only | VERIFIED |
| A9 | `DEMO_LEDGER` | `frival/execution_bot/core/demo_ledger.py`, `frival/execution_bot/data/demo_trades_ledger.jsonl` | `DEMO_OR_PAPER_COMPONENT` | FX + XAUUSD (shared) | n/a | bookkeeping of virtual fills | n/a | none | VERIFIED |
| A10 | `GOLD_RULES_DESIGN_DOC` | `ml-signal-service/docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md` | `DOCUMENTATION_ONLY` | XAUUSD | M15/M30/H1 | rule contract | n/a | none | VERIFIED |
| A11 | `QPF_PLATFORM_LIBRARY` | `quant-personal-fund/{signals,core,portfolio,risk,backtest,execution,monitoring}/**` | `UNKNOWN_OR_INCOMPLETE` (platform scaffolding) | multi-asset | mixed | deterministic helpers + Phase-6 placeholders | n/a | none observed | INFERRED |

## Gold / XAUUSD Assets

**A1 `GOLD_RULES_ENGINE` — VERIFIED.** Deterministic state machine, explicitly *no ML, no AI agents*
(design doc `EXP-2026-03` §1.2). Components:
- `bias.py`: H1 bias = EMA20/EMA50 + close-vs-EMA50 → `BULLISH`/`BEARISH`/`FLAT` (`compute_h1_bias`).
- `levels.py`: M30 5-bar fractal swing levels (`fractal_wing=2`), ATR merge, consumption, nearest-only arming.
- `engine.py`: states `WATCH_ZONE → WAIT_CANDLE_CLOSE → CONFIRMED → ENTRY_READY → IN_TRADE →
  DONE/INVALIDATED`; gates (location tolerance, R:R ≥ 1.5, $ risk ≤ 25, ≤1 concurrent, −$50/day);
  break-and-retest (A/B) plus a separate breakout-continuation trigger ("Claim C", comment `GOLD_RULES_C`).
- `run_gold_rules.py`: orchestrator owning MT5 I/O, journaling, state persistence, login guard, resilience
  wrapper, `--dry` (log-only) mode, and **demo virtual PnL realization** (`_realize_trade` → shared ledger).
- `config.yaml`: atomics (0.01 lot, ≤$25/trade, ≤1 position, −$50/day; timeouts
  `pending_retest_max_bars_m15=20`, `confirm_max_bars_m15=3`).
- Outputs: `journal/YYYY-MM-DD.jsonl` (per-evaluation; fields `action,reason,state,levels,gate_results,bid,ask,pnl,ts,utc`),
  `state/engine_state.json` (persisted `EngineState`).
- Evidence of tests/fixtures: `tests/test_{rules,engine,breakout,demo_pnl}.py`, `tests/sanity_walk.py`,
  `tests/fixtures/XAUUSD_{M15,M30,H1}.csv`.
- Prior evidence-plan caveat: `docs/experiments/ROADMAPS/GOLD-ENGINE-EVIDENCE-PLAN.md` documented a broken
  demo measurement loop (G7: simulated orders self-closing with `pnl 0`). `PORTFOLIO-DEMO-SPEC.md` §3 and
  `tests/test_demo_pnl.py` show the PnL realization was subsequently implemented. **VERIFIED** that the
  current code realizes demo PnL and that live mode must not write the demo ledger.
- **UNKNOWN:** current `trading.mode` value (config template not read here) and whether the running process
  was started against the current code revision.

**A10** is the human-readable rule contract for A1 and is the primary specification source for replay/demo
design. **A5** supplies small offline XAUUSD fixtures.

## FX Assets

**A2 `FX_SIGNAL_PIPELINE` — VERIFIED (structure).** Orchestrates per-pair runs: `model/ensemble.py`
(ML probability) → `signal_gate.py` (threshold → session → cooldown → M15 candle-close alignment;
optional borderline) → `agents/` (`technical.py`, `fundamental.py`, `senior.py`; prompts under
`agents/prompts/*.txt`). Writes `FIRED`/`SHELVED` (and `EURUSD_AGNOSTIC` shadow) signal records to
`frival/output/signals/<YYYY-MM>/<YYYY-MM-DD>.jsonl` with `signal_id`, `trade.{entry,entry_zone,stop_loss,take_profit}`,
`final_decision`. A targeted search found **no** `order_send`/`TRADE_ACTION`/`positions_get` in `main.py`
→ produces candidate signals only. Network: LLM APIs + MT5 market data. Historically rejected family.

**A3 `EXEC_D1_TERMINAL` — VERIFIED.** Real-order path (`run_exec_d1_terminal.py`, 1s monitor) reading today's
`FIRED` signals and routing to `TerminalExecutor` (`core/exec_d1_terminal.py`). Lifecycle engine
`core/lifecycle.py` + append-only store `core/lifecycle_store.py`. Isolated adapter: demo-env guard
(login + `trade_mode == 0`), emergency-stop file, idempotency, one position per pair, daily cap, and
entry-semantics modes `zone` (in-zone market, else ≤10-min touch pending) / `reanchor` (market at first
in-window tick, SL/TP re-anchored on the fill). Persists `data/exec_d1_runtime/lifecycle_events.jsonl`
(source of truth), derived `pending_entries.jsonl` / `open_positions.jsonl`, and real orders in
`data/exec_d1_executions.jsonl`.

**A4 `LEGACY_ORDER_BOT` — VERIFIED (structure).** `run.py --once` / `signal_watcher.py`; `core/order_manager.py`
has a demo simulated branch (`is_demo_mode()` → `"DEMO MODE - Simulated execution"`); `core/demo_ledger.py`
= virtual ledger; `core/broker_constraints.py` = MT5 field audit + fail-closed gate; delegation gate
(`order_bot.py` imports `exec_d1_enabled` and skips when `execution.enabled` is true).

**A6 `ML_LLM_ARTIFACTS` — rejected family.** Per-symbol training notebooks and `models_bin/*.joblib`
(EURUSD/GBPUSD/USDCAD/USDCHF/USDJPY/XAUUSD, MERG, US30). These are the rejected directional-ML/crosses/
event families. **NOT a candidate here.**

**A8 `FX_RULES_BACKTEST` — VERIFIED.** One-pass deterministic, read-only bar replay of the **unmodified A1
gold-rules engine** over each FX pair's local M15/M30 CSVs (`data/`), emitting per-pair trade ledgers and
decision logs (`results/`). This is a concrete existing simulator/replay harness and the clearest
offline-replay precedent. It does not itself invoke MT5 at replay time.

## Signal Lifecycle and Pending Entry

**A3** implements the full lifecycle (VERIFIED in `core/lifecycle.py`, `core/exec_d1_terminal.py`):

```text
SIGNAL_RECEIVED -> ENTRY_PENDING | MARKET_FILLED | PENDING_TRIGGERED
                -> VIRTUAL_OPEN -> CLOSED_TP | CLOSED_SL | CLOSED_TIMEOUT
                -> EXPIRED_UNFILLED | NO_VALID_PENDING | EXTERNAL_STATE_CONFLICT
```

- **Pending entries are supported** (`ENTRY_PENDING`, trigger level, quote watermark).
- **The ~10-minute validity window is confirmed in code**: `ENTRY_VALIDITY_SECONDS = 600`; expiry emits
  `EXPIRED_UNFILLED` with `reason` ∈ {`no_touch`,`no_quote`,`processed_after_expiry`,`broker_constraint_blocked`,…}.
- **Risk handling / exits**: closed states `CLOSED_TP`/`CLOSED_SL`/`CLOSED_TIMEOUT`, plus
  `EXTERNAL_STATE_CONFLICT` for manual/external closures (excluded from paper metrics).
- Lifecycle mechanics are unit-tested: `execution_bot/tests/test_exec_delta1.py`,
  `execution_bot/tests/test_exec_d1_terminal.py`.

## Logs, Reports and Test Evidence

- FX signal journal: `frival/output/signals/<MM>/<date>.jsonl`; scheduler log `frival/output/logs/*_live.log`.
- EXEC-D1 monitor log: `frival/output/logs/*_exec_d1.log`; runtime event log + derived snapshots under
  `frival/execution_bot/data/exec_d1_runtime/`; real-order log `frival/execution_bot/data/exec_d1_executions.jsonl`.
- Gold: `frival/gold_rules/journal/*.jsonl` (12 daily files present) + `state/engine_state.json`.
- Shared demo ledger: `frival/execution_bot/data/demo_trades_ledger.jsonl`.
- Replay outputs: `frival/fx_rules_backtest/results/{SUMMARY.md,*_ledger.csv,*_decisions.jsonl}` and local
  `frival/fx_rules_backtest/data/*_{M15,M30}.csv`.
- Reports: `frival/execution_bot/reports/*.md`; `frival/output/reports/*.json`.
- Tests/fixtures: `frival/execution_bot/tests/{test_exec_delta1,test_exec_d1_terminal,test_diagnostics,test_demo_ledger}.py`;
  `frival/gold_rules/tests/**`; `ml-signal-service/**/*.py` tests; `quant-personal-fund/{signals,portfolio,risk,backtest}/**/tests`.

## Demo Evaluation Readiness

See `DEMO_EVALUATION_READINESS.md`. In summary: **A1 gold rules** and **A3 EXEC-D1 lifecycle** are the two
most concrete, isolated, measurable existing assets, both best suited to a separately authorised
**forward-demo design**; **A8** provides an existing offline replay harness relevant to A1. FX ML/LLM signal
generation (A2/A6) and all prior hypothesis families remain rejected.

## Material Unknowns and Blockers

- A1: current `trading.mode` in the gold config template not read here; full-history M15/M30 beyond the
  fixtures and the `fx_rules_backtest/data` CSVs is unverified; running-process-vs-code revision unknown.
- A1/A3: forward measurement requires an explicit, pre-declared measurement/logging plan and a demo-only
  isolation confirmation; no cost/spread/swap model is applied in the demo ledger.
- A2: external LLM API dependency; signal quality historically rejected → not a candidate.
- A4: demo virtual fills are paper (not broker fills); consumer of A2 signals, not a distinct rule.
- A8: replays A1's engine on FX; EXP-2026-04 (per `GOLD-ENGINE-EVIDENCE-PLAN.md` §2) reported the rules do
  not transfer to FX — A8 is useful as a *harness*, not as a claim about the transferred edge.
- A11: platform phases 2–6 are planned/incomplete; execution and monitoring packages are placeholders.
- No PnL, cost, return, Sharpe, drawdown, win-rate or other statistic was computed; **no asset is claimed
  profitable, safe for production, or authorised to trade.**

## Conclusion

Concrete, implemented, deterministic rules and lifecycle machinery exist in the repository. The strongest
measurable candidates are **A1 `GOLD_RULES_ENGINE` (XAUUSD)** and **A3 `EXEC_D1_TERMINAL` (pending-entry
lifecycle)**, with **A8 `FX_RULES_BACKTEST`** available as an existing offline replay harness. This is a
technical-measurability result only. Any next stage (controlled forward-demo design) requires **separate
explicit authorisation**; no live execution is authorised or implied, and FX/XAUUSD are kept as separate strata.
