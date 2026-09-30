# H5-v1 — Snapshot Freeze Report

**Experiment:** `QPF-RV-2026-06-H5-V1-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V1_IMMUTABLE_MULTISERIES_SNAPSHOT_FREEZE` · **Date:** 2026-09-29
**Parent protocol:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM`
**Result:** `SNAPSHOT_FROZEN_PENDING_H5_V1_SCREEN`

---

## 1. Scope and data-only prohibitions

Deterministic, data-preparation-only freeze of one immutable internal-clock H1 multiseries snapshot for
H5-v1. No market statistic, log price, return, volatility, momentum, confirmation count, signal,
outcome, correlation, regression, ADF/AR-OU, variance ratio, bootstrap, cost, PnL, strategy, backtest,
ML, or trading/execution was computed. No MT5, downloader, broker, credentials, network, calendar,
news, or external access.

## 2. Source validation (all seven mandatory files)

| Instrument | SHA256 | Rows | First → Last label | Validation |
|---|---|---|---|---|
| EURUSD | `8161B866…6550B` | 48,186 | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | PASS |
| GBPUSD | `984C014A…798D09` | 48,191 | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | PASS |
| USDJPY | `BF92FF40…A4CBC` | 47,152 | `2019-01-02 00:00:00` → `2026-07-30 14:00:00` | PASS |
| USDCHF | `A25CBF3D…134DFB` | 48,191 | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | PASS |
| USDCAD | `EF32C404…BF2F31` | 48,162 | `2019-01-02 07:00:00` → `2026-09-29 21:00:00` | PASS |
| AUDUSD | `0BF89F68…110A66` | 48,116 | `2019-01-02 00:00:00` → `2026-09-24 18:00:00` | PASS |
| NZDUSD | `9707F4D0…7A85E9` | 48,087 | `2019-01-02 07:00:00` → `2026-09-24 18:00:00` | PASS |

Validation (all PASS): `datetime`/`close` present; ≥2 rows; no null/duplicate labels; strictly
ascending lexical labels; numeric finite strictly-positive closes. **USDJPY is present and valid** (its
file ends `2026-07-30 14:00:00`, which truncates the seven-way panel).

## 3. Strict seven-way intersection

- Raw strict seven-way intersection count: **47,065**
- Unmatched relative to the seven-way intersection: EURUSD 1,121 · GBPUSD 1,126 · USDJPY 87 ·
  USDCHF 1,126 · USDCAD 1,097 · AUDUSD 1,051 · NZDUSD 1,022
- Sorted lexicographically ascending; excluded exactly one label — the maximum common label.

## 4. Excluded maximum common label

**`2026-07-30 14:00:00`** (exclusion count = 1). No other common label removed.

## 5. Snapshot

| Field | Value |
|---|---|
| File | `h5_v1_multiseries_h1_internal_snapshot.csv` |
| Comment line | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_7WAY_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Schema | `internal_index_k, timestamp_label_internal, eurusd_close, gbpusd_close, usdjpy_close, usdchf_close, usdcad_close, audusd_close, nzdusd_close` |
| Rows (T) | **47,064** |
| First label | `2019-01-02 07:00:00` |
| Last retained label | `2026-07-30 13:00:00` |
| SHA256 | `F0B6DBB5EFB67F74DD12C626B117124904E739C86F5DC29C41514EC2CB6E59C8` |

## 6. Clock declaration

Labels are opaque ordinal internal labels (`NOT_UTC`); no datetime parsing, localization, or
session/calendar/market-close inference.

## 7. Prohibited work not performed

No price transformation, market statistics, costs, PnL, signals, ML, backtest, execution, MT5, broker,
credentials, network, calendar, news, or external access; no modification of raw data, parent design,
existing snapshots/manifests/registries/templates/experiments/audits.

## 8. Recommendation

```text
SNAPSHOT_FROZEN_PENDING_H5_V1_SCREEN
```
