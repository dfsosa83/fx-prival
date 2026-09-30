# G1 Decision — Data Audit

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Stage:** `G1_DATA_AUDIT`
**Decision:** `G1_PAUSE`

---

## Scope performed

Descriptive, read-only data audit of already-downloaded local files only. Findings recorded from
the completed read-only inspection; no new inspection was performed for this persistence task.

## Authorized paths inspected

```text
ml-signal-service\data\raw
ml-signal-service\data\raw\macro
```

## MT5 usage

**MT5 was not used.** No broker, credential, `.env`, network, or external access occurred.

## Artifacts created

- `data_audit_report.md`
- `data_quality_checks.csv`
- `data_manifest_v1.yaml`
- `G1_DECISION.md`
- `RUN_LOG.md` (append-only entry)

## Evidence summary

- Primary evidence: `mt5\H1\EURUSD_H1.csv` (48,184 rows) and `mt5\H1\GBPUSD_H1.csv` (48,189 rows),
  schema `open,high,low,close,volume,datetime`, coverage `2019-01-02 00:00` → `2026-09-29 19:00`.
- Quality: no duplicate timestamps, strictly monotonic, no nulls, OHLC integrity passes, volume
  non-zero; **zero** intraday gaps (1–24 h); 410 long gaps ≥ 24 h consistent with weekend/holiday
  closures.
- Cross-instrument alignment: union 48,189; intersection 48,184; EURUSD-only 0; GBPUSD-only 5
  (`2026-09-25 19:00–23:00`). Structural alignment ≈ 99.99%; the five unmatched GBPUSD bars must be
  **excluded**, not filled.
- Checksums: EURUSD `AFC3109108AE64E59800F99D4B87A11B58B26EDE5185DCBD3B132422E4F3DA5F`;
  GBPUSD `11D9D435C1DDBC4A797BDF236ED3F3F13765338D2AD21870268016F76FD24CB7`.

## Decision-rule mapping

Maps to the frozen `G1_PAUSE` rule in `G0_G1_DESIGN_SPEC.md`: potentially usable data exists, but
required evidence for `G1_PASS` is missing — explicit price semantics, source/server timezone and
bar-completion declaration, a provenance manifest, and bid/ask availability. These are potentially
remediable via a separately authorized read-only MT5 metadata/provenance query, so `G1_STOP` is
not warranted.

## Unresolved limitations

1. Price semantics unknown (no bid/ask/mid/last declaration).
2. Bid/ask, tick, and spread fields unavailable locally; `volume` is tick-volume only.
3. Timestamps naive; server timezone, UTC-offset history, and DST undocumented; UTC conversion `NOT_RUN`.
4. Bar-completion semantics unknown; final `2026-09-29 19:00` bar may be forming/incomplete.
5. Provenance undocumented (no broker/vendor, symbol/alias, extraction method, or manifest).

## Next candidate step

Only a separately authorized **`G1-R`** remediation task (read-only MT5 metadata/provenance and
bounded samples) may proceed. `G1_PAUSE` does **not** authorize G2, G3, G4, G5, G6, modeling,
signals, backtesting, shadow, demo, or live activity.

## Prohibited / unperformed work (declared)

No decision about tradability, cointegration, stationarity, mean reversion, economic viability, or
execution has been made. No MT5, credential, network, cost, return, correlation, cointegration,
ADF, Engle-Granger, Johansen, hedge-ratio, half-life, variance-ratio, Hurst, ML, LLM, signal,
backtest, shadow, demo, live, or order activity was performed.

## Evidence paths

- `data_audit_report.md`
- `data_quality_checks.csv`
- `data_manifest_v1.yaml`
- `G0_G1_DESIGN_SPEC.md`
- `READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
- `RUN_LOG.md`
