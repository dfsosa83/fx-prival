# H6 — Single-Instrument Snapshot Freeze Report

**Stage:** `H6_SINGLE_INSTRUMENT_IMMUTABLE_SNAPSHOT_FREEZE`
**Experiment:** `QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE`
**Parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Date:** 2026-09-30 · **Clock:** internal ordinal only (`NOT_UTC`)
**Result:** `H6_SNAPSHOTS_FROZEN_PENDING_SEPARATE_H6_SCREEN`

---

## 1. Scope and method

Data-preparation only. For each of the seven H6 instruments, verify the raw source schema/integrity,
read only `datetime` + `close`, build a **single-instrument close-only snapshot**, **exclude exactly the
maximum available label**, and write a hash-locked snapshot + SHA256. No H6 events, no statistics, no
costs/PnL, no backtest/trading, no MT5/broker/network.

Banner written as the first snapshot line:
`# INTERNAL_CLOCK_ONLY; NOT_UTC; SINGLE_INSTRUMENT; EXCLUDE_MAX_AVAILABLE_LABEL; NO_COSTS; NO_TRADING_USE`.

**Governance note:** the frozen continuity rule named this a **one-instrument-per-stage** action;
at the owner's explicit direction this stage freezes **all seven** instruments in one stage, each as a
separate single-instrument snapshot. FX and XAUUSD remain **separate strata**.

## 2. Frozen snapshots

| Symbol | Raw schema | Raw rows | Excluded max label | Snapshot rows | First label | Last retained label | Snapshot SHA256 |
|---|---|---|---|---|---|---|---|
| EURUSD | legacy | 48,204 | `2026-09-30 15:00:00` | 48,203 | `2019-01-02 00:00:00` | `2026-09-30 14:00:00` | `425EAB8E…89BA60` |
| USDJPY | canonical | 48,191 | `2026-09-29 21:00:00` | 48,190 | `2019-01-02 00:00:00` | `2026-09-29 20:00:00` | `543C4FC7…E6F0` |
| USDCHF | legacy | 48,209 | `2026-09-30 15:00:00` | 48,208 | `2019-01-02 00:00:00` | `2026-09-30 14:00:00` | `9D57303C…21847` |
| USDCAD | legacy | 48,180 | `2026-09-30 15:00:00` | 48,179 | `2019-01-02 07:00:00` | `2026-09-30 14:00:00` | `68BFAA13…EEADB` |
| AUDUSD | canonical | 48,116 | `2026-09-24 18:00:00` | 48,115 | `2019-01-02 00:00:00` | `2026-09-24 17:00:00` | `52B4E3BE…E54931` |
| NZDUSD | canonical | 48,087 | `2026-09-24 18:00:00` | 48,086 | `2019-01-02 07:00:00` | `2026-09-24 17:00:00` | `652997D6…D799B` |
| XAUUSD | canonical | 45,809 | `2026-09-30 14:00:00` | 45,808 | `2019-01-02 01:00:00` | `2026-09-30 13:00:00` | `3DB0C3CC…067F0D` |

Each snapshot: columns `internal_index_k, timestamp_label_internal, <sym>_close`; stored under
`snapshots/<SYMBOL>/<sym>_h1_internal_snapshot_v1.csv` with a companion `.sha256`. Full raw hashes and
exact labels are in `data_manifest_h6.yaml`.

## 3. Validation

Raw sources validated (recognized canonical/legacy schema; `datetime`+`close`; no null/duplicate labels;
strictly ascending; finite strictly-positive close). Output row count equals `raw rows − 1` (one maximum
label excluded). No errors were recorded.

## 4. No-computation statement

No prices, returns, volatility, ranges, breakout/invalidation events, correlations, regressions, ADF,
AR/OU, variance ratios, bootstrap, outcomes, costs, PnL, backtests, signals, strategies, ML, or trading
metrics were computed. No MT5/downloader/broker/network/calendar/external access. Labels are opaque
ordinals (`NOT_UTC`).

## 5. Recommendation

```text
H6_SNAPSHOTS_FROZEN_PENDING_SEPARATE_H6_SCREEN
```
