# Next Phase — Agent Pipeline Design for EURUSD H1 Signal System

*Created: 2026-07-10 · Status: Design & Documentation*

---

## What we have today

| Component | Status | Description |
|---|---|---|
| LightGBM BUY model | **Done** | 22 features, 0.678 threshold, 0.415 test precision |
| Signal combiner notebook | **Done** | BUY-only, cross-filter 0.60, session gate, cooldown 4 |
| Prediction script | **Done** | `eurusd_h1_predictor.py` — scores every bar, saves decision log |
| Decision log | **Done** | `eurusd_h1_decision_log.csv` — 46k rows, TP/SL/entry/reason per bar |
| Production executor | **MISSING** | Nothing executes trades or validates signals in production |

Our system generates alerts. It does not execute them. That's the next layer.

---

## What DeafAgent already does (reference architecture)

DeafAgent is a multi-agent trading system running hourly. Understanding its architecture is the blueprint for what we need to build.

### Agent anatomy (one currency pair = one agent)

```
Every hour at :01 past:

┌─────────────────────────────────────────────────────────────┐
│ 1. DATA UPDATE                                               │
│    update_H1_database("EURUSD")  ← fetches latest bars from │
│    MT5, appends to Export_EURUSD_H1.csv                     │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. FEATURE COMPUTE                                           │
│    technical_indicators(df)  ← SMA/EMA/RSI/MACD/ATR/BB etc │
│    pre-calculate ATR, ADX, trend context                     │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. PARALLEL AGENT QUERIES                                    │
│    ┌──────────────────┐    ┌──────────────────┐              │
│    │ BUY agent        │    │ SELL agent       │              │
│    │ ask_agent(buy)   │    │ ask_agent(sell)  │              │
│    │                  │    │                  │              │
│    │ Perplexity API   │    │ Perplexity API   │              │
│    │ (sonar-pro)      │    │ (sonar-pro)      │              │
│    │                  │    │                  │              │
│    │ 5 analysis       │    │ 5 analysis       │              │
│    │ pillars:         │    │ pillars:         │              │
│    │ • Technical      │    │ • Technical      │              │
│    │ • Fundamental    │    │ • Fundamental    │              │
│    │ • Sentiment      │    │ • Sentiment      │              │
│    │ • Breaking News  │    │ • Breaking News  │              │
│    │ • Correlation    │    │ • Correlation    │              │
│    └──────┬───────────┘    └──────┬───────────┘              │
│           │                       │                          │
│    CONFIRM/REJECT/NEUTRAL         CONFIRM/REJECT/NEUTRAL     │
└───────────┼───────────────────────┼──────────────────────────┘
            │                       │
            └───────────┬───────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. ADVERSARIAL DECISION                                      │
│    Rules engine determines final_action:                     │
│    - BUY CONFIRM + SELL REJECT → final_action = BUY         │
│    - BUY REJECT + SELL CONFIRM → final_action = SELL        │
│    - Both CONFIRM → conflict → do nothing                   │
│    - Both REJECT → do nothing                               │
│    - Only STRONG signals when only_strong=True               │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. SENIOR AGENT VALIDATION (GPT-4o)                          │
│    validate_with_senior_agent(buy_decision, sell_decision)   │
│                                                              │
│    Checks:                                                   │
│    □ Logic: does analysis support the action?                │
│    □ Risk/Reward: is the math correct?                       │
│    □ Account risk: within 5-10% limits?                      │
│    □ Stop Loss: appropriate for current ATR?                 │
│    □ Warnings: news events, volatility spikes?               │
│    □ Signal conflict: do buy/sell agents disagree?           │
│                                                              │
│    Returns: APPROVED / MODIFIED / REJECTED                   │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. TRADE EXECUTION                                           │
│    IF APPROVED: execute market order via MT5                 │
│    IF MODIFIED: execute with reduced lot size                │
│    IF REJECTED: log and skip                                 │
│                                                              │
│    Daily throttle: max 3 trades/agent/day                    │
│    Cooldown: 2h between same-direction trades                │
│    Profit protection: trailing stops, daily loss limits      │
└─────────────────────────────────────────────────────────────┘
```

### Key files and their roles

| File | Role |
|---|---|
| `commons.py` | Central library: Perplexity queries, signal scoring, MT5 execution, trade logging |
| `senior_agent.py` | GPT-4o trade validation — second pair of eyes before execution |
| `live_trading_scheduler.py` | Hourly scheduler: runs agents, checks market hours, handles shutdown |
| `abrax_decision_buy.py` | Per-pair buy decision (meta-model + rules for EURUSD) |
| `abrax_decision_sell.py` | Per-pair sell decision |
| `abrax_final_decision.py` | Per-pair final action determination |

