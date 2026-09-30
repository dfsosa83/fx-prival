# H6 — Research Question

**Stage:** `H6_FAILED_BREAKOUT_INVALIDATION_DESIGN`
**Experiment:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Clock:** internal ordinal only (`NOT_UTC`)

---

## The question

> When price breaks above or below a pre-defined trailing range and then rapidly re-enters that range,
> does the subsequent H1 price change tend to continue in the direction **opposite** to the failed
> breakout more often or more strongly than comparable non-event conditions?

## Scope and meaning

- H6 is **independent** of the rejected cointegration hypotheses (H3/H4) and the broad-USD
  continuation hypothesis (H5). It is a separate hypothesis family: those rejections **do not**
  reject failed-breakout behavior, reversal following invalidation, price-action event studies,
  instrument-specific conditional effects, or future strategy viability.
- It tests a **price-action event**: breakout → rapid invalidation → subsequent opposite-direction
  outcome.
- It is a **predictive statistical event-study hypothesis only**.
- A successful statistical result would **not** show profitability, PnL, tradable edge, execution
  feasibility, or trading authorization.
- Any later outcome is a **future log-price change**, not a strategy return or PnL.
- **Instrument and parameter selection must use validation only**; sealed data is reserved for one
  confirmation.
- **No parameter may be modified** after validation/sealed outcomes are observed.

## Explicitly distinguished stages

H6 must keep these strictly separate: **breakout detection** → **invalidation confirmation** →
**event timestamp** (`e = t + k*`) → **later future statistical outcome**. No outcome may use price
data already used to establish invalidation.
