# Phase 1B — Feasibility Report (XAUUSD M15)

**Experiment:** EXP-2026-05-INVALIDATION-REVERSAL  
**Phase:** 1B (historical retrieval + engine validation + feasibility)  
**Date:** 2026-09-24  
**Status:** FEASIBILITY AND ENGINE-VALIDATION ONLY — no performance scoring.

---

## 1. Data Retrieved

| Window | M15 bars | H1 bars | Range |
|---|---|---|---|
| **Development** | 90,718 | 22,692 | 2020-02-28 → 2023-12-31 |
| **Research-grade OOS** | 64,442 | 16,122 | 2024-01-01 → 2026-09-23 |
| **Full combined** | 155,252 | 38,837 | 2020-02-28 → 2026-09-23 |

- **Duplicates:** 0 (deduped to last).
- **UTC alignment:** 100% of M15/H1 bars align to quarter-hour/hour boundaries in UTC.
- **Provenance:** per-chunk SHA-256 in `RAW_PROVENANCE.json`; combined processed parquet under `data/processed/`.

## 2. Data Quality

| Check | Finding |
|---|---|
| Envelope | 2020-02-28 → present; development window effectively starts 2020-02-28 (no earlier XAUUSD data in terminal) |
| Duplicates | 0 |
| Gaps >22.5 min | 1,700 (M15) — dominated by: 1,310 daily maintenance gaps (modal start **23:45 UTC**), 318 weekend gaps (40–50h), ~66 other long gaps (holidays/weekends) |
| Spread (points) | min 0, max 435, mean 14.6, p50 18, p99 34 |
| **Spread anomalies** | min=0 bar (zero spread — flagged); max 435 (extreme outlier — flagged); bar spread is a per-bar snapshot, not constant |
| Timestamp | UTC-aligned (100%) |

**Missing-bar flag rule (pre-registered):** any gap > 22.5 min marks the following bar as `missing_bar` (weekends and the 23:45 maintenance window are expected and flagged, not silently filled). No holiday calendar was used (unconfirmed).

## 3. Conservative Session Exclusion (pre-registered)

- **Rule:** exclude any episode whose long entry, invalidation, C1, short entry, or max 12-bar short hold touches **22:30–02:00 UTC**.
- **Label:** `conservative_observed_window_exclusion_not_broker_confirmed`.
- Applied identically in both windows. No rescheduling or substitution.

| Window | Session-excluded episodes | Fraction of total |
|---|---|---|
| Development | 324 | 12.2% |
| Research-grade OOS | 283 | 11.0% |

## 4. Episode Counts (frozen rules, conservative exclusions applied)

### Development (2020-02-28 → 2023-12-31)

| Reason | Count |
|---|---|
| **Denominator (non-excluded):** | **1,616** |
| — c1_triggered | 323 |
| — no_c1 | 1,255 |
| — rollover_ineligible | 38 |
| Excluded: conservative session | 324 |
| Excluded: other_pre_registered (no invalidation within 500-bar scan) | 710 |

### Research-grade OOS (2024-01-01 → 2026-09-23)

| Reason | Count |
|---|---|
| **Denominator (non-excluded):** | **1,523** |
| — c1_triggered | 339 |
| — no_c1 | 1,154 |
| — rollover_ineligible | 30 |
| Excluded: conservative session | 283 |
| Excluded: other_pre_registered (no invalidation within 500-bar scan) | 773 |

## 5. Feasibility Verdict

### GO (feasibility) — sample sufficient for a later performance-scoring phase

| Criterion | Value | Met? |
|---|---|---|
| ≥100 development denominator episodes | **1,616** | ✅ |
| ≥100 OOS denominator episodes | **1,523** | ✅ |
| c1_triggered ≥ some usable count (development) | **323** | ✅ (each with short_stop/exit set) |
| Data quality permits implementation | Envelope, no dups, UTC-aligned, spread proxy usable | ✅ |

**This GO authorizes feasibility only.** It is NOT a strategy GO, NOT a trading decision, and NOT an OOS-sealed claim.

## 6. Rule-Engineering Finding (must be resolved before scoring)

**The 500-bar invalidation scan cap is NOT a frozen v3.3 design element.** The frozen design says "later completed solid-body close below frozen support" without a max-wait bound. Implementation requires *some* bound (an episode may persist indefinitely), but:

- **1,483 episodes (710 dev + 773 OOS, ~28% of all episodes) hit the 500-bar cap** with no invalidation and were classified `other_pre_registered` / excluded.
- The invalidation wait distribution is **right-skewed**: p50 71 bars, p90 317, **p99 476.6, max 500** — meaning the cap truncates a real tail of longer-wait invalidations.
- This exclusion changes the denominator materially. **Decision required from the user** (not a parameter tune — a design-bound choice):
  - Option A: keep 500-bar cap (shortest episodes only; documented limitation).
  - Option B: increase cap (e.g., 2000 bars ≈ 21 days) — more episodes, longer scan.
  - Option C: cap by elapsed time rather than bar count.
  - Option D: report both capped and uncapped counts as sensitivity.

**Recommendation:** the frozen design has no cap, so Option B or D is more faithful; but any choice must be a user-approved manifest revision, not an engine parameter tune.

## 7. Explicit Limitations

| Limitation | Status |
|---|---|
| Broker holiday/early-close calendar | **UNCONFIRMED** — no holiday inference used |
| Maintenance window 23:45–01:00 UTC | **PROVISIONAL / OBSERVED** (3+ days + gap distribution), not broker-confirmed; conservative 22:30–02:00 exclusion applied |
| Bar spread as cost proxy | Per-bar snapshot in points; **not** an executable bid/ask path; min=0 and max=435 outliers flagged |
| Historical bid/ask | **UNAVAILABLE** (tick API) |
| FX contract sizes | Not applicable in this phase (XAUUSD only); XAUUSD 100 oz/lot from prior pre-flight |
| DST behavior | Unknown — conservative window applied uniformly |
| Development window start | 2020-02-28 (data availability), not 2020-01-01 |
| 500-bar scan cap | **Unfrozen design element** — see §6 |

## 8. Engine Validation

- 12 unit/integration tests pass: Wilder ATR pre-entry-only + recurrence; fill formulas (buy/sell adverse, points×point); solid-body; maintenance-window touch; episode state machine (frozen levels, next-bar fill, reason-code consistency, no same-close fill).
- Ledger checks: all c1_triggered episodes have short_stop/short_exit set; zero same-close-fill violations.
- Full suite: **285 passed** (273 + 12).

## 9. Confirmation

- No orders, no login(), no terminal/account/settings/process changes.
- Session preserved: demo 7409623, $5,000.05, 0 positions, 0 orders (before/after).
- No `frival/` modification. No performance scoring, no EV/PF/win-rate/drawdown/CI computation.
- No EURUSD/GBPUSD economics; no replication verdicts.
- OOS is **research-grade, not sealed**.

---

*This report is feasibility and engine-validation only. Awaiting approval before any historical policy performance computation.*