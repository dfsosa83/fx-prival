# EXP-2026-12 — Cross-sectional momentum (relative-strength persistence)

**Verdict (2026-09-22):** HOLD by the pre-registered gate — **not supported on
substance.** The first genuinely new mechanism tested after the directional-ML
and gold lines were closed.

## Hypothesis (in one line)

Ranking 10 instruments by trailing return and holding the top-k long / bottom-k
short on a weekly rebalance produces positively-expected, net-of-cost returns.

## Why it was worth testing

Every prior falsification predicted one instrument's next move from its own H1
prices. This predicts *relative* ranking at a weekly horizon — a different
mechanism, and friction-favourable (weekly moves vs 1–14 pip spreads).

## Result (unseen 2025+ window, 81 rebalances, $1 notional)

| L | k | net | EV/wk | win% | PF | maxDD |
|---|---|---|---|---|---|---|
| 5 | 2 | −0.022 | −0.0003 | 55.6 | 0.87 | −4.4% |
| 5 | 3 | −0.036 | −0.0004 | 46.9 | 0.72 | −4.5% |
| 10 | 2 | −0.060 | −0.0007 | 50.6 | 0.69 | −9.0% |
| 10 | 3 | −0.049 | −0.0006 | 44.4 | 0.68 | −7.2% |
| 20 | 2 | −0.022 | −0.0003 | 48.1 | 0.86 | −5.5% |
| 20 | 3 | −0.032 | −0.0004 | 44.4 | 0.76 | −4.4% |

- Best CI: [−0.0016, +0.0010] — EV is **consistent with zero**, not a usable edge.
- Gross-of-cost, only L=20 is positive, and **2022 alone provides +0.068 of
  +0.081** — regime-dependent, not robust. Costs then flip every cell negative.

## Gate

Per `experiment.yaml`: no GO (EV ≤ 0 everywhere), not all STOP (EVs are tiny,
CI straddles zero) ⇒ **HOLD**. Substantive read: the hypothesis is **not
supported** — the answer is "no demonstrable effect," consistent with EV ≈ 0.

## Notes
- Universe 10 instruments; USDX/WTI excluded (spreads unmeasurable at
  instrumentation — market closed; no cost guessing, per project rule).
- Costs: round-trip spread from `_core/costs.py`; swap diagnostic only; slippage
  unmeasured (bias *against* GO).
- No ML was applied — mechanical rank-then-hold only, per pre-registration.

## Run it
```
python experiments/EXP-2026-12-CROSS-SECTIONAL-MOMENTUM/build_matrix.py   # once
python experiments/EXP-2026-12-CROSS-SECTIONAL-MOMENTUM/run_momentum.py
```