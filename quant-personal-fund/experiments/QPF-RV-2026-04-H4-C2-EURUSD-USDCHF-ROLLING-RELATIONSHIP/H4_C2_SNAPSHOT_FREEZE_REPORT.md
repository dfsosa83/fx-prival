# H4-C2 — Snapshot Freeze Report

**Experiment:** `QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP`
**Stage:** `H4_C2_IMMUTABLE_SNAPSHOT_FREEZE` · **Date:** 2026-09-29
**Result:** `SNAPSHOT_FROZEN_PENDING_H4_C2_SCREEN`

---

## 1. Scope and data-only prohibition

Deterministic, data-preparation-only freeze of an immutable internal-clock H1 snapshot for H4
candidate C2 (EURUSD/USDCHF). No statistical/economic screen, no market statistic, no costs, PnL,
signals, entries/exits, sizing, backtest, ML, or trading/execution was performed.

## 2. Source validation and hash provenance

| Instrument | Path | SHA256 | Rows | Schema | First → Last label |
|---|---|---|---|---|---|
| EURUSD (dependent) | `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` | `8161B866…6550B` | 48,186 | `open,high,low,close,volume,datetime` | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` |
| USDCHF (hedge) | `ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv` | `A25CBF3D…134DFB` | 48,191 | `open,high,low,close,volume,datetime` | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` |

Validation (both PASS): required columns present; no null/duplicate labels; strictly ascending lexical
labels; numeric finite strictly-positive closes.

## 3. Strict-intersection construction

- Raw strict-intersection count: **48,186**
- Unmatched: EURUSD-only **0**, USDCHF-only **5**
- Sorted lexicographically ascending; excluded exactly one label — the **maximum common label**.

## 4. Excluded maximum common label

**`2026-09-29 21:00:00`** (exclusion count = 1). No other label or row removed.

## 5. Snapshot

| Field | Value |
|---|---|
| Snapshot | `eurusd_usdchf_h1_internal_snapshot_v1.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Columns | `internal_index_k, timestamp_label_internal, eurusd_close, usdchf_close` |
| Rows (T) | **48,185** |
| First label | `2019-01-02 00:00:00` |
| Last retained label | `2026-09-29 20:00:00` |
| SHA256 | `67590790F8BF0E20A707792D8DE85077C6D1067BD45035B05744D5D235E1DBF6` |
| Hash file | `eurusd_usdchf_h1_internal_snapshot_v1.sha256` |

## 6. Clock declaration

Labels are opaque ordinal internal labels (`NOT_UTC`): not parsed, not localized, no
session/weekday/calendar/market-close inference.

## 7. Prohibited work not performed

No log prices, changes, returns, spreads, correlations, OLS/regression parameters, hedge ratios,
ADF, AR(1), half-life, Johansen, variance ratios, bootstrap, costs, PnL, drawdown, Sharpe, signals,
entries/exits, sizing, backtests, ML, or trading/execution; no MT5, broker, credentials, network, or
external access; no modification of raw data, config, credentials, earlier experiments, H4 design
files, registries, or templates.

## 8. Recommendation

```text
SNAPSHOT_FROZEN_PENDING_H4_C2_SCREEN
```
