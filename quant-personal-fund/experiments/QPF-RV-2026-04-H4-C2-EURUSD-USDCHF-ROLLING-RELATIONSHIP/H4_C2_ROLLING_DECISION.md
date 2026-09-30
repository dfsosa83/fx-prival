# H4-C2 Rolling-Relationship Decision

**Experiment:** `QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP`
**Parent design:** `QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY`
**Candidate:** C2 — orientation `log(EURUSD)` on `log(USDCHF)`, H1
**Date:** 2026-09-29

## Decision

```text
REJECT_ROLLING_STATISTICAL_VIABILITY
```

---

## 1. Snapshot hash verification

`eurusd_usdchf_h1_internal_snapshot_v1.csv` → SHA256 `67590790F8BF0E20A707792D8DE85077C6D1067BD45035B05744D5D235E1DBF6` — **match** (verified before parsing).

## 2. Input validation

PASS — exact ordered schema `internal_index_k, timestamp_label_internal, eurusd_close, usdchf_close`;
T = 48,185; `internal_index_k` = 1..48,185 with no gaps/repetitions; labels unique + strictly
lexicographically ascending (`NOT_UTC`); all closes non-null, finite, numeric, strictly positive.

## 3. Split boundaries and embargoes

| Segment | Indices | n |
|---|---|---|
| train | [0, 28911) | 28,911 |
| embargo_1 | [28911, 28941) | 30 |
| validation | [28941, 38548) | 9,607 |
| embargo_2 | [38548, 38578) | 30 |
| sealed | [38578, 48185) | 9,607 |

Boundary labels: train_end `2023-08-22 14:00:00`; val_start `2023-08-23 21:00:00`; val_end
`2025-03-13 03:00:00`; sealed_start `2025-03-14 10:00:00`; sealed_end `2026-09-29 20:00:00`.
No embargo observation entered any fit window, evaluation block, eligibility calculation, score, or
sealed calculation.

## 4. Validation summaries (all W)

| W | complete blocks | eligible blocks | eligibility rate | future passes | future pass rate | eligible for selection |
|---|---|---|---|---|---|---|
| 1,000 | 8 | 1 | 0.1250 | 0 | 0.0000 | **NO** (<3 eligible) |
| 2,000 | 7 | 1 | 0.1429 | 0 | 0.0000 | **NO** (<3 eligible) |
| 5,000 | 4 | 1 | 0.2500 | 0 | 0.0000 | **NO** (<3 eligible) |

## 5. Selection outcome

**No W was eligible for selection** (`eligible_blocks < 3` for all three). Therefore no W was
selected (`selected_W = null`), and the pre-registered selection gates (≥3 eligible blocks, ≥2
passes, pass rate ≥ 60%, eligibility rate ≥ 20%) could not be met → **REJECT**.

## 6. Sealed outcome

**Sealed was not evaluated.** Validation selection failed, so no sealed residual diagnostics were
computed beyond sealed input integrity (per the frozen rule).

## 7. Failed requirement(s)

- `eligible_blocks >= 3`: **FAIL** (W=1,000 → 1; W=2,000 → 1; W=5,000 → 1).
- Consequently `future_passes >= 2`, `future_pass_rate >= 0.60`, and the selection step all fail.

## 8. Meaning

- **Approval would be statistical only** and would permit **at most** future design of a separate
  cost-aware economic test; it is not profitability and not trading authorization.
- **Rejection applies only to this C2 orientation / H1 / H4 design** (EURUSD on USDCHF, rolling H4
  window protocol). It does not reject pairs trading generally, and it does not authorize retuning
  W, E, the eligibility gate, thresholds, orientation, or the split.

## 9. Prohibited work not performed

No costs, PnL, returns, strategy, signals, entries/exits, sizing, portfolio, drawdown, Sharpe,
backtests, ML, or trading/execution; no MT5, broker, credentials, `.env`, network, calendar, news,
external source, or downloader access. Internal ordinal clock only (`NOT_UTC`); no parameter was
tuned after observing results; the single frozen run is final for this phase.

## Artifacts

- `h4_c2_rolling_relationship_screen.py`
- `H4_C2_ROLLING_RESULTS.json`
- `H4_C2_ROLLING_DECISION.md`
- `RUN_LOG.md` (appended)
