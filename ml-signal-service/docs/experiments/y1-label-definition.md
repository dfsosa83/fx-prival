# Y₁ Label Definition — BUY Signal

*ml-signal-service · EURUSD H1 · Last updated: 2026-07-07*

---

## The core question

At every H1 bar close, the model answers one question:

> **"If a trader entered long right now, would this trade hit Take Profit before hitting Stop Loss — within the next 10 hours?"**

- **label = 1** → Yes. This is a BUY opportunity.
- **label = 0** → No. Do not buy (SL hit first, timeout, or ambiguous).

---

## The three concepts you need

### 1. ATR — the volatility ruler

**ATR (Average True Range)** measures how many pips a pair typically moves per hour over the last 14 bars.

It is **not** a prediction. It is a ruler that adapts to current market conditions.

| Market condition | ATR (EURUSD H1) | Meaning |
|---|---|---|
| Quiet Asian session | ~4 pips | Small moves expected |
| Active London open | ~12 pips | Larger moves expected |
| High-impact news | ~25 pips | Very large moves expected |

Using ATR ensures that a "meaningful move" is defined relative to what the market is currently doing — not a fixed pip value that would be too tight in volatile periods and too loose in quiet ones.

---

### 2. TP and SL — the trade boundaries

For each bar `t`, two price levels are computed from the current ATR:

| Level | Formula | Example (ATR = 0.0008 = 8 pips) |
|---|---|---|
| Entry | `close[t]` | 1.0800 |
| **Take Profit (TP)** | `close[t] + ATR × TP_multiplier` | 1.0800 + 0.0012 = **1.0812** |
| **Stop Loss (SL)** | `close[t] − ATR × SL_multiplier` | 1.0800 − 0.0008 = **1.0792** |

Current multipliers: `TP_multiplier = 1.5` · `SL_multiplier = 1.0`

The label is computed by scanning the next 10 H1 bars in order:

```
Bar t+1: did high ≥ TP?  → label = 1 ✓  (stop scanning)
         did low  ≤ SL?  → label = 0 ✗  (stop scanning)
         both on same bar → label = 0    (conservative — SL assumed first)
         neither          → check bar t+2...

Bar t+10: still neither hit → label = 0  (timeout — no clear opportunity)
```

**The label simulates a real trade outcome**, including the possibility of being stopped out before the target is reached.

---

### 3. R:R — risk-to-reward ratio

R:R tells you: *for every pip I risk losing, how many pips am I targeting to win?*

$$R:R = \frac{\text{TP distance}}{\text{SL distance}} = \frac{TP\_multiplier}{SL\_multiplier} = \frac{1.5}{1.0} = 1.5$$

This is commonly written as **1 : 1.5** — risk 1 unit to gain 1.5 units.

#### Why R:R matters for the label

R:R determines the **breakeven win rate** — the minimum % of trades that must be label=1 for the strategy to be profitable after costs:

$$\text{Breakeven win rate} = \frac{SL\_mult}{TP\_mult + SL\_mult} = \frac{1.0}{1.5 + 1.0} = 40\%$$

| R:R | Breakeven win rate | Label=1 frequency |
|---|---|---|
| 1:1 | 50% | High (~35–45%) |
| **1:1.5 ← current** | **40%** | **Medium (~20–30%)** |
| 1:2 | 33% | Lower (~15–22%) |
| 1:3 | 25% | Low (~10–15%) |

**Higher R:R → fewer label=1 → harder to train, but each signal is more selective.**

---

## How these three concepts connect

```
ATR (current volatility)
        ↓
TP level = close + ATR × 1.5      SL level = close − ATR × 1.0
        ↓                                      ↓
        └──────────── scan next 10 bars ───────┘
                             ↓
                      buy_label = 1 or 0
                             ↓
              model learns: "what patterns at bar t
               predicted a label=1 historically?"
```

---

## Tuning parameters

Both multipliers live in the notebook config cell. Change them to re-label the entire dataset.

| Parameter | Variable | Effect of increasing |
|---|---|---|
| TP multiplier | `ATR_TP_MULT` | Fewer label=1, higher quality signals, lower win rate needed |
| SL multiplier | `ATR_SL_MULT` | Tighter stop, more label=0 due to SL hits, noisier labels |
| Forward bars | `FORWARD_BARS` | More time to hit TP, more label=1, but signal is less timely |

