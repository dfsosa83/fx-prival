# H6 — Protocol (FROZEN)

**Stage:** `H6_FAILED_BREAKOUT_INVALIDATION_DESIGN`
**Frozen:** 2026-09-30 — written before any H6 screen; no market data parsed in this stage.

> Internal clock only (`NOT_UTC`). A predictive-**statistical** event-study protocol. No costs, PnL,
> strategy, entries/exits, sizing, portfolio, ML, backtest, or execution.

---

## 1. Internal clock and snapshot policy

- Timestamp labels are **ordinal internal labels only: `NOT_UTC`** (no UTC/broker/session/trading-day/
  weekday/event/market-close interpretation).
- Every later instrument must use a **hash-verified immutable H1 snapshot**.
- For an FX-only screen, use strict intersection **only if** a multi-instrument feature is required.
  H6 event detection itself is single-instrument and may use a single-instrument snapshot.
- Every snapshot **excludes exactly its maximum available label**.
- No imputation, interpolation, resampling, forward-fill, repair, or external joins.

## 2. Price definition

Later tests use **close prices only**: \(P_t = \mathrm{close}_t\). No high, low, open, volume, tick,
bid/ask, or external features in H6-v1.

## 3. Controlled grid

```text
Trailing breakout range  N ∈ {12, 24, 48} H1 bars
Invalidation window      M ∈ {2, 4, 8}   H1 bars
Future outcome horizon   H ∈ {4, 8, 24}  H1 bars
```

Directional event-study tests per instrument: \(3 \times 3 \times 3 \times 2 = 54\). Do **not** add,
remove, tune, optimize, or change \(N,M,H\) after results.

## 4. Breakout and invalidation rules (strict inequalities)

\[
U_t^{(N)}=\max(P_{t-N},\ldots,P_{t-1}),\qquad L_t^{(N)}=\min(P_{t-N},\ldots,P_{t-1}).
\]

Upward breakout begins if \(P_t > U_t^{(N)}\); downward breakout begins if \(P_t < L_t^{(N)}\).

Upward invalidation time \(k^*=\min\{k\in\{1,\ldots,M\}: P_{t+k} < U_t^{(N)}\}\); if it exists, create
exactly one `FAILED_UPWARD_BREAKOUT` event at **\(e=t+k^*\)**. Downward:
\(k^*=\min\{k\in\{1,\ldots,M\}: P_{t+k} > L_t^{(N)}\}\); if it exists, create exactly one
`FAILED_DOWNWARD_BREAKOUT` event at \(e=t+k^*\).

Use the strict inequalities **exactly as written**. Do **not** substitute equality, threshold
buffers, ATR filters, wick/high-low logic, spread adjustment, candle-body rules, volume filters, trend
filters, or any other feature.

## 5. Event de-duplication and overlap

For each instrument, \(N\), and event class:

1. Process potential breakout starts \(t\) in ascending order.
2. Once a breakout is confirmed invalidated at event index \(e=t+k^*\), record the event.
3. Start searching for the next breakout **only after \(e\)** (not within the original
   breakout-to-invalidation interval).
4. If two candidate breakouts would produce the same event index, keep the **earlier breakout start**
   only.
5. Do **not** merge or change events across different \(N\) values — each \(N\) is a separate
   pre-registered specification.
6. Do **not** delete events based on future outcome.

## 6. Future outcome (begins at the confirmation event)

\[
y_e^{(H)}=\log\!\left(\frac{P_{e+H}}{P_e}\right).
\]

This is a **future statistical target only** (never PnL/strategy return/trading return). Expected
sign:

| Event class | Expected sign of \(y_e^{(H)}\) |
|---|---:|
| `FAILED_UPWARD_BREAKOUT` | Negative |
| `FAILED_DOWNWARD_BREAKOUT` | Positive |

Sign-aligned outcome: \(z_e^{(H)}=\operatorname{ExpectedSign}(\text{event})\cdot y_e^{(H)}\). A valid
event requires complete prices through \(e+H\).

## 7. Non-event controls (deterministic, same-segment)

For each instrument, segment, \(N,M,H\), and event class, controls must:

- have complete \(N\), \(M\), and future \(H\) support;
- not be within any recorded breakout-to-invalidation interval for the same \(N\);
- not be confirmed events of either class for that \(N\);
- not cross an embargo or segment boundary;
- use the same close-only data;
- be sampled **deterministically**, not randomly.

Matching procedure:

1. For each confirmed event at index \(e\), define its calendar-free ordinal offset
   \(d = e - \text{segment\_start}\).
2. Controls are eligible non-event bars in the same segment with the same \(d \bmod H\) phase as the
   event.
3. Build the full eligible control pool **separately for each event class**.
4. Use all eligible controls; do **not** downsample, resample, or optimize.
5. Report control count and event count.

Controls must not use a future outcome to determine eligibility except the required availability of
\(P_{t+H}\).

## 8. Temporal splits

