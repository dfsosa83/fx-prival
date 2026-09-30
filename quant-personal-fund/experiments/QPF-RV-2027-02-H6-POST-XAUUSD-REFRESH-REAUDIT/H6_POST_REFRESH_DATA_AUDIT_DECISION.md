# H6 — Post-Refresh Data Audit Decision

**Stage:** `H6_POST_XAUUSD_REFRESH_DATA_REAUDIT`
**Parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Date:** 2026-09-30

```text
decision: H6_ALL_INSTRUMENTS_DATA_READY
```

---

- All **seven** H6 instruments are `H6_DATA_ELIGIBLE`: `EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD,
  NZDUSD`, plus the separate `XAUUSD`.
- XAUUSD-specific assertion **PASS** (canonical schema, 45,809 rows, `2019-01-02 01:00:00` →
  `2026-09-30 14:00:00`).
- This determination is **availability/integrity only** — **not** an H6 result.
- **FX and XAUUSD will stay separate snapshots and separate statistical strata.**
- **No snapshot exists yet.**
- **No H6 screen is authorized.**
- **No instrument was selected based on performance.**
- H6 primary family remains `7 instruments × 3 N × 3 M × 3 H × 2 event classes = 378 tests`.

## Next permitted action (requires separate authorization)

A separate authorization may freeze immutable **single-instrument** H1 snapshots for H6 instruments;
XAUUSD remains a separate stratum from FX. No H6 event screen, PnL, cost, backtest, or trading activity
is authorized by this re-audit.
