# G1-R3 — Controlled Epoch Timestamp Probe Report

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Stage:** `G1R3_CONTROLLED_EPOCH_TIMESTAMP_PROBE`

---

## 1. Scope and no-trading declaration

Narrow, read-only technical provenance probe. It determines whether raw epochs returned by the
current local MT5 Python API are consistent with UTC, whether the prior ~1 h discrepancy was a
local-conversion / bar-selection artifact, or whether a broker/terminal time anomaly remains. No
hypothesis test; no G2–G6; no cost/return/correlation/cointegration/ADF/Johansen/hedge-ratio
calculation; no signal/model/backtest/trading action. No secrets, account IDs, server identifiers,
or terminal paths were printed or stored.

## 2. Adapter path and static read-only guard

- Adapter: `quant-personal-fund/audits/mt5_readonly/g1r3_epoch_timestamp_probe.py`
  (`READ_ONLY_ONLY = True`, script version `g1r3-1`, sha256[:16] `13556cbc7098530d`).
- **Static guard passed** before `mt5.initialize()`: the source contains none of the forbidden
  trading tokens (assembled from split literals). Script-only; never imported by the research
  library; writes only inside the experiment folder.

## 3. MT5 initialization result (redacted)

**Succeeded** (`read_only: true`, `errors: []`); terminal connected, build 6230. No login/server/
terminal path emitted.

## 4. System UTC capture protocol

For each query group the adapter captured `datetime.now(timezone.utc)` before and after plus
`time.time()`. Reference system UTC for the whole run: **`2026-09-29T20:24:35Z`**
(epoch `1790713475.34`). Local naive time is recorded only as
`local_time_diagnostic_only` and was never used as a reference.

## 5. H1 raw epoch observations (per symbol)

`copy_rates_from_pos(symbol, TIMEFRAME_H1, 0, 2)` — raw epochs and canonical UTC conversions
(identical for EURUSD and GBPUSD):

| result_index | raw_time_epoch | canonical UTC | local diagnostic only |
|---|---|---|---|
| 0 | `1790719200` | `2026-09-29T22:00:00Z` | `2026-09-29T17:00:00` |
| 1 | `1790722800` | `2026-09-29T23:00:00Z` | `2026-09-29T18:00:00` |

Status: `CURRENT_OR_POSSIBLY_FORMING` (index 0) and `PRIOR_COMPLETED_CANDIDATE` (index 1) as
labeled by the adapter. **Observed ordering caveat:** the two returned epochs are 22:00 and 23:00;
interpreting the 23:00 element as the current forming bar (consistent with the tick below) implies
the returned array is oldest→newest and the *newest* element is the current bar. `h1 position-0
offset vs UTC hour-floor` computed by the adapter = **7200 s (+2 h)** for the index-0 element.

## 6. Tick timestamp observations (per symbol)

`symbol_info_tick(symbol)` — one call each, system UTC captured around it:

| symbol | raw tick epoch | canonical UTC | tick − query epoch | bid/ask present |
|---|---|---|---|---|
| EURUSD | `1790724264` | `2026-09-29T23:24:24Z` | **+10788 s (≈ +3:00)** | true / true |
| GBPUSD | `1790724269` | `2026-09-29T23:24:29Z` | **+10793 s (≈ +3:00)** | true / true |

Both ticks lie **~3 hours ahead** of system UTC → freshness `STALE_OR_NOT_COMPARABLE` under the
120 s window. This is consistent with the terminal reporting **server time ≈ UTC+3**, not UTC.

## 7. Bounded recent-tick retrieval results

`copy_ticks_from(symbol, now−5min, 50, COPY_TICKS_ALL)`:

| symbol | window from | count | first raw epoch | last raw epoch | last − query | freshness |
|---|---|---|---|---|---|---|
| EURUSD | `2026-09-29T20:19:35Z` | 50 | `1790713177` | `1790713224` | −251 s | STALE_OR_NOT_COMPARABLE |
| GBPUSD | `2026-09-29T20:19:35Z` | 50 | `1790713175` | `1790713233` | −242 s | STALE_OR_NOT_COMPARABLE |

