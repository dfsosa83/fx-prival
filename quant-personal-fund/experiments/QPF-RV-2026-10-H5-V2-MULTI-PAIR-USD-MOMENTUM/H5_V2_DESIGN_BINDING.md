# H5-v2 — Design Binding

**Experiment:** `QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Parent design:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM`
**Predecessor snapshot:** `QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM` (`FROZEN_UNUSED_USDJPY_STALE`)
**Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

- H5-v2 binds **unchanged** to the H5 parent protocol.
- **Mandatory basket includes USDJPY**: `EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD`.
- Same **targets** (`EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`), expected signs,
  \(L=\{4,8,24,48\}\), \(H=\{4,8,24\}\), \(V=\{24,72\}\), \(K=\{3,4\}\), **both directions**,
  target-**excluded** primary / target-**included** secondary treatments, 60/20/20 split with 30-bar
  embargoes, validation-only selection, **BH FDR \(q=0.10\)**, and single sealed confirmation (max
  three bound configurations).
- **H5-v1 remains immutable but unused** for statistical screening.
- **H5-v2 differs only** by using the post-repair canonical USDJPY source history.
- **No computation occurs in this freeze phase.**
- **No profitability or trading claim** is allowed.
