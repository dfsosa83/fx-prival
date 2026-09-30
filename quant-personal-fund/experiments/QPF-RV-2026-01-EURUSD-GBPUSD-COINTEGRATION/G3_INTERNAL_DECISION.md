# G3-Internal Decision — Statistical Viability Screening

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING`
**Decision:** `PAUSE_STATISTICAL_VIABILITY`

---

## Frozen gate evaluation

| Gate item | Result |
|---|---|
| Hash verification (precondition #5) | **FAIL** (EURUSD/GBPUSD SHA256 differ from `data_manifest_v1.yaml`) |
| Intersection / exclusion rules | NOT_EVALUATED (blocked) |
| Residual ADF (val/sealed) | NOT_RUN |
| Johansen rank ≥1 (val/sealed) | NOT_RUN |
| Rolling ADF ≥60% | NOT_RUN |
| AR(1) b<0, p<0.05, finite half-life | NOT_RUN |
| Variance-ratio horizons | NOT_RUN |
| Subperiod robustness | NOT_RUN |
| Bootstrap b CI below 0 | NOT_RUN |

## Key reasons

The screening **failed closed at hash verification** before parsing any data: the two input CSVs
have been updated since the G1 audit (incremental downloader appends), so their SHA256 no longer
matches the frozen manifest. Under the frozen protocol this is a remediable precondition/
data-integrity failure → `PAUSE_STATISTICAL_VIABILITY`. No statistical test was executed, so the
cointegration/mean-reversion hypothesis is neither approved nor rejected. The first frozen run is
recorded as final; no retry or parameter change was made.

## Scope limitation

`Internal clock only; no absolute UTC/session/event alignment.`

## Authorization consequence

**PAUSE → no G4–G6 work is authorized.** Only documented remediation may be proposed — i.e. re-freeze
the exact input files, record their new hashes in a new manifest version, and re-verify before any
future frozen statistical run. A re-run of the statistical protocol requires a new explicit
task-level authorization.

## Declaration

No costs, PnL, signals, ML, backtest, shadow/demo/live, or trading action occurred. No price data
was parsed (fail-closed at the hash gate). `statistical_only: true`; `not_economic_or_tradable: true`.
