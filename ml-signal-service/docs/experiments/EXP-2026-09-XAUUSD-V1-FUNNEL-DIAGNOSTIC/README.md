# EXP-2026-09 — XAUUSD Gold Rules Engine V1 — Offline Funnel Diagnostic

**Stage:** `XAUUSD_RULE_ENGINE_V1_OFFLINE_FUNNEL_DIAGNOSTIC`
**Date:** 2026-09-30
**Type:** offline, read-only historical replay + diagnostics. No MT5, no orders, no network, no PnL/performance.

## Purpose

Diagnose why the frozen XAUUSD Gold Rules Engine **V1** produced zero market
entries under its running production configuration, by measuring the causal
decision funnel over already-local XAUUSD M15/H1 history and classifying the
binding rejection reasons. This is a **signal-frequency and state-machine**
diagnostic only — it does not measure or claim profitability.

## Safety boundary

- Imports the frozen pure modules `engine.py`, `bias.py`, `levels.py` read-only; reads the frozen `config.yaml`.
- No production file, state file or journal is modified.
- No MetaTrader5 import/use; no broker, network, credentials, orders or positions.
- No PnL, returns, Sharpe, drawdown, profit factor, win rate or equity curve is computed.
- The replay never emits, simulates or submits an order; `ENTRY_INTENT` means the frozen engine returned `action == "ENTRY"`, nothing more.

## How it works

`replay_v1_funnel.py` walks every closed M15 bar once, chronologically. For the
M15 bar opening at `T` it forms the decision instant `t = T + 16 min` (matching
production `run_gold_rules.py`) and builds a snapshot containing only:

- M15 bars with `open <= T`,
- M30 bars whose close (`open + 30m`) `<= t`,
- H1 bars whose close (`open + 60m`) `<= t`.

The engine state persists across bars. Two passes are run: **combined** (frozen
config) and **A/B-only** (`breakout.enabled = False`, in memory). A contiguous
segment is replayed twice from the same initial state for the determinism check.

M30 is **derived** from M15 by deterministic 30-minute OHLC aggregation (no
native M30 file exists locally); see `DATA_MANIFEST.yaml`.

## Run

```
python replay_v1_funnel.py --win-m15 460 --win-m30 200 --win-h1 200
# outputs FUNNEL_RESULTS.csv, REJECTION_TAXONOMY.csv, MONTHLY_FUNNEL.csv
```

## Data dictionary

### `FUNNEL_RESULTS.csv`

| column | meaning |
|---|---|
| `scope` | `COMBINED` (frozen config), `A/B_ONLY` (Claim C disabled), `C_ONLY` (Claim-C attributions from the combined pass) |
| `stage` | funnel stage name (see below) |
| `count` | number of evaluations where the stage condition held |
| `share_of_m15` | `count / N_M15_CLOSED` for that scope |
| `conditional_from_prev` | `count / previous_stage_count` within the same scope (blank if undefined) |
| `note` | caveat for the row (e.g. C-only intermediate stages not emitted by the engine) |

Stage names: `N_H1_NON_FLAT`, `N_BIAS_CONSISTENT_LEVEL_ARMED`, `N_BREAK_EVENT`,
`N_REJECTION_EVENT`, `N_WAIT_CANDLE_CLOSE`, `N_RETEST_REJECTION`, `N_CONFIRMED`,
`N_CONFIRM_EXTREME_BROKEN`, `N_ENTRY_READY`, `N_ENTRY_INTENT`, `N_DROP`,
`N_ERROR`. (`N_M15_CLOSED` is the per-scope denominator and appears in `MONTHLY_FUNNEL.csv`.)

Stage definitions (all taken from the frozen engine's own decision/state output):

| stage | condition |
|---|---|
| `N_M15_CLOSED` | evaluated M15 close |
| `N_H1_NON_FLAT` | engine H1 bias ∈ {BULLISH, BEARISH} |
| `N_BIAS_CONSISTENT_LEVEL_ARMED` | engine holds an armed `watched_level` |
| `N_BREAK_EVENT` | reason contains "Break through" (A/B break → WAIT_CANDLE_CLOSE) |
| `N_REJECTION_EVENT` | reason contains "Rejection wick" (A/B rejection) |
| `N_WAIT_CANDLE_CLOSE` | state after evaluation = `WAIT_CANDLE_CLOSE` |
| `N_RETEST_REJECTION` | reason contains "retest rejection" |
| `N_CONFIRMED` | state after evaluation = `CONFIRMED` |
| `N_CONFIRM_EXTREME_BROKEN` | reason contains "break of confirm-candle extreme" |
| `N_ENTRY_READY` | state after evaluation = `ENTRY_READY` |
| `N_ENTRY_INTENT` | engine returned `action == "ENTRY"` (not submitted) |
| `N_DROP` | engine returned `action == "DROP"` |
| `N_ERROR` | engine returned `action == "ERROR"` |

### `REJECTION_TAXONOMY.csv`

| column | meaning |
|---|---|
| `bucket` | one of the fixed taxonomy buckets |
| `count` | evaluations classified into the bucket |
| `share_all_m15` | `count / N_M15_CLOSED` (combined) |
| `share_pre_entry_candidates` | `count / (#evaluations with ENTRY_READY or ENTRY)` |
| `month_distribution` | `YYYY-MM=n;...` for months with count > 0 |
| `representative_timestamp` | first timestamp hitting the bucket |
| `representative_summary` | anonymized action/state/bias/reason fragment |

Classification rule: every non-advancing evaluation (`action ∈ {NONE, DROP,
ERROR}` while not managing an open trade, `state != IN_TRADE`) is assigned its
first binding reason. `LEVEL_CONSUMED_OR_INVALID` is reserved; observed drops
land in the buckets the frozen engine actually emits.

### `MONTHLY_FUNNEL.csv`

| column | meaning |
|---|---|
| `month` | `YYYY-MM` |
| `N_M15_CLOSED` | evaluated M15 closes that month (combined) |
| other columns | the combined funnel stage counts for that month |

## Caveats

- **No bid/ask/spread history:** the diagnostic uses the last closed M15 close as
  the price reference for both bid and ask. Location/RR/risk gate *fidelity* to
  real execution is therefore `NOT_EVALUATED`; the structural gate outcomes are
  the best available closed-bar estimate. Concurrency and daily-loss gates use
  the permitted neutral placeholders (`open_positions=0`, `pnl=0`) and are not
  informative in this replay.
- **M30 is derived** from M15 (no native local M30), so A/B results are
  conditional on that deterministic aggregation.
- **Timezone:** all cutoffs are relative to the same UTC clock, so the causal
  sequence is unaffected by any broker-server offset; the offset itself is not
  asserted here.
- Results are **signal-frequency diagnostics**, not a profitability claim.

## Files

`README.md`, `DATA_MANIFEST.yaml`, `REPLAY_CAUSALITY_AUDIT.md`,
`FUNNEL_RESULTS.csv`, `REJECTION_TAXONOMY.csv`, `MONTHLY_FUNNEL.csv`,
`DETERMINISM_CHECK.md`, `V1_FREQUENCY_DECISION.md`,
`RESEARCH_VARIANT_REGISTER.md`, `RUN_LOG.md`, `replay_v1_funnel.py`.
