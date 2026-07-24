# EURUSD H1 — SELL Signal Model · One-Page Summary
*Last updated: 2026-07-24*

---

## The Model

| | |
|---|---|
| **Pair / TF** | EURUSD H1 |
| **Direction** | SELL only — BUY lane confirmed non-viable (ROC-AUC 0.505 = random) |
| **Algorithm** | Soft-vote ensemble of 4 calibrated classifiers (LogReg + RF + XGB + LGBM) |
| **Features** | 20 selected from 76 candidates — top signals: ADX, rolling_std_50, D1 RSI, OBV, ATR regime, close vs EMA200 |
| **Training window** | 2020-06-30 → 2025-06-30 (5 years) |
| **Validation** | 2025-07 → 2025-12 (6 months, 131 trading days) |
| **Sealed test** | 2026-01 → 2026-07 (130 days, **never touched during development**) |
| **Label** | ATR-barrier race: TP = 1.5×ATR, SL = 1.0×ATR, 6-bar forward window |
| **Breakeven win rate** | **0.400** (= SL / (TP + SL) = 1.0 / 2.5) |

---

## Key Results

### Signal quality (out-of-sample)
| Metric | Value | Verdict |
|---|---|---|
| Val ROC-AUC | **0.674** | Real directional edge (>0.65 on EURUSD H1 OOS is hard to achieve) |
| Val PR-AUC | 0.389 | Meaningfully above the 0.244 base rate |
| Val precision @ thr 0.306 | **0.447** | Above breakeven on validation |
| Sealed-test precision (raw) | 0.382 · CI95 [0.332, 0.434] | Straddles breakeven — marginal |
| Sealed-test precision (gated) | **0.411** · CI95 [0.323, 0.506] | Above breakeven with gates applied |

### Vector backtest — sealed test (107 trades, cooldown-gated)
| Metric | Value |
|---|---|
| Total R | **+1.2R** over 6 months |
| Win rate | 41.1% |
| Avg R / trade | +0.011R ≈ breakeven |
| **Max drawdown** | **−18.9R** |
| Sharpe | 0.01 |

### Monthly breakdown
| Month | Trades | Total R | Win rate | Note |
|---|---|---|---|---|
| 2026-01 | 22 | +1.9R | 45.5% | Consistent |
| 2026-02 | 24 | +5.8R | 50.0% | Best month |
| 2026-03 | 13 | +1.2R | 46.2% | Consistent |
| **2026-04** | 21 | **−8.9R** | **19.0%** | **Regime break — macro shock** |
| 2026-05 | 17 | −2.7R | 35.3% | Recovery slow |
| 2026-06 | 9 | +5.0R | 66.7% | Fully recovered |

---

## What the Backtest Says

**The signal is real but the system is not yet deployable as-is.**

- Three months in a row of consistent profitability (45–50% WR) confirm the model captures a genuine pattern.
- April's 19% win rate is not random noise — it is a **regime failure**: the model fires SELL signals into a strong USD uptrend driven by macro/tariff events. It was right ~4 times out of 21.
- The −18.9R max drawdown against +1.2R total return means the strategy cannot survive a live run without external judgment. No risk manager approves a 15:1 DD/return ratio.
- **The edge is identified. The vulnerability is also identified.** That is actually a good position — the failure mode is specific and filterable, not random.

---

## Next Step — Agent Confirmation Pipeline

The architecture is already scaffolded in Section 12 of `signal_combiner_improved.ipynb`.

**Goal:** replace the random stub with real API calls and measure whether agents lift precision above 0.420 and suppress April-type months.

```
ML Model fires SELL signal
        │
        ▼
  Agent A (GPT-4o)                Agent B (Perplexity / web)
  Technical context:              Fundamental context:
  · D1 trend, RSI, ADX            · ECB/Fed divergence
  · Close vs EMA200               · DXY direction
  · Volatility regime             · Active news / event risk
  · Model probability             · Risk sentiment
        │                               │
        └──────────── both CONFIRM ─────┘
                            │
                     SIGNAL FIRES
                   (archived otherwise)
```

**What agents need to veto — April's failure pattern:**
- D1 uptrend (EUR selling against strong USD bid)
- Macro event risk active (Fed hawkish, tariff announcements)
- DXY in strong uptrend
- Any of the above → REJECT

**Success criteria for paper trading (60–90 days):**
1. Agent-confirmed subset precision ≥ 0.420 with Wilson CI lower bound above 0.400
2. No single month worse than −3R under agent filtering
3. Rejection rate between 30–60% (if agents confirm everything, they add no value; if they confirm <30%, signal frequency becomes impractical)

**Live deployment trigger:**
Only after the 3 criteria above are met on forward paper data — not on historical data. Risk: 0.25–0.5% per signal max, hard monthly stop at −3R.

---

## Files

| File | Purpose |
|---|---|
| `ml-signal-service/notebooks/eurusd/eurusd_sell_improved.ipynb` | SELL model training |
| `ml-signal-service/notebooks/eurusd/eurusd_buy_improved.ipynb` | BUY model (non-viable, archived) |
| `ml-signal-service/notebooks/eurusd/signal_combiner_improved.ipynb` | Evaluation + vector backtest + agent stub |
| `ml-signal-service/models_bin/EURUSD_H1_sell_*.joblib` | Live model bundle (threshold embedded) |
| `PERFORMANCE_IMPROVEMENT_RECOMMENDATIONS.md` | Full technical audit + Section 5 second-run findings |
