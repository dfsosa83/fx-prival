# EXP-2026-07 — Liquid-cross book, cost-adjusted labels

**ID:** `EXP-2026-07-CROSSES-COSTLABEL`
**Manifest:** `experiment.yaml` (pre-registration, Issue A) — read it first.
**Run log:** `RUN_LOG.md` — one dated entry per run per pair-direction.

## Objective (roadmap §9 P1)

EURUSD BUY/SELL both failed (STOP / HOLD) under a USD-dominated regime. This
experiment tests the same cost-adjusted-label methodology on **three pairs that
do not quote the USD**: EURGBP, GBPJPY, EURJPY. Diversification first, edge
second — each pair is scored independently with the same pre-registered gate.

## Current state (2026-09-21)

- [x] **Data acquired** (MT5 H1, ~48k bars each, validated)
- [x] **Cost table extended** — pip conventions + live-measured spreads in
  `experiments/_core/costs.py` (EURGBP 4.7, GBPJPY 13.6, EURJPY 10.6 pips)
- [ ] Forks per pair (SELL then BUY) — next
- [ ] Smoke tests per pair (cost-adj label rate ≤ baseline every year)
- [ ] Sealed-test scoring per pair-direction, gate applied per pair

## Reproduce

```
# 0. P0.0 infrastructure (already green)
python -m pytest experiments/_core/tests -q            # 30 passed

# 1. (done) data — re-run to refresh if needed:
python steps/01_download/mt5_downloader.py --pair EURGBP --tf H1   # + GBPJPY, EURJPY

# 2. per pair: build fork → smoke → score (build scripts under _core/)
```

## Data validation summary (2026-09-21)

| Pair | Bars | Range | Dups | OHLC viol | Nulls | Gaps |
|---|---|---|---|---|---|---|
| EURGBP | 48,020 | 2019-01-02→2026-09-21 | 0 | 0 | 0 | weekend/holiday only |
| GBPJPY | 48,021 | 2019-01-02→2026-09-21 | 0 | 0 | 0 | weekend/holiday only |
| EURJPY | 48,021 | 2019-01-02→2026-09-21 | 0 | 0 | 0 | weekend/holiday only |

## Cost model (measure-first, locked)

Cross spreads are wider than majors (JPY crosses genuinely run 10–14 pips on
3-decimal quotes). Slippage remains 0.0 until §6.1 measurements exist. Per-pair
cost constants live in ONE place (`_core/costs.py`) — no notebook carries its own.

## Decision gate (per pair-direction)

- **GO** → `ev_per_r > 0` AND `ev_ci_95_lo > -0.05` AND `n_signals ≥ 30`
- **HOLD** → CI straddles zero beyond ±0.05R, or n_signals < 30
- **STOP** → `ev_per_r ≤ -0.05` AND `ci_hi < 0`

Do not start the BUY direction of a pair before its SELL gate has produced a
verdict (Issue A — no simultaneous two-direction multiple testing).