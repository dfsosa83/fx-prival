# H6 — Screen Output Schema (future reporting; not created here)

**Stage:** `H6_SCREEN_ORCHESTRATION_DESIGN`

Defines the structure a **future** H6 screen output must use (JSON + Markdown). No such output is
produced in this design stage.

## Required top-level sections

1. **global_integrity** — run id, protocol id, snapshot source path, orchestrator version, and a
   per-snapshot entry: `{symbol, snapshot_path, expected_sha256, actual_sha256, hash_ok, schema_ok,
   rows, index_ok, labels_monotonic, closes_finite_positive, status}`.
2. **splits** — per instrument: `{T, n_train, n_validation, n_sealed, embargo_bars, boundary_labels}`.
3. **validation_tests** — the **full** validation grids:
   - `fx`: **324** records;
   - `xauusd`: **54** records.
   Each record: `{instrument, stratum, N, M, H, event_class, valid_event_count, valid_control_count,
   event_rate, mean_event_outcome, mean_control_outcome, unaligned_delta, aligned_event_mean,
   aligned_delta, hit_rate, hac_delta, hac_se, hac_t, hac_p, nonoverlap_event_count,
   nonoverlap_control_count, nonoverlap_aligned_delta, nonoverlap_hit_rate}` — plus
   `insufficient: true` and `hac_p: null` for `NOT_TESTABLE_INSUFFICIENT_EVENTS`.
4. **multiplicity** — per stratum (separate families):
   `{family, fdr_q, total_tests, numeric_p_values, not_testable}` plus a BH table with
   `{record_ref, raw_p, bh_rank, bh_q_value, bh_pass}`; null p-values carry `bh_rank: null`,
   `bh_q_value: null`.
5. **survivors** — per stratum: survivor checks per bound configuration with explicit failure reasons.
6. **selection** — per stratum: ranking table and the selected configurations (≤3 per stratum).
7. **sealed** — only for selected configurations: `{instrument, stratum, N, M, H, event_class,
   valid_event_count, valid_control_count, unaligned_delta, aligned_event_mean, aligned_delta,
   hac_p, nonoverlap_aligned_delta, pass}` for both event classes.
8. **decisions** — `per_configuration` (APPROVE/REJECT) and `per_stratum`
   (APPROVE/REJECT/PAUSE for FX and for XAUUSD, separately).
9. **prohibition_attestation** — explicit statement that no PnL, cost, backtest, signal, execution,
   or trading fields exist in this output.

## Hard requirements

- FX and XAUUSD results are reported in **separate** blocks; never pooled.
- No PnL / cost / spread / slippage / position / order / execution / trading fields.
- No cross-instrument timestamp alignment or intersection.
- Labels remain `NOT_UTC` (opaque ordinals).
- All 324 + 54 validation records are present (including not-testable).
