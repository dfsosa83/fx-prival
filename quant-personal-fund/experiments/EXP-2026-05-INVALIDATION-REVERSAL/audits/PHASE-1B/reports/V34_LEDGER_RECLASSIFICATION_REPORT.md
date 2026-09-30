# v3.4 Ledger Reclassification Report

**Experiment:** EXP-2026-05-INVALIDATION-REVERSAL  
**Phase:** 1B update — data-free ledger reclassification + engine validation  
**Date:** 2026-09-24  
**Scope:** Episode identification and reason-code classification ONLY. **No performance scoring.**

---

## 1. Manifest Hashes

| Version | Path | SHA-256 | Unchanged? |
|---|---|---|---|
| v3.2 | `experiment.yaml` | `f3b1cea932ac085d2d0ea4298b76670ee894b1e8741c9396e39ce77715af2e71` | ✅ (unchanged) |
| v3.3 | `experiment.v3.3.yaml` | `6627de4c87a2ec1aa801532bcb5fcef8ac5a473ed248a4e5286a11e3a78f518d` | ✅ (unchanged) |
| **v3.4** | **`experiment.v3.4.yaml`** | **`30ff82ce3f230a3b364bdf553b58ddd501dcb7231d3dd98199c65305de5891ef`** | **new** |

## 2. Files Created/Changed

| File | Change |
|---|---|
| `experiment.v3.4.yaml` | **Created** — versioned manifest with 20-calendar-day observation window, revised reason codes, population definitions, restrictions |
| `engine/engine_v34.py` | **Created** — v3.4 engine variant (20-day window; no 500-bar cap; new reason codes) |
| `tests/test_engine_v34.py` | **Created** — 12 synthetic tests for the 20-day boundary + reason-code semantics |
| `reports/episode_ledger_v34.csv` | **Created** — 5,229-row ledger with v3.4 reason codes, **no performance columns** |
| `reports/LEDGER_V34_SUMMARY.json` | **Created** — v3.4 counts by period |
| `reports/V34_CHANGELOG.json` | **Created** — v3.3 vs v3.4 comparison |
| `reports/FEASIBILITY_SUMMARY.json` | (unchanged — v3.3 record preserved) |
| `reports/episode_ledger.csv` | (unchanged — v3.3 record preserved) |

## 3. Frozen Observation Rule (v3.4)

- Each original long episode begins at the **next-bar-open long fill**.
- Observe for a **maximum of 20 calendar days** from the actual entry timestamp.
- If no completed M15 solid-body close below frozen support occurs within 20 calendar days → `no_invalidation_within_observation_window`.
- Kept in the complete ledger; **outside** the A-vs-B population (no invalidation occurred).
- No scan for, substitution of, or use of a later invalidation/C1.
- No tuning/comparison of alternative window lengths.
- This is an **episode-definition boundary only** — no outcome inference.

## 4. Updated Reason Codes (v3.4 — mutually exclusive, exhaustive)

`c1_triggered` · `no_c1` · `no_invalidation_within_observation_window` · `conservative_observed_window_exclusion_not_broker_confirmed` · `missing_bar_calendar_exclusion` · `rollover_ineligible` · `other_pre_registered`

**Obsolete label (traceability only):** `no_invalidation_within_unfrozen_scan_cap` — no longer produced.

## 5. Development Counts (2020-02-28 → 2023-12-31)

| Category | Count |
|---|---|
| **Total original long entries** | **2,650** |
| **Invalidated episodes eligible for A-vs-B** (c1 + no_c1 + rollover_ineligible) | **1,841** |
| — C1-triggered short episodes | 354 |
| — no-C1 episodes | 1,445 |
| — rollover-ineligible | 42 |
| **no_invalidation_within_observation_window** | **468** |
| Conservative-session exclusions | 324 |
| Missing-bar/calendar exclusions | 17 |
| Other pre-registered | 0 |

## 6. Research-Grade OOS Counts (2024-01-01 → 2026-09-23)

| Category | Count |
|---|---|
| **Total original long entries** | **2,579** |
| **Invalidated episodes eligible for A-vs-B** | **1,715** |
| — C1-triggered short episodes | 384 |
| — no-C1 episodes | 1,291 |
| — rollover-ineligible | 40 |
| **no_invalidation_within_observation_window** | **562** |
| Conservative-session exclusions | 283 |
| Missing-bar/calendar exclusions | 19 |
| Other pre-registered | 0 |

## 7. Change Log vs Provisional 500-bar Scan (v3.3)

| Period | v3.3 denominator | v3.4 denominator | Δ |
|---|---|---|---|
| Development | 1,616 | **1,841** | **+225** |
| Research-grade OOS | 1,523 | **1,715** | **+192** |

| Period | v3.3 `other_pre_registered` (500-bar cap) | v3.4 `no_invalidation_within_observation_window` | v3.4 other/other |
|---|---|---|---|
| Development | 710 | 468 | 0 |
| OOS | 773 | 562 | 0 |

**Interpretation of the delta:** the v3.3 500-bar cap **truncated** episodes whose invalidation occurred after ~5.2 days (500 M15 bars ≈ 5.2 trading days but ~7 calendar days with the daily halt). Under v3.4's 20-calendar-day window, +225 (dev) / +192 (OOS) episodes that **did** invalidate within 20 days are now correctly classified as **invalidated and A-vs-B eligible** (c1_triggered/no_c1/rollover_ineligible), rather than being dropped as `other_pre_registered`. The remaining 468/562 are true `no_invalidation_within_observation_window` cases (never invalidated within 20 days).

**This is a material, correct reclassification:** the v3.3 denominator understated the A-vs-B population. The v3.4 counts are the frozen baseline for any future scoring.

## 8. Synthetic Test Results

`tests/test_engine_v34.py` + `tests/test_engine_validation.py`: **24 passed, 0 failed.**

| Test group | Coverage |
|---|---|
| TestObservationWindow | 20-day boundary from actual entry timestamp; invalidation at/before boundary included; after excluded; no later C1 after expiration |
| TestReasonCodes | codes mutually exclusive and exhaustive; no-invalidation label present; obsolete 500-bar label absent from output |
| TestNoPerformanceMetrics | ledger contains no PnL/EV/PF/win-rate/drawdown/CI fields |
| TestMaintenanceWindow / TestSolidBody | inherited v3.3 checks |

## 9. Confirmations

- ✅ No new MT5 retrieval (stored bars only)
- ✅ No broker/account calls, no login(), no terminal/process/settings changes
- ✅ No changes under `frival/`
- ✅ No PnL, EV/R, PF, win-rate, drawdown, bootstrap CI, or strategy decision computed
- ✅ No selection among windows/parameters/filters/variants
- ✅ v3.2/v3.3 manifests unchanged; v3.4 is additive

**Stopped. Awaiting explicit approval before any performance-scoring phase.**