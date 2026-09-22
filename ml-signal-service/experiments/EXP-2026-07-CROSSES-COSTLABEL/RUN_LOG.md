# RUN_LOG — EXP-2026-07-CROSSES-COSTLABEL

One dated entry per run per pair-direction. Each sealed test scored ONCE.
Material change after a scored run = NEW experiment ID (EXP-2026-07b) + supersede note.

| Date (UTC) | Pair/Dir | Action | Verification | Result | Notes |
|---|---|---|---|---|---|
| 2026-09-21 | — | Manifest written (pre-registration) | n/a — no run yet | — | Cost source frozen: `experiments/_core/costs.py` (spreads measured live 2026-09-21) |
| 2026-09-21 | EURGBP H1 | Data acquired (mt5_downloader, 48,020 bars) | schema ✓ OHLC ✓ dup=0 null=0 gaps=weekend-only | OK | EURGBP_H1.csv |
| 2026-09-21 | GBPJPY H1 | Data acquired (mt5_downloader, 48,021 bars) | schema ✓ OHLC ✓ dup=0 null=0 gaps=weekend-only | OK | GBPJPY_H1.csv |
| 2026-09-21 | EURJPY H1 | Data acquired (mt5_downloader, 48,021 bars) | schema ✓ OHLC ✓ dup=0 null=0 gaps=weekend-only | OK | EURJPY_H1.csv |
| 2026-09-21 | all | Downloader hardening: retry on empty first copy_rates_range + unbuffered | EURGBP reprduce on direct call, GBPJPY/EURJPY OK | OK | terminal state after connect can return empty once; retry resolves |
| 2026-09-21 | EURGBP SELL | Fork built (crosses/eurgbp_sell_costlabel.ipynb) + smoke | cost-adj ≤ baseline every year; splits 31,128/3,144/4,479 | PASS | fork is a faithful artifact — but see economic finding below |
| 2026-09-21 | all/SELL | **EXP-2026-07 ABORTED — no scoring run** | economic finding below | CANCELLED | operator decision 2026-09-21 |

## Economic finding — why EXP-2026-07 was aborted before scoring (2026-09-21)

Cross round-trip spread consumes **over half a risk unit**:

| Pair | median ATR (pips) | cost (pips) | cost per 1R | net win (TP=1.5R) | net loss (SL=1R) | **breakeven precision needed** |
|---|---|---|---|---|---|---|
| EURGBP | 8.5 | 4.7 | **0.56R** | +0.94R | −1.56R | **62.2%** |
| GBPJPY | 25.7 | 13.6 | **0.53R** | +0.97R | −1.53R | **61.2%** |
| EURJPY | 19.0 | 10.6 | **0.56R** | +0.94R | −1.56R | **62.4%** |
| EURUSD (ref) | 12.3 | 1.2 | 0.10R | +1.40R | −1.10R | 43.9% |

To be profitable net of cost at the 1.5R-target geometry, the models must clear
**~62% precision** — vs 40% raw breakeven, vs 44% EURUSD, vs the 35–39% these
models actually achieve. **Widening TP does not fix it**: on EURGBP, cost-adjusted
SELL rate falls 19.7% (TP1.5) → 7.5% (TP3.0), crashing below the 15% usability
floor beyond TP=2.

**Conclusion:** the ATR-triple-barrier cost-adjusted label family is structurally
unviable on high-spread crosses; the three precious sealed-test scorings were
NOT spent. Research priority shifts to the equity-index pilot (EXP-2026-08) per
roadmap §4.2/§9. The data, forks, and handicap table remain permanent inputs.

## What remains useful (not wasted)

- Three validated cross datasets (`data/raw/mt5/H1/EURGBP|GBPJPY|EURJPY_H1.csv`)
- Cost table with live cross spreads (30/30 tests green)
- Parameterized fork builder (`--pair`) + cross smoke pattern
- The handicap table above (evidence base for any future redesign decision)