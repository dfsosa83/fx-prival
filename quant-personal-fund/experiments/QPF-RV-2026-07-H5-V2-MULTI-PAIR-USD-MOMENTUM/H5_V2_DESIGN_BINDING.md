# H5-v2 — Design Binding

**Experiment:** `QPF-RV-2026-07-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Parent design:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V1B_USDJPY_HISTORY_COMPLETENESS_REPAIR`
**Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

- H5-v2 **inherits the parent H5 protocol unchanged** (basket, targets, signs, \(L/H/V/K\) grid,
  directions, target-excluded primary / target-included secondary, temporal split, 30-bar embargoes,
  validation-only selection, BH FDR \(q=0.10\), maximum three sealed configurations).
- It uses the **same mandatory seven instruments**: `EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD,
  NZDUSD`.
- **Only USDJPY raw history completeness** was to be repaired.
- The **H5-v1 snapshot remains immutable and unused for screening**.
- **No hypothesis, signal, grid, threshold, selection, or decision rule changed.**
- **This stage did not complete**: the repository downloader is schema-incompatible with the existing
  USDJPY file, so the repair was refused (fail-closed) and no v2 snapshot was created.
