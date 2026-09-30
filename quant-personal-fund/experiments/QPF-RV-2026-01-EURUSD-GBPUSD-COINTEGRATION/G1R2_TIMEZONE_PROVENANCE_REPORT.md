# G1-R2 — Timezone Provenance Report

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Stage:** `G1R2_TIMEZONE_PROVENANCE_RESOLUTION`

---

## 1. Scope and no-trading declaration

Read-only, evidence-only timezone/provenance research for the EURUSD/GBPUSD MT5 H1 CSVs. No
hypothesis test; no G2–G6 work; no cost, return, correlation, cointegration, ADF/Johansen,
hedge-ratio, variance-ratio, Hurst, signal, model, ML, LLM, backtest, or trading action. No new
market data was retrieved; no new MT5 session was opened (existing G1-R sample artifacts were
inspected only for timestamp provenance). No file outside the G1-R2 artifacts was modified.

## 2. Evidence hierarchy and sources inspected

| Tier | Source | Outcome |
|---|---|---|
| 1 | Repository export code search (`copy_rates_*`, `_H1.csv`, `to_datetime`, `tz_*`, `to_csv`) | **Exporter identified** |
| 2 | Local docs/config for server-time/offset/DST rules | Repo documents timezone as **open**; no broker offset rule |
| 3 | Official public documentation (MQL5; FP Markets attempted) | MQL5 states MT5 time is UTC; FP Markets 403 |

## 3. Tier 1 — Export-code findings

**Exporter located:** `ml-signal-service/steps/01_download/mt5_downloader.py`.

- Canonical output path matches exactly: `data/raw/mt5/{TF}/{SYMBOL}_{TF}.csv` (e.g.
  `data/raw/mt5/H1/EURUSD_H1.csv`) — lines 11–12, 103–106.
- Canonical columns: `["datetime","open","high","low","close","volume"]` — line 47 (matches the CSV
  header order).
- Retrieval: `mt5.copy_rates_range(symbol, mtf, from_dt, to_dt)` with retry — lines 132–137.
- Conversion (lines 162–166):
  - `df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)` — the raw MT5 bar-open epoch is
    labeled UTC;
  - `df = df.rename(columns={"time":"datetime","tick_volume":"volume"})`;
  - `df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")` — **timezone info is stripped**
    to a naive string.
- Write: append mode, header only on new file — line 169.
- Incremental resume: `pd.to_datetime(df["datetime"].iloc[-1], utc=True) + 1 bar` — lines 114–118.
- Docstring: "datetime (UTC, \"YYYY-MM-DD HH:MM:SS\")" — lines 7–8.

**Interpretation:** the CSVs are the raw MT5 bar-open timestamps, converted with pandas
`utc=True` (no offset shift applied) and written with the timezone stripped. The exporter *declares*
UTC; whether the underlying MT5 epoch is true UTC is the open question.

## 4. Tier 2 — Local terminal/broker documentation findings

- `project_last_state.md:214`: "Timezone unverified … Still open" (P0, unresolved).
- `frival/agents/calendar_context.py:154-155`: calendar files are "broker-time (no TZ marker) — the
  P0 timezone verification is still open."
- `ml-signal-service/docs/main/macro_event_response_eda_report.md:432-435`: event `time` has no TZ
  marker; explicitly asks "UTC, broker time (typically UTC+2/+3), or event-country local time?"
- `ml-signal-service/docs/main/exporteddata_xlsx_integration_plan_2026-08-12.md:198`: default to
  "broker time (UTC+2 winter / UTC+3 summer)" — stated as a *typical* assumption, not documentation.
- `frival/run_daily_scheduler.py:39`: `UTC_OFFSET = -5  # America/Panama (no DST)` — this is the
  **local** schedule timezone, not the broker server offset.
- `ml-signal-service/docs/main/market_entry_failure_analysis_2026-08-12.md:216-221`: a timezone key
  mismatch (`mt5.timezone` vs `market_timezone`) that silently falls back to `Asia/Qatar` — a known
  config defect, not a broker-offset statement.

**Conclusion:** local documentation **does not** establish the FP Markets server offset; it records
timezone as an open concern and offers "UTC+2/+3" only as a typical-broker assumption.

## 5. Tier 3 — Official public-source findings

- **MQL5 `copy_rates_from` docs (MetaQuotes):** "Data received from the MetaTrader 5 terminal has
  UTC time… MT5 stores tick and bar open time in UTC (without the shift)." (See
  `G1R2_PUBLIC_TIMEZONE_EVIDENCE.md`.)
- **FP Markets trading-hours page:** HTTP 403 (not captured).

## 6. Evidence-classification table (required questions)

