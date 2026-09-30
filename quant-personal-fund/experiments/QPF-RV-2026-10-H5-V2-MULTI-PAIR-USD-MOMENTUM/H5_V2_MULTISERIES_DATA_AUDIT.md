# H5-v2 — Multiseries Data Audit

**Experiment:** `QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V2_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE`
**Date:** 2026-09-29 · **Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

## 1. Source integrity (all seven mandatory files)

| Symbol | Path | SHA256 | Rows | Range | Validation |
|---|---|---|---|---|---|
| EURUSD | `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` | `8161B866D6CFE233B5361A51DE09ACFE9E9B8926D400EE09751DA8E65CA6550B` | 48,186 | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | PASS |
| GBPUSD | `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` | `984C014AFA960A66ACB4BF855DD3DB1AFB81A685929B257396A6DC1D52798D09` | 48,191 | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | PASS |
| USDJPY | `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.csv` | `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858` | 48,191 | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | PASS |
| USDCHF | `ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv` | `A25CBF3D0BF96C0A16FF41E9B157BBFFB1F94D8F268A16E5DD797D98F7134DFB` | 48,191 | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | PASS |
| USDCAD | `ml-signal-service/data/raw/mt5/H1/USDCAD_H1.csv` | `EF32C40422F4F45687E7A7E876E0F5F3F7E17F2CF2FF728D25D17DDA31BF2F31` | 48,162 | `2019-01-02 07:00:00` → `2026-09-29 21:00:00` | PASS |
| AUDUSD | `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv` | `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` | 48,116 | `2019-01-02 00:00:00` → `2026-09-24 18:00:00` | PASS |
| NZDUSD | `ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv` | `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` | 48,087 | `2019-01-02 07:00:00` → `2026-09-24 18:00:00` | PASS |

Validation (all PASS): `datetime`+`close` present; ≥2 rows; no null/duplicate labels; strictly
ascending lexical labels; numeric finite strictly-positive closes.

## 2. USDJPY-specific integrity assertion

| Condition | Result |
|---|---|
| SHA256 == `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858` | **PASS** |
| Schema == `datetime,open,high,low,close,volume` | **PASS** |
| Final label == `2026-09-29 21:00:00` | **PASS** |

## 3. Strict seven-way construction

- Raw strict seven-way intersection count: **48,029**
- Unmatched counts: EURUSD 157 · GBPUSD 162 · USDJPY 162 · USDCHF 162 · USDCAD 133 · AUDUSD 87 · NZDUSD 58
- First / maximum common label: `2019-01-02 07:00:00` / `2026-09-24 18:00:00`
- Excluded exactly one label — the maximum common label; no other label removed.

## 4. Excluded maximum common label

**`2026-09-24 18:00:00`** (exclusion count = 1). (The panel is bounded by AUDUSD/NZDUSD, which end
`2026-09-24 18:00:00`.)

## 5. Frozen snapshot

| Field | Value |
|---|---|
| Path | `h5_v2_multiseries_h1_internal_snapshot.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_7WAY_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Schema | `internal_index_k, timestamp_label_internal, eurusd_close, gbpusd_close, usdjpy_close, usdchf_close, usdcad_close, audusd_close, nzdusd_close` |
| Rows (T) | **48,028** |
| First label | `2019-01-02 07:00:00` |
| Last retained label | `2026-09-24 17:00:00` |
| SHA256 | `751EE1647D54E5402C762141DB8D8B547118C9825BDCBFB988F48F2DDA8B2588` |

## 6. Clock declaration

`internal_index_k = 1..T` is an ordinal internal clock; labels are `NOT_UTC` — opaque ordinals, not
parsed, not localized, no session/calendar/market-close inference.

## 7. No-prohibited-work statement

No imputation, interpolation, resampling, transformation, or external joins; no statistics, costs,
PnL, signals, backtests, ML, or trading activity; no MT5, broker, credentials, network, calendar, or
external access in this freeze.
