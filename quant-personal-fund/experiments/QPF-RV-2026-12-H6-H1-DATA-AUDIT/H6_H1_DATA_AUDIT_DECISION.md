# H6 — H1 Data Audit Decision

**Stage:** `H6_H1_DATA_AVAILABILITY_AUDIT`
**Parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Date:** 2026-09-30

```text
decision: H6_FX_READY_XAUUSD_BLOCKED
```

---

## Basis

- All **six FX instruments** (`EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`) are
  `H6_DATA_ELIGIBLE`.
- **XAUUSD is not eligible** — `H6_DATA_STALE` (final label `2026-08-17 16:00:00` < `2026-09-24 18:00:00`).
  XAUUSD remains a **separate stratum**, blocked and separate from FX.

## Statements

- This is an **availability/quality** determination only — **not** an H6 result.
- **No instrument is selected based on performance.**
- **No snapshot has been created.**
- **No H6 statistical screen is authorized yet.**
- FX snapshots may be authorized **separately** (independently of XAUUSD) in a later stage; XAUUSD must
  first be repaired/refreshed under its own separate authorization (e.g. a canonical-schema history
  refresh) before it can be snapshotted.

## Next permitted action (requires separate authorization)

A separate authorization may freeze immutable single-instrument H1 snapshots for the six eligible FX
instruments (kept as separate strata) and, if desired, a separate XAUUSD refresh stage; then exactly
one pre-registered H6 statistical screen may be run under the unchanged H6 protocol. No H6 screen,
cost, PnL, backtest, or trading work is authorized by this stage.
