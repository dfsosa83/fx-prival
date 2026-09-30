# H6 — Failed-Breakout Statistical Screen Decision

**Stage:** `H6_FAILED_BREAKOUT_STATISTICAL_SCREEN`
**Experiment:** `QPF-RV-2027-05-H6-FAILED-BREAKOUT-STATISTICAL-SCREEN`
**Parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Date:** 2026-09-30 · **Clock:** internal ordinal only (`NOT_UTC`)

```text
FX decision:      REJECT_H6_FX_STATISTICAL_VIABILITY
XAUUSD decision:  REJECT_H6_XAUUSD_STATISTICAL_VIABILITY
```

---

## 1. Snapshot hash / input validation

All seven frozen snapshots verified against `data_manifest_h6.yaml` (SHA256 before `pandas.read_csv`,
`comment="#"`), each with the exact ordered columns `internal_index_k, timestamp_label_internal,
<instrument>_close`, index `1..T`, unique/strictly-ascending labels, finite positive closes:
**EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD → all OK.**

## 2. Splits / embargoes (60/20/20, 30-bar embargo)

| Instrument | T | train | validation | sealed |
|---|---|---|---|---|
| EURUSD | 48,203 | [0,28921) | [28951,38561) | [38591,48203) |
| USDJPY | 48,190 | [0,28914) | [28944,38552) | [38582,48190) |
| USDCHF | 48,208 | [0,28924) | [28954,38565) | [38595,48208) |
| USDCAD | 48,179 | [0,28907) | [28937,38542) | [38572,48179) |
| AUDUSD | 48,115 | [0,28869) | [28899,38492) | [38522,48115) |
| NZDUSD | 48,086 | [0,28851) | [28881,38468) | [38498,48086) |
| XAUUSD | 45,808 | [0,27484) | [27514,36645) | [36675,45808) |

## 3. FX stratum

- Intended family: **324** tests (6×3×3×3×2); actual family: **324** (all six FX valid).
- Numeric validation HAC p-values: **324**; not-testable: **0**.
- BH FDR `q=0.10` applied across the FX family.
- Validation survivors: **0**; selected configurations: **0**.
- Sealed: **not evaluated** (no survivor).
- Decision: **`REJECT_H6_FX_STATISTICAL_VIABILITY`**.

## 4. XAUUSD stratum

- Family: **54** tests (1×3×3×3×2).
- Numeric validation HAC p-values: **54**; not-testable: **0**.
- BH FDR `q=0.10` applied across the XAUUSD family (separate from FX).
- Validation survivors: **0**; selected configurations: **0**.
- Sealed: **not evaluated** (no survivor).
- Decision: **`REJECT_H6_XAUUSD_STATISTICAL_VIABILITY`**.

## 5. Failed requirements

No bound configuration had **both** event classes (`FAILED_UPWARD_BREAKOUT`, `FAILED_DOWNWARD_BREAKOUT`)
independently satisfying all frozen survivor criteria (≥30 events, ≥200 controls, favorable unaligned Δ,
positive aligned event mean, positive aligned Δ, HAC p<0.05, BH q≤0.10, positive non-overlap aligned
difference). Hence no survivor in either stratum, so no sealed confirmation was run.

## 6. Meaning

- This is a **statistical** result only for the frozen H6 formulation, evaluated on the seven frozen
  single-instrument snapshots.
- **FX and XAUUSD were evaluated as separate strata** and never pooled, ranked together, or jointly
  BH-corrected.
- **Rejection applies only to this frozen H6 formulation.** It does not reject all breakout/reversal
  behavior, and it does **not** authorize retuning \(N,M,H\), controls, signs, or BH settings.
- The frozen H6 formulation is **rejected**; a **new, materially distinct hypothesis** would have to be
  pre-registered to continue.

## 7. Prohibited work not performed

No PnL, net return, costs, spread, commissions, slippage, swaps, sizing, entries/exits/stops, portfolio
exposure, drawdown, Sharpe, backtest, ML, or trading instruction was computed. No MT5/broker/
credentials/network/calendar/news/external access; no raw source or prior artifact modified. Internal
ordinal clock only (`NOT_UTC`).

## Artifacts

- `h6_failed_breakout_statistical_screen.py`
- `H6_FAILED_BREAKOUT_RESULTS.json`
- `H6_FAILED_BREAKOUT_DECISION.md`
- `RUN_LOG.md` (appended)
