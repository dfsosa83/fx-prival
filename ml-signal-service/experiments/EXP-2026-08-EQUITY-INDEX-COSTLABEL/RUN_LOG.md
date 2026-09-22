# RUN_LOG — EXP-2026-08-EQUITY-INDEX-COSTLABEL (US30, Dow Jones 30 CFD)

One dated entry per run. Sealed test scored ONCE; a material change after scoring
= new experiment ID (EXP-2026-08b) + supersede note.

| Date (UTC) | Action | Verification | Result | Notes |
|---|---|---|---|---|
| 2026-09-21 | Checklist issued + Q1/Q2/Q3 resolved (MT5 read-only) | NAS100 absent → US30 primary; swap answered; dividend adjudicated (0.05%/trade, non-blocking); session = 23h/day, quiet hour 00 UTC | AUTHENTICATED | broker_spec recorded |
| 2026-09-21 | US30 H1 data acquired (38,731 bars, 2020-02-28→2026-09-21) | schema ✓ dup=0 OHLC=0 null=0; median gap 1.0h (= daily quiet hour), 98h max = Christmas | OK | US30_H1.csv; friction 0.04R |
| 2026-09-21 | US30 SELL fork built (crosses/us30_sell_costlabel.ipynb) | 45 cells, PAY=US30, cost-aware label cell, 0 syntax errors | OK | |
| 2026-09-21 | US30 SELL smoke test | cost-adj ≤ baseline EVERY year; splits 29,540/2,981/4,254 | **PASS** | cost impact only −0.8 pts (vs −9.1 EURGBP) → label geometrically fair |
| 2026-09-21 | **US30 SELL sealed-test scoring** | execution OK, 31/32 code cells, 0 errors; report cell == metrics JSON | **STOP** | CI wholly below zero |
| 2026-09-21 | Label-semantics note | SELL NaN convention (same as FX forks); `realized_r` = +1.5/-1.0 on cost-adjusted label | recorded | consistent with EXP-2026-05/06 |

## Sealed-test metrics (2026-09-21, cost_pips = 320 (3.2 px), label = cost_adjusted_v1, US30 SELL)

| Metric | Value | Gate |
|---|---|---|
| n_signals | **1,576** | ≥ 30 ✓ |
| ev_per_r | **−0.178** | needs > 0 (GO) ✗ |
| ev_ci_95 | **[-0.261, -0.104]** | **entirely below zero** → STOP |
| precision | 0.329 | breakeven 0.40 — below |
| recall | 0.541 | threshold 0.28 captures ~54% of positive bars |
| roc_auc | **0.660** | real ordering skill (vs 0.504/0.629 FX runs) |
| block_length_used | 6 | = max(6, median gap) |

## Gate verdict — STOP (roadmap §9 P1, index-breakeven recomputed)

- GO denied: `ev_per_r = -0.178`.
- HOLD denied: CI upper bound `-0.104` < 0 — significant, not a data gap.
- **STOP**: the US30 SELL cost-adjusted model is significantly negative net of
  cost. KEY nuance: roc_auc 0.66 shows genuine **ranking skill** — the model
  discriminates US30 SELL trades — but precision 0.329 still undercuts the 0.40
  breakeven even though friction is only ~0.03R. The weakness is *feature/target
  link* (precision), not friction (unlike FX where cost dominated).

## Portfolio-level read (recorded 2026-09-21)

Five directional-ML experiments now resolved with the same label family:
EURUSD SELL=HOLD, EURUSD BUY=STOP, crosses=ABORT (arithmetic), US30 SELL=STOP.
Even on the clean-lab index where friction is ~30x lower than crosses, the
model cannot push precision above breakeven. Combined with roc_auc 0.66
(skill exists but doesn't convert to precision at 1.5R/1R), the evidence says:
the ATR-triple-barrier *label design*, not the cost environment, is the binding
constraint on this whole program. Next options: different label/target structure
or a fundamentally different signal. Recorded for roadmap §9 decision.

## Smoke result detail (2026-09-21, train window)

| Year | baseline % | cost-adj % |
|---|---|---|
| 2020 | 27.23 | 26.66 |
| 2021 | 25.65 | 24.59 |
| 2022 | 25.55 | 25.11 |
| 2023 | 22.85 | 21.74 |
| 2024 | 21.59 | 20.84 |
| 2025 | 24.71 | 24.26 |

Mean cost impact: **−0.79 pts** (EURGBP −9.1, EURUSD −1.7 for contrast).