**Important:** these epochs convert ~1 minute after the requested UTC window start (20:19:35 →
20:20:24), i.e. they are **UTC-consistent** with the window — *inconsistent* with the +3 h seen
from `symbol_info_tick`/rates. The `last − query` values (−~250 s) are an artifact of the 50-tick
cap (the retrieval stopped ~1 min into the window), not evidence of a 3 h offset. No tick CSV was
written.

## 8. Canonical UTC vs local diagnostic conversion

- Canonical: `datetime.fromtimestamp(epoch, timezone.utc)` and
  `datetime.utcfromtimestamp(epoch).replace(tzinfo=timezone.utc)` — **identical** for every epoch.
- Local diagnostic: `datetime.fromtimestamp(epoch)` (machine local, UTC−5) — shown only to
  demonstrate that the local rendering is NOT the origin of the discrepancy.

So a local naive-conversion/formatting error alone does not explain the +3 h: the **raw integer
epochs themselves** are ahead of system UTC for the tick and rates queries.

## 9. Official-documentation claim vs observed current sample

- **Claim** (MQL5 `copy_rates_from` doc): "Data received from the MetaTrader 5 terminal has UTC
  time… MT5 stores tick and bar open time in UTC (without the shift)." (`G1R2_PUBLIC_TIMEZONE_EVIDENCE.md`.)
- **Observed:** `symbol_info_tick` and `copy_rates_from_pos` epochs are ~+3 h vs the machine's UTC;
  `copy_ticks_from` over a UTC window returned UTC-consistent epochs. The claim is **not confirmed**
  by this sample and is **internally inconsistent** across query types.

## 10. Controlled outcome classification

**`BROKER_OR_TERMINAL_TIME_ANOMALY_UNRESOLVED`.**

Raw tick/rates epochs are persistently ahead of system UTC (~3 h) and cannot be reconciled with the
UTC claim or with the UTC-consistent `copy_ticks_from` window. Not `UTC_CONFIRMED…` (the raw epochs
are not contemporaneous with system UTC), not `LOCAL_CONVERSION_ERROR_IDENTIFIED` (canonical vs
local conversion are both correct; the raw epochs themselves differ), not
`INSUFFICIENT_CURRENT_TICK_EVIDENCE` (ticks were returned).

**Alternative hypothesis (not excluded):** the discrepancy could be a **local system-clock skew**;
the probe compares MT5 against the same machine clock, so it cannot fully distinguish
"broker server time" from "local clock error" without an independent time reference (none was
authorized).

## 11. Implication for historical CSV timestamp interpretation

If the historical CSVs were produced from the same MT5 rates path, their `datetime` labels would
inherit the same **server-time** basis (~UTC+3), i.e. **not UTC** — contradicting the exporter's
"UTC" declaration. (The earlier observation that the CSV's last bar read `19:00` while exported
near `19:12Z` remains an additional inconsistency.) The historical basis therefore remains
**`CONSISTENT_WITH_CURRENT_MT5_SEMANTICS`**, not `PROVEN_…`, and is server-time, not UTC.

## 12. Implication for the G1 decision

**G1 remains `G1_PAUSE`.** The probe did **not** confirm a UTC basis and instead produced direct
evidence *against* it; the frozen `G1_PASS` condition ("server offset/DST documented, or raws proven
UTC") is unmet. `G1_STOP` is not warranted: the conflict is bounded and EURUSD/GBPUSD share one
basis (an internally synchronized study remains possible). No conclusion is drawn about
tradability, cointegration, or economic viability.

## 13. Explicit non-computations and remaining prohibitions

No returns, price changes, spreads, correlations, covariance, cointegration, ADF, Engle-Granger,
Johansen, hedge ratio, half-life, variance ratio, Hurst, cost, margin, PnL, alpha, signal, model,
ML, LLM, backtest, or portfolio quantity was computed. No historical market-data retrieval beyond
the bounded 2-bar / 50-tick probe; no tick CSV; no order/execution/demo/shadow/live action. G2–G6
remain unauthorized.

## Artifacts

- `G1R3_EPOCH_PROBE_REDACTED.json` (machine-readable diagnostic)
- `G1R3_DECISION.md`
- `data_manifest_v1.yaml` (updated: `g1r3_*` fields)
- `RUN_LOG.md` (appended)
