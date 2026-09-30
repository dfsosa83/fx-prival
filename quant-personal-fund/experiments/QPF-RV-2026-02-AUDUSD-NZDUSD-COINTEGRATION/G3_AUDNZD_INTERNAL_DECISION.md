# G3 Decision — AUDUSD/NZDUSD Statistical Viability

**Experiment ID:** `QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G3_AUDNZD_STATISTICAL_VIABILITY_SCREENING`
**Decision:** `REJECT_STATISTICAL_VIABILITY`
**Clock:** internal ordinal only (`NOT_UTC`)

---

## Decision checks

| Check | Result | Key value |
|---|---|---|
| `C1_hashes_ok` | **PASS** | snapshot hash matches |
| `C2_rules_followed` | **PASS** | T = 48,029; columns/order/exclusions verified |
| `C3_adf_validation_lt_05` | **FAIL** | ADF −2.369, p = **0.1508** |
| `C3_adf_sealed_lt_05` | **FAIL** | ADF −0.092, p = **0.9503** |
| `C4_johansen_rank_ge1` | **FAIL** | ranks train 0 / validation 0 / sealed 0 |
| `C5_presealed_rolling_pass_ge_60` | **FAIL** | **6.06%** (primary 5,000/1,000) |
| `C6_ar1_validation` | **PASS** | b = −0.001449, p = 0.0078, HL 478 bars |
| `C6_ar1_sealed` | **FAIL** | b = −0.0000291, p = **0.835** |
| `C7_vr_validation_ge2` | **PASS** | 4/4 horizons mean-reversion-compatible |
| `C7_vr_sealed_ge2` | **PASS** | 4/4 horizons mean-reversion-compatible |
| `C8_subperiod_validation_ge2` | **FAIL** | **0/3** blocks pass |
| `C8_subperiod_sealed_ge2` | **FAIL** | **0/3** blocks pass |
| `C9_bootstrap_validation_b_ci_below0` | **PASS** | CI [−0.002455, −0.000449] |
| `C9_bootstrap_sealed_b_ci_below0` | **FAIL** | CI [−0.000303, +0.000233] includes 0 |
| `C10_no_prohibited_activity` | **PASS** | — |

## Failed mandatory conditions (→ REJECT)

- validation and sealed residual ADF both fail at 5% (p = 0.1508, 0.9503);
- validation Johansen rank < 1 (0/0/0 across segments);
- primary pre-sealed rolling pass rate **6.06% < 40%**;
- validation and sealed AR(1): sealed fails (p = 0.835);
- subperiod stability **0/3** in both validation and sealed;
- sealed bootstrap AR(1) b 95% CI includes zero.

## Interpretation

`REJECT_STATISTICAL_VIABILITY` closes this specific **AUDUSD/NZDUSD H1 fixed-OLS residual
mean-reversion hypothesis**. It does **not** reject pairs trading generally, and it does **not**
reject the remaining preordered candidates (C2–C5). Had the result been approval, it would only have
supported designing a later, separately authorized, **cost-aware economic/PnL test** — it is **not**
proof of profitability and **not** authorization to trade.

## Scope

Internal ordinal clock only; no absolute UTC/session/event alignment. No costs, PnL, returns,
signals, entries/exits, sizing, portfolio, ML, backtest, MT5/broker/credentials/network, or
execution/demo/shadow/live activity occurred. No parameter was tuned after observing results; the
single frozen run is final for this phase.

## Artifacts

- `g3_audnzd_statistical_viability.py`
- `G3_AUDNZD_INTERNAL_RESULTS.json`
- `G3_AUDNZD_INTERNAL_DECISION.md`
- `RUN_LOG.md` (appended)
