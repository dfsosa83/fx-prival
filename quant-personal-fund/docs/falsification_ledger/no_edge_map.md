# Falsification Ledger — No-Edge Map

**Status:** Permanent reference  
**Source:** Q4 2026 research program (legacy project "frival")  
**Preserved:** 2026-09-22

This document preserves the specific, verified findings from the prior research program. Each entry documents a research family that was tested and falsified, including the specific mechanism of failure. These findings constrain future research: no experiment may reopen a closed family without demonstrating a genuinely different economic mechanism, information source, horizon, and evaluation framework.

---

## Family 1: Directional H1 Entry ML (triple-barrier hit/miss labels)

**Status:** CLOSED  
**Experiments:** EXP-2026-05 (EURUSD SELL, HOLD), EXP-2026-06 (EURUSD BUY, STOP), P0.2 retrofit (all 4 pairs → STOP), EXP-2026-08 (US30 SELL, STOP), EXP-2026-09 (US30 geometry redesign, STOP)

**Why it fails:**
- Costs dominate small-target FX signals (~0.4R friction on ~3-pip stops).
- The model family shows ranking skill (US30 AUC 0.66→0.69) but an **irreducible precision ceiling**: skill cannot convert to breakeven precision at any target width.
- Within the fired subset, correlation between model score and outcome is ≈0 — no usable operating point exists in the tradeable region.
- The triple-barrier hit/miss label itself is the binding constraint, not costs, not instrument, not barrier width.

**What is NOT a new hypothesis:**
- Different currency pair (changes noise, not mechanism).
- Different TP/SL multiplier (EXP-2026-09: skill↑, precision↓).
- Different classifier (same features → same label → same constraint).
- Different class weights, thresholds, training windows, or feature sets.
- Any label variant that remains a directional hit/miss prediction at H1 on OHLC-derived technical features.

**What WOULD be a new hypothesis:**
- A different information source (macro data, positioning, cross-asset signals).
- A different target variable (regime, volatility, correlation, drawdown probability).
- A materially longer horizon where the cost-to-signal ratio changes by an order of magnitude.
- A portfolio-level risk or allocation problem, not a single-instrument entry prediction.

---

## Family 2: FX Crosses as Diversification (same label family)

**Status:** CLOSED  
**Experiment:** EXP-2026-07 (ABORTED on economics)

**Why it fails:**
- Arithmetic, not tuning. Measured spreads of 4.7–13.6 pips consume 0.53–0.56R per trade against ATRs of 8–26 pips.
- Forces ~62% breakeven precision — the model family achieves 35–39%.
- Widening TP to reduce the spread/ATR ratio collapses the cost-adjusted label rate below the 15% floor.
- No TP/SL geometry rescues it.

**What is NOT a new hypothesis:**
- Testing a different cross pair (substitutes one arithmetic handicap for another).
- Testing at a different session (ATR also shrinks in thin sessions; ratio is approximately preserved).

---

## Family 3: Manual Gold Trading + Mechanical Exit Optimization

**Status:** CLOSED  
**Experiments:** Real account statement (139 trades, −$815, PF 0.94, max DD 107%), EXP-2026-10 (operator-SL-anchored exits, STOP), EXP-2026-11 (ATR-anchored exits, STOP)

**Why it fails:**
- The entries have no demonstrable edge (net −$815, 55% win rate but avg loss > avg win).
- Mechanical exits do not create edge where none exists in entries.
- The one apparently positive exit configuration (+$8,689, PF 1.15 at 1×ATR/3R) was an artifact of 3 tail trades concentrated in a single week. Top-3 trade removal → −$4,325. Simulated max DD → −$58,697.

**What is NOT a new hypothesis:**
- Any exit policy anchored to the same manual entry decisions.
- Adding a trend filter or volatility condition to entries that still lack edge.
- Changing the exit multiplier (already tested monotonically: all killed by robustness).

---

## Family 4: Cross-Sectional Momentum (weekly relative strength)

**Status:** CLOSED  
**Experiment:** EXP-2026-12 (not supported)

**Why it fails:**
- All 6 cells net-negative in 2025+.
- The only gross-positive cell (L=20) was entirely 2022-driven (+0.068 of +0.081).
- Effect is ≈ 0 in recent regimes, not "present but costly."

**What is NOT a new hypothesis:**
- Different lookback window (± a few weeks).
- Different instrument subset from the same universe.
- Different ranking or weighting scheme that does not change the information source.

---

## Family 5: Macro-Event Reaction (scheduled surprise → price)

