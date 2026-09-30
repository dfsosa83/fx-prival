# MT5 Read-Only Metadata Audit Adapter (G1-R)

**Purpose.** A standalone, script-only adapter that performs **read-only** MT5 metadata and
provenance queries for experiment `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION` (G1-R
remediation). It documents broker symbol mapping, symbol metadata, bounded completed-H1 bars,
bounded recent ticks, and timezone/completion evidence.

**Read-only scope.** The adapter uses only MT5 metadata/history query APIs (`initialize`,
`shutdown`, `terminal_info`, `account_info` for redacted context, symbol discovery, `symbol_info`,
`symbol_info_tick`, bounded `copy_rates_*`, bounded `copy_ticks_*`). It never places, modifies, or
cancels orders/positions and never changes account, terminal, broker, or production configuration.

**Prohibited APIs/actions.** No order submission or management, no trade-action requests, no
configuration/credential changes, no secret printing/persisting, no external network/API calls.
A source-level self-guard assembles the forbidden token names from split literals and refuses to
run if any appear verbatim in the script.

**Outputs.** Written only under
`quant-personal-fund/experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/` (redacted):
`audit_mt5_run_summary_redacted.json`, `audit_mt5_symbol_metadata_redacted.json`,
`audit_mt5_h1_sample_EURUSD.csv`, `audit_mt5_h1_sample_GBPUSD.csv`,
`audit_mt5_tick_sample_redacted.csv`.

**Never importable.** This adapter must **never** be imported by the research library (`core/`,
`data/pipelines/`, `signals/`, `portfolio/`, `risk/`, `backtest/`, `llm_tools/`, `monitoring/`).
It lives under `audits/`, is script-only, and is excluded from the research-library isolation scan.

**Secrets.** Credentials/terminal path are read locally only, never printed, logged, serialized,
or persisted; account and server identifiers are redacted in all outputs.
