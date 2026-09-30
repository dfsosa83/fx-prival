# Run Log — QPF-RV-2027-07-A1-A3-A8-PRACTICAL-EVALUATION-DESIGN

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — A1_A3_A8_REPLAY_AND_FORWARD_DEMO_EVALUATION_DESIGN

- **date:** 2026-09-30
- **stage:** `A1_A3_A8_REPLAY_AND_FORWARD_DEMO_EVALUATION_DESIGN`
- **status:** `preregistered`
- **assets bound:** A1 `GOLD_RULES_ENGINE`, A3 `EXEC_D1_TERMINAL`, A8 `FX_RULES_BACKTEST`.
- **nature:** documentation / static-inspection only.
- **two-track plan:** (1) controlled offline replay reproducibility (A1, with A8 as support harness);
  (2) forward observation with orders disabled (A1 rule, A3 lifecycle/recording adapter).
- **orders disabled by design:** default mode `OBSERVATION_ONLY`, `ORDERS_DISABLED`,
  `NO_BROKER_CONNECTION_REQUIRED`.
- **actions explicitly NOT performed:** no replay, forward observation, demo/paper/shadow/live activity;
  no code/test/bot/notebook execution; no market-data/PnL/statistical analysis; no broker/MT5/network/
  credentials; no orders; no modification of A1/A3/A8 or prior artifacts.
- **artifacts created:**
  - `quant-personal-fund/experiments/QPF-RV-2027-07-A1-A3-A8-PRACTICAL-EVALUATION-DESIGN/PRACTICAL_EVALUATION_OVERVIEW.md`
  - `.../A1_CONTROLLED_REPLAY_DESIGN.md`
  - `.../A1_A3_FORWARD_OBSERVATION_DESIGN.md`
  - `.../EVALUATION_EVENT_SCHEMA.yaml`
  - `.../SAFETY_AND_PROMOTION_GATES.md`
  - `.../RUN_LOG.md`
- **authorization consequence (next):**
  ```text
  A separate authorization may perform only the controlled offline
  reproducibility check using the frozen A1 rule version and existing local
  fixtures. No broker connection, forward observation, demo order, virtual fill,
  PnL analysis or trading is authorized.
  ```