### Agent config examples (from live_trading_scheduler.py)

```python
'abrax': {
    'nickname': 'abrax',      # Agent name
    'symbol': 'EURUSD',        # MT5 symbol
    'lot_size': 0.45,          # Base lot size
    'risk_profile': 'ULTRA_AGGRESSIVE',
    'balance_perc': 0.06,      # % of balance risked per trade
    'scripts': [
        "abrax_decision_sell.py",  # Step 3a: sell agent
        "abrax_decision_buy.py",   # Step 3b: buy agent
        "abrax_final_decision.py"  # Step 4: adversarial decision
    ]
}
```

---

## What needs to go next — two approaches

### Approach A: Integrate into existing DeafAgent scheduler (lighter)

Replace the abrax agent's meta-model step with our LightGBM predictor:

```
Every hour at :01:

1. Update H1 data from MT5           ← existing (commons.update_H1_database)
2. Compute features (86 cols)        ← NEW: reuse compute_features from predictor
3. Score with BUY LGBM model         ← NEW: replaces meta-model
4. Apply 4 decision gates            ← NEW: threshold, cross-filter, session, cooldown
   ┌─────────────────────────────────┐
   │ If BUY signal generated:        │
   │   entry = close                  │
   │   TP = close + ATR × 1.5        │
   │   SL = close - ATR × 1.0        │
   └─────────────────────────────────┘
5. [OPTIONAL] Perplexity validation  ← existing: confirms/rejects the alert
6. Senior Agent validation (GPT-4o)  ← existing: risk review before execution
7. Execute trade via MT5             ← existing
```

**Pros:** Reuses battle-tested scheduler, risk management, and execution layer.
**Cons:** Tied to DeafAgent's MT5 infrastructure and Perplexity dependency.

### Approach B: Standalone lightweight executor (minimalist)

Build a self-contained script that:
1. Calls `eurusd_h1_predictor.py`
2. Reads the latest signal from the decision log
3. If signal exists and is new (not already acted on):
   - Optionally queries Perplexity for multi-pillar confirmation (step 5 above)
   - Optionally validates with GPT-4o Senior Agent (step 6 above)
   - Sends the alert (file, API, notification — not MT5 yet)
4. Logs the outcome

**Pros:** Decoupled from DeafAgent, can run independently, no MT5 dependency.
**Cons:** Builds new execution/infrastructure layer from scratch.

### Recommendation: Approach A for production, Approach B for now

We don't have MT5 access or a live account yet. Build **Approach B** first as a lightweight alert emitter that can be tested end-to-end. It mirrors the DeafAgent architecture conceptually but outputs to files/notifications instead of MT5 orders.

When ready for live trading, wire it into the DeafAgent scheduler (Approach A) using the same alert format.

---

## Approach B — Lightweight Alert Emitter (immediate next step)

### Architecture

```
cron / Task Scheduler (every hour at :01)
        │
        ▼
┌──────────────────────────────────────────────┐
│ eurusd_h1_predictor.py                       │
│  • Load raw data + compute features          │
│  • Score BUY model                           │
│  • Apply 4 decision gates                    │
│  • Save eurusd_h1_decision_log.csv           │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ eurusd_h1_alert_emitter.py  [NEW — to build] │
│                                               │
│  1. Read latest signal from decision log      │
│  2. Check if already processed (dedup)        │
│  3. [Optional] Perplexity multi-pillar check  │
│  4. [Optional] GPT-4o Senior Agent validation │
│  5. Emit alert:                               │
│     • Save to alerts/YYYY-MM-DD_HHMM.json    │
│     • Send to agent pipeline (HTTP/callback)   │
│     • Log to alerts_history.csv               │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────┐
│ Alert format (JSON, one alert = one file)    │
│                                               │
│ {                                             │
│   "timestamp": "2026-07-10 14:01:00 UTC",     │
│   "pair": "EURUSD",                           │
│   "direction": "BUY",                         │
│   "entry": 1.13940,                           │
│   "tp": 1.14044,                              │
│   "sl": 1.13870,                              │
│   "atr": 0.00069,                             │
│   "buy_proba": 0.6794,                        │
│   "sell_proba": 0.4763,                       │
│   "gates_passed": ["threshold",                │
│     "cross_filter", "session", "cooldown"],    │
│   "perplexity_check": "CONFIRM" | null,        │
│   "senior_agent": "APPROVED" | null,           │
│   "status": "pending_review"                   │
│ }                                             │
└──────────────────────────────────────────────┘
```

