# EURUSD Buy Model — v2 Changes & Explanations

## Overview

`eurusd_buy_v2.ipynb` is an improved version of `eurusd_buy.ipynb`.  
Five targeted changes were applied to raise the model's precision above the breakeven threshold and make it more robust for deployment.

---

## Change 1 — Fix Same-Bar Ambiguity in Label Generation
**Cell:** Section 6 · `generate_buy_labels()`  
**Recommendation:** REC #1

### What changed
In the original notebook, when both the TP level (`high >= TP`) **and** the SL level (`low <= SL`) were touched on the **same H1 bar**, the label was forced to `0` (a loss).

In v2, those bars are assigned `NaN` and **dropped** from the dataset entirely.

### Why it matters
An H1 bar can span several dozen pips. When both TP and SL are touched in the same bar, we have no way of knowing which was hit first without sub-hourly (M15/M5) data. Forcing `label = 0` creates **false negatives** — trades that may have been winners are recorded as losers. This silently caps the maximum precision the model can ever learn, because it is being trained on corrupted ground truth.

Dropping ambiguous bars removes the noise without introducing bias in either direction.

| Outcome | Original | v2 |
|---|---|---|
| `high >= TP` AND `low <= SL` (same bar) | `label = 0` (false negative) | `label = NaN` → **excluded** |
| `high >= TP` only | `label = 1` | `label = 1` (unchanged) |
| `low <= SL` only | `label = 0` | `label = 0` (unchanged) |
| No hit within forward window | `label = 0` | `label = NaN` → **excluded** |

---

## Change 2 — Threshold Selected by Precision Margin, Not Max Recall
**Cell:** Section 8.3 · Threshold Calibration  
**Recommendation:** REC #2

### What changed
The original code scanned the Precision-Recall curve and picked the threshold with the **highest recall** that still cleared breakeven — i.e. the loosest threshold that barely worked on validation.

v2 sorts viable thresholds by **precision margin** (how far above breakeven the precision sits) and picks the one with the **largest buffer**. A minimum signal floor (`MIN_SIGNALS_PER_DAY = 0.3`) ensures the strategy stays tradeable.

A **read-only cross-check on the test set** is also added: the chosen threshold is evaluated on sealed test data to confirm it generalises. The threshold is **never retuned** on the test set — that would be data leakage.

### Why it matters
The loosest threshold that clears breakeven is the most fragile point on the PR curve. Any small distribution shift (new volatility regime, spread widening) will push precision below breakeven and make the strategy lose money. Selecting by margin gives a safety buffer and produces a threshold that is more likely to hold in live trading.

---

## Change 3 — Wider R:R Ratio (ATR_TP_MULT 1.75 → 2.0)
**Cell:** Section 1 · Configuration  
**Recommendation:** REC #3

### What changed
`ATR_TP_MULT` was changed from `1.75` to `2.0`.

### Why it matters
Breakeven precision is calculated as:

$$\text{Breakeven} = \frac{SL\_mult}{TP\_mult + SL\_mult}$$

| Setting | Breakeven |
|---|---|
| TP × 1.75, SL × 1.0 (original) | **36.4%** |
| TP × 2.0, SL × 1.0 (v2) | **33.3%** |

The model needs to be correct on **3 percentage points fewer** trades to be profitable. This is a meaningful reduction — the difference between a model that barely misses breakeven and one that clears it comfortably.

---

## Change 4 — Probability Calibration
**Cell:** Section 8.2b · Probability Calibration (new cell inserted after final model fit)  
**Recommendation:** REC #4

### What changed
After fitting the final LightGBM model, v2 wraps it with `CalibratedClassifierCV(method="isotonic", cv="prefit")`.

The calibration is fit on the **last 15% of training data** (chronological holdout), while the base model is refit on the remaining 85%. This means:
- No overlap with validation or test sets (no leakage).
- The calibrator sees only out-of-sample data relative to the base model.

### Why it matters
Tree-based models like LightGBM produce **uncalibrated probabilities**. A raw score of `0.65` does not mean the model is 65% confident — it is an arbitrary output of the boosting algorithm. This makes threshold selection unreliable: two thresholds that look equally good on the PR curve may behave very differently in practice.

After isotonic calibration, the output probabilities are closer to true win rates, which means:
1. The threshold has a meaningful interpretation.
2. High-confidence signals are more likely to be genuine.
3. The chosen cutoff is more stable across market regimes.

---

## Change 5 — Median Imputer Instead of fillna(0)
**Cell:** Section 8.1 (model matrices) — `X_train`, `X_val`, `X_test` construction  
**Recommendation:** REC #5

### What changed
The original code used `.fillna(0)` to handle missing values in the feature matrix.

v2 replaces this with `SimpleImputer(strategy="median")` from scikit-learn, fit **only on the training set**, then applied to all three splits (train, val, test).

### Why it matters
Many features in this notebook are z-scored, ratio-based, or centred (e.g. `close_vs_ema50`, `rsi_14 - 50`, `bb_pct`). For these features, `0` is a **real, meaningful value** — it means the price is exactly at the EMA, or RSI is neutral, or price is exactly at the Bollinger midpoint.

Filling missing values with `0` corrupts these features by injecting false signal at a neutral/boundary point. Using the **median** fills with the most representative observed value instead.

Fitting the imputer **only on train data** prevents the val/test distribution from leaking into the imputation step (a subtle but real form of data leakage).

---

## Summary Table

| # | Location | Original | v2 | Impact |
|---|---|---|---|---|
| REC 1 | `generate_buy_labels()` | Ambiguous bars → `label=0` | Ambiguous bars → excluded | Removes false negatives, raises precision ceiling |
| REC 2 | Threshold calibration | Sort by recall DESC (loosest) | Sort by precision margin DESC + test check | More robust threshold, confirmed on test set |
| REC 3 | Configuration | `ATR_TP_MULT = 1.75` → breakeven 36.4% | `ATR_TP_MULT = 2.0` → breakeven 33.3% | Lowers the bar the model must clear |
| REC 4 | After final model fit | Raw LightGBM probabilities | `CalibratedClassifierCV(isotonic)` | Probabilities become meaningful; threshold more stable |
| REC 5 | Model matrices | `.fillna(0)` | `SimpleImputer(median)` fit on train only | Correct imputation; no leakage from val/test |
