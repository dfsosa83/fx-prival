# RUN_LOG — EXP-2026-06-EURUSD-BUY-COSTLABEL

One dated entry per run. The sealed test window is scored **once** per entry.
Any material change (cost constant, threshold, feature set, label logic) after
a scored run = NEW experiment ID (EXP-2026-06b) + entry marking prior superseded.

| Date (UTC) | Action | Verification | Result | Notes |
|---|---|---|---|---|
| 2026-09-21 | Manifest written (pre-registration) | n/a — no run yet | — | Cost source frozen: `experiments/_core/costs.py`; SELL verdict (EXP-2026-05) was HOLD at gate time |
| 2026-09-21 | Attempt 1 (15:47Z→~15:35Z env reboot) | **machine rebooted**, zero artifacts written | ABORTED (environment) | Root cause: OS reboot at ~15:35Z killed the kernel mid-training. Sealed test NEVER scored — no violation of the once-only rule. |
| 2026-09-21 | Attempt 2 (15:47Z relaunch → ~17:55Z) | executed notebook: cells 1–36 OK, **died mid cell-36 XGBoost fold** | ABORTED (OOM) | Root cause: `n_jobs=-1` (8 logical/4 physical cores) + ~2.1 GiB free RAM after reboot → kernel OOM-killed. No python error; cell 41 (predict_proba/test) never ran → sealed test still unscored. Runner hardened: `LOKY_MAX_CPU_COUNT=4`, `OMP_NUM_THREADS=2`, per-cell timeout 7200s. |
| 2026-09-21 | Attempt 3 (headless, 18:10Z → 20:00Z) | kernel reached final cell; **fork executed directly in VS Code Jupyter at ~20:00Z by operator** produced `reports/test_metrics.json` + bundle | **STOP** | Sealed-test scored once per Issue A (see metrics below). |
| 2026-09-21 | **Sealed test scored (once)** — operator Jupyter run | fork report cell output == `test_metrics.json` (byte-identical) | **STOP** | BUY cost-adjusted label is significantly negative net of cost. CI wholly below zero. |

## Sealed-test metrics (2026-09-21, cost_pips = 1.2, label = cost_adjusted_v1, BUY)

| Metric | Value | Gate |
|---|---|---|
| n_signals | **2003** | ≥ 30 ✓ |
| ev_per_r | **-0.111** | needs > 0 (GO) ✗ |
| ev_ci_95 | **[-0.197, -0.021]** | **entirely below zero** → STOP |
| precision | 0.3555 | breakeven 0.40 — below |
| recall | 1.000 | threshold 0.313 fires on ~65% of test bars — no discrimination |
| roc_auc | 0.5043 | ≈ coin flip — no ordering skill |
| block_length_used | 6 | = max(6, median gap) |

## Gate verdict — STOP (roadmap §9 P1)

- GO denied: `ev_per_r = -0.111` is not > 0.
- HOLD denied: the block-bootstrap CI **does not straddle zero** — its upper bound is `-0.021`, below zero.
- **STOP**: the EURUSD BUY cost-adjusted label is significantly negative net of cost (CI [-0.197, -0.021] rejects EV/R ≥ 0 at 95%). This is a *decision*, not a data gap: with 2,003 signals and roc_auc ≈ 0.50, the model has no discriminative edge, and after friction its realized R is materially negative. Kill this label variant for EURUSD BUY; do NOT proceed to any paper/live use.

## Manifest correction (2026-09-21, post-score audit)

The experiment.yaml + smoke test originally documented the **SELL** split windows
(test from 2026-01-01). The **BUY** production notebook (`eurusd_buy_improved.ipynb`)
uses a DIFFERENT split (train→2025-10-31, val 2025-11-01→2026-03-31,
**test from 2026-04-01**) — the fork inherits the BUY notebook's own dates. Manifest
and smoke test corrected to the actual BUY windows; smoke re-run green
(cost-adj rate ≤ baseline every year under the true split). The sealed-test
metrics were computed on the real BUY test window (2026-04-01+) regardless.

## Cross-experiment read (SELL + BUY)

Both directional ML experiments are now resolved: SELL = HOLD (insufficient evidence), BUY = STOP (significant negative). The friction-adjusted labels destroy the apparent edge in the near-real strategy — consistent with P0.2's finding that ~3-pip stops + 1.2-pip cost ≈ 0.4R/trade handicap. The research priority per roadmap §9 shifts toward the alternatives (cross-book diversification, equity-index pilot) or a fundamentally different label/stop structure — continuing to tune this label family is not supported by the evidence.