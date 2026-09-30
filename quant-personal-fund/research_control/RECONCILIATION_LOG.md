# Reconciliation Log

Append-only. Records documentation-only continuity reconciliations. Do not edit prior entries.

---

## 2026-09-30 — A1_MT5_DEMO_READONLY_AUTHORIZATION_RECONCILIATION

Documentation reconciliation only. No MT5, broker, account, raw data, snapshots, source code,
network, APIs, calendar/news, execution, market computation, signals, returns, PnL, costs,
backtests or orders were accessed or performed.

### Source documents reviewed

```text
quant-personal-fund/research_control/PROJECT_HANDOFF.md
quant-personal-fund/research_control/RESEARCH_LEDGER.yaml
quant-personal-fund/research_control/NEXT_ACTION.md
quant-personal-fund/tools/raw_data_schema_rebuild/SYNTHETIC_VALIDATION_REPORT.md
quant-personal-fund/tools/raw_data_schema_rebuild/CORRECTIVE_RERUN_REPORT.md
```

Note (provenance): the stage listed two QPF-RV-2027-11 artifacts as
`A1_MT5_DEMO_ENVIRONMENT_REPORT.md` / `A1_MT5_DEMO_ENVIRONMENT_DECISION.md`. The actual artifacts on
disk are named `A1_MT5_DEMO_OBSERVATION_ENVIRONMENT_REPORT.md` /
`A1_MT5_DEMO_OBSERVATION_ENVIRONMENT_DECISION.md`. No other file was read for this reconciliation.

### Discrepancy 1 — prior wording about broker access

Earlier continuity text stated that no broker connection was authorized and that a data-source
method was not yet approved, while the QPF-RV-2027-11 stage had already validated a DEMO-only,
orders-disabled MT5 read environment (demo verified, XAUUSD available, 0 positions / 0 orders,
H1/M30/M15 + tick read OK).

**Resolution:** read-only MetaTrader 5 access to the **verified demo** environment is approved as the
A1 forward-observation data-source method, for that purpose only. It may read XAUUSD H1/M30/M15 bars
and tick data and may inspect count-only existing demo orders/positions for collision detection. It
may not create, modify, cancel or close orders/positions, access live accounts, calculate PnL, or
activate virtual fills unless a later stage explicitly authorizes those actions. Wording that treated
broker/MT5 read-only access as categorically unauthorized for the A1 observation setup was removed.

### Discrepancy 2 — 16 executed tests vs 17 required synthetic cases

The safe H1 CSV rebuild utility reports `16/16_PASS` while its validation matrix enumerates 17
required cases.

**Resolution:** 16 tests were executed and all passed; the 17 required synthetic validation cases are
covered because the two path-isolation requirements (each test path inside its own temporary
directory; no test path contains production/experiment raw paths) were combined into one executed
test. The utility's test result is unchanged (`16/16_PASS`); this is a coverage-notation
clarification only. H6 history and raw-data state are unaltered.

### Files updated

```text
quant-personal-fund/research_control/PROJECT_HANDOFF.md
quant-personal-fund/research_control/RESEARCH_LEDGER.yaml
quant-personal-fund/research_control/NEXT_ACTION.md
quant-personal-fund/research_control/RECONCILIATION_LOG.md  (created)
```

### Prohibition attestation

No order was submitted, modified, cancelled or closed; no position was opened or closed; no virtual
fill, PnL, cost analysis, backtest, demo-order pilot, live-account access or trading occurred. No
market data, MT5, broker, network, source code, statistical, economic or raw-data action occurred.

### Scope statement

This reconciliation does **not** start forward observation and does **not** authorize orders.
Forward observation remains `REQUIRES_SEPARATE_AUTHORIZATION`.
