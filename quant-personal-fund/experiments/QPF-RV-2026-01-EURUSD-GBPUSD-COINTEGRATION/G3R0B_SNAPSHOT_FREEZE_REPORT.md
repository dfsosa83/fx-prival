# G3-R0b — Snapshot Freeze Report (v3)

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Stage:** `G3R0B_COMPLETED_LABEL_BOUNDARY_REPAIR`
**Date:** 2026-09-29
**Result:** `SNAPSHOT_V3_FROZEN_PENDING_G3_V3`

---

## 1. Experiment and stage identity

Experiment `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION` (program scope `FUTURE_QPF`), stage
`G3R0B_COMPLETED_LABEL_BOUNDARY_REPAIR`.

## 2. Scope and absolute prohibition statement

Deterministic, pre-statistical boundary repair + immutable v3 snapshot freeze, internal clock only
(`NOT_UTC`). No MT5, broker, credentials, `.env`, network, external data, calendars, sessions, or
production systems; no `frival/` or `ml-signal-service` application code. No statistical or trading
calculation of any kind.

## 3. Why v3 was necessary

The v2 snapshot's fixed exclusion removed the named label `2026-09-29 19:00:00` while the strict
intersection then ended at `2026-09-29 20:00:00`, so v2 retained the **greatest common label**. v3
replaces that fixed-label rule with a deterministic **maximum-common-label exclusion**.

## 4. No statistical results observed in v1, v2, or this phase

G3-v1 failed closed at hash verification (no data parsed). No G3-v2 test was run. This phase performed
no statistical test. **No log prices, returns, spread, correlations, hedge ratio, cointegration, ADF,
Johansen, AR(1), variance ratio, bootstrap, or economic/trading result was observed.**

## 5. Old v2 exclusion vs v3 exclusion

| | Rule | Excluded label |
|---|---|---|
| v2 (G3-R0) | fixed named label | `2026-09-29 19:00:00` |
| v3 (G3-R0b) | **maximum common label** | `2026-09-29 20:00:00` |

## 6. Source paths, current hashes, schema, row counts, label ranges

| Instrument | Path | SHA256 (current) | Rows | Label range |
|---|---|---|---|---|
| EURUSD | `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` | `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` | 48,185 | 2019-01-02 00:00:00 → 2026-09-29 20:00:00 |
| GBPUSD | `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` | `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` | 48,190 | 2019-01-02 00:00:00 → 2026-09-29 20:00:00 |

Schema used: `datetime, close` only. Validation PASS (≥2 rows; no null/duplicate `datetime`; strictly
ascending labels; finite, positive numeric `close`).

## 7. Intersection count

Raw strict intersection: **48,185**.

## 8. Maximum common label removed

**`2026-09-29 20:00:00`** (exclusion count = **1**). No bar-completion/UTC/session/broker-time claim
is made; it is excluded solely by the deterministic maximum-label rule.

## 9. Unmatched count per instrument

EURUSD-only: **0**; GBPUSD-only: **5** (excluded through the intersection).

## 10. Snapshot v3 schema, row count, first/last retained label, hash

| Field | Value |
|---|---|
| Path | `g3_internal_clock_snapshot_v3.csv` |
| Header comment | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE` |
| Columns | `internal_index_k, timestamp_label_internal, eurusd_close, gbpusd_close` |
| Rows (T) | **48,184** |
| First label | `2019-01-02 00:00:00` |
| Last retained label | `2026-09-29 19:00:00` |
| SHA256 | `B372EF5B508E11A244B521C9BD7D475D05682ABEFA8A383C3372D7F56AC81448` |

## 11. v2 remains unchanged and does not authorize G3-v2

`g3_internal_clock_snapshot_v2.csv` and its `.sha256` are **not** modified; the v2 decision does
**not** authorize any G3-v2 run.

## 12. Internal-clock-only declaration

`internal_index_k = 1..T` is an ordinal clock; labels are **NOT_UTC**; nothing was parsed as a
datetime, localized, or interpreted as any named time. No external data was joined.

## 13. Prohibited work not performed

No log prices, returns, differences, spreads, hedge ratios, correlation, covariance, cointegration,
Johansen, ADF, AR(1), half-life, variance ratio, Hurst, bootstrap, costs, slippage, swaps, PnL, EV,
Sharpe, signals, positions, sizing, portfolios, ML, LLM, backtests, trades, or any trading/execution/
demo/shadow/live action. No G3-v2/G3-v3/G2/G4/G5/G6 run.

## 14. Recommendation

```text
SNAPSHOT_V3_FROZEN_PENDING_G3_V3
```

## Artifacts

- `G3R0B_COMPLETED_LABEL_BOUNDARY_AMENDMENT.md`
- `g3r0b_snapshot_freeze.py`
- `g3_internal_clock_snapshot_v3.csv`
- `g3_internal_clock_snapshot_v3.sha256`
- `data_manifest_v3.yaml`
- `G3R0B_SNAPSHOT_FREEZE_REPORT.md`
- `G3R0B_DECISION.md`
- `RUN_LOG.md` (appended)