**Status:** CLOSED  
**Experiment:** EXP-2026-13 (FX null + XAUUSD regime-only)

**Why it fails:**
- FX prices-in scheduled macro surprises within 1 hour (all ≤0, −0.8 to −1.8 bp).
- XAUUSD showed a 2025-only effect (+4.9 bp, CI [+2.3, +7.7]) that disappeared in 2026 (+1.1 bp, CI [−6, +8]).
- 24-hour cells are approximately half unconditional gold drift.

**What is NOT a new hypothesis:**
- Different event calendar (NFP instead of FOMC).
- Different window (4h instead of 1h).
- Different FX pair.
- The core finding is about the speed of information incorporation, not the specific event.

---

## Family 6: Gold Rules Engine (automated A/B level-test)

**Status:** CLOSED — measurement failure  
**Experiment:** EXP-2026-03 (never traded)

**Why it fails:**
- The gold rules engine ran in demo mode with a broken evidence loop: simulated orders but real-position exit check → every trade self-closed in ~1 minute with PnL $0.00.
- Produced zero usable PnL evidence — a measurement failure, not a market result.
- The engine itself may or may not have edge, but it cannot be assessed without fixing the evidence loop.

**What is NOT a new hypothesis:**
- Any gold strategy evaluated against the engine's current zero-PnL journal.

---

## Family 7: ML Volatility-Forecast Sizing Overlay (price features only)

**Status:** CLOSED  
**Experiment:** EXP-2026-01-VOL-FORECAST-OVERLAY (2024-09-23)

**Why it fails:**
- LightGBM vol-forecast model with noise-voting feature selection, trained on lagged price-derived features (returns, realized/EWMA vol, candle structure, RSI), applied as conditional exposure scaling.
- Result: Sharpe 0.27 full / 0.69 test vs baseline 0.53 full / 1.06 test. Max DD worse (−19.1% vs −16.7%). Cost-to-gross doubled (60.5% vs 29.6%).
- The vol forecast is **reactive, not predictive**: rolling-window features detect elevated vol only after it arrives. De-risking then misses the initial rise and the rebound, while paying extra turnover.

**What is NOT a new hypothesis:**
- Re-tuning the model, changing the scaling sensitivity k, or changing the min/max scale bounds.
- Using different rolling-window lengths for the same price-derived features.

**What WOULD be a new hypothesis:**
- A genuinely different information source (macro data — tested separately, Family 8).
- A different risk target (correlation forecast, drawdown probability).

---

## Family 8: ML Volatility-Forecast Sizing Overlay (FRED macro features)

**Status:** CLOSED  
**Experiments:** EXP-2026-02 (continuous de-risking, HOLD → superseded), EXP-2026-03 (selective top-decile de-risking, STOP)

**Why it fails:**
- EXP-2026-02: FRED macro features were genuinely selected (11–18 per instrument), confirming the information source is real — but continuous de-risking destroyed value by reducing exposure during recovery as well as the elevated regime (Sharpe 0.33 full / 0.83 test; max DD −19.2%).
- EXP-2026-03 (selective top-decile de-risking): changed ONLY the sizing rule — de-risk to 0.5× only when forecast vol exceeded its trailing 252-day 90th percentile. Result: Sharpe 0.35 full / 0.77 test, max DD −19.1%, cost/gross 50.4%. The de-risk mechanism improved cost efficiency but STILL failed the pre-registered gate (Sharpe ≥ 0.55, max DD > −0.167).
- De-risking to cash on forecast vol — whether continuous or selective — costs more in missed recovery than it saves in avoided drawdown. The overlay never made drawdown strictly better than passive (always ≥ −19%).

**What is NOT a new hypothesis:**
- Re-tuning derisk_scale, quantile threshold, or quantile window on the same forecast.
- Using a different model on the same features (LGBM vs RF vs NN — same information).
- Adding more macro series to the same feature pool.

**What WOULD be a new hypothesis (requires new economic mechanism):**
- Correlation-forecast or drawdown-probability targets (different risk quantity).
- De-risking into defensives (bonds/USD) instead of to cash — maintaining return during elevated regimes.
- A different base portfolio than equal-weight (e.g., risk-parity) where the overlay's interaction may differ.

---

## Cross-Cutting Lessons

1. **Costs dominate small-target strategies.** At 2–8 pip targets and 1.2–1.6 pip spreads, friction consumes the signal. This is not fixable by better modeling — it is arithmetic.

2. **Ranking skill without actionable precision is a diagnostic, not an edge.** US30 AUC 0.69 is real but useless: the model's skill discriminates vetoed bars from fired bars, not good trades from bad trades within the fired set.

