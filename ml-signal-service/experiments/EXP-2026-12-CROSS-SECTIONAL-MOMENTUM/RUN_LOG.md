# RUN_LOG — EXP-2026-12-CROSS-SECTIONAL-MOMENTUM

One dated entry per run. The unseen evaluation window (2025→present) is scored
ONCE per grid. Material change after scoring = EXP-2026-12b + supersede note.

| Date (UTC) | Action | Verification | Result | Notes |
|---|---|---|---|---|
| 2026-09-22 | Manifest pre-registered (hypothesis + 2×3 grid + gate) | n/a — no run yet | — | Universe 10 instruments; costs from `_core/costs.py`; eval window 2025→present |
| 2026-09-22 | **Sealed evaluation window scored (2025-01-01 → 2026-07-30, 81 weekly rebalances)** | grid 3×2 (L ∈ {5,10,20} × k ∈ {2,3}); block-bootstrap CI, block=5 | **HOLD per gate** (no GO cell; not all STOP) — but see interpretation | Full results `reports/momentum_grid.csv` |

## Results (net-of-cost, per $1 notional, eval window 2025+)

| L | k | n | net | EV/week | win% | PF | CI | maxDD |
|---|---|---|---|---|---|---|---|---|
| 5 | 2 | 81 | −0.022 | −0.0003 | 55.6 | 0.87 | [−0.0015, +0.0008] | −4.4% |
| 5 | 3 | 81 | −0.036 | −0.0004 | 46.9 | 0.72 | [−0.0013, +0.0003] | −4.5% |
| 10 | 2 | 81 | −0.060 | −0.0007 | 50.6 | 0.69 | [−0.0022, +0.0005] | −9.0% |
| 10 | 3 | 81 | −0.049 | −0.0006 | 44.4 | 0.68 | [−0.0017, +0.0004] | −7.2% |
| 20 | 2 | 81 | −0.022 | −0.0003 | 48.1 | 0.86 | [−0.0016, +0.0010] | −5.5% |
| 20 | 3 | 81 | −0.032 | −0.0004 | 44.4 | 0.76 | [−0.0014, +0.0005] | −4.4% |

## Interpretation (HOLD on the letter, effective REJECT on substance)

- **No robustness band reaches zero** — the best cell has CI [-0.0016, +0.0010]:
  the estimate is consistent with EV ≈ 0.
- **Momentum itself is barely present gross-of-cost**: L=5/10 gross is negative;
  only L=20 gross is positive, and that is **2022-driven** (+0.068 of +0.081
  comes from 2022, a trending year). Costs then flip it negative in every cell.
- **Conclusion:** on the genuinely unseen window, cross-sectional momentum at a
  weekly horizon over this 10-instrument universe shows **no demonstrable edge
  after costs** — consistent with EV = 0 ± noise, not a usable signal. The
  hypothesis is **not supported**; the letter-of-the-gate HOLD is a reflection of
  the effect being ~zero rather than strongly negative. No further grid expansion
  is proposed under this ID (per the pre-registration non-goals).