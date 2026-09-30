# v3.5 Ledger Reconstruction Report

**Experiment:** EXP-2026-05-INVALIDATION-REVERSAL  
**Phase:** 1B update — episode-boundary correction + ledger reconstruction  
**Date:** 2026-09-24  
**Scope:** Episode identification + reason-code classification ONLY. **No performance scoring.**

---

## 1. Manifest Hashes (before/after — all unchanged except v3.5 new)

| Version | SHA-256 | Unchanged? |
|---|---|---|
| v3.2 | `f3b1cea932ac085d2d0ea4298b76670ee894b1e8741c9396e39ce77715af2e71` | ✅ (unchanged) |
| v3.3 | `6627de4c87a2ec1aa801532bcb5fcef8ac5a473ed248a4e5286a11e3a78f518d` | ✅ (unchanged) |
| v3.4 | `30ff82ce3f230a3b364bdf553b58ddd501dcb7231d3dd98199c65305de5891ef` | ✅ (unchanged) |
| **v3.5** | **`a1a9a990eabe4cbabc42b669e88d8486e0c1e7001794c6052e0cf3d5ac4c3f5d`** | **new** |

## 2. Files Created

| File | Purpose |
|---|---|
| `experiment.v3.5.yaml` | Versioned manifest (entry-timestamp assignment, right-censoring, dependence metadata, reason codes) |
| `engine/engine_v35.py` | v3.5 engine (full-history run, right-censor label, dependence metadata, no catch-all) |
| `tests/test_engine_v35.py` | 10 synthetic/integration tests |
| `reports/episode_ledger_v35.csv` | 5,225-row ledger with v3.5 reason codes + metadata |
| `reports/LEDGER_V35_SUMMARY.json` | Counts by window |
| `reports/V35_RECONSTRUCTION_REPORT.md` | This document |

## 3. Frozen v3.5 Rules (applied)

1. **Assignment:** by entry-fill timestamp only; dev 2020-02-28→2023-12-31, OOS 2024-01-01→last eligible; engine runs on **full concatenated history** so post-entry bars across the 2023-12-31 boundary resolve invalidation/C1/exit. Label: `entry_timestamp_assignment_with_cross_boundary_outcome_resolution`.
2. **Right censoring:** if the 20-day window ends after `last_available_bar_time` → `right_censored_at_data_end`; never no_invalidation/other/no_c1/rollover/c1. In full ledger; excluded from fully-observed population.
3. **Fully observed:** only complete-window episodes may be no_invalidation or enter A-vs-B; boundary-time invalidation included; post-boundary excluded.
4. **Dependence metadata:** entry_time, invalidation_time, c1_time, shared_invalidation_cluster_id, time_block_id (24-bar/6h), observation_complete, assignment_window. No statistics.
5. **Reason codes:** mutually exclusive and exhaustive; no `other_pre_registered` catch-all; obsolete 500-bar label removed.

## 4. Development Counts (full-history, entry-timestamp assignment)

| Reason | Count |
|---|---|
| **Total original long entries** | **2,650** |
| **A-vs-B eligible (fully observed, invalidated)** | **1,863** |
| — c1_triggered | 359 |
| — no_c1 | 1,446 |
| — rollover_ineligible | 42 |
| no_invalidation_within_observation_window | 446 |
| conservative_observed_window_exclusion | 324 |
| missing_bar | 23 |
| **right_censored_at_data_end** | **0** (dev entries ≤ 2023-12-31; windows end ≤ 2024-01-20, well before data end 2026-09-23) |

## 5. Research-Grade OOS Counts

| Reason | Count |
|---|---|
| **Total original long entries** | **2,575** |
| **A-vs-B eligible** | **1,692** |
| — c1_triggered | 382 |
| — no_c1 | 1,270 |
| — rollover_ineligible | 40 |
| no_invalidation_within_observation_window | 562 |
| conservative_observed_window_exclusion | 281 |
| missing_bar | 19 |
| **right_censored_at_data_end** | **21** (entries after ~2026-09-03; window extends past 2026-09-23) |

## 6. Difference vs v3.4 (correction summary)

| Metric | v3.4 | v3.5 | Δ |
|---|---|---|---|
| Development A-vs-B denominator | 1,841 | **1,863** | **+22** |
| Development no_invalidation | 468 | 446 | −22 |
| OOS A-vs-B denominator | 1,715 | **1,692** | −23 |
| OOS no_invalidation | 562 | 562 | 0 |
| **OOS right_censored_at_data_end** | (not labeled) | **21** | +21 explicit |

**Correction of the 27 misclassified development episodes (from the review):**
- In v3.4, 27 dev episodes were truncated at the 2023-12-31 slice end and misclassified `no_invalidation` despite their window extending into 2024.
- In v3.5, the engine runs on full history: **22 of those 27 are now resolved as truly invalidated** (moved into the A-vs-B denominator via c1/no_c1/rollover), and the remaining episodes that genuinely never invalidate within 20 days stay `no_invalidation`. The dev denominator rose +22.
- **OOS correction:** 21 late entries whose windows extend past 2026-09-23 are now explicitly `right_censored_at_data_end` instead of silently falling into no_c1/other. The OOS denominator fell −23 (21 right-censored + 2 c1/no_c1 that resolved differently under full-history; net −23 is the correction).

## 7. Test Results

`tests/test_engine_v35.py`: **10 passed, 0 failed.**

| Test | Proves |
|---|---|
| test_cross_boundary_outcome_resolution | Dev entry resolves invalidation/C1 using 2024 bars while retaining dev assignment |
| test_assignment_only_by_entry_timestamp | Assignment by entry fill timestamp only |
| test_window_past_data_end_is_right_censored | Entry window past last bar → right_censored |
| test_censored_never_no_invalidation_or_eligible | Censored never no_invalidation nor A-vs-B eligible |
| test_invalidation_at_boundary_included | Boundary-time invalidation included |
| test_invalidation_after_boundary_excluded | Post-boundary invalidation excluded |
| test_exhaustive_and_mutually_exclusive | Reason codes exhaustive; no catch-all; no obsolete label |
| test_metadata_present_and_deterministic | Metadata present; time_block deterministic |
| test_shared_cluster_deterministic | Cluster id deterministic across runs |
| test_no_performance_fields | No PnL/EV/R/PF/win-rate/drawdown/CI fields |

## 8. Reconciliation (independent)

| Check | Result |
|---|---|
| Total ledger rows | 5,225 |
| Sum of reason counts | 5,225 (= total) ✅ |
| Duplicate (window, idx) | 0 ✅ |
| observation_complete missing | 0 ✅ |
| Right-censored episodes | 21 (all OOS) ✅ |
| A-vs-B eligible (fully observed) | dev 1,863 + OOS 1,692 = 3,555 ✅ |

## 9. Confirmations

- ✅ No performance metrics (PnL, EV/R, PF, win rate, drawdown, CI, bootstrap) computed
- ✅ No MT5 retrieval / broker/account calls / login() / process/settings changes
- ✅ No `frival/` modifications; no orders
- ✅ No prior manifests, ledgers, reports, or hashes modified
- ✅ Overlap metadata deterministic; no episodes collapsed/removed/selected

**Stopped. Awaiting explicit approval before any performance-scoring phase.**