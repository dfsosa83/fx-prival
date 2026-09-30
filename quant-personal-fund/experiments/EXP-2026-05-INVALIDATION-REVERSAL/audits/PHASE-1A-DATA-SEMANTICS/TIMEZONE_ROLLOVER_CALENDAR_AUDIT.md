# Timezone, Rollover, and Calendar Audit — Phase 1A

**Date:** 2026-09-24  
**Scope:** Read-only M15 bar sample (2026-09-21 → 09-24) for XAUUSD, EURUSD, GBPUSD.

---

## 1. Timezone

### Finding
All M15 bar timestamps align to :00/:15/:30/:45 **in UTC** (100% of sample for all three symbols).

### Interpretation
The MT5 `copy_rates_range` returns UTC-aligned bar times for these symbols. No server-local offset observed.

| Symbol | UTC-aligned fraction | Sample size |
|---|---|---|
| XAUUSD | 1.000 | 346 |
| EURUSD | 1.000 | 362 |
| GBPUSD | 1.000 | 362 |

### Verdict
**GO — UTC-aligned timestamps.** Full-history re-verification deferred to Phase 1 retrieval (cheap check).

---

## 2. Rollover / Maintenance (XAUUSD)

### Observed daily gap (3 consecutive days)

| Date (UTC) | Gap window | Duration |
|---|---|---|
| 2026-09-21 → 22 | 23:45 → 01:00 | 1.25h |
| 2026-09-22 → 23 | 23:45 → 01:00 | 1.25h |
| 2026-09-23 → 24 | 23:45 → 01:00 | 1.25h |

EURUSD and GBPUSD show **no** intraday gap (continuous 24/5).

### Verdict
**GO (observed) — XAUUSD maintenance window ~23:45 → 01:00 UTC daily.**

**Material correction:** the frozen manifest's candidate `~21–22 UTC` is **wrong**; observed window is **23:45–01:00 UTC**. Recorded as an audit finding (frozen manifest not edited without approval).

### DST behavior
- Stable across 3 days in UTC.
- DST drift (±1h) not observable in this window. **Unresolved — broker.**

---

## 3. Calendar / Sessions

| Item | Finding | Source |
|---|---|---|
| FX sessions | 24/5 continuous (EURUSD, GBPUSD) | 5-day M15 sample |
| XAUUSD sessions | ~23h/day + maintenance window | 5-day M15 sample |
| Holidays / early closes | **Not exposed** in terminal metadata | MT5 API |
| Early-close rules | **Not exposed** | MT5 API |

### Verdict
**HOLD — holiday/early-close calendar requires broker confirmation.**

---

## 4. Implications for the Experiment

1. **Cost model:** `S = bar_spread_field × point` is unit-correct (verified). Bar spread is a per-bar snapshot — using a constant would be wrong; using the bar's own spread field per-bar is the correct proxy.
2. **No-rollover mechanics:** the observed maintenance window (23:45–01:00 UTC) must be used in place of the manifest's candidate. The "latest eligible entry" and "forced exit before window" rules remain, now with a confirmed window.
3. **Timezone:** all episode timing (entry/exit bars, rollover eligibility) operates on UTC-aligned timestamps — consistent with the manifest's UTC convention.

---

## 5. Remaining Broker Confirmations

- Holiday and early-close calendar per instrument.
- DST behavior of the maintenance window across seasons.
- FX contract sizes (not exposed by terminal API).
- Whether bar-spread field is open/mid/average-of-bar (units confirmed; temporal semantics secondary).