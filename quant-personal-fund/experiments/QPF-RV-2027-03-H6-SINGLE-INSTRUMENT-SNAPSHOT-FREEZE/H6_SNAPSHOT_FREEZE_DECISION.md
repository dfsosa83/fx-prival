# H6 — Single-Instrument Snapshot Freeze Decision

**Stage:** `H6_SINGLE_INSTRUMENT_IMMUTABLE_SNAPSHOT_FREEZE`
**Experiment:** `QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE`
**Date:** 2026-09-30

```text
decision: H6_SNAPSHOTS_FROZEN_PENDING_SEPARATE_H6_SCREEN
```

---

- Seven **single-instrument**, close-only, hash-locked H1 snapshots were frozen (one per H6
  instrument) under `snapshots/<SYMBOL>/`, each excluding exactly its maximum available label.
- **FX and XAUUSD remain separate snapshots and separate statistical strata.**
- **No H6 statistical screen was run.**
- **No H6 events were calculated.**
- **No costs, PnL, backtest, strategy, signal, execution, or trading work was performed.**
- **No instrument is selected or approved based on performance** — this is data preparation only.
- The H6 primary family remains `7 instruments × 3 N × 3 M × 3 H × 2 event classes = 378 tests`.

## Next permitted action (requires separate authorization)

A separate authorization may run **one** H6 failed-breakout statistical screen, **per instrument**,
reading only the corresponding hash-verified snapshot (comment line skipped) under the unchanged H6
protocol — with XAUUSD evaluated as its own separate stratum and never pooled with FX. No cost, PnL,
backtest, or trading work is authorized by this freeze.

## Governance note

The frozen continuity rule named this a one-instrument-per-stage action; at the owner's explicit
direction, all seven instruments were frozen in this single stage (each still a separate
single-instrument snapshot). This override is recorded here and in the run log.
