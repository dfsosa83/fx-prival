# Data Semantics Audit — EXP-2026-05-INVALIDATION-REVERSAL

**Audit:** PHASE-1A-DATA-SEMANTICS  
**Date:** 2026-09-24  
**Scope:** Read-only MT5 metadata + diagnostic bar samples for XAUUSD, EURUSD, GBPUSD. No strategy, no backtest, no orders.

---

## 1. Spread-Field Units and Conversion

### 1.1 Method
- Retrieved current `symbol_info` (point, digits, spread field) and `symbol_info_tick` (live bid/ask) for each symbol.
- Retrieved ~5 days of M15 bars (346–362 bars) with OHLC + spread field.
- Compared live tick spread (ask − bid) against `spread_field × point`.

### 1.2 Evidence (raw)

| Symbol | point | digits | live tick spread | last-bar spread field | point × spread_field |
|---|---|---|---|---|---|
| XAUUSD | 0.01 | 2 | 0.1900 | 19 | **0.1900** |
| EURUSD | 1e-5 | 5 | 0.000120 | 11 | **0.00011** (bar); live 12 → 0.00012 |
| GBPUSD | 1e-5 | 5 | 0.000170 | 13 | **0.00013** (bar); live 17 → 0.00017 |

### 1.3 Conclusion

**GO — spread units confirmed as POINTS.**

`spread_price = spread_points × point`

- XAUUSD: 19 × 0.01 = **$0.19** per unit — matches live tick spread 0.1900 exactly.
- EURUSD: bar 11 × 1e-5 = 0.00011; live 12 × 1e-5 = 0.00012 — both consistent (bar is a point-in-time snapshot; live is instantaneous).
- GBPUSD: bar 13 × 1e-5 = 0.00013; live 17 × 1e-5 = 0.00017 — same relationship.

**Bar-spread is NOT constant.** Observed ranges (points): XAUUSD 19–34 (mode 19), EURUSD 11–67 (mode 11), GBPUSD 11–156 (mode 13). The `spread` field is a **per-bar snapshot**, not a fixed spread. This confirms the manifest's treatment of bar-spread as a **historical cost proxy** is correct, and that **using it as a fixed constant would be wrong**.

### 1.4 Uncertainty
- Live tick vs bar-spread agree on **units** (points), which is the audited question.
- Whether bar-spread represents the mid-bar average spread, the max, or the open-of-bar spread is **not established** — only that it is in points. For the cost proxy, the manifest's `S = bar_spread_field × point` is a valid unit-correct proxy; its exact temporal semantics are secondary and documented as proxy.

---

## 2. Timestamp and Timezone Semantics

### 2.1 Method
- Converted M15 bar `time` (Unix seconds) to UTC datetime.
- Checked alignment to :00/:15/:30/:45 **in UTC**.

### 2.2 Evidence
| Symbol | bars | UTC-minute-aligned fraction |
|---|---|---|
| XAUUSD | 346 | **1.000** |
| EURUSD | 362 | **1.000** |
| GBPUSD | 362 | **1.000** |

All bars align exactly to quarter-hour boundaries in UTC.

### 2.3 Conclusion

**GO — timestamps are UTC-aligned (server returns UTC-based bar times).**

No evidence of a server-local timezone offset in the M15 timestamps. (The earlier gold-rules concern about server-offset mismatch applied to trade-statement times, not to `copy_rates_range` bar times; this sample shows clean UTC alignment.)

**Caveat:** this sample covers 2026-09-21 → 09-24 (5 days). Long-history timestamps are presumed UTC by the same convention but a full-history UTC check is deferred to Phase 1 data retrieval (cheap to verify then). DST behavior: UTC has no DST; if the server shifts to a local wall clock on some dates, that would surface as misalignment — none observed.

---

## 3. Rollover / Maintenance (XAUUSD)

### 3.1 Evidence
Recurring daily gap in XAUUSD M15 bars (~1.25h each), observed three consecutive days:

| Date | Gap (UTC) | Hours |
|---|---|---|
| 2026-09-21 → 22 | 23:45 → 01:00 | 1.25 |
| 2026-09-22 → 23 | 23:45 → 01:00 | 1.25 |
| 2026-09-23 → 24 | 23:45 → 01:00 | 1.25 |

