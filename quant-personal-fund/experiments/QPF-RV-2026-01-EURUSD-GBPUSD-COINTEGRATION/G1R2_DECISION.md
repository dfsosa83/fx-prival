# G1-R2 Decision — Timezone Provenance Resolution

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G1R2_TIMEZONE_PROVENANCE_RESOLUTION`
**Decision:** `G1_PAUSE`

---

## Frozen decision-rule mapping

`G1_PASS` requires a documented server UTC-offset history and DST convention, **or** proof that the
raw timestamps are already UTC, plus completed-bar semantics and sufficient provenance. G1-R2
recovered strong Tier-1 provenance (the exporter `ml-signal-service/steps/01_download/mt5_downloader.py`
and its exact conversion), but the server offset remains **`UNRESOLVED`** and the vendor "UTC"
statement is **contradicted** by the empirical observation that the latest completed H1 bar label is
~1 hour ahead of the machine's UTC. No reproducible `timestamp_server -> timestamp_utc` conversion
exists. Hence `G1_PASS` is not met; `G1_STOP` is not warranted (the conflict is bounded and the
EURUSD/GBPUSD series share one basis).

## Evidence hierarchy conclusion

- Tier 1 (export code): **resolved** — CSV timestamps are raw MT5 bar-open values converted with
  `pd.to_datetime(unit="s", utc=True)` and tz-stripped via `strftime`; no offset shift.
- Tier 2 (local docs/config): **insufficient** — repo documents timezone as open; "UTC+2/+3" only as
  a typical-broker assumption.
- Tier 3 (official public docs): **used** — MQL5 doc says MT5 time is UTC; FP Markets page blocked
  (HTTP 403).

## Resolved limitations

- Original exporter identified with exact conversion code (previously "original exporter cannot be
  identified" → now resolved).
- Timestamps **proven** to derive directly from MT5 raw bar timestamps, with tz stripping and no
  offset conversion.
- Historical CSV vs current MT5: same basis (`CONSISTENT_WITH_CURRENT_MT5_SEMANTICS`).

## Unresolved limitations

- Broker/server **UTC offset and DST rule: `UNRESOLVED`** (vendor doc vs empirical observation
  conflict; FP Markets source unavailable).
- No reproducible historical `timestamp_server -> timestamp_utc` conversion across
  2019-01-02…2026-09-29.
- `PROVEN_HISTORICAL_EXPORT_SEMANTICS` not established (export procedure identified but its output
  was not independently validated end-to-end).
- Absolute session/event/cross-vendor alignment remains unsafe.

## Created / updated artifacts

- `G1R2_TIMEZONE_PROVENANCE_REPORT.md` (new)
- `G1R2_DECISION.md` (new)
- `G1R2_PUBLIC_TIMEZONE_EVIDENCE.md` (new; official-doc citation note)
- `data_manifest_v1.yaml` (updated: `timezone_provenance` block)
- `RUN_LOG.md` (appended)

## Authorization consequence

**`G1_PAUSE` authorizes no G2–G6 work.** Only a separately authorized remediation that documents
the broker/server offset history (or a formally documented export procedure validated end-to-end)
could move this toward `G1_PASS`.

## Declaration

No hypothesis, statistical, economic, cost, model, signal, backtest, order, demo, shadow, or live
action occurred. No new market data was retrieved. No secret, account identifier, server identifier,
or terminal path was printed or persisted.
