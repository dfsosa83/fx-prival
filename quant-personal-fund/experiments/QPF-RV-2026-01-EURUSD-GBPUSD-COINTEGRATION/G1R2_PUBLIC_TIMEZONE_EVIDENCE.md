# G1-R2 Public Timezone Evidence Note

Short citation note for official public documentation consulted during G1-R2. No credentials,
accounts, or secrets. This is a citation note only, not a webpage archive.

## Source 1 — Official MetaQuotes documentation

- **Title:** copy_rates_from — Python Integration — MQL5 Reference
- **Organization:** MetaQuotes Ltd (mql5.com)
- **URL:** https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrom_py
- **Accessed:** 2026-09-29
- **Exact claim supported** (quoted):
  > "When creating the 'datetime' object, Python uses the local time zone, while MetaTrader 5
  > stores tick and bar open time in UTC time zone (without the shift). Therefore, 'datetime'
  > should be created in UTC time for executing functions that use time. Data received from the
  > MetaTrader 5 terminal has UTC time."
- **Bearing:** This is the platform vendor's statement that MT5 Python bar/tick time is UTC. It is
  contradicted by the G1-R/G1-R2 empirical observation that the current sample's latest completed
  H1 bar label is ~1 hour ahead of the machine's UTC at retrieval (see G1R2 report §9).

## Source 2 — Broker (attempted, not captured)

- **Title/organization:** FP Markets — trading-hours help page
- **URL:** https://www.fpmarkets.com/help-center/trading-hours/
- **Accessed:** 2026-09-29
- **Outcome:** HTTP 403 (access blocked). No content captured; no claim attributed.

## Limitations

- Only official MetaQuotes documentation is cited. No forum/blog/social claims are used.
- The FP Markets server offset/DST rule is **not** established by these sources.