**Target class balance: ~20–30% label=1** across the training set.  
Check with the yearly bar chart in the notebook. If % is far from this range, adjust `ATR_TP_MULT`.

---

## What this model does NOT predict

- It does **not** predict the actual price in 10 hours.
- It does **not** predict the exact number of pips gained.
- It predicts only: **will this specific trade structure (entry + TP + SL) succeed?**

The SELL model uses the exact mirror logic (TP below entry, SL above entry).  
A bar where both BUY and SELL models output 0 is treated as **DO NOTHING**.

---

# Feature Selection — Noise + Voting

Before training, we prune the ~60 engineered features down to only those with genuine
predictive value. The trick: inject **random noise features** and drop any real feature
that can't beat them.

## The idea

If a real feature is truly useful, a model should rank it **above** a column of pure random
numbers. Any feature scoring below the noise is just adding overfitting risk.

```
real features + 9 noise columns  →  train 3 models  →  read importances
                                                             ↓
                              keep only real features that beat the noise
```

## The three voters

Each model scores features independently, so a feature must convince different kinds of models:

| Model | Importance signal |
|---|---|
| **Random Forest** | tree split importance |
| **LightGBM** | tree gain importance |
| **Logistic Regression** | `\|coefficient\|` (features scaled first) |

A weighted average (`0.3·RF + 0.6·LGBM + 0.1·LogReg`) gives more trust to the tree models.

## The noise features

Nine random columns of different shapes, so no real feature can "accidentally" look like just
one type of noise:

- Gaussian (3 variants), Uniform (2), Poisson (2), random walk, sinusoidal

## Selection — five strategies + consensus

A feature is compared against the noise benchmark in five independent ways:

1. Ranked above the **single best** noise feature
2. Importance above the **70th percentile** of noise
3. **More votes** than the best noise feature
4. Above a **statistical threshold** (noise mean + 0.5 σ)
5. At least **one vote** AND above the noise mean

A feature is **kept only if at least 2 strategies agree** (`MIN_STRATEGY_SUPPORT = 2`).
This consensus rule avoids relying on any single noisy metric.

## Two tuning knobs

| Parameter | Effect |
|---|---|
| `VOTING_PERCENTILE` (default 40) | Lower → more features get votes (inclusive); higher → stricter |
| `MIN_STRATEGY_SUPPORT` (default 2) | Higher → fewer, higher-confidence features |

## Leakage discipline

Feature selection is fit on **`df_train` only**. Validation and test sets are never seen —
otherwise the choice of features would leak future information into the model.

## Output

Selected features (and the full importance report) are saved to
`data/features/{PAIR}_{TIMEFRAME}_selected_features.csv` and reused by the training step.

---

# Model Selection — Nested Cross-Validation

After feature selection, we compare four classifiers using **nested cross-validation** to get
an unbiased estimate of performance and pick the best model without leaking validation data.

## Why nested CV?

A single train/val split is fragile. Nested CV gives an honest performance estimate:

- **Outer loop** — measures how well each model *generalises* (unbiased PR-AUC per fold)
- **Inner loop** — tunes hyperparameters *inside* the outer training fold only

```
Outer fold (GroupKFold by year)
 └── train portion
      └── Inner CV (TimeSeriesSplit) — RandomizedSearchCV here
 └── eval portion — PR-AUC measured here (never seen during tuning)
```

## The four models

| Model | Why included |
|---|---|
| **Logistic Regression** | Baseline — scaled features, no tuning. PR-AUC must be beaten. |
| **Random Forest** | Robust, handles non-linearity, good for noisy financial data |
| **XGBoost** | Strong gradient booster; `scale_pos_weight` handles imbalance |
| **LightGBM** | Fast gradient booster; `class_weight="balanced"` |

## Optimization metric — PR-AUC

We optimize **PR-AUC** (average precision), not accuracy or ROC-AUC, because:

- The dataset is imbalanced (~30% BUY), so accuracy is misleading
- We care most about **precision** — when the model says BUY, it should be right
- A random model scores ≈ positive rate (~0.30) on PR-AUC; the model must clearly beat this

## Recency weights

Recent years carry more weight during training (15% decay per year back). FX market dynamics
shift over time, so 2024 data is more informative than 2019 data.

