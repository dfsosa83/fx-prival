# AUDUSD/NZDUSD Snapshot Freeze Report

**Experiment ID:** `QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION`
**Stage:** `G1_AUDNZD_IMMUTABLE_SNAPSHOT_FREEZE`
**Date:** 2026-09-29 · **Result:** `SNAPSHOT_FROZEN_PENDING_G3`

---

## 1. Scope

Deterministic, data-preparation-only freeze of an immutable internal-clock H1 snapshot for the
primary candidate C1 (AUDUSD/NZDUSD). Not a statistical test, economic test, backtest, signal, or
trading task.

## 2. Source data validation

| Instrument | Path | SHA256 | Rows | Schema | First → Last label |
|---|---|---|---|---|---|
| AUDUSD | `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv` | `0BF89F68…110A66` | 48,116 | `datetime,open,high,low,close,volume` | `2019-01-02 00:00:00` → `2026-09-24 18:00:00` |
| NZDUSD | `ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv` | `9707F4D0…7A85E9` | 48,087 | `datetime,open,high,low,close,volume` | `2019-01-02 07:00:00` → `2026-09-24 18:00:00` |

Validation (both PASS): required columns present; no null labels; no duplicate labels; strictly
ascending lexical order; finite numeric closes; strictly positive closes; ≥ 2 rows.

## 3. Strict-intersection construction

- Intersection count: **48,030**
- Unmatched: AUDUSD-only **86**, NZDUSD-only **57**
- Sorted lexicographically ascending; excluded exactly one observation — the **maximum common label**.

## 4. Excluded maximum common label

**`2026-09-24 18:00:00`** (exclusion count = 1). No other observation removed.

## 5. Output

| Field | Value |
|---|---|
| Snapshot | `audnzd_h1_internal_snapshot_v1.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Columns | `internal_index_k, timestamp_label_internal, audusd_close, nzdusd_close` |
| Rows (T) | **48,029** |
| First label | `2019-01-02 07:00:00` |
| Last retained label | `2026-09-24 17:00:00` |
| SHA256 | `B4F90F302C5181FBC881318910CC3904E9CB9C95CC400AF3D29FA42218E71BB2` |
| Hash file | `audnzd_h1_internal_snapshot_v1.sha256` |

## 6. Internal-clock declaration

Labels are opaque ordinal internal labels (`NOT_UTC`): not parsed as time, not localized, no
session/calendar/DST inference.

## 7. No-statistics / no-trading declaration

No log prices, price changes, returns, spreads, correlations, regressions, hedge ratios,
cointegration, ADF, Johansen, AR/OU, half-life, variance ratios, bootstrap statistics, costs,
slippage, swaps, PnL, signals, positions, ML, optimization, or backtests occurred; no MT5, broker,
credentials, network, or execution activity.

## 8. Recommendation

```text
SNAPSHOT_FROZEN_PENDING_G3
```
