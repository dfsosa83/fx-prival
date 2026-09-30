# H5 — Protocol (FROZEN)

**Stage:** `H5_MULTI_PAIR_USD_MOMENTUM_VOLATILITY_DESIGN`
**Frozen:** 2026-09-29 — written before any H5 screen; no market data parsed in this stage.

> Internal clock only (`NOT_UTC`). A predictive-**statistical** protocol. No costs, PnL, strategy,
> orders, execution, ML, or LLM decisions.

---

## 1. Internal clock and snapshot policy

- All timestamp labels are **ordinal internal labels only: `NOT_UTC`** (no UTC/broker/session/date/
  weekday/event/market-close parsing).
- H5-v1 must use a **hash-verified immutable strict multiseries-intersection snapshot** containing the
  five confirmation-basket pairs **and** all seven target pairs:
  `EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`.
- Exclude **exactly the maximum common timestamp label** before analysis.
- No imputation, interpolation, resampling, forward-fill, repair, or external join.
- If any required series fails validation or prevents a usable strict common intersection, H5-v1 must
  **PAUSE** rather than omit that series.

## 2. Units and allowable transformations

Historical log-price change (a **signal component**, not a PnL/strategy return):

\[
r_{j,t}^{(L)}=\log\!\left(\frac{P_{j,t}}{P_{j,t-L}}\right).
\]

Future statistical outcome for target \(q\) (an **out-of-sample statistical target only**; never
called strategy return, trading return, or PnL):

\[
y_{q,t}^{(H)}=\log\!\left(\frac{P_{q,t+H}}{P_{q,t}}\right).
\]

## 3. Fixed controlled grid

```text
L ∈ {4, 8, 24, 48}   H1 bars (signal momentum lookback)
H ∈ {4, 8, 24}       H1 bars (future outcome horizon)
V ∈ {24, 72}         H1 bars (volatility window)
K ∈ {3, 4}           confirmation requirement (of five basket members)
Directions: USD strength and USD weakness (symmetric)
```

- `K=3` → ≥3 of 5 members show coherent USD sign; `K=4` → ≥4 of 5.
- No \(L,H,V,K\), direction, target, basket composition, or threshold may be added, removed, or tuned
  after results. Per target and basket treatment the raw grid is \(4\times3\times2\times2\times2=96\);
  with 7 targets × 2 treatments → **1,344** descriptive results. The **target-excluded** treatment
  is the only primary selection/multiplicity family; target-included is secondary-descriptive only.

## 4. Volatility condition

Trailing realized-volatility proxy:

\[
\sigma_{q,t}^{(V)}=\sqrt{\frac{1}{V}\sum_{i=t-V+1}^{t}\left(r_{q,i}^{(1)}\right)^2}.
\]

Trailing historical median (earlier available values only):

\[
\widetilde{\sigma}_{q,t}^{(V)}=\operatorname{median}\!\left(\sigma_{q,u}^{(V)}:u\in[t-5V,t-1]\right).
\]

High-volatility regime:

\[
\mathrm{HighVol}_{q,t}^{(V)}=\mathbf{1}\!\left\{\sigma_{q,t}^{(V)}>\widetilde{\sigma}_{q,t}^{(V)}\right\}.
\]

If the trailing history for the median is unavailable, that timestamp is **not used**. No other
percentile, multiplier, threshold, window, or volatility estimator.

## 5. Signal conditions

\[
S_{q,t}^{(L,V,K,+)}=\mathbf{1}\{C_t^{(L)}\ge K,\ \mathrm{HighVol}_{q,t}^{(V)}=1\},\qquad
S_{q,t}^{(L,V,K,-)}=\mathbf{1}\{C_{t,\mathrm{weak}}^{(L)}\ge K,\ \mathrm{HighVol}_{q,t}^{(V)}=1\}.
\]

Expected future target-outcome signs (fixed):

| Target | USD-strength expected \(y^{(H)}\) sign | USD-weakness expected sign |
|---|---:|---:|
| EURUSD | Negative | Positive |
| GBPUSD | Negative | Positive |
| USDJPY | Positive | Negative |
| USDCHF | Positive | Negative |
| USDCAD | Positive | Negative |
| AUDUSD | Negative | Positive |
| NZDUSD | Negative | Positive |

The target's own historical \(L\)-movement must **not** be added as an independent signal condition.
The only permitted basket variants are the pre-declared **target-included** and **target-excluded**
treatments.

## 6. Valid timing and overlap

- Every input used by the signal **ends at \(t\)**; the target outcome uses strictly future prices
  from \(t\) to \(t+H\).
- No feature uses data from \(t+1\) or later.
- Labels lacking complete history for \(L\), \(V\), \(5V\), and \(H\) are ineligible.
- **Primary** inference: retain all valid timestamps, HAC/Newey–West with lag \(H-1\).
- **Robustness**: non-overlapping eligible outcome starts spaced by exactly \(H\).
- Both methods applied unchanged to every target/specification.

## 7. Temporal splits and embargoes

\(N_{\mathrm{train}}=\lfloor0.60T\rfloor\), \(N_{\mathrm{validation}}=\lfloor0.20T\rfloor\),
\(N_{\mathrm{sealed}}=T-N_{\mathrm{train}}-N_{\mathrm{validation}}\); 30-bar embargoes:

```text
Train: first N_train rows
Embargo 1: next 30 rows
Validation: next N_validation rows
Embargo 2: next 30 rows
Sealed: all remaining rows
```

