# EXEC-D1 Migration Report — 2026-09-28 invalid fills (D-9)

**Date:** 2026-09-28 (implementation of EXEC-D1 final plan)
**Scope:** migration of the two demo-virtual fills produced on 2026-09-28 by the
pre-D1 simulator. Read/immutable: no outcome is reconstructed; both records are
excluded from every PnL/performance metric.

## 1. Why these fills are invalid (evidence)

| Signal / ticket | Evidence (execution_log.jsonl, 2026-09-28) | Defect |
|---|---|---|
| `EURUSD_H1_SELL_2026-09-28T16:00:00Z` / `DEMO-1790611402310` | Fill 1.13648 at 16:03:22.310Z; quote at fill 1.13648 (zone edge) | Pre-D1 `OrderBot` opened the virtual position at the **nominal** entry 1.13628, not the actual fill 1.13648; outcome never resolved or recorded |
| `EURUSD_H1_SELL_2026-09-28T17:00:00Z` / `DEMO-1790614996372` | Fill 1.13641 at 17:03:16.372Z while the live bid was **1.13713** — 7.2 pips outside the entry zone [1.13661, 1.13621] | Pre-D1 demo path (`order_manager._send_order` demo branch) returns a simulated success with `price = prepared price` — an instant synthetic fill with **no qualifying quote touch**; outcome never resolved |

Neither position ever closed (`demo_trades_ledger.jsonl` has no record of either
ticket; both `--once` subprocesses exited at 16:03Z / 17:03Z with in-memory
positions only). Their outcomes are **unknowable and must never be inferred**.

## 2. Migration action (approved D-9)

- Both records are tagged **`INVALID_SYNTHETIC_FILL_NO_OUTCOME`** in the manifest
  `frival/execution_bot/data/invalid_signal_ids.json`.
- The exclusion contract lives in `frival/execution_bot/core/invalid_fills.py`:
  - `is_excluded(signal_id)` — gate for any metric consumer;
  - `partition(records)` — every PnL/performance aggregation MUST use only the
    "valid" split;
  - `assert_no_reconstruction(closed_records)` — refuses (AssertionError) any
    closed-lifecycle record carrying either signal id.
- The EXEC-D1 lifecycle engine never emits these signal ids (they are not in its
  event log), so the exclusion is structural, not just reporting-side.

## 3. Post-migration state

- No outcome reconstructed; no PnL imputed; no ledger rows added for these owns.
- Any future metric pipeline that omits the manifest fails safe (the loader
  raises if the manifest file is missing).

**Verification:** `test_exec_delta1.TestMigrationManifest` (3 tests) covers the
manifest content, the partition/exclusion contract, and the no-reconstruction
guard — all passing (see test report).