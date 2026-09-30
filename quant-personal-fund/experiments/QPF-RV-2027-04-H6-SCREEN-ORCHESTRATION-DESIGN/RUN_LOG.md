# Run Log — QPF-RV-2027-04-H6-SCREEN-ORCHESTRATION-DESIGN

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — H6_SCREEN_ORCHESTRATION_DESIGN

- **date:** 2026-09-30
- **stage:** `H6_SCREEN_ORCHESTRATION_DESIGN`
- **status:** `preregistered`
- **scope:** design only — orchestration specification, output schema, pseudocode, decision matrix.
- **snapshot binding requirement:** a future screen must read only the seven snapshot paths and exact
  hashes recorded in `QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE/data_manifest_h6.yaml`,
  verify each SHA256 before `pandas.read_csv`, load with `comment="#"`, validate each single-instrument
  schema (`internal_index_k, timestamp_label_internal, <instrument>_close`), and never align/join/pool
  instruments.
- **separate FX/XAUUSD families:** FX = `EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`; XAUUSD =
  `XAUUSD` only; **never pooled or jointly BH-corrected**.
- **fixed H6 grid:** `N ∈ {12,24,48}`, `M ∈ {2,4,8}`, `H ∈ {4,8,24}`, classes
  `FAILED_UPWARD_BREAKOUT` / `FAILED_DOWNWARD_BREAKOUT` (54 tests per instrument).
- **validation/BH/sealed flow:** validation-only selection; **FX BH family = 324**, **XAUUSD BH family
  = 54** (BH FDR q=0.10, separate); at most three selected configurations per stratum; sealed
  confirmation once for selected configurations only; per-configuration and per-stratum decisions
  (FX and XAUUSD independent).
- **actions explicitly NOT performed:** no snapshot/raw/market-data access, parse, hash, or computation;
  no events/outcomes/returns/HAC/BH/statistics; no costs/PnL/backtest/ML/signals/trading; no MT5/broker/
  credentials/network/calendar/external; no modification outside this design folder; no H6 screen run.
- **continuity:** research-control files were **not** modified (H6 remains unexecuted; global next action
  unchanged).
- **authorization consequence (next):**
  ```text
  A separate authorization may execute one H6 screen using only the seven
  hash-verified frozen snapshots and the frozen H6 protocol plus this
  orchestration design. FX and XAUUSD must remain separate strata. No costs,
  PnL, backtest or trading work is authorized.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2027-04-H6-SCREEN-ORCHESTRATION-DESIGN/H6_SCREEN_ORCHESTRATION.md`
  - `.../H6_SCREEN_OUTPUT_SCHEMA.md`
  - `.../H6_SCREEN_PSEUDOCODE.py`
  - `.../H6_SCREEN_DECISION_MATRIX.md`
  - `.../RUN_LOG.md`
