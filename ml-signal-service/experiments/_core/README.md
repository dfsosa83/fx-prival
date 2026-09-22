# `experiments/_core` — shared methodology (P0.0)

Single source of truth for the two roadmap corrections that every experiment
consumes (ROADMAP-2026-Q4-RESEARCH.md §2 Issues B & C, §9 P0.0).

## Modules

| Module | Purpose | Key API |
|---|---|---|
| `costs.py` | Per-pair round-trip friction (Issue C) | `cost_pips(pair, session)` · `to_price(pair, pips)` · `apply_cost_to_barrier(entry, atr, mult, direction, cost_pips, pair=...)` · `set_slippage_pips(pair, pips)` |
| `bootstrap.py` | Overlap-aware EV/R CI (Issue B) | `block_bootstrap_ci(returns, block_length, ...) -> (point, lo, hi)` · `default_block_length(forward_bars, median_gap_bars)` · `point_evr(returns)` |

## Rules

- **No experiment owns a copy** of these constants/functions. Import from
  `experiments._core`.
- **Cost table**: `MEASURED_SPREAD_PIPS` is the live 2026-09-18 measurement
  (spread only). Slippage is 0.0 until measured from real paper fills
  (`set_slippage_pips`), and session multipliers are flat 1.0 until measured.
  Changing a constant = a new cost-model variant = a new experiment log entry
  (roadmap Issue A rule).
- **CI**: report `block_bootstrap_ci`, never `iid_bootstrap_ci` (kept only as
  the test/measurement baseline).

## Tests

Run from the `ml-signal-service/` directory (so `experiments` is importable):

```
python -m pytest experiments/_core/tests -v
```

Required: `numpy`, `pytest` (`requirements.txt` — **test** section).

## Roadmap P0.0 acceptance (checked by these tests)

1. Cost sign: BUY/SELL cost always makes the barrier harder to reach, never
   easier (`test_costs.py`).
2. Block bootstrap with `block_length=1` equals the IID bootstrap on the same
   RNG stream (`test_bootstrap.py`).
3. On positively autocorrelated AR(1) data, the block bootstrap CI is wider
   than the naive IID CI — the correction demonstrably does something.