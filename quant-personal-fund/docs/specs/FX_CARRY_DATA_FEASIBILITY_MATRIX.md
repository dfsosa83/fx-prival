# FX Carry Data-Feasibility Matrix

**Status:** Stage 1A parallel audit (source inventory only — NOT strategy research)  
**Date:** 2026-09-25  
**Classification key:** Confirmed available · Available with limitations · Unavailable · Requires paid/vendor source · Requires broker confirmation

---

## Purpose

Determine whether date-consistent historical data can be obtained for a future FX carry experiment. This is a data-feasibility inventory, not a strategy, ranking, or backtest. No hypothesis is being tested.

---

## 1. Data-Field Matrix

### 1.1 Spot FX prices

| Instrument | Availability | Source | Limitations |
|---|---|---|---|
| EURUSD, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY, EURJPY | **Confirmed available** | Yahoo Finance daily (local parquet), MT5 terminal | Daily only in current storage; MT5 envelopes 2016+ (FX) verified; contract sizes unconfirmed |
| Date consistency | **Confirmed available** | Phase 0.5/1A audits | UTC-aligned timestamps verified |

### 1.2 FX forward points / forward-return construction

| Field | Availability | Source | Limitation |
|---|---|---|---|
| Forward points (outrights) | **Unavailable** | — | Not present in Yahoo/FRED/MT5; requires a broker forward desk or a paid vendor |
| Defensible forward-return construction | **Requires broker confirmation / paid vendor** | Broker forward desk; vendor (Refinitiv/Bloomberg-class) | Must be date-consistent with spot; publication/revision timestamps needed |
| Forward tenor conventions | **Requires broker confirmation** | Broker contract specs | 1W/1M/3M conventions per pair |

### 1.3 Rate differentials / OIS / policy rates

| Field | Availability | Source | Limitation |
|---|---|---|---|
| US rates (policy, OIS-class) | **Confirmed available** | FRED (DGS3MO etc.) | US only; not a substitute for FX carry |
| EUR/GBP/JPY/AUD/NZD/CAD/CHF policy or OIS rates | **Available with limitations** | FRED has some (e.g., ECB, BOJ series); OIS-class requires vendor | Publication/revision timestamps needed; FRED gives reference dates but not all revision history |
| **Caveat (explicit)** | — | — | **FRED policy rates are NOT executable FX forward/carry data.** They may explain macro conditions but cannot produce a carry return without forwards. |

### 1.4 Financing / rollover / broker costs

| Field | Availability | Source | Limitation |
|---|---|---|---|
| Current swap (long/short per lot/day) | **Confirmed available (current only)** | MT5 symbol_info (Phase 1A) | Current values only; not a historical series |
| Historical swap series | **Unavailable** | — | Not retrievable via terminal; requires broker archive or vendor |
| Rollover cost | **Unavailable** | — | Requires forward points or broker roll schedule |
| Broker-specific commissions | **Requires broker confirmation** | Broker schedule | Not yet obtained |

### 1.5 Contract specs / trading conventions

| Field | Availability | Source | Limitation |
|---|---|---|---|
| XAUUSD contract size | **Confirmed available** | Prior live pre-flight (100 oz/lot) | — |
| FX contract sizes | **Unavailable / requires broker confirmation** | MT5 terminal returned null (Phase 1A) | Broker confirmation required |
| Tick size, volume min/step | **Confirmed available** | MT5 symbol_info | — |
| Trading calendars / roll schedules | **Available with limitations** | Terminal symbol metadata; gap analysis | Holidays/early-close not exposed; DST behavior incompletely confirmed |

### 1.6 Historical calendars

| Field | Availability | Source | Limitation |
|---|---|---|---|
| FX weekend/session structure | **Confirmed available** | 5-day M15 sample (Phase 1A/1B) | 24/5 verified |
| Holiday/early-close calendar | **Requires broker confirmation** | Broker documentation | Not exposed via terminal API |

---

## 2. Classification Summary

| Data field | Classification |
|---|---|
| Spot FX prices (daily) | **Confirmed available** |
| UTC timestamp alignment | **Confirmed available** |
| US policy rates (FRED) | **Confirmed available** |
| Non-US policy/OIS rates | **Available with limitations** (revision timestamps partial) |
| FX forward points | **Unavailable** (requires broker forward desk or paid vendor) |
| Historical swap series | **Unavailable** |
| Current swap values | **Confirmed available (current only)** |
| FX contract sizes | **Requires broker confirmation** |
| Holiday/early-close calendar | **Requires broker confirmation** |
| DST behavior | **Requires broker confirmation** |

---

## 3. Feasibility Determination

**A future FX carry experiment requires, at minimum, one of:**

1. **FX forward points** (broker forward desk or paid vendor), OR
2. **A defensible forward-return construction** with date-consistent spot + forwards + rate series with publication/revision timestamps, OR
3. **Broker-supplied historical swap/financing series** for the exact pairs and tenors.

**None of these is currently available.**

**FRED-class policy rates are confirmed NOT a substitute.** They may explain macro conditions; they cannot produce an executable carry return without forwards.

---

## 4. HOLD/STOP Condition

If adequate carry data cannot be obtained (date-consistent forwards or an equivalent defensible construction), the FX carry candidate receives **HOLD/STOP**. No zero-swap proxy and no arbitrary approximation will be substituted.

**Current status: the FX carry hypothesis is NOT yet testable — the forward/carry data gate is not met.**

---

*This matrix is a source inventory only. No strategy, ranking, forecast, or backtest was performed.*