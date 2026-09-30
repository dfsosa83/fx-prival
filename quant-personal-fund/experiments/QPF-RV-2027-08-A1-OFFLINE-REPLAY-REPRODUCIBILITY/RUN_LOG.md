# Run Log — QPF-RV-2027-08-A1-OFFLINE-REPLAY-REPRODUCIBILITY

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK

- **date:** 2026-09-30
- **stage:** `A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK`
- **status:** `preregistered`
- **scope:** A1 `GOLD_RULES_ENGINE` only; XAUUSD local fixtures only.
- **source/fixture binding (recorded, not executed):** `engine.py` `9653AE90…2357E8`; `bias.py`
  `10699993…F8362F`; `levels.py` `63442EBB…E0E49D5`; `run_gold_rules.py` `CF1EC9A4…D811967`;
  fixtures `XAUUSD_M15.csv` `574A38DC…D28FBB`, `XAUUSD_M30.csv` `9345E3D3…0A55566F`,
  `XAUUSD_H1.csv` `81E51BBF…170B7521`.
- **offline-only safety boundary:** required `OFFLINE_ONLY`, `ORDERS_DISABLED`, `NO_BROKER_CONNECTION`,
  `NO_MT5_IMPORT_OR_INITIALIZATION`, `NO_NETWORK`, `NO_EXTERNAL_DATA`, `NO_VIRTUAL_FILL`, `NO_PNL`.
- **static isolation result:** **NOT demonstrable** — the A1 runtime entry point imports
  `execution_bot.core.mt5_connector`/`order_manager` and uses MetaTrader5 (bar fetch needed even in dry
  mode); `tests/test_rules.py` imports `tests/fetch_data` (MetaTrader5); `tests/test_demo_pnl.py`
  imports `run_gold_rules` + `demo_ledger`.
- **two-run comparison:** **not performed** (no safe offline entry point). No event records produced.
- **decision:** `REPLAY_REPRODUCIBILITY_PAUSE` (reason `OFFLINE_ISOLATION_NOT_DEMONSTRABLE`).
- **no broker/MT5/network/execution/PnL activity:** confirmed.
- **continuity:** not updated (PAUSE).
- **next authorization consequence:**
  ```text
  No forward observation, demo order, virtual fill, PnL analysis or trading is
  authorized. A separately authorized corrective stage may design an isolated
  offline A1 runner that imports only the pure engine modules and reads the
  local fixtures with no MT5/broker imports.
  ```
- **artifacts created:**
  - `quant-personal-fund/experiments/QPF-RV-2027-08-A1-OFFLINE-REPLAY-REPRODUCIBILITY/A1_REPLAY_REPRODUCIBILITY_REPORT.md`
  - `.../A1_REPLAY_REPRODUCIBILITY_RESULTS.json`
  - `.../A1_REPLAY_REPRODUCIBILITY_DECISION.md`
  - `.../RUN_LOG.md`
