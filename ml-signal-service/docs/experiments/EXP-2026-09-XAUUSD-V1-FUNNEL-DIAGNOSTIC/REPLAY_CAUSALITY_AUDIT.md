# REPLAY CAUSALITY AUDIT — EXP-2026-09

**Harness:** `replay_v1_funnel.py` (imports frozen `engine.py`, `bias.py`, `levels.py`).
**Rule enforced:** no information from `t+1` or later may influence the decision at `t`.

Decision instant for the M15 bar opening at `T` is `t = T + 16 minutes`
(identical to production `run_gold_rules.py`: `utc_now = last_time + timedelta(minutes=16)`).

## 1. Frozen source SHA-256

| file | SHA-256 |
|---|---|
| `frival/gold_rules/engine.py` | `9653ae906d30583493a49a478ca123b6a190ac16b93b3fd4f9a2ccdd4b2357e8` |
| `frival/gold_rules/bias.py` | `106999937cfc810c88e58dccf9476ec63ff998d2cdf08a4bfe43dcd259f8362f` |
| `frival/gold_rules/levels.py` | `63442ebbadaf059b816e49f9fdb28d71471ca4e7c5c98c8c3fe997674e0e49d5` |
| `frival/gold_rules/config.yaml` | `055430e4772d3c01d396fad386b78681cae3db7fa469bf638c6f835dbc92520a` |

Hashes are recomputed by the harness at run time and printed; they match the
manifest. No frozen file was modified.

## 2. Syntax / import verification

The harness runs end-to-end and imports the three frozen modules directly from
`frival/gold_rules` (added to `sys.path`). It never imports the production
runner, MetaTrader5, or any broker module. **PASS.**

## 3. Input schema validation

Required columns `datetime, open, high, low, close, volume` are built for M15,
M30 and H1 from local parquet (`time, open, high, low, close, tick_volume`).
Timestamps are unique and sorted. **PASS.**

## 4. Sorting, duplicate and gap report

| series | rows | dup timestamps | gaps > step | notes |
|---|---|---|---|---|
| M15 | 155,252 | 0 | 1,700 | 1,310 × 1-2h (daily maintenance halt), 43 × 2-24h, 333 × 1-3d, 14 × >3d |
| M30 (derived) | 77,608 | 0 | — | complete 30-min buckets only |
| H1 | 38,837 | 0 | 1,695 | weekends/holidays + halt |

Gaps are consistent with market closures (weekends, the ~1h daily halt,
holidays). No fill/repair/interpolation was applied. **PASS.**

## 5. Timestamp / timezone alignment

All series are interpreted in **UTC** (epoch seconds → tz-naive). Every cutoff
uses the same clock, so the causal ordering is internally consistent. Any
broker-server-vs-UTC offset is constant and therefore does not alter the
bar-sequence funnel; the offset itself is **not asserted** here. **PASS (with note).**

## 6. Causality audit

The harness raises `AssertionError` (aborting the run) if any of these fail,
for every evaluated bar:

- the last visible M15 bar is exactly the bar under evaluation `T` (closed);
- `max(M30 visible).open + 30m <= t` (no M30 lookahead);
- `max(H1 visible).open + 60m <= t` (no H1 lookahead);
- M15 window is the last `<= 460` bars ending at `T` (no future bars).

Fractal confirmation: M30 is truncated to bars **closed by `t`**, so a 5-bar
(w=2) pivot is only materialised once its two later M30 bars have closed — the
frozen `fractal_swings` sets `confirmed_time = pivot + wing` and can only reach
that index when those bars are present. No unclosed M30/M15 bar is ever exposed
to the engine.

State continuity: a single `EngineState` instance is carried across all M15
evaluations; there is no per-bar reset. **PASS.**

## 7. Determinism test

A contiguous 1,500-bar segment is replayed twice from the same initial state;
`(action, state_after, reason)` must match for every bar.
**Result: see `DETERMINISM_CHECK.md`.**

## 8. Production isolation attestation

- No production file, config, state file or journal was created, modified or deleted.
- No MetaTrader5 import/use; no broker/network/credentials.
- No order/position was created, modified, cancelled or closed.
- The only in-memory patch is an exact memoization of
  `levels.build_active_levels` (pure function); its results are identical
  (verified: identical funnel counts with and without the cache, and vs the
  production window cap of 1000). No frozen behaviour was altered.

## Causality verdict

`CAUSALITY_AND_DETERMINISM_VALID` (pending the determinism result in
`DETERMINISM_CHECK.md`; if that check fails the whole stage verdict becomes
`REJECT_XAUUSD_V1_REPLAY_INVALID`).
