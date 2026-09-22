# RUN_LOG — EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN

One dated entry per run. Sealed test scored ONCE; re-run with changed assumptions
= new ID (EXP-2026-09b) + supersede note.

| Date (UTC) | Action | Verification | Result | Notes |
|---|---|---|---|---|
| 2026-09-21 | Manifest pre-registered | Issue A: geometry marked TBD->frozen by sweep | — | builds on EXP-2026-08 (roc_auc 0.66 = skill; precision bottleneck) |
| 2026-09-21 | Geometry pre-analysis (NO training) | 12-cell TP/SL sweep on train window, cost-adjusted | FROZEN TP2.0/SL1.0 | only cell with usable label rate (15.6%) AND breakeven 34.6% (<0.35) |
| 2026-09-21 | Fork built (crosses/us30_sell_costlabel_geom.ipynb) | 45 cells, PAIR=US30, ATR_TP_MULT=2.0, ATR_SL_MULT=1.0, cost-aware label, 0 syntax errors | OK | auditor-reviewed: EXP-2026-08 fork NOT clobbered (distinct _geom name) |
| 2026-09-21 | Smoke test | cost-adj ≤ baseline EVERY year; splits 29,540/2,981/4,254 | PASS | cost impact only −0.5 pts (vs −0.8 at TP1.5) |
| 2026-09-22 | **US30 SELL TP2.0/SL1.0 sealed-test scoring** | 32 code cells, 0 errors; report cell == metrics JSON; bundle ATR mults verified | **STOP** | decisive — hypothesis FALSIFIED |

## Sealed-test metrics (2026-09-22, cost_pips=320, TP2.0/SL1.0, R:R 2.0)

| Metric | Value | vs TP1.5 run (EXP-2026-08) | Gate |
|---|---|---|---|
| n_signals | 1,241 | (1,576) | ≥30 ✓ |
| precision | **0.268** | (0.329) — **WORSE** | vs 0.346 breakeven ✗ |
| recall | 0.466 | (0.541) | — |
| **roc_auc** | **0.687** | (0.660) — **BETTER** | real skill, confirmed again |
| ev_per_r | **−0.197** | (−0.178) | needs >0 ✗ |
| ev_ci_95 | **[−0.292, −0.093]** | wholly below zero → **STOP** |
| breakeven | 0.333 = 1/(2+1) | pre-registered cost-adj 0.346 | precision 0.268 < 0.346 |

## Verdict — STOP (P1 gate, pre-registered 0.346 breakeven)

- GO denied (`ev = -0.197`).
- STOP confirmed: `ev <= -0.05` AND `ci_hi = -0.093 < 0`.
- **The geometry-redesign hypothesis is FALSIFIED, and the data are informative:**
  - roc_auc went **UP** (0.660 → 0.687): the wider target makes the model's
    ranking skill *more* visible, not less.
  - Yet precision went **DOWN** (0.329 → 0.268): the model cannot convert skill
    into precision at this label, no matter the barrier width.
  - The −7pt breakeven relaxation (0.415→0.346) was more than eaten by the
    precision drop. The skill exists; the *same* bottleneck persists.

## Programme-level conclusion (recorded 2026-09-22)

SIX experiments, ZERO GO, where the one positive finding (US30 skill) has now
been isolated to the label family itself, NOT to friction (highest skill on
lowest-friction instrument) and NOT to geometry (skill↑, precision↓ with wider
target). The directional H1 triple-barrier ML program on this stack has exhausted
its falsifiable variants. Per roadmap P2 gate ("only if P0/P1 shows signal"),
the evidence-based decision is to **close the directional-ML program** and move
research effort to the gold engine (the only asset with real recorded PnL) or a
structurally different signal family. This is a decision point, documented for
the operator.

## Geometry pre-analysis (frozen 2026-09-21, full sweep in reports/geometry_sweep.csv)

| TP | SL | label rate | cost-adj breakeven | usable? |
|---|---|---|---|---|
| 2.0 | 1.0 | 15.6% | **34.6%** | YES ← FROZEN |
| 1.5 | 1.0 | 22.6% | 41.5% | YES (the geometry that just scored STOP) |
| 1.5 | 0.75 | 19.6% | 35.5% | YES |
| 2.0 | 1.25 | 17.3% | 39.4% | YES |
| 2.5+/3.0 | any | <12% | — | no (label too rare) |

Rationale: the failed EXP-2026-08 model needed 41.5% precision; NONE of the
TP≥2.0 usable cells drop breakeven below 34.6%. TP2.0/SL1.0 (R:R 2.0) is the
only geometry that simultaneously (a) keeps a usable label rate and (b) relaxes
the precision bar by the largest margin (−7 pts).