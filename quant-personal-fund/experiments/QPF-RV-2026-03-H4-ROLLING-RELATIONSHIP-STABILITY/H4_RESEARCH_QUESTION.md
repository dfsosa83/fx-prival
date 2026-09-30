# H4 — Research Question

**Stage:** `H4_ROLLING_RELATIONSHIP_STABILITY_DESIGN`
**Experiment:** `QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY`
**Clock:** internal ordinal only (`NOT_UTC`)

---

## The question

H4 is a **new hypothesis**, distinct from fixed full-history OLS residual cointegration.

It asks whether **pre-identified stable historical relationship windows** generate a
**higher-than-random incidence of mean-reverting residuals** in the **immediately following unseen
evaluation blocks**.

Stated as a question:

> For pair \((X,Y)\), if a trailing historical window \([t-W, t-1]\) yields a stable, mean-reverting
> OLS residual under a frozen eligibility gate, does the immediately following block \([t, t+E-1]\),
> evaluated with that window's **frozen** \((\hat\alpha_t,\hat\beta_t)\), mean-revert more often than
> chance?

## What H4 is not

- It is **not** a test of whether a pair is globally cointegrated.
- It **does not** claim profitability or tradability.
- It is **not** a trading strategy (no signals, thresholds, positions, costs, PnL).

## Candidate ordering

H4 will test candidates in the **fixed audit order**:

```text
C2 → C3 → C4 → C5
```

A candidate is **not** replaced, reordered, or selected based on results.

## Relationship to prior rejections

The prior fixed-beta hypotheses (EURUSD/GBPUSD, AUDUSD/NZDUSD) were rejected because a hedge ratio
fixed over a multi-year sample is too restrictive. H4 does not re-test them; they are historical
controls only and are **not** used to calibrate H4.
