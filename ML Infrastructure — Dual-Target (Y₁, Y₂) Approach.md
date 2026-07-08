# ML Infrastructure — Dual-Target (Y₁, Y₂) Approach

*Design note — new ML core for the FX risk-aware trading system*

---

## 1. Purpose

This document defines a **new machine-learning infrastructure** built around two coordinated targets:

- **Y₁** — the *primary trading signal* (BUY / SELL / NEUTRAL) for a single FX pair.
- **Y₂** — the *hedge / risk-adjustment decision* (hedge / no-hedge) evaluated only when Y₁ fires.

The ML layer is being **redesigned from scratch** around Y₁ and Y₂. The existing **agent flow** (Perplexity validation, OpenAI "Senior Agent", MT5 execution, MonoBot) is **kept as-is for now** and only re-wired where it must consume the new outputs. We will revisit the agent flow later in development.

This replaces the current per-agent MCD model (LightGBM + XGBoost + meta stack producing `confir_buy` / `confir_sell`) with a cleaner, purpose-built dual-target design.

---

## 2. What we keep vs. what we change

| Layer | Current system (`feature/validation-agent`) | New approach |
|---|---|---|
| **Directional ML** | MCD model: separate buy/sell stacks → `confir_buy` / `confir_sell` → 27-combo `calc_final_action` matrix | **Y₁ model**: BUY & SELL sub-models → 3-state signal (BUY / SELL / NEUTRAL) |
| **Risk / hedge ML** | *None* (risk handled ad-hoc in lot sizing + Senior Agent) | **Y₂ model**: binary hedge decision at portfolio level |
| **LLM validation** | Perplexity (buy + sell adversarial) | **Keep** (consumes Y₁ output) |
| **Senior risk gate** | OpenAI GPT-4o `senior_agent.py` | **Keep** (now also sees Y₂ hedge recommendation) |
| **Execution** | MT5 `sendOrder` + MonoBot | **Keep** |
| **Scheduling** | `live_trading_scheduler.py` | **Keep** |

> **Design principle:** the ML layer produces *decisions and confidences*; the agent layer *validates and executes*. The interface between them is a small, stable contract (Section 6) so either side can evolve independently.

---

## 3. Target definitions

### 3.1 Y₁ — Primary signal

