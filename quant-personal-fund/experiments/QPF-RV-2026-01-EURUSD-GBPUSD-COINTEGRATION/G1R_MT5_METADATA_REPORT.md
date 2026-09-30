# G1-R — MT5 Metadata & Provenance Remediation Report

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Stage:** `G1R_MT5_METADATA_PROVENANCE_REMEDIATION`

---

## 1. Scope and no-trading declaration

Narrow read-only remediation of the documented `G1_PAUSE` gaps: broker symbol mapping, current MT5
metadata/contract fields, bar/tick field semantics, server-time/timezone evidence, completed-bar
semantics, bid/ask and spread availability, and compatibility of the local historical CSVs with
current MT5 semantics. **No** hypothesis test, **no** G2–G6 work, **no** model, signal, backtest,
or trading activity. No order was placed, modified, or cancelled; no configuration or credential
was changed.

## 2. Adapter path and static no-trading guard

- Adapter: `quant-personal-fund/audits/mt5_readonly/g1r_mt5_metadata_audit.py` (script-only, `READ_ONLY_ONLY`).
- **Static no-trading guard passed** at runtime: the source contains none of the forbidden tokens
  (assembled from split literals and asserted before any MT5 call). The adapter uses only
  read-only metadata/history APIs and is never imported by the research library
  (`core/`, `data/pipelines/`, `signals/`, `portfolio/`, `risk/`, `backtest/`, `llm_tools/`, `monitoring/`).
- Credentials/terminal path were read locally only and neither printed nor persisted. Account and
  server identifiers are redacted in all outputs.

## 3. MT5 initialization

**Succeeded** (`read_only: true`, `errors: []`). Connected read-only to the locally running
terminal; no credentials were emitted.

## 4. Redacted terminal / account context

| Field | Value |
|---|---|
| Terminal connected | true |
| Terminal build | 6230 |
| Terminal trade_allowed | true |
| Account login | `REDACTED` |
| Account server | `REDACTED` |
| Account trade_mode | 0 (demo) |
| Account currency | USD |
| Account leverage | 30 |
| Account margin_mode | 2 |

## 5. EURUSD and GBPUSD symbol-mapping findings

| Canonical | MT5 symbol (broker alias) | Visible | Mapping status |
|---|---|---|---|
| EURUSD | `EURUSD` (no suffix/prefix) | true | `CONFIRMED_FOR_CURRENT_MT5_SAMPLE` |
| GBPUSD | `GBPUSD` (no suffix/prefix) | true | `CONFIRMED_FOR_CURRENT_MT5_SAMPLE` |

The current MT5 sample contains exact `EURUSD`/`GBPUSD` symbols. This **does not prove** the
historical CSV symbol mapping; it establishes current-sample confirmation only (`selectable` is not
exposed by the read API and is recorded as `null`).

## 6. Symbol metadata (allowed descriptive fields only)

| Field | EURUSD | GBPUSD |
|---|---|---|
| digits | 5 | 5 |
| point | 1e-05 | 1e-05 |
| trade_tick_size | 1e-05 | 1e-05 |
| trade_contract_size | 100000.0 | 100000.0 |
| volume_min | 0.01 | 0.01 |
| volume_max | 50.0 | 50.0 |
| volume_step | 0.01 | 0.01 |
| trade_mode | 4 (full) | 4 (full) |
| spread_current_points | 12 | 16 |
| swap_long | -6.47 | -2.22 |
| swap_short | 2.83 | -2.02 |
| swap_rollover3days | 3 | 3 |
| currency_base | EUR | GBP |
| currency_profit | USD | USD |
| currency_margin | EUR | GBP |

(Redacted JSON: `audit_mt5_symbol_metadata_redacted.json`. These are descriptive metadata values
captured at one instant; no cost, margin, PnL, or position-size calculation was performed.)

## 7. Bounded completed-H1 sample

- Method: `copy_rates_from_pos(symbol, TIMEFRAME_H1, start_pos=1, count=500)`. **Position 0 (the
  current forming bar) is explicitly excluded**; 500 completed bars returned per symbol.
- Returned raw fields: `time, open, high, low, close, tick_volume, spread, real_volume`
  (plus `broker_symbol, canonical_symbol, retrieval_timestamp_utc, bar_completed=true`).