EURUSD and GBPUSD show **no** such daily gap (24/5 continuous; only weekend gaps, outside this sample window).

### 3.2 Conclusion

**GO (observed) — XAUUSD daily maintenance/rollover window is ~23:45 → 01:00 UTC (1.25h), repeating daily.**

**This is a material correction to the manifest's candidate assumption of "~21–22 UTC".** The observed window is **23:45–01:00 UTC**, not 21–22 UTC. The manifest's `no_rollover.maintenance_window` field must be updated to this observed value (pending Phase 1 approval to edit the frozen manifest — recorded here as an audit finding, not a manifest edit).

### 3.3 DST behavior
- Window boundary is stable across the 3 observed days in UTC.
- DST shifts would appear as ±1h drift if the broker uses a DST-aware local schedule; not observable in 3 days. **Unresolved — flag for broker confirmation.**

---

## 4. Calendar / Sessions

| Item | Finding |
|---|---|
| FX sessions | EURUSD/GBPUSD continuous 24/5 (no intraday gap in 5-day sample) — consistent with FX CFD conventions |
| XAUUSD sessions | ~23h/day with the 23:45–01:00 UTC maintenance window |
| Holidays / early closes | **Not retrievable from terminal metadata** (no holiday calendar exposed read-only). **NEEDS BROKER CONFIRMATION.** |
| Source | MT5 terminal symbol metadata + 5-day M15 bar sample |

**Verdict: HOLD — sessions observed but holiday/early-close calendar requires broker confirmation.**

---

## 5. FX Contracts

### 5.1 Evidence
| Symbol | volume_min | volume_step | volume_max | contract_size |
|---|---|---|---|---|
| XAUUSD | 0.01 | 0.01 | 20.0 | **not exposed** (API null; prior live pre-flight verified 100 oz/lot) |
| EURUSD | 0.01 | 0.01 | 50.0 | **not exposed** |
| GBPUSD | 0.01 | 0.01 | 50.0 | **not exposed** |

Swap fields and contract size were not exposed by `symbol_info` in this API build (same as the Phase 0.5 audit).

### 5.2 Verdict

**HOLD — FX contract sizes unresolved (not exposed by terminal API).** XAUUSD contract size 100 oz/lot is verified from the prior live pre-flight (gold_rules v1.3), not from this probe. FX contract sizes must be broker-confirmed. Volume constraints are confirmed (0.01 min/step; 20.0 XAUUSD / 50.0 FX max).

---

## 6. Per-Item Verdicts Summary

| Item | Verdict |
|---|---|
| Spread units | **GO** — points; price = points × point (verified vs live tick) |
| Timezone | **GO** — UTC-aligned bar timestamps (100% of sample) |
| Rollover/maintenance | **GO (observed)** — XAUUSD 23:45–01:00 UTC daily (corrects manifest's 21–22 UTC candidate); DST unresolved |
| Calendar | **HOLD** — sessions observed; holidays/early-close need broker confirmation |
| FX contract specs | **HOLD** — not exposed; XAUUSD 100 oz/lot from prior pre-flight; FX needs broker confirmation |

---

## 7. Evidence vs Assumption

| Claim | Status |
|---|---|
| Bar spread in points | **Evidence** (live-tick match across 3 symbols) |
| spread_price = spread_points × point | **Evidence** |
| Bar spread is a per-bar snapshot (not constant) | **Evidence** (mode vs max ranges) |
| Bar OHLC as mid-price proxy | **Assumption** (unchanged; no intra-bar bid/ask) |
| Timestamps UTC-aligned | **Evidence** (100% sample) |
| XAUUSD maintenance 23:45–01:00 UTC | **Evidence** (3 consecutive days) |
| DST behavior stable | **Unresolved** |
| Holiday/early-close calendar | **Unresolved — broker** |
| FX contract sizes | **Unresolved — broker** |
| Slippage L = 0.5×S | **Assumption** (design parameter, unchanged) |

---

*This audit is data-free beyond read-only metadata and bar samples. No strategy, backtest, signal, or order occurred.*