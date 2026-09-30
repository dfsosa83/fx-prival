# RUN LOG — EXP-2026-09 XAUUSD V1 FUNNEL DIAGNOSTIC

## 2026-09-30 — stage execution (offline, read-only)

- **stage:** `XAUUSD_RULE_ENGINE_V1_OFFLINE_FUNNEL_DIAGNOSTIC`
- **mode:** offline historical replay + diagnostics. Read-only.
- **mandatory reads (frozen V1 spec):** `frival/gold_rules/engine.py`,
  `bias.py`, `levels.py`, `config.yaml`, `run_gold_rules.py`,
  `ml-signal-service/docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md`.
- **diagnostic reads:** `frival/gold_rules/journal/*.jsonl`, `frival/gold_rules/state/engine_state.json`.
- **local data used:** XAUUSD M15 and H1 parquet under
  `quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/data/processed/`
  (M15 155,252 bars / H1 38,837 bars, 2020-02-28 → 2026-09-23, UTC). M30 derived
  deterministically from M15 (no native local M30).
- **harness:** `replay_v1_funnel.py` (imports the frozen modules; no production
  runner executed).

### Attestation — prohibitions honoured

- **No MT5:** MetaTrader5 was never imported or initialized; no terminal, no broker, no API, no network, no calendar/news/external source was contacted.
- **No orders:** no order or position was created, modified, cancelled, closed or inspected; the harness never calls `order_send` or any trading call.
- **No production change:** no production script, `config.yaml`, state file or journal was created/modified/deleted; the only in-memory patch is an exact memoization of `levels.build_active_levels` (verified identical results).
- **No performance analysis:** no PnL, returns, Sharpe, drawdown, profit factor, win rate, equity curve, spread, slippage or cost statistic was computed. `ENTRY_INTENT` means the engine returned `action == "ENTRY"`; nothing was submitted.
- **No future data:** per-bar assertions enforce that only bars closed by the decision instant `t = T + 16 min` are visible; fractal confirmation is delayed to closed bars.
- **No parameter changes:** the frozen config was used as-is; the A/B-only pass only toggles `breakout.enabled` in memory to isolate Claim C.

### Artifacts created (this experiment folder only)

`README.md`, `DATA_MANIFEST.yaml`, `REPLAY_CAUSALITY_AUDIT.md`,
`FUNNEL_RESULTS.csv`, `REJECTION_TAXONOMY.csv`, `MONTHLY_FUNNEL.csv`,
`DETERMINISM_CHECK.md`, `V1_FREQUENCY_DECISION.md`,
`RESEARCH_VARIANT_REGISTER.md`, `RUN_LOG.md`, `replay_v1_funnel.py`.

### Result

- **funnel result:** see `FUNNEL_RESULTS.csv` and `V1_FREQUENCY_DECISION.md`.
- **determinism:** see `DETERMINISM_CHECK.md`.
- **formal decision:** `REJECT_XAUUSD_V1_UNDERFREQUENT` (see `V1_FREQUENCY_DECISION.md`).
- **production impact:** none. V1 remains frozen and unchanged.
