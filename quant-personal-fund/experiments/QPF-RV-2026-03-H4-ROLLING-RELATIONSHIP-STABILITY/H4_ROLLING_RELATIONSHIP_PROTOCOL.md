# H4 — Rolling-Relationship Stability Protocol (FROZEN)

**Stage:** `H4_ROLLING_RELATIONSHIP_STABILITY_DESIGN`
**Frozen:** 2026-09-29 — written before any H4 screen; no data parsed in this stage.

> Internal clock only. No costs, PnL, signals, positions, execution, ML, or LLM decisions. This is a
> statistical-viability design only.

---

## 1. Internal clock

- All labels are **ordinal internal labels only: `NOT_UTC`**.
- No timezone, session, weekday, calendar, event, broker-time, or market-close interpretation is
  allowed.
- Every later candidate must use an **immutable strict-intersection snapshot** and exclude **exactly
  the maximum common label** before analysis.

## 2. Split structure

For a later snapshot with \(T\) observations:

\[
N_{\text{train}}=\lfloor0.60T\rfloor,\quad N_{\text{validation}}=\lfloor0.20T\rfloor,\quad
N_{\text{sealed}}=T-N_{\text{train}}-N_{\text{validation}}.
\]

- First 60% → **train**.
- **30-bar embargo** after train.
- Next 20% → **validation**.
- **30-bar embargo** after validation.
- Remaining observations → **sealed**.
- **No embargo observation** may enter a fit window, evaluation block, or metric.
- The **sealed segment is not used** to choose a window, eligibility rule, threshold, pair, or
  interpretation.

## 3. Fixed candidate windows

Pre-registered fit windows:

```text
W ∈ {1,000, 2,000, 5,000} H1 observations
```

Pre-registered evaluation length:

```text
E = 1,000 H1 observations
```

- Do **not** add, remove, or tune values after results.
- A block is **eligible** only if it contains a **full W-bar historical fit window** and a **full
  E-bar future evaluation block** within the applicable segment.

## 4. Pair orientation

Use the audited order exactly (do not reverse later based on results):

- C2: `log(EURUSD)` on `log(USDCHF)`
- C3: `log(AUDUSD)` on `log(USDCAD)`
- C4: `log(EURGBP)` on `log(EURUSD)`
- C5: `log(NZDUSD)` on `log(USDCAD)`

## 5. Block construction

Within each applicable segment:

1. Construct **sequential non-overlapping** E = 1,000 evaluation blocks.
2. For each evaluation block beginning at \(t\), fit OLS **only** on the preceding W contiguous
   eligible observations in the same segment:
   \[
   \log X_i=\alpha_t+\beta_t\log Y_i+\varepsilon_i,\quad i=t-W,\ldots,t-1.
   \]
3. Compute the **in-window residual** only for historical eligibility diagnostics.
4. Apply the frozen eligibility gate **solely** to that in-window residual.
5. If eligible, **freeze** \(\hat\alpha_t,\hat\beta_t\) and evaluate the future residual over
   \(t,\ldots,t+E-1\):
   \[
   s_i^{(t)}=\log X_i-\hat\alpha_t-\hat\beta_t\log Y_i.
   \]
6. **Never** use future/evaluation observations in the fit or eligibility gate.
7. Evaluation blocks **do not overlap**.
8. Fit windows may overlap only because each is a trailing historical window; an evaluation block
   never overlaps its own fit period.

Each rolling block is a **separate local hypothesis test**; it does **not** assert a global,
full-sample cointegrating vector.

## 6. Eligibility gate (frozen before any future-block result is seen)

A historical fit window is eligible only if **both**:

1. ADF on its in-window OLS residual (`adfuller(residual, regression="c", autolag="AIC")`) has
   **p < 0.05**;
2. its AR(1) residual estimate \(\Delta s_i=a+b\,s_{i-1}+u_i\) has
   `b < 0` **and** `p_value(b) < 0.05` **and** a **finite half-life** under `0 < -b < 1`
   (\(t_{1/2}=\ln 2 / -\ln(1-\kappa)\), \(\kappa=-b\)).

The eligibility **rate** is descriptive, **not** a pass criterion.

## 7. Future-block pass

For each **eligible** future evaluation block, a pass requires **both**:

1. future residual ADF p < 0.05; and
2. future AR(1) with `b < 0`, `p_value(b) < 0.05`, and finite half-life.

Record **all** eligible and ineligible blocks; do **not** discard failures.

## 8. Candidate-level validation selection (validation only)

1. Evaluate all three fixed \(W\) values.
2. Validation score per W:
   \[
   \text{score}(W)=\frac{\#\text{future-block passes among eligible blocks}}{\#\text{eligible blocks}}.
   \]
3. If a W has **fewer than three** eligible validation blocks → `NOT_ELIGIBLE_FOR_SELECTION`.
4. Select the W with the **highest** validation score among eligible W values.
5. **Tie-break strictly in favor of the smallest W.**
6. The selected W must satisfy **all**: ≥ 3 eligible validation blocks; validation future-block pass
   rate ≥ 60%; ≥ 2 future-block passes; eligibility rate ≥ 20% of complete validation blocks.
7. If no W meets these → **reject the candidate** without evaluating sealed data beyond basic input
   integrity checks.
8. If exactly one selected W passes validation → **freeze it** and test it **once** on sealed data.

## 9. Sealed confirmation (selected W only)

- Evaluate all complete sealed blocks.
- Do **not** change W, eligibility gate, thresholds, orientation, pair, E, or any other rule.
- Require: ≥ 3 eligible sealed blocks; sealed future-block pass rate ≥ 60%; ≥ 2 future-block passes;
  sealed eligibility rate ≥ 20% of complete sealed blocks.

## 10. Candidate outcome

```text
APPROVE_ROLLING_STATISTICAL_VIABILITY
```
only if the candidate passes **both** validation selection and sealed confirmation. Otherwise:

```text
REJECT_ROLLING_STATISTICAL_VIABILITY
```

A technical data/integrity failure → `PAUSE_ROLLING_STATISTICAL_VIABILITY`.

## 11. Anti-overfitting rule

- This design tests **3 pre-specified windows** per candidate.
- Candidate order is **fixed**.
- A rejected candidate does **not** allow retroactive adjustment of W, E, eligibility tests,
  cutoffs, pair orientation, or split boundaries.
- The next candidate may be tested only under this **identical** protocol.
- Any later strategy/PnL phase must treat this candidate-screening multiplicity as part of the
  research record and use **fresh** cost-aware out-of-sample data.

## 12. Prohibited work

No later H4 statistical screen may compute costs, PnL, signals, trade entries, exits, sizing,
portfolio allocations, drawdown, Sharpe, ML, LLM decisions, backtest performance, or execute trades.
