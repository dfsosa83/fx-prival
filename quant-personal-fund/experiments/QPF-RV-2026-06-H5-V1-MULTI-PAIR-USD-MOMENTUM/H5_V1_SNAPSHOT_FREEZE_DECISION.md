# H5-v1 — Snapshot Freeze Decision

**Experiment:** `QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM`
**Date:** 2026-09-29

```text
decision: SNAPSHOT_FROZEN_PENDING_H5_V1_SCREEN
```

---

- Only **one separately authorized H5-v1 statistical screen** may use this exact verified snapshot
  (`h5_v1_multiseries_h1_internal_snapshot.csv`,
  `F0B6DBB5EFB67F74DD12C626B117124904E739C86F5DC29C41514EC2CB6E59C8`), reading it with the **comment
  line skipped**.
- It must use the **parent H5 protocol unchanged** (mandatory basket `EURUSD, GBPUSD, USDJPY, USDCHF,
  USDCAD`; targets `EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`; \(L=\{4,8,24,48\}\),
  \(H=\{4,8,24\}\), \(V=\{24,72\}\), \(K=\{3,4\}\); both directions; target-excluded primary /
  target-included secondary; validation-only selection; BH FDR \(q=0.10\); max three sealed
  configurations; `NOT_UTC`).
- **No PnL, cost, strategy, backtest, trading, or execution work is authorized.**
- The panel is frozen at **47,064** rows (seven-way intersection 47,065 minus the maximum common label
  `2026-07-30 14:00:00`); USDJPY's source ends `2026-07-30 14:00:00`, which truncates the panel.
- No workaround or modified universe is authorized.

## Declaration

No market statistic, outcome, cost, PnL, signal, ML, backtest, or trading result was produced. This is
not a claim that H5-v1 is viable, profitable, or tradable.
