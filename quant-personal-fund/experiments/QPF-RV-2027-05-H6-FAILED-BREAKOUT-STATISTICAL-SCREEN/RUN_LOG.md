# Run Log — QPF-RV-2027-05-H6-FAILED-BREAKOUT-STATISTICAL-SCREEN

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — H6_FAILED_BREAKOUT_STATISTICAL_SCREEN

- **date:** 2026-09-30
- **stage:** `H6_FAILED_BREAKOUT_STATISTICAL_SCREEN`
- **status:** `preregistered`
- **inputs:** the seven frozen single-instrument snapshots named in
  `QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE/data_manifest_h6.yaml`; each SHA256 verified
  before parsing; all seven integrity OK.
- **splits:** per-instrument 60/20/20 with 30-bar embargoes.
- **FX family:** intended 324, actual 324; numeric p-values 324; not-testable 0; survivors 0; selected 0.
- **XAUUSD family:** 54; numeric p-values 54; not-testable 0; survivors 0; selected 0.
- **BH:** FDR q=0.10 applied **separately** per stratum (FX 324; XAUUSD 54); never combined.
- **sealed:** not evaluated (no validation survivor in either stratum).
- **decisions:** `REJECT_H6_FX_STATISTICAL_VIABILITY`; `REJECT_H6_XAUUSD_STATISTICAL_VIABILITY`.
- **actions explicitly NOT performed:** no PnL/costs/backtest/strategy/signals/trading; no MT5/broker/
  credentials/network/calendar/news/external; no raw/prior-artifact modification; no retuning.
- **result:** frozen H6 failed-breakout formulation **REJECTED** in both strata.
- **next authorization consequence:**
  ```text
  The frozen H6 failed-breakout formulation is rejected. Any continuation
  requires a new, materially distinct hypothesis pre-registered under a new
  protocol; no retuning or revival of the rejected formulation is authorized,
  and no costs, PnL, backtest or trading work is authorized.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2027-05-H6-FAILED-BREAKOUT-STATISTICAL-SCREEN/h6_failed_breakout_statistical_screen.py`
  - `.../H6_FAILED_BREAKOUT_RESULTS.json`
  - `.../H6_FAILED_BREAKOUT_DECISION.md`
  - `.../RUN_LOG.md`
