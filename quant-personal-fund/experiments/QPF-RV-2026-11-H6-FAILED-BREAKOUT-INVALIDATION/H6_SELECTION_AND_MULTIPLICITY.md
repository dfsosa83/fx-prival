# H6 — Selection and Multiplicity

**Stage:** `H6_FAILED_BREAKOUT_INVALIDATION_DESIGN`

---

## Why H6 tests a distinct mechanism

Cointegration tested **long-run equilibrium** between two price series; broad-USD momentum tested
**coordinated multi-pair direction**. H6 tests neither: it is a **single-instrument price-action
event** — a range breakout that **fails and re-enters**, then a subsequent opposite-direction move.
It shares no data engine, no label, and no selection logic with the rejected families.

## Why \(N,M,H\) vary in a controlled grid

Range length (\(N\)), invalidation speed (\(M\)), and outcome horizon (\(H\)) are unknown a priori and
differ across instruments and regimes. Freezing a small grid (\(3\times3\times3\)) lets us observe
whether an effect is broad rather than fabricating the one good setting afterward. The grid is
**fixed before** any result.

## Why failed-up and failed-down evidence must both be present

A result that works in only one direction is likely noise or drift. Requiring **both** event classes
to pass is a built-in symmetry control, and neither may be selected independently.

## Why events are confirmed only after re-entry, and outcomes begin after confirmation

The event timestamp is the **first re-entry bar** \(e=t+k^*\), not the breakout bar. This ensures
invalidation is established using data up to and including \(e\), and the outcome starts **strictly
after** \(e\) — so no outcome uses the prices that established invalidation.

## Why controls are deterministic and in the same segment

Random or optimized matching invites data-snooping. Controls are every eligible non-event bar in the
**same segment** sharing the event's \(d \bmod H\) phase, giving a fixed, reproducible comparison
sample without propensity models or resampling.

## Why all 378 tests are reported and BH FDR is needed

Reporting the whole grid (`7 × 3 × 3 × 3 × 2 = 378`) prevents selective reporting. With many tests,
some will look significant by chance; **Benjamini–Hochberg FDR at q = 0.10** controls the expected
proportion of false discoveries across the family. BH does **not** prove any single effect is real.

## Why selection is validation-only, ≤3 to sealed

Comparing specifications on validation keeps sealed data clean. Capping sealed at **three**
configurations stops sealed from becoming a second optimization pass; sealed is evaluated **once**.

## Why successful statistics ≠ profitability

The screen measures a statistical association between a confirmed event and a future log-price
change. Spreads, commissions, slippage, swaps, fills, sizing, exits, and PnL are **untested**; only a
later, separate **cost-aware economic test** could speak to profitability.

## Compact design table

| Component | Frozen values |
|---|---|
| FX instruments | EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD |
| Separate stratum | XAUUSD, not pooled with FX |
| Timeframe | H1 |
| Price | Close only |
| \(N\) | 12, 24, 48 |
| \(M\) | 2, 4, 8 |
| \(H\) | 4, 8, 24 |
| Directions | Failed up and failed down |
| Selection | Validation only; at most 3 |
| Confirmation | Sealed once |
| Multiplicity | BH FDR \(q=0.10\), 378 tests |