3. **A trustworthy null beats a false positive.** Three times in Q4 the naive gate said GO and the audit said no. The audit reflex (top-trade removal, year splits, unconditional baseline) caught all three.

4. **The triple-barrier hit/miss label at H1 is the binding constraint.** Six experiments across FX and indices, with varying geometries, costs, and instruments, all failed to convert ranking skill into breakeven precision. The label family, not the instrument or the model, is the ceiling.

5. **Passive diversification is a strong benchmark.** Equal-weight across 18 global assets returned +2.4%/yr (Sharpe 0.53) over 2015–2026 with near-zero costs. Every active strategy tested — trend, FX carry/value, ML vol overlay — failed to beat it net of costs.

6. **Lagged technical features are reactive, not predictive.** Rolling-window volatility features detect elevated regimes only after they arrive. De-risking on such forecasts misses the rise and the rebound. A genuinely predictive source must lead the regime, not lag it.

7. **New information sources can carry signal even when the mechanism fails.** FRED macro features were selected by the noise-voting procedure in 11–18 per instrument and improved the vol overlay — but the sizing mechanism was too blunt to convert that information into net value. Information ≠ tradeable edge.

8. **De-risking to cash costs more than it saves.** Whether continuous (EXP-2026-02) or selective top-decile (EXP-2026-03), scaling exposure to cash on a volatility forecast never made drawdown strictly better than passive (−19.1% vs −16.7% best case) while always costing return. Any future risk overlay must either rotate into defensives rather than cash, or target a different risk quantity.

9. **The platform verdict is definitive for the tested strategy space.** After 10 pre-registered experiments across trend, carry/value, and ML vol overlays (2 information sources × 3 mechanisms), NO active strategy has beaten passive equal-weight net of costs on 2015–2026 data. New research on this platform requires a new economic mechanism, not a new parameterization.

---

*This ledger is a permanent reference. Every new experiment manifest must cite why its hypothesis does not contradict the findings listed here (`why_existing_results_do_not_already_reject_it` field).*

---

## Supersession Pointer — EXP-2026-04A (2026-09-23)

The benchmark used to produce the verdicts in Families 5, 7, 8 and the cross-cutting lessons has been corrected by EXP-2026-04A:

- **H9 fixed:** USD base-currency conversion now applied to non-USD assets (SX5E, NKY, EURJPY). JPY-leg returns materially reduced (−238 to −370 bps/yr).
- **H1 fixed:** financing is no longer double-charged (removed from transaction costs; daily-holding-only).
- **H5 fixed:** the benchmark is now either Benchmark A (USD buy-and-hold) or Benchmark B (USD monthly-rebalanced, PRIMARY) with economically tracked drift and real transaction costs.
- **Universe corrected:** US10Y, BUND, JGB excluded (bonds/REIT heterogeneous leg removed; ADR-003 proposal for a future homogeneous solution).

**Status of prior verdicts:** The strategy verdicts (trend HOLD, carry/value HOLD-as-zero-swap-proxy, ML vol STOP) are **PRESERVED append-only but NOT yet re-evaluated** on the corrected benchmark. Re-evaluation is EXP-2026-04B, which is gated on user approval of the 04A report. No verdict is rewritten by this pointer.

---

## Supersession Pointer — EXP-2026-04B (2026-09-23)

The corrected-accounting re-evaluation (15-instrument USD, Benchmark B, accounting v2) produced:

| Sleeve | 04B outcome | Status |
|---|---|---|
| Trend | Sharpe 0.259 vs B 0.503; selection-driven underperformance | **Prior HOLD CONFIRMED** |
| EXP-2026-01 (price vol overlay) | HOLD — Sharpe 0.502 at parity with B (CI includes 0) | **Prior STOP SUPERSEDED by HOLD** |
| EXP-2026-03 (macro selective derisk) | STOP — literal historical gate fires on max DD −25.9% ≤ −0.167 | **Prior STOP CONFIRMED** |
| Carry/value | Not rerun; preserved as zero-swap spot proxy | **UNRESOLVED / PRESERVED** |

**Key update to cross-cutting lessons:** the blanket "ML volatility overlays do not work" conclusion (Families 7–8) is **partially superseded** — the price-feature overlay is neutral at corrected-benchmark parity, while the macro-selective overlay still fails on drawdown. The prior Family 7/8 verdicts remain the historical record; this pointer records the corrected re-evaluation. See `experiments/EXP-2026-04B-STRATEGY-RERUNS/reports/` for full evidence.