# H4-C2 — Data Audit (EURUSD/USDCHF internal-clock snapshot v1)

**Experiment:** `QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP`
**Stage:** `H4_C2_IMMUTABLE_SNAPSHOT_FREEZE`
**Date:** 2026-09-29 · **Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

## 1. Raw sources

| Instrument | Path | SHA256 (uppercase) | Schema | Rows | First label | Last label |
|---|---|---|---|---|---|---|
| EURUSD | `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` | `8161B866D6CFE233B5361A51DE09ACFE9E9B8926D400EE09751DA8E65CA6550B` | `open,high,low,close,volume,datetime` | 48,186 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` |
| USDCHF | `ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv` | `A25CBF3D0BF96C0A16FF41E9B157BBFFB1F94D8F268A16E5DD797D98F7134DFB` | `open,high,low,close,volume,datetime` | 48,191 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` |

## 2. Validation (per raw file)

Required columns present (`datetime`, `close`); no null labels; no duplicate labels; strictly
ascending lexical labels; numeric finite strictly-positive closes; ≥ 2 rows. **Both PASS.**

## 3. Strict-intersection construction

- Raw strict-intersection count: **48,186**
- Unmatched — EURUSD-only: **0**; USDCHF-only: **5** (excluded through the intersection)
- Sorted lexicographically ascending; excluded exactly one label — the **maximum common label**.
- **`excluded_max_common_label` = `2026-09-29 21:00:00`** (exclusion count = 1)
- No other label/row removed; no imputation, interpolation, resampling, or transformation.

## 4. Frozen snapshot

| Field | Value |
|---|---|
| Path | `eurusd_usdchf_h1_internal_snapshot_v1.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Columns | `internal_index_k, timestamp_label_internal, eurusd_close, usdchf_close` |
| Rows (T) | **48,185** |
| First label | `2019-01-02 00:00:00` |
| Last retained label | `2026-09-29 20:00:00` |
| SHA256 | `67590790F8BF0E20A707792D8DE85077C6D1067BD45035B05744D5D235E1DBF6` |

## 5. Clock declaration

`internal_index_k = 1..T` is an ordinal internal clock; labels are **`NOT_UTC`** — opaque ordinals,
not parsed, not localized, no session/weekday/calendar/market-close inference.

## 6. No-prohibited-work statement

No imputation, interpolation, resampling, or transformation; no external joins; no statistics, costs,
PnL, signals, backtests, ML, or trading activity; no MT5, broker, credentials, network, or external
access.
