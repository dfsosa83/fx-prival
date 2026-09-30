# H5-v1 — Multiseries Data Audit

**Experiment:** `QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V1_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE`
**Date:** 2026-09-29 · **Clock:** `INTERNAL_ORDINAL_NOT_UTC`

---

## 1. Per-instrument raw sources

| Instrument | Path | SHA256 (uppercase) | Required schema | Rows | First label | Last label | Validation |
|---|---|---|---|---|---|---|---|
| EURUSD | `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` | `8161B866D6CFE233B5361A51DE09ACFE9E9B8926D400EE09751DA8E65CA6550B` | `datetime, close` | 48,186 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | PASS |
| GBPUSD | `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` | `984C014AFA960A66ACB4BF855DD3DB1AFB81A685929B257396A6DC1D52798D09` | `datetime, close` | 48,191 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | PASS |
| USDJPY | `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.csv` | `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC` | `datetime, close` | 47,152 | `2019-01-02 00:00:00` | `2026-07-30 14:00:00` | PASS |
| USDCHF | `ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv` | `A25CBF3D0BF96C0A16FF41E9B157BBFFB1F94D8F268A16E5DD797D98F7134DFB` | `datetime, close` | 48,191 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | PASS |
| USDCAD | `ml-signal-service/data/raw/mt5/H1/USDCAD_H1.csv` | `EF32C40422F4F45687E7A7E876E0F5F3F7E17F2CF2FF728D25D17DDA31BF2F31` | `datetime, close` | 48,162 | `2019-01-02 07:00:00` | `2026-09-29 21:00:00` | PASS |
| AUDUSD | `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv` | `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` | `datetime, close` | 48,116 | `2019-01-02 00:00:00` | `2026-09-24 18:00:00` | PASS |
| NZDUSD | `ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv` | `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` | `datetime, close` | 48,087 | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` | PASS |

Validation per file (all PASS): `datetime` and `close` present; ≥2 rows; no null labels; no duplicate
labels; strictly ascending lexical labels; numeric finite strictly-positive closes.

**Note:** USDJPY ends at `2026-07-30 14:00:00`; the seven-way intersection is therefore truncated by
that series (the panel ends `2026-07-30`). This is a data-staleness observation only, recorded for the
later freeze/screen governance; not a failure.

## 2. Strict seven-way intersection

- Raw strict seven-way intersection count: **47,065**
- Unmatched counts relative to the seven-way intersection: EURUSD **1,121**, GBPUSD **1,126**,
  USDJPY **87**, USDCHF **1,126**, USDCAD **1,097**, AUDUSD **1,051**, NZDUSD **1,022**.
- Sorted lexicographically ascending; excluded exactly **one** label — the **maximum common label**.

## 3. Excluded maximum common label

**`2026-07-30 14:00:00`** (exclusion count = 1). No other common label removed.

## 4. Frozen snapshot

| Field | Value |
|---|---|
| Path | `h5_v1_multiseries_h1_internal_snapshot.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_7WAY_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Schema | `internal_index_k, timestamp_label_internal, eurusd_close, gbpusd_close, usdjpy_close, usdchf_close, usdcad_close, audusd_close, nzdusd_close` |
| Rows (T) | **47,064** |
| First label | `2019-01-02 07:00:00` |
| Last retained label | `2026-07-30 13:00:00` |
| SHA256 | `F0B6DBB5EFB67F74DD12C626B117124904E739C86F5DC29C41514EC2CB6E59C8` |

## 5. Clock declaration

`internal_index_k = 1..T` is an ordinal internal clock; labels are **`NOT_UTC`** — opaque ordinals,
not parsed, not localized, no session/weekday/calendar/event/market-close inference.

## 6. No-prohibited-work statement

No imputation, interpolation, resampling, transformation, external joins, market statistics, cost/PnL
analysis, signals, backtesting, ML, or trading occurred; no MT5, broker, credentials, network,
calendar, or external access.
