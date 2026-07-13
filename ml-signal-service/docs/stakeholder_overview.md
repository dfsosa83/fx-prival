# EURUSD H1 Signal System — Stakeholder Overview

*Last updated: 2026-07-10*

---

## What this system does

Every hour, the system answers one question:

> **"Does this bar look like a good moment to go long on EURUSD?"**

If yes → it sends a BUY alert to the agent pipeline. If no → do nothing.

It is **not** an auto-trader. It is an alert generator. Downstream agents confirm or reject each alert using additional context.

---

## The Y₁ target — what exactly is the model predicting?

The model is trained on historical data to answer a concrete question:

| Question | Answer |
|---|---|
| *If I entered long right now, would price hit Take Profit before hitting Stop Loss?* | Yes → **label = 1** (good entry) |
| | No → **label = 0** (bad entry) |

The label is computed by simulating a real trade: from the current bar's close price, two boundaries are set — a **Take Profit** above and a **Stop Loss** below. The simulation scans forward 6 hours:

| Outcome within 6 hours | Label | Meaning |
|---|---|---|
| TP hit first (before SL) | **1** | Good entry — trade would have won |
| SL hit first (before TP) | **0** | Bad entry — trade would have lost |
| Neither hits | **0** | Unclear — entry didn't prove itself in time |

This is a **binary classification** problem: the model learns what market conditions historically preceded successful long entries.

### Important: the 6-hour window is for labeling, not for trade management

The 6-hour horizon is how we **judge past entries** during training. It does **not** mean a real trade closes automatically at 6 hours.

In production, the **agent** (not the model) decides what to do with an open trade:

| Scenario | Model says | Agent decides |
|---|---|---|
| TP hit within 6h | "Good entry" ✓ | Close in profit |
| SL hit within 6h | "Bad entry" | SL already protected capital |
| Neither hit after 6h | "Unclear entry" | Agent can: close manually, trail the stop, or hold longer |

The model only answers one question: *was this a good moment to enter?* It delegates trade management to the agent.

---

## Why we use ATR (not fixed pips)

**ATR = Average True Range** — how many pips EURUSD typically moves per hour, averaged over the last 14 hours.

| Without ATR | With ATR |
|---|---|
| Fixed TP = 12 pips, fixed SL = 8 pips | TP = 1.5 × current ATR, SL = 1.0 × current ATR |
| Same targets in quiet Asian session and volatile London open | Targets adapt to current market conditions |
| Too tight in volatile periods → stopped out early | Volatile = wider targets |
| Too loose in quiet periods → targets rarely hit | Quiet = tighter targets |

ATR is not a prediction. It is a **volatility ruler** — it measures what "a meaningful move" means right now.

---

## Fixed parameters (locked as of July 2026)

These values define the label and are baked into the model:

| Parameter | Value | Meaning |
|---|---|---|
| **Take Profit** | 1.5 × ATR | Target above entry |
| **Stop Loss** | 1.0 × ATR | Stop below entry |
| **Forward window** | 6 hours | Max time to hit TP or SL |
| **Risk:Reward** | 1 : 1.5 | Risk 1 to gain 1.5 |

From R:R we derive the **breakeven precision** — the minimum hit rate needed:

$$
\text{Breakeven} = \frac{\text{SL}}{\text{TP} + \text{SL}} = \frac{1.0}{1.5 + 1.0} = 40\%
$$

If the model's precision is above 40%, the alerts are net profitable before external filters.

---

## The 4 decision gates — when does an alert fire?

After the model scores every bar, **four rules** gate whether an alert is sent:

```
Every H1 bar
     │
     ▼
┌─────────────────────┐
│ Gate 1: THRESHOLD   │  buy_proba ≥ 0.678 ?
└───────┬─────────────┘
        │ YES
        ▼
┌─────────────────────┐
│ Gate 2: CROSS-FILTER│  sell_proba < 0.60 ?
└───────┬─────────────┘  (if SELL model also confident → bar is ambiguous → skip)
        │ YES
        ▼
┌─────────────────────┐
│ Gate 3: SESSION     │  Is it London or NY session ?
└───────┬─────────────┘  (Asian session = range-bound noise → skip)
        │ YES
        ▼
┌─────────────────────┐
│ Gate 4: COOLDOWN    │  Has it been ≥ 4 hours since last alert ?
└───────┬─────────────┘  (prevents multiple alerts on same move)
        │ YES
        ▼
     🔔 ALERT
```

### Gate 1 — Threshold (buy_proba ≥ 0.678)

The LightGBM model outputs a probability between 0 and 1. The threshold 0.678 was chosen to maximize precision above breakeven. Only bars where the model is at least 67.8% confident trigger alerts.

### Gate 2 — Cross-filter (sell_proba < 0.60)

A separate SELL model also scores every bar. If the SELL model thinks there's a ≥60% chance of a good short, the bar is **ambiguous** — both directions have merit. We skip it. This removes many false positives.

### Gate 3 — Session filter (London + NY only)

| Session | UTC hours | Why filtered |
|---|---|---|
| Asian | 00:00 – 06:59 | Low volatility, range-bound — most false alerts happen here |
| **London** | **07:00 – 15:59** | High volume, directional moves — good alert zone |
| **NY** | **13:00 – 21:59** | High volume, directional moves — good alert zone |
| NY close | 22:00 – 23:59 | Low liquidity — skipped |

Simply removing Asian session bars raises precision from 0.355 to **0.415** — the single most impactful rule.

### Gate 4 — Cooldown (4 hours)

After an alert fires, no new alert is sent for 4 hours (4 bars). This prevents the system from generating multiple alerts on the same price movement.

---

## What the numbers look like (sealed test set, Feb–Jul 2026)

| Metric | Value |
|---|---|
| **Precision** | 0.415 |
| Breakeven | 0.400 |
| Edge over breakeven | +0.015 |
| Alerts in 109 days | 41 |
| Alerts per day | 0.37 |
| Average time between alerts | ~2.7 days |

On the sealed test set (109 trading days, Feb–Jul 2026):

- 2,632 H1 bars screened
- 99 bars passed Gates 1–3 (threshold + cross-filter + session)
- After Gate 4 (cooldown) removes duplicates: **41 final alerts**
- Of those 41 alerts: ~17 hit TP (41.5% precision)
- The other ~24 either hit SL or timed out

---

## What "good enough" means

0.415 precision = ~59% of the 63 candidate bars were correct. The other ~41% are false positives.

This is **by design**. The system is not expected to be perfect — it is an **opportunity surfacer**:

> *The model finds moments that look promising based on historical patterns.  
> A human or downstream agent then decides whether to act.*

A 41% hit rate means agents can expect roughly 2 out of every 5 alerts to be valid — a signal worth reviewing.

---

## Production artifacts

| File | Role |
|---|---|
| `models_bin/EURUSD_H1_buy_LightGBM.joblib` | Trained BUY model (22 features, 0.678 threshold) |
| `models_bin/EURUSD_H1_sell_LightGBM.joblib` | Trained SELL model (19 features, cross-filter only) |
| `steps/05_inference/eurusd_h1_predictor.py` | Production inference script |
| `data/processed/eurusd_h1_decision_log.csv` | Full decision trace (one row per bar) |

---

## What this system does NOT do

- It does **not** predict exact prices.
- It does **not** predict how many pips will be gained.
- It does **not** auto-execute trades.
- It does **not** generate SELL alerts (SELL lane is disabled — proven non-viable on test).

It answers one question only: *does this bar look like a historically favorable long entry?*
