# A1 Offline Replay Reproducibility — Decision

**Stage:** `A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK`
**Date:** 2026-09-30

```text
decision: REPLAY_REPRODUCIBILITY_PAUSE
reason: OFFLINE_ISOLATION_NOT_DEMONSTRABLE
```

## Blocker

The A1 runtime entry point (`frival/gold_rules/run_gold_rules.py`) imports
`execution_bot.core.mt5_connector` and `execution_bot.core.order_manager` and uses MetaTrader5 (bar fetch
is needed "even in dry mode"); `tests/test_rules.py` imports `tests/fetch_data` (imports MetaTrader5);
`tests/test_demo_pnl.py` imports `run_gold_rules` + `demo_ledger`. There is therefore **no existing,
demonstrably safe offline path** that reads the local XAUUSD fixtures, runs the frozen A1 engine, and
emits the required event records without initializing MT5/broker functionality. No execution was attempted.

The pure engine modules (`engine.py`, `bias.py`, `levels.py`) are offline-safe, and the local fixtures are
eligible — but there is no existing offline runner that consumes the fixtures and emits the frozen
event-record schema.

## Statement

```text
The A1 reproducibility gate did not pass. No forward observation, demo order,
virtual fill, PnL analysis or trading is authorized until a separately
authorized corrective stage resolves the documented blocker.
```

A corrective stage would need an author-designed, isolated offline A1 runner that imports only the pure
engine modules and reads the local fixtures, with no MT5/broker imports.