### Alert format specification

| Field | Type | Description |
|---|---|---|
| `timestamp` | datetime | When the alert was generated (UTC) |
| `pair` | string | Currency pair |
| `direction` | string | Always "BUY" for now |
| `entry` | float | Entry price (bar close) |
| `tp` | float | Take profit level (entry + ATR × 1.5) |
| `sl` | float | Stop loss level (entry − ATR × 1.0) |
| `atr` | float | Current ATR(14) at signal time |
| `buy_proba` | float | BUY model confidence (0–1) |
| `sell_proba` | float | SELL model cross-filter value |
| `gates_passed` | array | Which gates the signal cleared |
| `perplexity_check` | string/null | Perplexity validation result (if run) |
| `senior_agent` | string/null | GPT-4o validation result (if run) |
| `status` | string | `pending_review`, `confirmed`, `rejected`, `executed` |

### Execution decisions

No trades are auto-executed. Each alert goes to `pending_review` status and waits for:

1. **Automated**: Perplexity fundamental/news check → if CONFIRM, promote to `confirmed`
2. **Automated**: Senior Agent GPT-4o risk review → if APPROVED, promote to `confirmed`  
3. **Manual**: A human reviews the alert file and marks it `confirmed` or `rejected`

Only `confirmed` alerts proceed to execution (when we have live trading).

This keeps full control while the system proves itself.

---

## What to build next (ordered)

### Phase 1 — Alert emitter (no external APIs)

**File:** `ml-signal-service/steps/05_inference/eurusd_h1_alert_emitter.py`

- Reads `eurusd_h1_decision_log.csv`
- Finds the latest `buy_signal == 1` row
- Checks dedup: has this signal already been emitted? (track last emitted timestamp)
- Writes alert JSON to `data/alerts/YYYY-MM-DD_HHMM.json`
- Appends to `data/alerts/alert_history.csv`
- Console output: one-line summary of the alert

### Phase 2 — Perplexity validation (optional enhancement)

- Load Perplexity API key from secure config
- Send the same multi-pillar prompt that DeafAgent uses (technical + fundamental + sentiment + news + correlation)
- Parse CONFIRM/REJECT/NEUTRAL result
- Add to the alert JSON
- Adds ~2-5 seconds of latency; can be skipped with a flag

### Phase 3 — Senior Agent validation (optional enhancement)

- Load OpenAI API key from secure config
- Send the alert + market context to GPT-4o for risk review
- Parse APPROVED/MODIFIED/REJECTED result
- Add to the alert JSON
- Adds cost per alert (~$0.01 with GPT-4o)

### Phase 4 — Production executor (future)

- Wire into MT5 or broker API
- Execute APPROVED alerts with position sizing
- Implement daily throttle + cooldown + profit protection (same as DeafAgent)
- Run via Windows Task Scheduler or cron every hour

---

## Key decisions to make now

1. **API keys**: Where will Perplexity/OpenAI keys be stored? Follow DeafAgent pattern (credentials.env) or use environment variables?

2. **Scheduling**: Windows Task Scheduler (matches DeafAgent) or cron? The `live_trading_scheduler.py` pattern of running at `:01` past the hour ensures OHLC data is complete.

3. **Execution**: Do we want MT5 execution or just alert notification for now?

4. **Perplexity integration**: DeafAgent queries Perplexity for both BUY and SELL every hour. With our system, we only need it when a signal actually fires (saving cost). Should we query on every signal, or only the first time?

---

## Summary of gap between current state and production

```
DONE:                                    MISSING:
┌─────────────────────┐                  ┌─────────────────────┐
│ EURUSD H1 model     │                  │ Scheduler (hourly)  │
│ Feature engineering │                  │ Alert emitter       │
│ Decision gates      │                  │ Perplexity validat. │
│ Decision log        │                  │ GPT-4o Senior Agent │
│ TP/SL computation   │                  │ MT5 execution       │
└─────────────────────┘                  │ Trade management    │
                                         │ Risk limits         │
                                         │ Alert dedup         │
                                         └─────────────────────┘
         ✔                                        ✘
```

The next document in this series should be the implementation of Phase 1 — the alert emitter.