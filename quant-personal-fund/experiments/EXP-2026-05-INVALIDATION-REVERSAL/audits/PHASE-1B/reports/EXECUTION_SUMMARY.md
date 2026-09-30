# EXECUTION SUMMARY — Phase 1B

**Experiment:** EXP-2026-05-INVALIDATION-REVERSAL  
**Phase:** 1B — XAUUSD M15 historical retrieval, engine validation, feasibility  
**Date:** 2026-09-24

---

## 1. Feasibility Verdict

**GO (feasibility) — sufficient sample and data quality for a later performance-scoring phase.**

| Window | Denominator episodes | c1_triggered | no_c1 | rollover_ineligible | session-excluded |
|---|---|---|---|---|---|
| Development (2020-02-28→2023-12-31) | **1,616** | 323 | 1,255 | 38 | 324 |
| Research-grade OOS (2024→2026-09-23) | **1,523** | 339 | 1,154 | 30 | 283 |

## 2. Data Retrieved and Quality

| Item | Value |
|---|---|
| M15 bars (full) | 155,252 (2020-02-28 → 2026-09-23), 0 dups, 100% UTC-aligned |
| H1 bars (full) | 38,837 |
| Spread (points) | mean 14.6, p50 18, p99 34, max 435, min 0 (outliers flagged) |
| Gaps | 1,310 daily maintenance (modal 23:45 UTC), 318 weekends, ~66 other |
| Provenance | Per-chunk SHA-256 in RAW_PROVENANCE.json |

## 3. Engine Validation

- **12/12** engine unit/integration tests pass (ATR pre-entry, fill formulas, solid-body, maintenance window, state machine, reason-code consistency, no same-close fill).
- **285 total tests pass** (273 existing + 12 new).
- Ledger: 5,229 episodes; 662 c1_triggered all have complete short paths; zero same-close-fill violations.

## 4. Feasibility Conditions Met

- ✅ ≥100 development denominator (1,616)
- ✅ ≥100 OOS denominator (1,523)
- ✅ c1_triggered usable counts (323 dev / 339 OOS)
- ✅ Data quality permits implementation (envelope, no dups, UTC-aligned, spread proxy)

## 5. Required Design Decision Before Any Scoring

**The 500-bar invalidation scan cap is NOT part of the frozen v3.3 design.** 1,483 episodes (28%) hit the cap with no invalidation and were excluded as `other_pre_registered`. The invalidation wait is right-skewed (p99 476.6, max 500) — the cap truncates a real tail. The user must choose the cap convention (keep / increase / time-based / sensitivity) via a manifest revision **before** any performance scoring. This is a design-bound decision, not a parameter tune.

## 6. Explicit Limitations (unchanged)

- Broker holiday/early-close calendar **unconfirmed**; no holiday inference used.
- Maintenance window 23:45–01:00 UTC **provisional/observed**; conservative 22:30–02:00 exclusion applied.
- Bar spread is a per-bar snapshot cost proxy; min=0 and max=435 outliers flagged; not an executable bid/ask path.
- Historical bid/ask unavailable; FX contract sizes N/A this phase (XAUUSD only).
- OOS is **research-grade, not sealed**.
- Development window effectively starts 2020-02-28 (data availability).

## 7. Confirmation

- ✅ No orders, no login(), no terminal/account/settings/process changes
- ✅ Session preserved: demo 7409623, $5,000.05, 0 positions, 0 orders (before/after identical)
- ✅ No `frival/` modification
- ✅ No performance scoring, no EV/PF/win-rate/drawdown/CI computed
- ✅ No EURUSD/GBPUSD economics; no replication verdicts
- ✅ No trading recommendation or GO trading decision

## 8. Next Step (blocked on approval)

1. **User decides the invalidation scan-cap convention** (§5) — required before scoring.
2. **On approval**, a performance-scoring phase may compute historical policy performance (EV/R, PF, win rate, drawdown, bootstrap CIs) — currently **not authorized**.

**Stopped. Awaiting explicit approval.**