**Horizons** (aligned to the desk's low-frequency style):
- **H1**: each bar = 1 hour, predict move over next **10 bars (10 hours)**. ← *start here*
- **D1**: each bar = 1 day, predict move over next **5 bars (~1 trading week)**. ← *Phase 2 extension only; do not build in parallel with H1*

**Future return** over horizon $h$:

$$
r_{t \to t+h} = \frac{Close_{t+h} - Close_{t}}{Close_{t}}
$$

**Three-state label** (thresholds expressed in pips / ATR / R-units so signals are economically meaningful):

- **BUY** when 
  \[
  r_{t \to t+h} \ge \theta^{+}
  \]
  

- **SELL** when 
  \[
  r_{t \to t+h} \le \theta^{-}
  \]
  

  

- **NEUTRAL** when 
  \[
  \theta^{-} < r_{t \to t+h} < \theta^{+}
  \]
  

**Two sub-models per pair per horizon** (keeps the interpretable, robust structure the current system already uses):

- **BUY model** → "BUY vs NO-BUY"
- **SELL model** → "SELL vs NO-SELL"

Each outputs a calibrated probability. The 3-state signal + a **confidence score** are derived from the two probabilities.

### 3.2 Y₂ — Hedge / risk-adjustment decision

Evaluated **only when Y₁ = BUY or SELL**. Binary:

- **Y₂ = 1** → apply a companion/hedge position (e.g. a USDJPY position alongside a long EURUSD) sized to reduce or redistribute currency-factor risk.
- **Y₂ = 0** → run the primary trade only.

Y₂ is a **portfolio-level** decision, not a naive opposite trade. It looks at net currency exposure, cross-pair correlation regime, and volatility to decide whether a companion trade improves the book's risk-adjusted profile.

---

## 4. ML design

### 4.1 Data

- **Source**: MT5 OHLCV export (same `Export_<PAIR>_H1.csv` / `_D1.csv` pipeline already in place).
- **Pairs**: start with the current agent set (EURUSD, USDJPY, GBPUSD, USDCHF, USDCAD, AUDUSD, NZDUSD, EURAUD, EURCHF, AUDJPY). XAUUSD kept separate (different pip math).
- **Point-in-time discipline**: all features computed only from data available at bar close; labels use *future* returns and must never leak into features.

### 4.2 Features

**Y₁ features** (per pair, reuse existing `feature_engineering` where possible):
- Trend: SMA/EMA (10/20/50/100/200), Ichimoku, ADX
- Momentum: RSI, Stochastic, MACD, ROC, CCI, Williams %R
- Volatility: ATR, Bollinger width, rolling std
- Structure: lagged closes/volumes, price-change features, time-of-day / day-of-week

**Y₂ features** (portfolio-level, new):
- **Net currency exposure** (EUR, USD, JPY, … before and after the proposed Y₁ trade)
- **Rolling cross-pair correlations** (e.g. EURUSD vs USDJPY over 60 / 120 / 250 windows)
- **Per-factor volatility** (ATR / std per pair and per currency factor)
- **Regime / event flags** (proximity to high-impact macro events, volatility regime bucket)

### 4.3 Models

- **Baseline**: gradient boosting (XGBoost / LightGBM) — fast, interpretable, matches current stack.
- **Calibration**: probability calibration (Platt / isotonic) so thresholds are meaningful; optionally **conformal prediction** for coverage-controlled confidence (the repo already forks a conformal-prediction reference).
- **Interpretability**: SHAP values retained for every model — required for risk sign-off.

Y₂ label bootstrapping: start with a **rule-based label** (hedge = 1 when net USD exposure > threshold **and** USD-pair volatility elevated **and** correlation structure historically reduces portfolio variance), then train an ML model to *replicate and refine* it.

### 4.4 Confidence & sizing hook

Y₁ confidence + Y₂ decision feed the existing signal-strength / position-sizing logic. Recommended mapping:

| Y₁ confidence | Signal tier | Position multiplier |
|---|---|---|
| ≥ 0.80 | STRONG | 1.25× |
| 0.65–0.80 | MODERATE | 1.0× |
| 0.55–0.65 | WEAK | 0.5× |
| < 0.55 | NEUTRAL | no trade |

Y₂ = 1 adds a companion position sized as a fraction of the primary notional (calibrated per risk profile).

---

## 5. Training & validation methodology

1. **Walk-forward (expanding window)** splits — never random shuffles. Train on `[0, t]`, validate on `(t, t+k]`, roll forward.
2. **Point-in-time labels** — future-return labels computed strictly forward; drop the last `h` bars of each split (they have no complete label).
3. **No leakage between Y₁ and Y₂** — Y₂ training conditions on realistic (noisy) Y₁ outputs, not on ground-truth Y₁ labels, so deployment behavior matches training.
4. **Cost-aware evaluation** — metrics net of spread + slippage; report per-pair hit rate, expectancy (R), Sharpe/Sortino, max drawdown, and hedge effectiveness (portfolio variance / drawdown with vs without Y₂).
5. **Baselines** — always compare against: (a) Y₁-only (no hedge), (b) no-ML rule baseline, (c) buy-and-hold.

---

## 6. Integration contract (ML → agents)

The ML layer writes a single structured record per pair per cycle that the agent flow consumes. Keeping this contract small lets us change either side later.

```json
{
  "datetime": "2026-07-01T15:00:00Z",
  "pair": "EURUSD",
  "horizon": "H1",
  "y1_signal": "buy",            // buy | sell | neutral
  "y1_confidence": 0.78,
  "y1_prob_buy": 0.78,
  "y1_prob_sell": 0.06,
  "signal_tier": "MODERATE",
  "position_multiplier": 1.0,
  "y2_hedge": 1,                  // 0 | 1  (only meaningful if y1_signal != neutral)
  "y2_hedge_pair": "USDJPY",
  "y2_hedge_confidence": 0.64,
  "atr": 0.00071
}
```

Flow after the ML layer (unchanged in spirit):

```
Y₁ + Y₂ record
      │
      ├─► Perplexity buy/sell agents   (validate Y₁ direction)
      │
      ├─► calc_final_action            (now driven by Y₁ signal + confidence, not confir_buy/confir_sell)
      │
      ├─► position sizing              (uses Y₁ tier + Y₂ hedge)
      │
      ├─► Senior Agent (GPT-4o)        (sees primary trade + Y₂ hedge proposal)
      │
      └─► sendOrder (MT5) + MonoBot    (primary + optional companion order)
```

---

## 7. Proposed repository structure

A dedicated ML service, decoupled from the trading/agent code:

```
ml-signal-service/
├── config/
│   ├── pairs.yaml               # pairs, horizons, thresholds (θ+, θ-)
│   └── training.yaml            # walk-forward params, model hyperparams
├── data/
│   ├── raw/                     # MT5 exports (Export_<PAIR>_<TF>.csv)
│   ├── features/                # engineered feature tables
│   └── labels/                  # Y1 and Y2 label tables
├── src/
│   ├── features/
│   │   ├── y1_features.py       # per-pair technical features
│   │   └── y2_features.py       # portfolio exposure/correlation features
│   ├── labels/
│   │   ├── y1_labels.py         # 3-state future-return labels
│   │   └── y2_labels.py         # rule-based hedge labels (bootstrap)
│   ├── models/
│   │   ├── y1_buy.py / y1_sell.py
│   │   └── y2_hedge.py
│   ├── training/
│   │   ├── walk_forward.py      # expanding-window splits
│   │   └── calibrate.py         # probability calibration / conformal
│   ├── inference/
│   │   └── predict.py           # writes the Section 6 contract record
│   └── evaluation/
│       └── backtest.py          # cost-aware metrics + hedge effectiveness
├── models_bin/                  # serialized Y1/Y2 models per pair/horizon
└── notebooks/                   # research & validation
```

Trained artifacts are consumed by the existing agent scripts via the `inference/predict.py` output — no changes required to Perplexity/Senior/MT5 internals beyond reading the new record.

---

## 8. Roadmap (phased)

| Phase | Scope | Outcome |
|---|---|---|
| **P0** | Scaffold `ml-signal-service`, wire MT5 export → feature/label tables for 1 pair (EURUSD, H1) | Reproducible data pipeline |
| **P1** | Build & calibrate **Y₁** BUY/SELL sub-models for EURUSD; walk-forward + cost-aware backtest | Y₁ baseline vs buy-and-hold |
| **P2** | Extend Y₁ to all pairs + D1 horizon | Full Y₁ coverage |
| **P3** | Rule-based **Y₂** labels + ML Y₂ model; measure hedge effectiveness | Portfolio risk reduction proven |
| **P4** | Wire Y₁/Y₂ contract into existing agent flow (Perplexity + Senior Agent read new record) | End-to-end on demo account |
| **P5** | Revisit agent layer (prompts, thresholds) now that ML core is trustworthy | Optimized full system |

---

## 9. Open questions (to resolve during development)

1. **Y₂ label leakage** — the rule-based bootstrap must be strictly point-in-time; validate that no realized-outcome info leaks into the hedge label.
2. **Threshold tuning** — θ⁺ / θ⁻ per pair via walk-forward, not in-sample. Concrete approach: set `θ⁺ = k × ATR_H1` (ATR is the volatility ruler, not the prediction target) and validate with a percentile check — aim for ~25% BUY / 25% SELL / 50% NEUTRAL across the training set. If the split is far from that, adjust `k`. Too tight → all NEUTRAL; too loose → noisy signals and class imbalance.
3. **Correlation regime instability** — static rolling windows break in stress regimes; consider regime buckets or a DCC-style estimator for Y₂.
4. **Joint vs. sequential training** — Y₂ conditions on Y₁; confirm training on *noisy* Y₁ outputs to avoid cascading bias.
5. **Model staleness** — define a retraining cadence (the current system has pre-trained `.sav` blobs with no retrain pipeline).

---

## 10. Summary

- The ML core is rebuilt around **Y₁ (signal)** and **Y₂ (hedge)** as first-class targets.
- The proven **agent flow (Perplexity + OpenAI Senior Agent + MT5 + MonoBot) is preserved**, consuming a small, stable ML output contract.
- A dedicated **`ml-signal-service`** keeps ML concerns separate from trading/agent code.
- Delivery is phased: prove Y₁ on one pair first, expand, add Y₂, then integrate, then re-tune the agent layer.



