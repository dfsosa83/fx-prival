# A1 — Controlled Offline Replay Reproducibility Report

**Stage:** `A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK`
**Experiment:** `QPF-RV-2027-08-A1-OFFLINE-REPLAY-REPRODUCIBILITY`
**Date:** 2026-09-30

## Result

```text
REPLAY_REPRODUCIBILITY_PAUSE
reason: OFFLINE_ISOLATION_NOT_DEMONSTRABLE
```

---

## 1. Scope and offline safety boundaries

Verify that frozen A1, run twice on identical local fixtures offline, produces complete and
deterministic event records. Reproducibility/integrity only — no price performance, PnL, returns,
costs, outcomes, or economic evaluation. Required boundary: `OFFLINE_ONLY`, `ORDERS_DISABLED`,
`NO_BROKER_CONNECTION`, `NO_MT5_IMPORT_OR_INITIALIZATION`, `NO_NETWORK`, `NO_EXTERNAL_DATA`,
`NO_VIRTUAL_FILL`, `NO_PNL`.

## 2. Selected entry-point / source / fixture paths

- A1 pure engine modules: `frival/gold_rules/engine.py`, `frival/gold_rules/bias.py`,
  `frival/gold_rules/levels.py`.
- A1 runtime entry point: `frival/gold_rules/run_gold_rules.py` (loop/MT5 I/O owner).
- A1 local fixtures: `frival/gold_rules/tests/fixtures/XAUUSD_M15.csv`, `XAUUSD_M30.csv`, `XAUUSD_H1.csv`.
- Referenced tests: `frival/gold_rules/tests/test_engine.py`, `test_rules.py`, `test_breakout.py`,
  `test_demo_pnl.py`, `fetch_data.py`.

## 3. Source and fixture hashes (read-only; no execution)

| File | SHA256 |
|---|---|
| `frival/gold_rules/engine.py` | `9653AE906D30583493A49A478CA123B6A190AC16B93B3FD4F9A2CCDD4B2357E8` |
| `frival/gold_rules/bias.py` | `106999937CFC810C88E58DCCF9476EC63FF998D2CDF08A4BFE43DCD259F8362F` |
| `frival/gold_rules/levels.py` | `63442EBBADAF059B816E49F9FDB28D71471CA4E7C5C98C8C3FE997674E0E49D5` |
| `frival/gold_rules/run_gold_rules.py` | `CF1EC9A4B0DDD1FF71E26D3E89C421112FB9A40098F78B248FD7C5CADD811967` |
| `frival/gold_rules/tests/fixtures/XAUUSD_M15.csv` | `574A38DC501821106FB5CA32E43F61CEACCEDBC31E281470B70B0D2665D28FBB` |
| `frival/gold_rules/tests/fixtures/XAUUSD_M30.csv` | `9345E3D33DE2391A2FDED8B2BC49FC5DD1F2E071C24B30D195D5D7910A55566F` |
| `frival/gold_rules/tests/fixtures/XAUUSD_H1.csv` | `81E51BBF9C720BBA96E5AB4A5B0C98EE483B14A84D0B8AE57C5526B2170B7521` |

Fixtures are local, XAUUSD-specific, and not modified. **Fixture eligibility: OK.**

## 4. Static isolation assessment (blocker)

- `frival/gold_rules/run_gold_rules.py` (the A1 runtime entry point) imports
  `execution_bot.core.mt5_connector` (MT5Connector) and `execution_bot.core.order_manager`
  (OrderManager) (lines 52–55), and calls `import MetaTrader5` and MT5 in several places
  (e.g. bar fetch "needed even in dry mode", lines 123, 183–185, 223–224, 294–295, 389, 477–478).
  Importing/running it therefore **initializes/uses MT5/broker functionality** → violates
  `NO_MT5_IMPORT_OR_INITIALIZATION`.
- `frival/gold_rules/tests/test_rules.py` imports `tests.fetch_data`, whose `_init_mt5()` imports
  MetaTrader5 → importing the test triggers MT5. `test_demo_pnl.py` imports `run_gold_rules` +
  `execution_bot.core.demo_ledger` → MT5 chain.
- `frival/gold_rules/tests/test_engine.py` is pure (bias/engine/pandas) but **synthesizes OHLCV** and
  asserts transitions; it does not read the local fixtures and does not emit the required event-record
  sequence.

**Conclusion:** there is **no demonstrably safe existing offline entry point** that reads the local
fixtures, runs the frozen A1 engine, and emits the required event records without importing MT5/broker
code. Per the frozen rule, no execution was attempted.

## 5. Run 1 / Run 2 status and event records

- Run 1: **not executed** (blocked pre-execution).
- Run 2: **not executed**.
- Event-record count: **0** (none produced).
- Field completeness: n/a. Canonical comparison: n/a. Temporary cleanup: n/a (no temp created).

## 6. Prohibited activity attestation

No code/test/bot executed; no MT5/broker/network/credentials access; no orders, virtual fills, PnL,
cost, or performance computation; no repository file modified; no replay run.

## 7. Final decision

```text
REPLAY_REPRODUCIBILITY_PAUSE
reason: OFFLINE_ISOLATION_NOT_DEMONSTRABLE
```

## 8. Next authorization consequence

The A1 reproducibility gate did not pass. No forward observation, demo order, virtual fill, PnL
analysis or trading is authorized until a separately authorized corrective stage resolves the
documented blocker (e.g. an author-designed isolated offline A1 runner that imports only the pure
`engine.py`/`bias.py`/`levels.py` and reads the local fixtures, with no MT5/broker imports).