- A signal at \(t\) belongs to a segment only when its **entire future outcome through \(t+H\)** lies
  inside the same segment.
- Feature lookbacks may use earlier available observations (including pre-segment non-embargoed data)
  but **never** embargoed observations.
- No future outcome crosses a segment boundary/embargo; **no sealed observation** selects target,
  horizon, \(L,V,K\), direction, treatment, method, or interpretation.

## 8. Statistical test per specification (later screen only)

For every target, treatment, direction, \((L,H,V,K)\):

1. number of valid eligible timestamps; 2. number of signal events; 3. signal event rate;
4. \(\bar y_{\mathrm{signal}}\); 5. \(\bar y_{\mathrm{non\text{-}signal}}\); 6.
\(\Delta=\bar y_{\mathrm{signal}}-\bar y_{\mathrm{non\text{-}signal}}\);
7. directional hit rate vs the pre-declared expected sign;
8. HAC/Newey–West t-statistic and two-sided p-value for \(\Delta\) (lag \(H-1\));
9. non-overlap robustness difference and hit rate;
10. sign-aligned outcome \(z_{q,t}^{(H)}=\operatorname{ExpectedSign}(q,\text{direction})\cdot y_{q,t}^{(H)}\).

Report effect sign and magnitude; **never infer evidence solely from hit rate**.

## 9. Matched non-signal controls

"Matched non-signal eligible timestamps" = same segment, same target, same \(L,H,V,K\), same
volatility-regime eligibility, same directional basket availability, but the relevant USD
strength/weakness confirmation is not met. Controls must satisfy the same future-outcome availability,
exclude embargoes and boundary crossings, be reported with their count, never cross segments, and be
used consistently for every specification. **No** propensity model, optimization, matching algorithm,
or data-derived subsampling in H5-v1.

## 10. Validation candidate filtering

Selection is on **validation only**, only from the **target-excluded** treatment. A specification is a
**validation survivor** only if **all** hold:

1. ≥50 signal events in USD-strength **and** ≥50 in USD-weakness;
2. ≥200 matched non-signal eligible timestamps in each direction;
3. in both directions, \(\Delta\) has the pre-declared favorable sign;
4. in both directions, aligned conditional mean \(\bar z_{\mathrm{signal}}>0\);
5. in both directions, HAC two-sided p < 0.05;
6. in both directions, the non-overlap robustness difference has the same favorable sign;
7. both directional tests pass Benjamini–Hochberg FDR (below).

A **bound configuration** is `target, target-excluded basket, L, H, V, K`. USD-strength and
USD-weakness are a **required paired confirmation** and cannot be selected independently.

## 11. Multiplicity control

Primary family = every validation HAC p-value from the target-excluded grid:
\(7\times4\times3\times2\times2\times2=672\) tests. Apply **Benjamini–Hochberg FDR at \(q=0.10\)**
across all 672. For every primary specification report: raw p-value, BH rank, BH-adjusted q-value,
total test count, and whether it passes BH \(q\le0.10\). **Do not remove** failed/low-event/
unfavorable/non-significant tests. A test that cannot produce a valid statistic due to pre-defined
sample constraints is reported `NOT_TESTABLE_INSUFFICIENT_EVENTS` and kept in the complete grid table
(never replaced). Target-included diagnostics do **not** enter the BH family.

## 12. Selection of configurations

From validation survivors only, rank bound configurations by: (1) larger minimum of the two
directional BH-adjusted significance margins; (2) lower maximum raw HAC p-value across directions;
(3) larger minimum absolute aligned \(\Delta\); (4) larger minimum signal-event count; (5)
lexicographically smallest target symbol; (6) smaller \(L\), then \(H\), then \(V\), then \(K\).
**Select at most three** bound configurations total. Report the entire validation grid, all failures,
all survivors, and the exact rank/tie-break logic. Target-included diagnostics must not select or
replace a configuration.

If there are no validation survivors → `REJECT_DIRECTIONAL_STATISTICAL_VIABILITY` and **sealed
outcomes are not computed** beyond input integrity validation.

## 13. Sealed confirmation

For each of at most three selected configurations, evaluate exactly the frozen configuration on sealed
data (same target, target-excluded basket, \(L,H,V,K\), directions, expected signs, high-volatility
definition, control definition, timing, HAC lag, non-overlap method). Do not rerank/replace/optimize/
add/drop after validation. In **both** directions require:
1. ≥50 signal events; 2. ≥200 matched non-signal eligible timestamps; 3. favorable \(\Delta\);
4. positive aligned conditional mean; 5. HAC two-sided p < 0.05; 6. favorable non-overlap
robustness difference.

```text
APPROVE_DIRECTIONAL_STATISTICAL_VIABILITY
```
only if **every** sealed requirement passes in both directions; otherwise
`REJECT_DIRECTIONAL_STATISTICAL_VIABILITY`. A hash/validation/numerical/technical failure →
`PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY`.

## 14. Decision meaning

- **Approval** means only that a directional statistical relationship is promising enough to design a
  **separate cost-aware economic test**.
- It does **not** demonstrate net profitability, tradability, or capital-allocation suitability.
- Costs, spreads, commissions, slippage, swaps, financing, latency, fills, exposure aggregation,
  drawdown, position sizing, and PnL remain **untested**.
- **Rejection** applies only to the tested target/basket/H1/H5 configuration; it does not reject FX
  momentum or continuation generally.
