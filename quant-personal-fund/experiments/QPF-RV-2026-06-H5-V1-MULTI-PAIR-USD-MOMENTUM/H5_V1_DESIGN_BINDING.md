# H5-v1 — Design Binding

**Experiment:** `QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM`
**Parent design:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V1_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE`
**Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

This experiment **binds exactly to the H5 parent protocol** without changing it:

- **Mandatory basket:** `EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD`.
- **Targets:** `EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`.
- **Timeframe H1**, internal ordinal clock only (`NOT_UTC`).
- **Grid:** \(L=\{4,8,24,48\}\), \(H=\{4,8,24\}\), \(V=\{24,72\}\), \(K=\{3,4\}\); directions = USD
  strength and USD weakness.
- **Treatments:** target-**excluded** primary selection; target-**included** secondary diagnostic only.
- **Selection/multiplicity/escalation:** validation-only selection, **BH FDR \(q=0.10\)** across the
  672 target-excluded primary tests, **maximum three** sealed configurations.
- **Snapshot:** hash-verified immutable strict **seven-way intersection**; exclude exactly the maximum
  common label; no imputation/resampling/transformation.
- **No computation occurs in this freeze stage.**
- **No profitability or trading claim is allowed.**
