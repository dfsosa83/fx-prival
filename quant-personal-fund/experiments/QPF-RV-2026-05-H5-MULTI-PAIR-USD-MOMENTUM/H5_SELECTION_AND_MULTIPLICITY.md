# H5 — Selection and Multiplicity

**Stage:** `H5_MULTI_PAIR_USD_MOMENTUM_VOLATILITY_DESIGN`

---

## Why explore more than one pair and horizon

A USD-factor continuation, if real, is unlikely to appear identically in every pair and every horizon —
different pairs have different liquidity, quoting conventions, and USD sensitivity, and the
continuation horizon itself is unknown. Exploring a **pre-declared** set of pairs and horizons lets us
observe whether an effect is broad-based or absent, without inventing the specification after seeing
the answer.

## Why flexibility is limited to a pre-declared grid

Free exploration becomes a search for the best-looking outcome. Freezing \(L,H,V,K\), directions,
targets, treatments, and thresholds **before** results keeps the exercise falsifiable: any result can
be checked against the fixed family, and multiplicity can be controlled.

## Why every allowed specification must be reported

If only successful cells are reported, the analysis is uninterpretable. Every specification — including
failures, low-event cells, unfavorable signs, and non-significant results — is reported, so the reader
sees the whole grid (`NOT_TESTABLE_INSUFFICIENT_EVENTS` where applicable, never dropped).

## Why target-excluded is primary and target-included is secondary

If the target pair is also a basket member, the target's own recent move mechanically enters the
confirmation count, biasing the signal toward the target's own momentum. The **target-excluded** basket
removes that mechanical overlap and is therefore the only **selection** treatment. **Target-included**
output is a secondary diagnostic and can never select, replace, or reorder a candidate.

## Why selection uses validation only

Validation is the honest place to compare specifications. Using sealed data to choose would burn the
only clean confirmation sample. Selection is done **on validation only**; sealed data is untouched
until ≤3 configurations are frozen.

## Why no more than three reach sealed testing

Capping the sealed set at **three bound configurations** preserves the sealed segment as genuine
out-of-sample confirmation rather than a second optimization pass.

## What BH FDR \(q=0.10\) controls — and what it cannot guarantee

Benjamini–Hochberg at \(q=0.10\) controls the **expected proportion of false discoveries** across the
672 primary (target-excluded) tests. It does **not** guarantee that any individual "pass" is a true
effect, does not correct for choices not in the frozen grid, and says nothing about economic
significance, costs, or profitability.

## Why sealed data is used once only

Running sealed data repeatedly until a configuration passes turns it into training data. It is evaluated
**once** for the frozen selected configurations; no reranking, replacement, or tuning after validation.

## Why no profitability claim is valid yet

The screen measures a statistical association between a historical signal and a future log-price
change. It excludes spreads, commissions, slippage, swaps, fills, latency, sizing, and PnL. Only a
later, **separate, cost-aware economic test** could speak to profitability — and even that would remain
a separate governance decision.

## Compact design table

| Component | Fixed values |
|---|---|
| Targets | EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD |
| USD basket | EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD |
| Basket treatments | Target-included, target-excluded |
| \(L\) | 4, 8, 24, 48 |
| \(H\) | 4, 8, 24 |
| \(V\) | 24, 72 |
| \(K\) | 3, 4 |
| Directions | USD strength and USD weakness |
| Selection | Validation only; at most 3 bound configurations |
| Confirmation | Sealed once |
| Multiplicity | BH FDR \(q=0.10\), 672 primary tests |
