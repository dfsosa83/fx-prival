# G3-R0b — Completed-Label Boundary Amendment

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Stage:** `G3R0B_COMPLETED_LABEL_BOUNDARY_REPAIR`
**Date:** 2026-09-29

---

1. **G3-v1** remained `PAUSE_STATISTICAL_VIABILITY` after a **source hash mismatch**, before any
   parsing of market data or observation of any statistical result.
2. **G3-R0** froze `g3_internal_clock_snapshot_v2.csv` (result `SNAPSHOT_FROZEN_PENDING_G3_V2`)
   **without any statistical calculation**.
3. The **v2 report** documented that the explicit label `2026-09-29 19:00:00` was excluded while
   `2026-09-29 20:00:00` was retained as the **greatest common label**.
4. **No G3-v2 test was run** and **no statistical result was observed** from v2.
5. **v3 replaces only the future input boundary rule:**
   ```text
   Form the strict sorted intersection of internal timestamp labels, then
   exclude exactly the maximum common label.
   ```
6. This is a **deterministic data-integrity repair** — **not** parameter tuning, result-selection,
   hypothesis modification, or p-hacking. It is a pre-statistical correction of the completed-label
   boundary rule and must not be used to inspect or optimize market results.
7. **`NOT_UTC` is preserved.** No bar-completion, market-session, UTC, or broker-time assertion is
   made; the maximum common label is excluded solely by the deterministic maximum-label rule.
8. **All V2 statistical choices remain unchanged:** split proportions (60/20/20), 30-bar embargoes,
   OLS construction, ADF settings, Johansen settings, AR(1)/OU settings, variance-ratio horizons,
   bootstrap parameters, rolling window design (pre-sealed 5,000/1,000 primary; sealed confirmatory;
   4,000/6,000 sensitivity), decision thresholds, seed 42, and all prohibitions.
9. **v1 and v2 artifacts remain immutable historical evidence** and must not be altered, deleted,
   renamed, regenerated, or rehashed. v2 does not authorize any G3-v2 run.

## Boundary rule change (only)

| | v2 (G3-R0) | v3 (G3-R0b) |
|---|---|---|
| Excluded label | fixed `2026-09-29 19:00:00` | **maximum common label** |
| Rationale | explicit named label | deterministic maximum-label rule |

No other change is made. No statistical setting, threshold, seed, or decision rule is changed.