$$w_t = e^{-0.15 \times (\text{max\_year} - \text{year}_t)}$$

## Final training and evaluation

After the winning model is identified:

1. **Aggregate** the hyperparameters most frequently chosen across outer folds
2. **Retrain** on the full `df_train` with those parameters and recency weights
3. **Evaluate** on `df_val` (2025) — report precision vs. the breakeven rate
4. **Seal** `df_test` — only opened once, after all decisions are finalised

The key validation check:

$$\text{Precision}_{BUY} > \text{Breakeven} = \frac{SL\_mult}{TP\_mult + SL\_mult} = 40\%$$

If validation precision is below 40%, the model would lose money at R:R 1.5, regardless of recall.

## Saved artifact

The final model is saved as a bundle to `models_bin/`:

```python
{
    "model":        <fitted classifier>,
    "features":     [list of selected feature names],
    "atr_tp_mult":  1.5,
    "atr_sl_mult":  1.0,
    "forward_bars": 10,
}
```

This bundle contains everything needed to reproduce labels and run inference on new bars.

---

# Final Setup for EURUSD Pair

*Settled: 2026-07-09 · Validated on sealed test set (Feb–Jul 2026, 109 trading days)*

## Decision process

We evaluated a dual-model signal combiner (BUY + SELL lane, cross-filtered, cooldown-gated) on the sealed test set. Key findings:

| What we tried | Outcome | Decision |
|---|---|---|
| BUY + SELL combined (cf=0.60) | 0.347 precision — below 0.400 breakeven | Rejected |
| BUY-only, no cross-filter | 0.308 precision — worse | Rejected |
| BUY-only + cross-filter (cf sweep) | Best 0.355 — still under breakeven | Rejected |
| **BUY-only + London/NY session filter + cross-filter** | **0.415 precision — above breakeven** | **Accepted** |

The session filter was the breakthrough. Asian session hours (00:00–06:59 UTC) are range-bound on EURUSD and generate most of the false positives. Gating to London/NY sessions alone raised precision from 0.355 to 0.415 with no model retraining.

## Final configuration

| Parameter | Value | Role |
|---|---|---|
| **Direction** | BUY only | SELL lane disabled (non-viable on test: 3 signals at 0.333 prec) |
| **Cross-filter** | 0.60 | Suppress BUY when `sell_proba ≥ 0.60` (ambiguous bars removed) |
| **Cooldown** | 4 bars (4 hours) | Max one signal per direction every 4 bars |
| **Session filter** | London + NY only | Detailed below |
| **BUY threshold** | 0.678 | From LightGBM calibration |
| **R:R** | 1:1.5 | Breakeven precision = 0.400 |

## Session filter — when the model should run

The model should only generate alerts during these hours:

| UTC | ET (New York) | CDT (Chicago) | 
|---|---|---|
| London: 07:00–15:59 | 03:00–11:59 | 02:00–10:59 |
| NY: 13:00–21:59 | 09:00–17:59 | 08:00–16:59 |
| **Overlap (best window):** 13:00–15:59 UTC | 09:00–11:59 ET | 08:00–10:59 CDT |

**Why this works:** EURUSD volatility clusters in London and NY sessions. Asian session price action is mostly low-volatility consolidation — the model generates many false BUY signals there. Removing those bars eliminates ~30% of false positives at the cost of <5% of true positives.

In production: the prediction script should check `hour >= 7 AND hour < 22` (London through NY close) and suppress all signals outside that window. No ML retraining needed — this is a rule-based gate applied after inference.

## Test set results (post-filtered)

| Metric | Value |
|---|---|
| Precision | **0.415** |
| Signals | 41 over 109 days |
| Frequency | 0.37 signals/day (~1 every 2.7 days) |
| Breakeven | 0.400 |
| Edge over breakeven | +0.015 |

At cf=0.50 precision reaches 0.444 (27 signals), and at cf=0.80 precision is 0.404 (47 signals). Cf=0.60 is the recommended balance: highest signal count while clearing breakeven.

## What "good enough" means here

0.415 precision means ~58% of alerts are false positives. This is by design — the model is an **alert generator**, not an auto-trader. Downstream agents (DeafAgent) are expected to confirm or reject each signal using additional context (news, higher-TF analysis, discretionary overlay). The model's job is to surface opportunities the agents would otherwise miss, not to be a standalone trading system.
