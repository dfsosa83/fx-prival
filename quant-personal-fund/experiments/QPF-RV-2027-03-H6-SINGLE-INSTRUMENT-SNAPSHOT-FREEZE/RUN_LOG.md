# Run Log — QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — H6_SINGLE_INSTRUMENT_IMMUTABLE_SNAPSHOT_FREEZE

- **date:** 2026-09-30
- **stage:** `H6_SINGLE_INSTRUMENT_IMMUTABLE_SNAPSHOT_FREEZE`
- **status:** `preregistered`
- **parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
- **owner override:** frozen continuity named this a one-instrument-per-stage action; at the owner's
  explicit direction this stage froze **all seven** instruments (each still a separate
  single-instrument snapshot).
- **snapshots frozen (per instrument: raw schema / raw rows / excluded max label / snapshot rows / snapshot sha256):**
  - EURUSD — legacy / 48,204 / `2026-09-30 15:00:00` / 48,203 / `425EAB8EE05208051CE34C59B534E0AE84994312A585DE4FDB4877E40B89BA60`
  - USDJPY — canonical / 48,191 / `2026-09-29 21:00:00` / 48,190 / `543C4FC7CB8AD995099EDD1417EF6189A431098E8C632093A4E81FAAF523E6F0`
  - USDCHF — legacy / 48,209 / `2026-09-30 15:00:00` / 48,208 / `9D57303C8F6A45B896540B761692AFBFEE0BF7424CE8BA853D03CDAA06221847`
  - USDCAD — legacy / 48,180 / `2026-09-30 15:00:00` / 48,179 / `68BFAA1366B2D2B92B214BC99FC8CF8E59E4330CFEB57C9748E109C6040EEADB`
  - AUDUSD — canonical / 48,116 / `2026-09-24 18:00:00` / 48,115 / `52B4E3BE59058882E73081509E7A3B9FBE4CF68A37A0E366137B8EC968E54931`
  - NZDUSD — canonical / 48,087 / `2026-09-24 18:00:00` / 48,086 / `652997D6CEB409D97AC151BD470AA61DC7538D9EA8C099E81C18703909CD799B`
  - XAUUSD — canonical / 45,809 / `2026-09-30 14:00:00` / 45,808 / `3DB0C3CCEB25823CC11F655AE5690C1697E263A918F40CB4A29DBA0CB8067F0D`
- **snapshot convention:** single-instrument; columns `internal_index_k, timestamp_label_internal,
  <sym>_close`; banner `# INTERNAL_CLOCK_ONLY; NOT_UTC; SINGLE_INSTRUMENT; EXCLUDE_MAX_AVAILABLE_LABEL;
  NO_COSTS; NO_TRADING_USE`; exclude exactly the maximum available label; no imputation/transformation/
  external joins.
- **actions explicitly NOT performed:** H6 events; statistical tests; returns/volatility/ranges/
  breakout/invalidation/outcome; costs/PnL; backtest; strategy/signals/execution/trading; MT5/broker/
  credentials/network/calendar/external; modification of any raw source or prior artifact.
- **result:** `H6_SNAPSHOTS_FROZEN_PENDING_SEPARATE_H6_SCREEN`
- **next authorization consequence:**
  ```text
  A separate authorization may run one H6 failed-breakout statistical screen
  per instrument, reading only the corresponding hash-verified snapshot
  (comment line skipped) under the unchanged H6 protocol, with XAUUSD as its own
  separate stratum. No cost/PnL/backtest/trading work is authorized by this freeze.
  ```
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE/freeze_h6_single_instrument_snapshots.py`
  - `.../H6_SNAPSHOT_FREEZE_REPORT.md`
  - `.../H6_SNAPSHOT_FREEZE_DECISION.md`
  - `.../data_manifest_h6.yaml`
  - `.../snapshots/<SYMBOL>/<sym>_h1_internal_snapshot_v1.csv` + `.sha256` (all seven)
  - `.../RUN_LOG.md`
