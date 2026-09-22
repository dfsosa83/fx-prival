# EXP-2026-06 — EURUSD BUY cost-adjusted label

**ID:** `EXP-2026-06-EURUSD-BUY-COSTLABEL`
**Manifest:** `experiment.yaml` (pre-registration, Issue A) — read it first.
**Run log:** `RUN_LOG.md` — one dated entry per run; sealed test scored once.

## Objective (roadmap §9 P1)

Mirror of `EXP-2026-05` on the **BUY** side: retrain the production EURUSD BUY
model on a cost-adjusted label (TP must clear ATR barrier + round-trip
friction) and test profitability on the sealed test window. The **only** code
difference from production is the TP barrier line in `generate_buy_labels`;
features, split, purged-embargo CV, isotonic calibration, threshold rule, and
the BUY NaN-ambiguity label semantics are byte-identical.

## Reproduce (order matters)

```
# 0. prerequisites (P0.0, already green)
python -m pytest experiments/_core/tests -q                # 29 passed

# 1. Build the fork (shared direction-parameterized builder)
python experiments/_core/build_costlabel_fork.py BUY EXP-2026-06-EURUSD-BUY-COSTLABEL

# 2. Smoke test — label-layer validation on real data, NO training
python experiments/EXP-2026-06-EURUSD-BUY-COSTLABEL/smoke_cost_label.py
#    asserts cost-adjusted BUY rate <= baseline EVERY year (P1 check 1)

# 3. Full run — trains, scores sealed test once, writes reports/ (long)
python experiments/EXP-2026-06-EURUSD-BUY-COSTLABEL/run_exp.py
```

## Inputs / outputs

| | Path |
|---|---|
| Production notebook (read-only reference) | `notebooks/eurusd/eurusd_buy_improved.ipynb` |
| Raw data | `data/raw/mt5/H1/EURUSD_H1.csv` |
| Cost constants (single source of truth) | `experiments/_core/costs.py` |
| Fork (generated) | `notebooks/eurusd/eurusd_buy_costlabel.ipynb` |
| Executed copy (run output, for audit) | `notebooks/` under this folder |
| Trained bundle (NEVER overwrites production) | `models_bin/EURUSD_H1_buy_costlabel_<model>.joblib` |
| Sealed-test metrics + signal ledger | `reports/test_metrics.json` · `reports/test_signals.csv` |

## Decision gate (evaluated once — roadmap §9 P1)

- **GO** → proceed to shadow/paper: `ev_per_r > 0` AND `ev_ci_95_lo > -0.05`
  AND `n_signals >= 30`.
- **HOLD** → document, wait for more test-window data.
- **STOP** → kill this label variant for EURUSD BUY:
  `ev_per_r <= -0.05` AND `ci_hi < 0`.

Any re-run with changed cost/threshold/features after seeing output = new
experiment ID (`EXP-2026-06b`) + RUN_LOG entry marking prior superseded.

## Non-goals

No ATR-multiplier retuning; no new features; no model-family change; no
SELL/cross work in this experiment; the sealed test is never re-scored under
this ID.