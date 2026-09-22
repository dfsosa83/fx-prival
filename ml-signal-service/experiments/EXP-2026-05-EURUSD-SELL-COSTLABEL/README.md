# EXP-2026-05 — EURUSD SELL cost-adjusted label

**ID:** `EXP-2026-05-EURUSD-SELL-COSTLABEL`
**Manifest:** `experiment.yaml` (pre-registration, Issue A) — read it first.
**Run log:** `RUN_LOG.md` — one dated entry per run; sealed test scored once.

## Objective (roadmap §9 P0.1)

Retrain the production EURUSD SELL model on a **cost-adjusted label** (TP must
clear ATR barrier + round-trip friction, not just the ATR barrier) and test
whether it remains profitable on the sealed test window. The **only** code
difference from production is the TP barrier line in `generate_sell_labels`;
everything else is byte-identical (features, split, purged-embargo CV,
isotonic calibration, threshold rule).

## Reproduce (order matters)

```
# 0. P0.0 prerequisite (ran once; unit tests must pass)
cd ml-signal-service
python -m pytest experiments/_core/tests -q        # 29 passed

# 1. Build the fork (idempotent; refuses on any unexpected source change)
python experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/build_costlabel_notebook.py

# 2. Smoke test — label-layer validation on real data, NO training (fast)
python experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/smoke_cost_label.py
#    asserts cost-adjusted SELL rate <= baseline EVERY year (P0.1 check 1)

# 3. Full run — trains, scores sealed test once, writes reports/ (long)
python experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/run_exp.py
```

## Inputs / outputs

| | Path |
|---|---|
| Production notebook (read-only reference) | `notebooks/eurusd/eurusd_sell_improved.ipynb` |
| Raw data | `data/raw/mt5/H1/EURUSD_H1.csv` |
| Cost constants (single source of truth) | `experiments/_core/costs.py` |
| Fork (generated) | `notebooks/eurusd/eurusd_sell_costlabel.ipynb` |
| Executed copy (run output, for audit) | `notebooks/` under this folder |
| Trained bundle (NEVER overwrites production) | `models_bin/EURUSD_H1_sell_costlabel_<model>.joblib` |
| Sealed-test metrics + signal ledger | `reports/test_metrics.json` · `reports/test_signals.csv` |

## Decision gate (evaluated once — roadmap §9 P0.1)

- **GO** → open shadow-paper slot on account A2: `ev_per_r > 0` AND
  `ev_ci_95_lo > -0.05` AND `n_signals >= 30`.
- **HOLD** → document, wait for more test-window data.
- **STOP** → kill this label variant for EURUSD SELL:
  `ev_per_r <= -0.05` AND `ci_hi < 0`.

Any re-run with changed cost/threshold/features after seeing output = new
experiment ID (`EXP-2026-05b`) + RUN_LOG entry marking prior superseded.

## Non-goals

No ATR-multiplier retuning; no new features; no model-family change; no
GBPUSD/USDCHF/USDCAD or EURUSD BUY work; the sealed test is never re-scored
under this ID.