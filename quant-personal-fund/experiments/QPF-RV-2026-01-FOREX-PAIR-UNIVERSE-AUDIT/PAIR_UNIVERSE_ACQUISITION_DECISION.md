# Pair-Universe Acquisition Decision

**Stage:** `PAIR_UNIVERSE_DATA_AVAILABILITY_AUDIT`
**Date:** 2026-09-29

## Decision

```text
AUDIT_COMPLETE_PRIMARY_PAIR_READY
```

The primary candidate (C1: **AUDUSD / NZDUSD**) has **both sources valid** and **48,030 common H1
labels** (≥ 30,000) before any future maximum-common-label exclusion, so it is
`ELIGIBLE_FOR_FUTURE_G3_FREEZE`.

## Required statements

- This is **not** a statistical approval of any pair. No statistical test was run, and no market
  statistic of any kind was computed.
- **No candidate was selected based on performance.**
- **No PnL, cost, execution, or tradability conclusion exists.**
- All five pre-specified candidates have valid sources with ≥ 30,000 common H1 labels (see the
  audit matrix); eligibility here means only "data is adequate for a future freeze", not viability.

## Next permitted action

If the primary pair is ready (it is): a **separately authorized immutable-snapshot freeze for
AUDUSD/NZDUSD**, followed by **exactly one pre-registered G3-style statistical screening** — nothing
in this stage authorizes that screening itself.

If the primary pair had been blocked, the next step would have been to report the **first secondary
candidate in the fixed order** that is data-eligible (C2 → C3 → C4 → C5), without running its
statistical test. That step was not required.

## Scope confirmation

No statistical tests, cost/PnL analysis, returns, signals, ML, backtests, or trade/execution activity
occurred. Data acquisition was limited to the two missing H1 files via the repository's existing
downloader; no existing file was altered.