For a later single-instrument frozen H1 snapshot with \(T\) observations:
\(N_{\mathrm{train}}=\lfloor0.60T\rfloor\), \(N_{\mathrm{validation}}=\lfloor0.20T\rfloor\),
\(N_{\mathrm{sealed}}=T-N_{\mathrm{train}}-N_{\mathrm{validation}}\). Use 30-bar embargoes after
train and after validation.

Rules:

- An event belongs to a segment only if its breakout start \(t\), the entire invalidation-search
  interval \([t+1,t+M]\), the confirmation event \(e\), and the entire outcome through \(e+H\) are
  **all inside that segment**.
- No event, breakout interval, control, or outcome may use embargo bars; no outcome may cross split/
  embargo boundaries.
- **Train is descriptive only; validation performs selection.**
- Sealed data cannot choose \(N,M,H\), instrument, direction, control rule, or interpretation.

## 9. Primary inference

For each instrument, \(N,M,H\), event class (later):

1. valid event count; 2. valid control count; 3. event rate; 4. \(\bar y_{\mathrm{event}}\);
5. \(\bar y_{\mathrm{control}}\); 6. \(\Delta=\bar y_{\mathrm{event}}-\bar y_{\mathrm{control}}\);
7. aligned event mean \(\bar z_{\mathrm{event}}\);
8. aligned difference \(\Delta_z=\operatorname{ExpectedSign}\cdot\Delta\);
9. directional hit rate \(\frac{1}{n}\sum \mathbf{1}\{z_e^{(H)}>0\}\);
10. intercept-plus-event-indicator regression on combined event/control samples with HAC/Newey–West
    covariance `maxlags = H-1`, two-sided p-value — record \(\Delta\), SE, t, p.

## 10. Non-overlap robustness

For every specification and event class:

1. Order valid events and controls by internal index.
2. Retain the earliest valid eligible observation.
3. Exclude every subsequent event/control start within the next \(H-1\) bars.
4. Continue sequentially.
5. Compute separate non-overlap event/control counts, aligned difference, and hit rate.
6. Non-overlap aligned difference **must have favorable sign** for a configuration to survive
   validation.

No random subsampling, bootstrap, alternate HAC lag, or additional robustness filter.

## 11. Validation multiplicity family

The primary H6 validation family contains
\(7\ \text{instruments} \times 3N \times 3M \times 3H \times 2\ \text{event classes} = 378\) tests. All
378 records must be reported, **including insufficient-event records**. Apply **Benjamini–Hochberg
FDR q = 0.10** to numeric primary HAC p-values. Report: total configurations; numeric p-value count;
insufficient/not-testable count; raw p-value; BH rank; adjusted q-value; BH pass/fail. Do **not**
remove tests from the family after observing results.

## 12. Validation survivor rule

A bound configuration `instrument, N, M, H` survives only when **both** event classes independently
satisfy: 1. ≥30 valid events; 2. ≥200 valid controls; 3. favorable unaligned \(\Delta\) sign;
4. positive aligned event mean; 5. positive aligned difference; 6. HAC two-sided p < 0.05;
7. BH adjusted q ≤ 0.10; 8. favorable non-overlap aligned-difference sign. The two failed-breakout
classes are **required together** and cannot be selected independently.

## 13. Selection

From all validation survivors, rank by: 1. lower maximum BH q-value across the two event classes;
2. lower maximum raw HAC p-value; 3. larger minimum absolute aligned difference; 4. larger minimum
valid event count; 5. lexicographically smallest instrument symbol; 6. smaller \(N\), then \(M\), then
\(H\). Select **at most three** bound configurations across all instruments.

If zero configuration survives validation → `REJECT_FAILED_BREAKOUT_STATISTICAL_VIABILITY` and **no**
sealed event/outcome statistics are computed.

## 14. Sealed confirmation

For each selected configuration only, test the same instrument, \(N,M,H\) and **both** event classes
once on sealed. Each class must independently satisfy: 1. ≥30 valid events; 2. ≥200 valid controls;
3. favorable \(\Delta\); 4. positive aligned event mean; 5. positive aligned difference; 6. HAC
two-sided p < 0.05; 7. favorable non-overlap aligned difference.

```text
APPROVE_FAILED_BREAKOUT_STATISTICAL_VIABILITY
```
only if both classes pass every criterion; otherwise
`REJECT_FAILED_BREAKOUT_STATISTICAL_VIABILITY`. Hash/input/technical failure →
`PAUSE_FAILED_BREAKOUT_STATISTICAL_VIABILITY`.

## 15. Decision meaning

- **Approval** supports only a separately authorized design of a later **cost-aware economic test**.
- It does **not** show profitability, tradability, or permission to trade.
- Costs, spreads, commissions, slippage, swaps, leverage, execution, fills, position sizes, exits,
  stops, capital allocation, drawdown, Sharpe, PnL, and backtesting remain **untested**.
- **Rejection** applies only to the specific instrument/H1/H6 configuration and does not reject all
  breakout or reversal behavior generally.
