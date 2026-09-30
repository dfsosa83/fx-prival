# G1-R3 Decision — Controlled Epoch Timestamp Probe

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G1R3_CONTROLLED_EPOCH_TIMESTAMP_PROBE`
**Controlled probe outcome:** `BROKER_OR_TERMINAL_TIME_ANOMALY_UNRESOLVED`

---

## Evidence summary

- System UTC at probe: `2026-09-29T20:24:35Z`.
- `symbol_info_tick` raw epochs → canonical UTC `23:24:24Z` / `23:24:29Z` (EURUSD / GBPUSD):
  **~+3 h ahead** of system UTC.
- `copy_rates_from_pos(H1, 0, 2)` raw epochs → `22:00Z` and `23:00Z`: server-time basis
  (current forming bar aligns with a ~UTC+3 clock).
- `copy_ticks_from(now−5min, 50)` returned epochs ~1 min after the UTC window start
  (`20:19:35Z` → `20:20:24Z`): **UTC-consistent**, inconsistent with the +3 h above.
- Canonical conversions (fromtimestamp-utc and utcfromtimestamp-utc) are identical; the local
  naive conversion (UTC−5) is only diagnostic and is not the cause.

## Is the prior ~1 h discrepancy explained?

**Partly.** The raw epochs themselves are ahead of system UTC (server-time basis), so the prior
apparent offset is **not** merely a local naive-conversion or formatting artifact. However, the
observed sample is **internally inconsistent** across query types (tick/rates ~+3 h vs
`copy_ticks_from` UTC-consistent), and a **local system-clock skew** cannot be excluded because the
probe has no independent time reference. So the discrepancy is **not fully explained**.

## Implication for the historical CSV timestamp basis

The CSVs most plausibly inherit the same **server-time** (~UTC+3) basis from the MT5 rates path,
i.e. **not UTC**, contrary to the exporter's declaration. Basis remains
`CONSISTENT_WITH_CURRENT_MT5_SEMANTICS` (not `PROVEN_HISTORICAL_EXPORT_SEMANTICS`).

## Recommended G1 decision

**`G1_PAUSE`.** The frozen `G1_PASS` criteria (documented server offset/DST rule, or raws proven
UTC) are unmet, and G1-R3 produced evidence *against* a UTC basis. `G1_STOP` is not warranted —
the conflict is bounded and the two series share one basis. G1_DATA_AUDIT stays `PAUSE`; G2–G6 stay
`NOT_RUN`.

## Artifacts created / updated

- `G1R3_EPOCH_PROBE_REDACTED.json` (new)
- `G1R3_CONTROLLED_EPOCH_PROBE_REPORT.md` (new)
- `G1R3_DECISION.md` (new)
- `data_manifest_v1.yaml` (updated: `g1r3_*` fields under `timezone_provenance`)
- `RUN_LOG.md` (appended)

## Authorization consequence

`G1_PAUSE` authorizes **no G2–G6 work**. Only a separately authorized follow-up (e.g. an independent
time reference to separate broker-server-time from local-clock skew, or a documented broker
server-time rule) could move this toward `G1_PASS`.

## Declaration

No statistics, cost, correlation, cointegration, ADF/Johansen, hedge-ratio, variance-ratio, model,
signal, backtest, or order action occurred. No historical market-data retrieval beyond the bounded
probe; no tick CSV. No secret, account identifier, server identifier, or terminal path was printed
or stored.