- Window (server-time labels): `2026-09-01 02:00:00` → `2026-09-29 21:00:00`.
- Artifacts: `audit_mt5_h1_sample_EURUSD.csv`, `audit_mt5_h1_sample_GBPUSD.csv`.
- Note: MT5 H1 bars carry a `spread` (points) field, which the local historical CSVs do **not**.

## 8. Tick field-availability findings

- `copy_ticks_from(symbol, now−2d, 1000, COPY_TICKS_ALL)` returned 1000 ticks per symbol.
- Fields exposed: `time, bid, ask, last, volume, time_msc, flags, volume_real`.
- **Bid and ask are available in the current MT5 tick feed.** Artifact:
  `audit_mt5_tick_sample_redacted.csv` (redacted; no account/server/terminal identifiers).

## 9. Timestamp / timezone / DST evidence and uncertainties

- MT5 documents bar/tick `time` as **server time**; the read API does not expose the server UTC
  offset or DST rule.
- Observed relation (qualitative only): system UTC now `2026-09-29T19:57:11Z`, while the latest
  **completed** H1 bar is server-labelled `2026-09-29 21:00:00`. This is consistent with a server
  clock ahead of UTC, but the exact offset and DST convention **cannot be identified** from the API.
- `server_timezone_status`: **`UNRESOLVED`**.
- Per the frozen design, the historical CSV timezone must **not** be inferred from current samples.

## 10. Historical-CSV compatibility classification

**`CONSISTENT_WITH_CURRENT_MT5_SEMANTICS`.**

Comparison of the current MT5 H1 sample against the local CSV at identical naive timestamps:
EURUSD 492/493 aligned bars with equal OHLC (1 minor mismatch); GBPUSD 498/498 equal. Naive
timestamp labels match, and OHLC values agree, consistent with the local files being a prior export
of the same MT5 rates. This is **not** `PROVEN_HISTORICAL_EXPORT_SEMANTICS` (the original export
procedure is not documented), so the exact price type of the historical CSV remains formally
undeclared.

## 11. G1 limitation status after G1-R

| G1 limitation | Status |
|---|---|
| Broker symbol mapping | **RESOLVED** (`CONFIRMED_FOR_CURRENT_MT5_SAMPLE`) |
| Symbol/contract metadata | **RESOLVED** (descriptive) |
| Bid/ask & spread availability | **PARTIALLY RESOLVED** (ticks expose bid/ask; H1 bars expose `spread`; historical CSV has neither) |
| Completed-bar semantics | **RESOLVED** (position 0 excluded; forming bar identified) |
| Historical CSV vs MT5 consistency | **PARTIALLY RESOLVED** (`CONSISTENT_…`, not `PROVEN_…`) |
| Provenance | **PARTIALLY RESOLVED** (same-terminal consistent; no formal export manifest) |
| Source/server timezone & UTC conversion | **UNRESOLVED** (offset/DST not exposed by the API) |

## 12. Recommendation

**`G1_PAUSE`.** Most G1 gaps are now resolved or partially resolved, but the frozen `G1_PASS`
conditions require a **known canonical timezone conversion**, and the source/server timezone and
UTC offset remain `UNRESOLVED`. Historical price semantics are only `CONSISTENT_WITH_CURRENT_MT5_SEMANTICS`
(not `PROVEN_…`). Therefore `G1_PASS` is not met and `G1_STOP` is not warranted (no contradiction
makes the data unusable).

## 13. Explicit non-computations and remaining prohibitions

No returns, log prices, correlation, cointegration, ADF, Engle-Granger, Johansen, hedge ratio,
half-life, variance ratio, Hurst, spread statistics, cost, margin, PnL, alpha, signal, portfolio,
model, or backtest quantity was computed. No order/execution/demo/shadow/live action occurred. No
G2–G6 work is authorized.

## Artifacts

- `audit_mt5_run_summary_redacted.json`
- `audit_mt5_symbol_metadata_redacted.json`
- `audit_mt5_h1_sample_EURUSD.csv`
- `audit_mt5_h1_sample_GBPUSD.csv`
- `audit_mt5_tick_sample_redacted.csv`
- `G1R_DECISION.md`
- `data_manifest_v1.yaml` (updated)
- `RUN_LOG.md` (appended)
