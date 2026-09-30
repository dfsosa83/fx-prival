# QPF-RV-2026-02 — G1 Data Audit (AUDUSD/NZDUSD internal-clock snapshot v1)

**Experiment ID:** `QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION`
**Stage:** `G1_AUDNZD_IMMUTABLE_SNAPSHOT_FREEZE`
**Date:** 2026-09-29 · **Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

## 1. Raw sources

| Instrument | Path | SHA256 (uppercase) | Rows | First label (as stored) | Last label (as stored) |
|---|---|---|---|---|---|
| AUDUSD | `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv` | `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` | 48,116 | `2019-01-02 00:00:00` | `2026-09-24 18:00:00` |
| NZDUSD | `ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv` | `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` | 48,087 | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` |

Schemas: AUDUSD `datetime,open,high,low,close,volume`; NZDUSD `datetime,open,high,low,close,volume`.

## 2. Validation (per raw file)

Required columns present (`datetime`, `close`); no null labels; no duplicate labels; strictly
ascending lexical label order; finite numeric closes; strictly positive closes; ≥ 2 rows. **Both
PASS.**

## 3. Strict intersection construction

- Strict timestamp-label intersection count: **48,030**
- Unmatched labels — AUDUSD-only: **86**; NZDUSD-only: **57** (all excluded through the intersection)
- Sort order: lexicographically ascending
- Exclusion rule: **exclude exactly the maximum common timestamp label**
- **`excluded_max_common_label` = `2026-09-24 18:00:00`** (exclusion count = 1)
- No other observation removed; no fill/interpolation/resample/dedup/normalize/transform.

## 4. Frozen snapshot

| Field | Value |
|---|---|
| Path | `audnzd_h1_internal_snapshot_v1.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Columns | `internal_index_k, timestamp_label_internal, audusd_close, nzdusd_close` |
| Rows (T) | **48,029** |
| First label | `2019-01-02 07:00:00` |
| Last retained label | `2026-09-24 17:00:00` |
| SHA256 | `B4F90F302C5181FBC881318910CC3904E9CB9C95CC400AF3D29FA42218E71BB2` |

## 5. Clock declaration

`internal_index_k = 1..T` is an ordinal internal clock; all timestamp labels are **`NOT_UTC`** —
opaque ordinals, not parsed as time, not localized, no session/calendar/DST inference.

## 6. No-statistics / no-trading statement

No log prices, price changes, returns, spreads, correlations, regressions, hedge ratios,
cointegration, ADF, Johansen, AR/OU, half-life, variance ratios, bootstrap statistics, costs,
slippage, swaps, PnL, signals, positions, ML, optimization, backtests, or trading/execution activity
occurred. No MT5, broker, credentials, or network access.
