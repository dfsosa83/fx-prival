# G3-Internal Statistical Protocol (FROZEN)

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Stage:** `G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING`
**Authority:** Internal Clock Only Research Amendment (`INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT.md`)
**Frozen:** 2026-09-29 — this protocol is written **before** any result is inspected.

> Internal clock only. Timestamp labels are **ordinal** (`NOT_UTC`); they are never interpreted as
> UTC/broker/session/event time. No costs, PnL, EV, signals, entries/exits, sizing, ML/LLM,
> backtests, or execution.

---

## A. Dataset definition

- **Inputs (exact):** `ml-signal-service\data\raw\mt5\H1\EURUSD_H1.csv`, `...\GBPUSD_H1.csv`.
- **Expected SHA256:** EURUSD `AFC3109108AE64E59800F99D4B87A11B58B26EDE5185DCBD3B132422E4F3DA5F`;
  GBPUSD `11D9D435C1DDBC4A797BDF236ED3F3F13765338D2AD21870268016F76FD24CB7`. Hash mismatch → fail closed (PAUSE).
- **Panel:** strict chronological timestamp **intersection** of EURUSD and GBPUSD H1 bars,
  `(P_k^EURUSD, P_k^GBPUSD)`, `k = 1..T`.
- **Price field:** `close` only. **Transform:** natural log close only. No return/label fields.
- **Exclusions:** the five unmatched GBPUSD Friday-evening observations (18:00–23:00 2026-09-25) are
  excluded by the intersection itself; the final timestamp `2026-09-29 19:00:00` is excluded from
  both series (completion unprovable). No forward-fill/interpolation/resample/repair.

## B. Chronological splits (ordinal index)

- `n_train = floor(0.60 * T)`, `n_val = floor(0.20 * T)`, `n_test = T - n_train - n_val`.
- Raw segments: train `[0, n_train)`, validation `[n_train, n_train+n_val)`, sealed `[n_train+n_val, T)`.
- **30-bar embargo** removed from the **front** of the later partition:
  - validation = `[n_train+30, n_train+n_val)`, embargo1 = `[n_train, n_train+30)`;
  - sealed = `[n_train+n_val+30, T)`, embargo2 = `[n_train+n_val, n_train+n_val+30)`.
- All boundaries, counts, and excluded embargo counts are written before any test result.

## C. Hedge ratio and spread

1. TRAIN-only OLS: `log(P^EURUSD_k) = alpha + beta * log(P^GBPUSD_k) + eps`.
2. Fixed TRAIN `alpha, beta` construct validation/sealed spreads:
   `s_k = log(P^EURUSD_k) - alpha - beta*log(P^GBPUSD_k)`.
3. No refit on validation/sealed for the primary OOS evaluation.
4. Rolling diagnostics only: trailing 5,000-bar window (up to and including window end) → hedge; then
   assess the subsequent non-overlapping 1,000-bar block. No future data per block.

## D. Tests

1. **Engle–Granger / residual ADF** (`statsmodels.tsa.stattools.adfuller`, `regression="c"`,
   `autolag="AIC"`) on the residual spread separately for TRAIN, VALIDATION, SEALED (validation/sealed
   labeled as TRAIN-fixed-hedge-ratio residual stationarity, not a re-estimated EG test). Record
   statistic, p-value, selected lag, nobs, critical values.
2. **Johansen** (`statsmodels.tsa.vector_ar.vecm.coint_johansen`, `det_order=0`, `k_ar_diff=1`) on
   log-price pairs per segment. Record trace/max-eig, 90/95/99% critical values, inferred rank at 5%,
   sample count. `NOT_APPLICABLE` (with reason) rather than re-tuning.
3. **Rolling ADF stability**: trailing 5,000-bar hedge windows; non-overlapping 1,000-bar eval blocks;
   ADF per block; record internal labels, alpha, beta, statistic, p, lag, pass (p<0.05).

## E. Mean-reversion diagnostics (TRAIN-fixed spread)

1. **AR(1)/OU:** `Δs_k = a + b*s_{k-1} + eps`; `kappa = -b`; half-life only if `b<0` and `0<kappa<1`:
   `t_half = ln(2)/(-ln(1-kappa))`, else `NOT_MEAN_REVERTING_UNDER_AR1_RULE`. Record a, b, kappa,
   SE(b), t, p, status, half-life bars.
2. **Lo–MacKinlay homoskedastic variance ratio** on spread changes, horizons `q = 2,4,8,16`, per
   segment (validation, sealed). Record VR, z, two-sided p, and classification:
   `MEAN_REVERSION_COMPATIBLE` (VR<1 & p<0.05) / `RANDOM_WALK_NOT_REJECTED` (p>=0.05) /
   `MOMENTUM_OR_NON_REVERSION` (VR>1 & p<0.05). No horizon selection post hoc.

## F. Robustness

1. **Three chronological equal subperiods** within validation, and separately within sealed; repeat
   residual ADF, AR(1)/half-life, VR (q=2,4,8,16).
2. **Stationary block bootstrap** for `mean(Δs)` and AR(1) `b`, separately on validation and sealed:
   1,000 resamples, average block length 24, seed 42; 95% CIs. Diagnostic only.
3. **Parameter sensitivity**: rolling stability with trailing windows 4,000 and 6,000 bars (eval block
   exactly 1,000); report pass-rate sensitivity. No change to primary train/test procedure.

## G. Frozen statistical decision gate

**APPROVE_STATISTICAL_VIABILITY** — all of:
1. hash verification passes; 2. intersection/exclusion rules followed exactly;
3. validation & sealed residual ADF p < 0.05; 4. validation & sealed Johansen rank ≥ 1 at 5%
(or Johansen `NOT_APPLICABLE` for a documented reason);
5. ≥ 60% of primary 5,000/1,000 rolling ADF blocks pass p<0.05;
6. validation & sealed AR(1) b<0, p<0.05, finite half-life;
7. validation & sealed: ≥ 2 of 4 VR horizons `MEAN_REVERSION_COMPATIBLE`;
8. validation & sealed: ≥ 2 of 3 subperiods pass residual ADF p<0.05 **and** b<0;
9. bootstrap 95% CI for b entirely below zero in both validation & sealed;
10. no prohibited external/time/cost/trading feature or calculation.

**REJECT_STATISTICAL_VIABILITY** — any of: hash/intersection violation; validation/sealed residual ADF
p ≥ 0.05; validation/sealed AR(1) b ≥ 0 or p ≥ 0.05; finite half-life not established in both;
rolling ADF pass rate < 40%; validation/sealed zero VR horizons compatible; < 2/3 subperiods pass
ADF or show b<0 in either; bootstrap b CI includes zero in either; prohibited data/calculation used.

**PAUSE_STATISTICAL_VIABILITY** — only if: an implementation limitation blocks a required test; a
remediable artifact/hash/integrity problem; internally contradictory evidence without a REJECT rule;
or Johansen not applicable while all other primary conditions hold and judgment is deferred.

**Run once.** No tuning or repetition after observing results; the first frozen run is final for this
phase.

## Restrictions

Only local CSVs + pandas/numpy/scipy/statsmodels; no `frival`/`ml-signal-service`/MetaTrader5/broker/
credentials/network/execution imports. Random seed 42. Fail closed on hash mismatch or prohibited
input. Write only the required artifacts under the experiment folder. No PnL/returns/position/order
objects; no cost/PnL/EV calculations.