| # | Question | Status |
|---|---|---|
| 1 | Time basis of the historical CSV `datetime` labels | `CONSISTENT_WITH_EVIDENCE` — raw MT5 bar-open time, exporter-declared UTC (tz stripped); exact UTC equivalence unresolved |
| 2 | Evidence timestamps came directly from MT5 raw bar timestamps | `PROVEN` (Tier 1 code: `copy_rates_range` → `df["time"]`) |
| 3 | Evidence of conversion / localization / tz stripping / UTC normalization during export | `PROVEN` — `utc=True` label + `strftime` strip; **no** server-offset conversion |
| 4 | Current MT5 time basis exposed by the API | `INCONSISTENT` — MQL5 doc says UTC; empirical bar label ~1 h ahead of machine UTC |
| 5 | Broker/server UTC offset and DST rule, and period | `UNRESOLVED` — not documented locally; FP Markets source blocked |
| 6 | Reproducible `timestamp_server -> timestamp_utc` conversion over 2019-01-02…2026-09-29 | `UNRESOLVED` — no documented offset history |
| 7 | Historical CSV timezone interpretation | `CONSISTENT_WITH_CURRENT_MT5_SEMANTICS` (not `PROVEN_HISTORICAL_EXPORT_SEMANTICS`) |
| 8 | Can bars be classified as completed from existing documented evidence? | `CONSISTENT_WITH_EVIDENCE` for current sample (start_pos=1 excludes forming bar); historical CSV has no completion marker |
| 9 | Remaining constraints for external-event / session / cross-vendor alignment | `UNRESOLVED` — absolute UTC offset undocumented |

## 7. Historical CSV timestamp interpretation

The CSVs are the raw MT5 bar-open timestamps, written with `unit="s", utc=True` and the timezone
stripped by `strftime`. There is no offset shift. The exporter labels them UTC; the exact UTC
correctness cannot be confirmed and is contradicted by observation.

## 8. Current MT5 timestamp interpretation

The official vendor doc says MT5 Python data is UTC. Empirically (G1-R; G1-R2 re-check of the
existing sample), the latest **completed** H1 bar label is ~1 hour ahead of the machine's UTC at
retrieval — impossible if the labels were true UTC. This conflict is **not resolved**.

## 9. Offset / DST rule, coverage, and exact limitations

- No broker offset/DST rule is documented for any period.
- The local sampler's attempt to measure offset from the tick sample was **inconclusive** (the
  bounded sample returned the *earliest* 1000 ticks of a 2-day window, ending ~42 h before
  retrieval — not usable for an offset comparison).
- Therefore no `timestamp_server -> timestamp_utc` conversion function can be declared over
  2019-01-02…2026-09-29.
- Limitations: the offset is plausibly constant (both instruments share one basis) but is **not
  documented**; DST behaviour is unknown.

## 10. Completed-bar evidence

- Current sample: `copy_rates_from_pos(start_pos=1)` excludes the forming bar — `CONSISTENT_WITH_EVIDENCE`.
- Historical CSV: no completion marker; the exporter appended bars from `copy_rates_range`, whose
  upper bound is a UTC-floored "now" — bars are treated as completed, but this is not independently
  proven for every historical row.

## 11. Implications for future external-event / session / cross-vendor alignment

Absolute session/event alignment and cross-vendor joins are **unsafe** until the server offset is
documented. An internally synchronized EURUSD/GBPUSD study (both legs on the same basis) is
plausible, but any macro/calendar or third-party alignment would carry an unknown constant offset.

## 12. Updated G1 recommendation

**`G1_PAUSE`.** Tier 1 materially improves provenance (exporter and exact conversion recovered;
timestamps proven to be raw MT5 bar-open values, tz-stripped, declared UTC). However, the frozen
`G1_PASS` condition requiring a **documented server UTC-offset history / DST rule or proof that the
raw timestamps are UTC** is **not met**: the vendor doc ("UTC") conflicts with the empirical
observation, the broker offset stays undocumented, and no reproducible historical conversion
exists. `G1_STOP` is not warranted — the conflict is bounded and the series remain internally
synchronized.

## 13. Explicit non-computations and remaining prohibitions

No returns, log-prices, correlation, cointegration, ADF, Engle-Granger, Johansen, hedge ratio,
half-life, variance ratio, Hurst, cost, margin, PnL, alpha, signal, model, ML, LLM, backtest, or
portfolio computation was performed. No order/execution/demo/shadow/live action occurred. No G2–G6
work is authorized.

## Artifacts

- `G1R2_TIMEZONE_PROVENANCE_REPORT.md`
- `G1R2_DECISION.md`
- `G1R2_PUBLIC_TIMEZONE_EVIDENCE.md`
- `data_manifest_v1.yaml` (updated)
- `RUN_LOG.md` (appended)
