# G1-R Decision — MT5 Metadata & Provenance Remediation

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G1R_MT5_METADATA_PROVENANCE_REMEDIATION`
**Result:** `G1_PAUSE`

---

## Decision-rule mapping (frozen G1 conditions)

`G1_PASS` requires acceptable source provenance, **known price semantics**, a **known canonical
timezone conversion**, completed-bar semantics, adequate aligned coverage, and no material
unresolved integrity defect. G1-R resolved symbol mapping, metadata, bid/ask (ticks), spread
(bars), and completed-bar semantics — but the **source/server timezone and UTC offset remain
`UNRESOLVED`**, so canonical timezone conversion cannot be documented. Historical price semantics
are `CONSISTENT_WITH_CURRENT_MT5_SEMANTICS` only, not `PROVEN`. Hence `G1_PASS` is not met and
`G1_STOP` is not warranted.

## Resolved limitations

- Broker symbol mapping: EURUSD → `EURUSD`, GBPUSD → `GBPUSD` (`CONFIRMED_FOR_CURRENT_MT5_SAMPLE`).
- Symbol/contract metadata captured (digits, point, tick size, contract size, volume min/max/step,
  trade mode, current spread points, swaps, rollover3days, currencies).
- Bid/ask available in the current MT5 tick feed; H1 bars carry a `spread` (points) field.
- Completed-bar semantics: `copy_rates_from_pos(start_pos=1)` excludes the forming bar.

## Unresolved limitations

- **Source/server timezone, UTC offset, and DST: `UNRESOLVED`** (not exposed by the read API;
  historical CSV timezone must not be inferred from current samples).
- Historical CSV price semantics: `CONSISTENT_WITH_CURRENT_MT5_SEMANTICS` (not `PROVEN_HISTORICAL_EXPORT_SEMANTICS`).
- No formal historical export manifest/procedure.
- Minor EURUSD H1 mismatch (1 of 493 aligned bars) in the current-sample comparison.

## Artifact list

- `G1R_MT5_METADATA_REPORT.md`
- `audit_mt5_run_summary_redacted.json`
- `audit_mt5_symbol_metadata_redacted.json`
- `audit_mt5_h1_sample_EURUSD.csv`
- `audit_mt5_h1_sample_GBPUSD.csv`
- `audit_mt5_tick_sample_redacted.csv`
- `data_manifest_v1.yaml` (updated)
- `RUN_LOG.md` (appended)

## Authorization consequence

- `G1_PAUSE` authorizes **no G2–G6 work** and no hypothesis/cost/statistical/backtest activity.
- Only a separately authorized remediation targeting the outstanding **timezone/UTC-offset**
  evidence (or a formally documented export procedure) could move this toward `G1_PASS`.

## Declaration

No hypothesis test, cost, return, correlation, cointegration, ADF/Johansen, hedge-ratio,
variance-ratio, signal, model, backtest, order, demo, shadow, or live action occurred. No secret,
account identifier, server identifier, or terminal path was printed or persisted.
