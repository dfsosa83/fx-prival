# H4-C2 — Snapshot Freeze Decision

**Experiment:** `QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP`
**Date:** 2026-09-29

```text
decision: SNAPSHOT_FROZEN_PENDING_H4_C2_SCREEN
```

---

- Only **one separately authorized H4-C2 statistical screen** may use this exact hash-verified
  snapshot (`eurusd_usdchf_h1_internal_snapshot_v1.csv`,
  `67590790F8BF0E20A707792D8DE85077C6D1067BD45035B05744D5D235E1DBF6`) with the comment line skipped.
- The screen must use the **parent H4 protocol unchanged** (C2 orientation `log(EURUSD)` on
  `log(USDCHF)`; \(W=\{1000,2000,5000\}\); \(E=1000\); 60/20/20 with 30-bar embargoes; frozen
  eligibility/selection/confirmation gates; internal ordinal clock `NOT_UTC`).
- **No cost/PnL/strategy/backtest/trading activity is authorized.**
- **All other candidates remain untested** (C3, C4, C5) and are not selected on performance.

## Declaration

No market statistic, economic result, or trading output was computed. This is not a claim that C2 is
statistically viable, profitable, or tradable.
