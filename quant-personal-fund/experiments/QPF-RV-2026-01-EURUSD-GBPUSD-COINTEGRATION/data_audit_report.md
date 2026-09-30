# G1 Data Audit Report

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Stage:** `G1_DATA_AUDIT`
**Result:** `G1_PAUSE`

---

## 1. Scope and prohibition statement

This report records the **descriptive** G1 data audit of already-downloaded local files. It is
read-only and descriptive. No MT5, broker, credential, `.env`, network, or external access
occurred. No returns, correlation, cointegration, ADF, Johansen, hedge ratio, half-life, variance
ratio, Hurst, cost, alpha, signal, or backtest was computed. No data was modified, moved, renamed,
deduplicated, reformatted, or created inside the authorized locations.

This report uses only findings produced during the immediate read-only inspection; no new
inspection was performed for this persistence task.

## 2. Authorized locations

```text
ml-signal-service\data\raw
ml-signal-service\data\raw\macro
```

`ml-signal-service\data\raw\macro` is a **nested** subdirectory of `ml-signal-service\data\raw`;
it was inventoried as a distinct category (context/metadata only) without duplicating file-level
results from the parent inventory.

## 3. Inventory classification

| Category | Contents |
|---|---|
| `PRIMARY_G1_EVIDENCE` | `ml-signal-service\data\raw\mt5\H1\EURUSD_H1.csv`, `...\GBPUSD_H1.csv` |
| `MACRO_CONTEXT_ONLY` | all files under `macro\` (calendar + MERG event-anatomy) |
| `OUT_OF_SCOPE` | other `mt5\H1` instruments (inventoried only) |

Authorized-location census: **34 files, ≈57.0 MB total — 33 CSV + 1 XLSX**. No manifest, README,
extraction metadata, or source-provenance document exists anywhere under the authorized locations.

## 4. EURUSD / GBPUSD evidence table

| Check | EURUSD_H1.csv | GBPUSD_H1.csv |
|---|---|---|
| Path | `ml-signal-service\data\raw\mt5\H1\EURUSD_H1.csv` | `ml-signal-service\data\raw\mt5\H1\GBPUSD_H1.csv` |
| Schema | `open,high,low,close,volume,datetime` | `open,high,low,close,volume,datetime` |
| Rows | 48,184 | 48,189 |
| Coverage | 2019-01-02 00:00 → 2026-09-29 19:00 | 2019-01-02 00:00 → 2026-09-29 19:00 |
| Duplicate timestamps | 0 | 0 |
| Strictly monotonic | true | true |
| Nulls | 0 | 0 |
| OHLC integrity | all checks pass | all checks pass |
| Volume | min 1, max 75,410, zero-volume 0 | min 2, max 88,929, zero-volume 0 |
| Intraday gaps (1–24 h) | 0 | 0 |
| Gaps ≥ 24 h | 410 (~49 h dominant) | 410 (~49 h dominant) |
| SHA256 | `AFC3109108AE64E59800F99D4B87A11B58B26EDE5185DCBD3B132422E4F3DA5F` | `11D9D435C1DDBC4A797BDF236ED3F3F13765338D2AD21870268016F76FD24CB7` |

## 5. Per-instrument quality checks

- **Schema validation:** PASS — six expected fields present in both files.
- **Monotonic timestamps:** PASS — strictly increasing in both.
- **Duplicate timestamps:** PASS — none in either file.
- **Null fields:** PASS — none.
- **OHLC integrity:** PASS — `high >= max(open, close)`, `low <= min(open, close)`,
  `high >= low`, all prices positive.
- **Volume:** PASS — no zero-volume rows; volume is tick-volume.
- **Intraday gaps:** PASS — zero gaps in the 1–24 h band for both instruments.
- **Long-gap classification:** PASS/expected — all 410 gaps ≥ 24 h are consistent with
  weekend/holiday closures (~49 h dominant).

## 6. Cross-instrument alignment

| Metric | Value |
|---|---|
| Union timestamps | 48,189 |
| Intersection timestamps | 48,184 |
| EURUSD-only timestamps | 0 |
| GBPUSD-only timestamps | 5 |
| GBPUSD-only times | 2026-09-25 19:00–23:00 (Friday evening) |
| First / last timestamps | identical |
| Alignment | ≈ 99.99% |

No forward-fill, interpolation, deletion, repair, or transformation was performed. The five
unmatched GBPUSD Friday-evening bars are a **minor completeness discrepancy** and must be
**excluded**, not filled, in any future synchronized dataset. Note: this is a **structural**
alignment statement only — see §7 (UTC conversion was not run).

## 7. Provenance, price semantics, timezone, completion, and bid/ask gaps

1. **Price semantics are unknown.** The files have OHLC but no declaration of bid, ask, mid, or
   last. Under the frozen G1 contract, unknown price semantics prevent `G1_PASS`.
2. **Bid/ask, tick data, and spread fields are unavailable locally.** `volume` is tick-volume only;
   this dataset cannot provide G2 execution-cost evidence.
3. **Timestamps are naive.** MT5/server timezone, UTC-offset history, and DST convention are
   undocumented.
4. **Bar-completion semantics are unknown.** The final `2026-09-29 19:00` bar may be
   forming/incomplete and cannot be treated as completed without later verification.
5. **Provenance is undocumented.** No source broker/vendor, source symbol/alias, extraction
   method, requested/received-range declaration, or manifest exists.

## 8. Macro context-only inventory and encoding note

- 20 `EconomicCalendarEvents-2007…2026.csv` files with fields
  `Id,Date,Time,Name,Impact,Currency,Actual,Deviation,Consensus,Previous,Sentiment`, `MM/DD/YYYY`
  dates, and no timezone field.
- `ExportedData.csv` and `ExportedData.xlsx` — MERG event-candle-anatomy datasets
  (`event,time,tWick*/body*/bWick*…,target*`).
- **Encoding note:** macro files contain a minor mojibake anomaly (examples `â€™`, `â€“`).
- All macro material is `MACRO_CONTEXT_ONLY`; it was not used for any event, return, direction,
  or signal calculation.

## 9. G1 decision and decision-rule mapping

**Decision: `G1_PAUSE`.**

Maps to the frozen `G1_PAUSE` rule: potentially usable data exists, but required evidence for
`G1_PASS` is missing — explicit **price semantics**, **source/server timezone and bar-completion
declaration**, a **provenance manifest**, and **bid/ask availability**. These deficiencies are
potentially remediable through a separately authorized read-only MT5 metadata/provenance query,
so `G1_STOP` (fundamentally unusable / irreconcilable) is **not** warranted.

- `G1_PAUSE` does **not** authorize G2, G3, G4, G5, G6, modeling, signals, backtesting, shadow,
  demo, or live activity.
- The only candidate next phase is a separately authorized **`G1-R`** remediation task focused on
  read-only MT5 metadata/provenance and bounded samples.
- No decision about tradability, cointegration, stationarity, mean reversion, economic viability,
  or execution has been made.

## 10. Explicit non-computations

No returns, log-returns, correlation, cointegration, ADF, Engle-Granger, Johansen, hedge ratio,
half-life, variance ratio, Hurst exponent, cost, spread-cost, alpha, signal, portfolio, or
backtest quantity was computed. No forward-fill or transformation was applied.

## 11. G1-R remediation requirements

A separately authorized `G1-R` task should obtain, read-only and with bounded samples:

- documented MT5 rates/price semantics (bid / ask / mid / last) for EURUSD and GBPUSD;
- source/server timezone and UTC-offset/DST convention, and a canonical-UTC conversion declaration;
- bar-completion semantics (completed bars only; exclude the forming bar);
- a versioned provenance manifest (broker/vendor, source symbol/alias, extraction method,
  requested/received ranges, checksums);
- bid/ask or documented spread evidence for G2.

## Related artifacts

- `data_quality_checks.csv`
- `data_manifest_v1.yaml`
- `G1_DECISION.md`
- `G0_G1_DESIGN_SPEC.md`
- `READ_ONLY_RESEARCH_ACCESS_AUTHORIZATION.md`
