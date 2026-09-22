# RUN_LOG — EXP-2026-05-EURUSD-SELL-COSTLABEL

One dated entry per run. The sealed test window is scored **once** per entry.
Any material change (cost constant, threshold, feature set, label logic) after
a scored run = NEW experiment ID (EXP-2026-05b) + entry marking prior superseded.

| Date (UTC) | Action | Verification | Result | Notes |
|---|---|---|---|---|
| 2026-09-21 | Manifest written (pre-registration) | n/a — no run yet | — | Cost source frozen: `experiments/_core/costs.py` |
| 2026-09-21 | Notebook fork built + smoke test | cost-adj SELL rate ≤ baseline every year; splits populated | PASS | smoke_cost_label.py, P0.1 check 1 |
| 2026-09-21 | **Scaled test scored (once)** | execution OK, 43/43 cells, no cell errors | **HOLD** | See metrics below. CI straddles zero widely → do not proceed, do not kill, wait for more test-window data. |

## Sealed-test metrics (2026-09-21, cost_pips = 1.2, label = cost_adjusted_v1)

| Metric | Value | Gate |
|---|---|---|
| n_signals | **62** | ≥ 30 ✓ |
| ev_per_r | **-0.032** | needs > 0 (GO) ✗ |
| ev_ci_95 | **[-0.516, +0.452]** | straddles zero beyond ±0.05R → **HOLD** |
| precision | 0.3871 | breakeven 0.40 — just under |
| recall | 0.0226 | — |
| roc_auc | 0.629 | — |
| block_length_used | 8 | = max(6, median gap ~8h) |
| model bundle | `models_bin/EURUSD_H1_sell_costlabel_Ensemble.joblib` | production bundles untouched |

## Gate verdict — HOLD (roadmap §9 P0.1)

- GO denied: `ev_per_r = -0.032` is not > 0.
- STOP denied: ci_hi (+0.452) is not below zero, so the negative point estimate is **not significant**.
- **HOLD**: point estimate is slightly negative and precision (0.387) just misses breakeven (0.40), but the block-bootstrap CI is extremely wide ([-0.516, +0.452]) — 62 sealed-test signals cannot distinguish a real negative edge from noise. Do NOT proceed to A2 shadow; do NOT kill the label variant; accumulate more test-window data and re-score only under a new experiment ID (`EXP-2026-05b`) per the Issue A rule.