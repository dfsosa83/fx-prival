# Frival — Agent Decision Flow Explained

*Internal reference · 2026-08-04 · Covers `frival/agents/` and `frival/main.py`*

---

## Overview

The Frival pipeline generates trade recommendations for FX pairs (EURUSD, GBPUSD, USDCHF) by combining a machine-learning ensemble with a two-agent validation layer. A signal only reaches a trader if it passes a chain of automated gates **and** both AI agents independently support the trade idea.

The final output is a structured recommendation with a specific entry price, stop loss, take profit, and confidence level — everything needed to place the trade.

---

## The Big Picture



Raw H1 OHLCV data (from MT5 or CSV)
│
▼
┌─────────────────────┐
│ Feature Engine │ 82 technical + 14 calendar features per bar
│ features.py │
└────────┬────────────┘
│
▼
┌──────────────────────────┐
│ ML Ensemble (4 models) │ Calibrated soft-vote probability of SELL
│ LogReg + RF + XGB + LGB │ Output: p ∈ [0, 1] per bar
└────────┬─────────────────┘
│
▼
┌─────────────────────────┐
│ Decision Gates │ Three hard filters applied in order
│ [signal_gate.py](vscode-file://vscode-app/c:/Users/david/AppData/Local/Programs/Microsoft VS Code/e4c7e7b1d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) │
│ 1. Threshold │ Is p high enough?
│ 2. Session │ London / New York hours only?
│ 3. Cooldown │ No signal in last 4 bars?
└────────┬────────────────┘
│ PASS (standard or borderline)
▼
┌──────────────────────────────────────────┐
│ Agent A — Technical (GPT-4o) │ Is the chart aligned with the signal?
│ agents/technical.py │
└────────────────────┬─────────────────────┘
│ CONFIRM / REJECT / NEUTRAL
▼
┌──────────────────────────────────────────┐
│ Agent B — Fundamental (Perplexity Sonar)│ Does macro support the trade?
│ agents/fundamental.py │
└────────────────────┬─────────────────────┘
│ CONFIRM / REJECT / NEUTRAL
▼
┌──────────────────────────────────────────┐
│ Senior — Coordination Layer │ Combines both into FIRED or SHELVED
│ agents/senior.py (pure code, no LLM) │
└────────────────────┬─────────────────────┘
│
┌───────────┴───────────┐
▼ ▼
FIRED ✅ SHELVED ❌
Trade levels printed Reason logged
JSONL record written JSONL record written



---

## Step 1 — Feature Engineering

**File:** `frival/model/features.py`

Before the model or any agent can evaluate anything, every H1 bar is converted into a rich feature vector. Two categories are computed:

### Technical features (82)

| Category        | Examples                                                     |
| --------------- | ------------------------------------------------------------ |
| Moving averages | SMA(10/20/50), EMA(10/20/50/100/200), `close_vs_ema50`, `close_vs_ema200` |
| Momentum        | RSI(14), Stochastic %K/%D, Williams %R, MACD / hist / signal / slope |
| Volatility      | ATR(14), `atr_regime`, Bollinger Bands, `rolling_std(10/20/50)` |
| Trend           | ADX(14), +DI, −DI, CCI(20), ROC(10)                          |
| Volume          | OBV, `volume_ratio`                                          |
| D1 context      | D1 EMA(20/50), `d1_trend`, `d1_rsi`, `d1_close_vs_ema20` — shifted 1 day (no lookahead) |
| Lags            | close / rsi / atr / volume lagged 1, 2, 3, 5 bars            |
| Session         | `london_session`, `ny_session`, hour/day-of-week cyclics     |

### Calendar features (14)

Derived from 20 years of economic calendar data (2007–2026). No lookahead — backward-looking features use only events already released at bar time `T`.

| Feature                                                      | What it captures                                             |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| `deviation_sum_24h`                                          | Sum of (Actual − Consensus) for all pair-currency events in last 24h. Negative = data missed forecasts. **#1 ranked feature for EURUSD and GBPUSD.** |
| `hours_since_last_high`                                      | Hours since most recent HIGH-impact event. Low values = inside post-event trend window. |
| `high_events_next_1h`                                        | Count of HIGH-impact events in the next hour — flags pre-release risk. |
| `high_events_next_4h` / `high_events_next_24h`               | Broader look-ahead event density.                            |
| `is_fomc_day`, `is_ecb_day`, `is_boe_day`, `is_snb_day`, `is_nfp_day` | Binary flags for central bank decision days.                 |

---

## Step 2 — ML Ensemble Inference

**File:** `frival/model/ensemble.py`

The ensemble is a soft-vote `VotingClassifier` with 4 independently calibrated estimators:

| Sub-model          | Calibration                              |
| ------------------ | ---------------------------------------- |
| LogisticRegression | `CalibratedClassifierCV(isotonic, cv=5)` |
| RandomForest       | `CalibratedClassifierCV(isotonic, cv=5)` |
| XGBoost            | `CalibratedClassifierCV(isotonic, cv=5)` |
| LightGBM           | `CalibratedClassifierCV(isotonic, cv=5)` |

Each sub-model outputs a probability in [0, 1]. The ensemble averages the four. Calibration ensures well-scaled probabilities — `p = 0.40` means the model expects SELL to win roughly 40% of the time.

**Per-pair operating thresholds** (optimized for precision on validation data):

| Pair        | Threshold | Borderline lower bound |
| ----------- | --------- | ---------------------- |
| EURUSD SELL | 0.326     | 0.20                   |
| GBPUSD SELL | 0.369     | 0.20                   |
| USDCHF SELL | 0.376     | 0.20                   |

The model uses only the pair's selected feature set (20–22 features per pair), extracted in exact order from the `.joblib` bundle.

---

## Step 3 — Decision Gates

**File:** `frival/signal_gate.py`

Three sequential hard filters are applied to every bar. A bar must pass **all three** to reach the agents.

### Gate 1 — Probability Threshold

| Range                  | Label          | Outcome                                         |
| ---------------------- | -------------- | ----------------------------------------------- |
| `p ≥ threshold`        | **Standard**   | Passes to agents with normal evaluation rules   |
| `0.20 ≤ p < threshold` | **Borderline** | Passes to agents with stricter evaluation rules |
| `p < 0.20`             | **Blocked**    | Discarded — no agent call, no record written    |

### Gate 2 — Trading Session

Only bars during **London** (07:00–15:59 UTC) or **New York** (13:00–21:59 UTC) hours pass. This avoids the low-liquidity Asian session where spreads widen and directional momentum is weaker.

### Gate 3 — Cooldown

A minimum of **4 bars (4 hours)** must have elapsed since the last signal of any type. This prevents multiple entries in the same sustained market move.

---

## Step 4 — Agent A: Technical Evaluator

**File:** `frival/agents/technical.py`  
**Model:** GPT-4o via OpenRouter (temperature = 0.1, max_tokens = 500)  
**Prompt file:** `frival/agents/prompts/technical.txt` (pair-specific: `technical_gbpusd.txt`, `technical_usdchf.txt`)

### What Agent A receives

Agent A gets a fully structured text block built by `agents/context.py`:

Signal mode: STANDARD
Current price: 1.15143
Ensemble probability (SELL): 0.3421
Operating threshold: 0.326
Model agreement: 2/4 sub-models above threshold

Sub-model probabilities:
LightGBM: 0.3201
LogReg: 0.2987
RandomForest: 0.2874
XGBoost: 0.3112

D1 Context (prior day close):
d1_rsi: 52.14
d1_close_vs_ema20: 0.0021
d1_trend: 1
d1_ema20: 1.14920
d1_ema50: 1.14411

Current bar features (model inputs):
ema_10: 1.15180 ema_50: 1.14870 ema_200: 1.13940
rsi_14: 42.30 macd_hist: -0.00031
adx_14: 24.10 plus_di: 18.2 minus_di: 26.4
atr_regime: 1.12 atr_14: 0.00074
close_vs_ema50: -0.00273

Calendar context (dates and events):
deviation_sum_24h: -1.45
hours_since_last_high: 6.50
high_events_next_1h: 0.00
high_events_next_4h: 2.00
is_fomc_day: NO
is_ecb_day: NO

### Decision rules (STANDARD mode, applied in strict order)

| #          | Rule                                                         | Outcome                                                      |
| ---------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **Rule 1** | D1 close > D1 EMA20 **AND** D1 ADX > 30 **AND** H1 price > EMA50 | **REJECT** — strong USD bid on both timeframes; selling is adverse selection |
| **Rule 2** | 0 or 1 of 4 sub-models ≥ threshold                           | **REJECT** — ensemble is internally conflicted               |
| **Rule 3** | Price > EMA(10, 50, 200) **AND** RSI > 50                    | **REJECT** — H1 uptrend firmly intact                        |
| **Rule 4** | `high_events_next_1h ≥ 1`                                    | **NEUTRAL** — major release imminent; pre-release data is stale |
| **Rule 5** | ≥ 2 CONFIRM conditions hold                                  | **CONFIRM** — technical picture supports SELL                |
| **Rule 6** | None of the above fire                                       | **NEUTRAL** — mixed or inconclusive picture                  |

**CONFIRM conditions** (need ≥ 2 in standard mode, ≥ 3 in borderline mode):

1. Price below EMA50
2. MACD histogram < 0 (any negative value)
3. RSI < 45
4. ADX between 20–40 with −DI > +DI (bearish directional pressure)
5. ATR regime > 1.0 (above-normal volatility — room for the trade to breathe)
6. `deviation_sum_24h < 0` (recent economic data came in below expectations — macro supports SELL)
7. `hours_since_last_high` between 2 and 24 (inside a post-event trend continuation window)

### Borderline mode differences

In borderline mode, Rule 2 is relaxed: REJECT only if the ensemble is *fully collapsed* — all 4 sub-models below `threshold − 0.05`, or the highest sub-model below `threshold − 0.10`. This is necessary because in borderline mode none of the sub-models are expected to exceed the threshold by design.

### Agent A output

```json
{
  "decision": "CONFIRM",
  "confidence": "HIGH",
  "justification": "Price below EMA50, MACD negative, -DI > +DI at ADX 24. Deviation sum -1.45 indicating recent data disappointments. Pre-event check clear. 3 confirm conditions met.",
  "regime_flags": {
    "strong_dollar_bid": false,
    "d1_uptrend": true,
    "volatility_spike": false
  }
}
```

## Step 5 — Agent B: Fundamental / Macro Evaluator

**File:** `frival/agents/fundamental.py`
**Model:** Perplexity Sonar Pro (live web search, `search_recency_filter = "day"`)
**Prompt file:** `frival/agents/prompts/fundamental.txt` (pair-specific: `fundamental_gbpusd.txt`, `fundamental_usdchf.txt`)

### What Agent B receives

**1. Pre-built structured calendar context** (from `agents/calendar_context.py`):

=== Macro Calendar Context (2026-08-04 15:00 UTC) ===

Last 24 hours (3 HIGH/MEDIUM events):
  - USD ISM Manufacturing PMI (Jul): actual 47.9 vs consensus 48.3 (-1.39 MISS)
  - EUR S&P Global Composite PMI: actual 50.2 vs consensus 50.0 (+0.20 beat)
  - USD JOLTS Job Openings: actual 8.01M vs consensus 7.90M (+0.11 beat)

Upcoming — next 4 hours:
  - 16:00 UTC: USD Factory Orders (MEDIUM)

Upcoming — next 24 hours: 2 HIGH/MEDIUM events

Today: no central bank decision or NFP day.
Event density: 5 recent / 4 upcoming

**2. Web search** (supplemental) — Perplexity searches for: DXY direction, central bank policy tone, geopolitical events, and risk sentiment.

### Decision rules (EURUSD SELL)

| #          | Rule                                                         | Outcome                                |
| ---------- | ------------------------------------------------------------ | -------------------------------------- |
| **Rule 1** | Active macro shock strengthening EUR: ECB hawkish surprise, DXY drop > 1%, major USD-negative event | **REJECT** (unconditional veto)        |
| **Rule 2** | ≥ 2 USD-strength conditions: Fed more hawkish than ECB, DXY uptrend, risk-off, USD-positive data | **CONFIRM**                            |
| **Rule 3** | No EUR-positive events + DXY stable/rising + no high-impact event in next 4h | **CONFIRM** ("technical-only context") |
| **Rule 4** | Insufficient macro signal                                    | **NEUTRAL**                            |

**For GBPUSD:** Central banks are BoE vs Fed. UK CPI, GDP, and employment replace Eurozone inputs.

**For USDCHF:** Central banks are SNB vs Fed. CHF dynamics are driven by safe-haven demand, gold correlation, and SNB intervention risk rather than growth data.

### Agent B output

{
  "decision": "NEUTRAL",
  "confidence": "LOW",
  "justification": "Calendar shows ISM miss and upcoming Factory Orders. Web search finds no clear Fed-ECB divergence. DXY mixed. No active EUR-positive event.",
  "regime_flags": {
    "macro_event_active": false,
    "fed_hawkish": false,
    "dxy_uptrend": false,
    "risk_off": false
  },
  "news_sources": ["https://reuters.com/...", "https://fxstreet.com/..."]
}

## Step 6 — Senior: Coordination Layer

**File:** [senior.py](vscode-file://vscode-app/c:/Users/david/AppData/Local/Programs/Microsoft VS Code/e4c7e7b1d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html)
**Type:** Pure Python rule engine — no LLM call, deterministic, instantaneous

### Standard mode decision table

| Agent A (Technical) | Agent B (Fundamental) | Result      | Confidence |
| ------------------- | --------------------- | ----------- | ---------- |
| CONFIRM             | CONFIRM               | **FIRED**   | HIGH       |
| CONFIRM             | NEUTRAL               | **FIRED**   | MODERATE   |
| NEUTRAL             | CONFIRM               | **FIRED**   | MODERATE   |
| REJECT              | *any*                 | **SHELVED** | —          |
| *any*               | REJECT                | **SHELVED** | —          |
| NEUTRAL             | NEUTRAL               | **SHELVED** | —          |

### Borderline mode decision table

Stricter — both agents must CONFIRM for the signal to fire.

| Agent A         | Agent B         | Result      | Confidence |
| --------------- | --------------- | ----------- | ---------- |
| CONFIRM         | CONFIRM         | **FIRED**   | MODERATE   |
| *anything else* | *anything else* | **SHELVED** | —          |

### Soft-veto: 3-strike rule

Fundamental REJECT is normally unconditional. After **3 consecutive** Agent B REJECTs on the same pair (tracked in [last_signal.json](vscode-file://vscode-app/c:/Users/david/AppData/Local/Programs/Microsoft VS Code/e4c7e7b1d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html)), if Agent A returns CONFIRM with HIGH confidence, the veto softens:

- Signal **fires** with **LOW confidence**
- The veto reason is retained as a warning note in the JSONL record
- Streak resets to 0 after any FIRED signal or any Agent B CONFIRM/NEUTRAL

This prevents a prolonged macro narrative (e.g., "Fed dovish, DXY falling" for 5 straight days) from indefinitely blocking technically valid setups.

------

## Step 7 — Output: What the Trader Sees

### When SHELVED

One line prints to the console. A full JSONL record is written for auditing.

Signal SHELVED: fundamental: Fed rate-hike bets receding after weaker US jobs data,
ECB hawkish tone persists. DXY at one-month low. No USD-strength confirmation.
Agents: A=NEUTRAL B=REJECT -> SHELVED

### When FIRED — Console output

============================================================
  SIGNAL FIRED: EURUSD SELL
  Timestamp:    2026-07-28T14:00:00+00:00
  Confidence:   HIGH
  Probability:  0.3421  (threshold: 0.326)
  Gate type:    STANDARD

  Entry:        1.15332
  Entry zone:   1.15352  →  1.15312   (±2 pips, enter anywhere in this range)
  Stop Loss:    1.15406  (+7.4 pips above entry)
  Take Profit:  1.15221  (−11.1 pips below entry)
  R:R ratio:    1.5 : 1
  Expires:      2026-07-28T20:00:00+00:00  (6 bars / 6 hours)

  Agent A: CONFIRM (HIGH)
  Agent B: CONFIRM (MODERATE)
============================================================

### rade level calculation

All levels are derived from the bar's **ATR(14)** — the 14-period Average True Range — which adapts to current market volatility automatically.

| Level              | Formula             | Meaning                                                  |
| ------------------ | ------------------- | -------------------------------------------------------- |
| Entry              | Bar close price     | Execute at or near the close of the signal bar           |
| Entry zone         | Entry ± 2 pips      | Practical execution bracket for manual orders            |
| Stop Loss (SELL)   | Entry + (ATR × 1.0) | Above entry — caps the loss if price reverses up         |
| Take Profit (SELL) | Entry − (ATR × 1.5) | Below entry — locks in profit on a downward move         |
| R:R ratio          | 1.5 : 1             | Risk 1 unit to make 1.5 units                            |
| Expiry             | Bar time + 6 hours  | Close manually if neither TP nor SL is hit within 6 bars |

**For BUY signals** (directions are flipped):

- Stop Loss = Entry − (ATR × 1.0)
- Take Profit = Entry + (ATR × 1.5)

**Practical example** (EURUSD, ATR ≈ 0.00074):

| Level       | Price   | Distance   |
| ----------- | ------- | ---------- |
| Entry       | 1.15332 | —          |
| Stop Loss   | 1.15406 | +7.4 pips  |
| Take Profit | 1.15221 | −11.1 pips |

------

## Step 8 — JSONL Audit Trail

Every signal — fired or shelved — is appended to:
`frival/output/signals/YYYY-MM/YYYY-MM-DD.jsonl`

Files are append-only and never overwritten. This is the source of truth for `evaluate_precision.py`, which calculates live precision, EV, and Wilson 95% confidence intervals.

{
  "run_id": "20260728_140012",
  "signal_id": "EURUSD_H1_SELL_2026-07-28T14:00:00Z",
  "symbol": "EURUSD",
  "direction": "SELL",
  "timestamp_utc": "2026-07-28T14:00:00",
  "trade": {
    "entry": 1.15332,
    "entry_zone": [1.15352, 1.15312],
    "stop_loss": 1.15406,
    "take_profit": 1.15221,
    "rr_ratio": 1.5,
    "expires_at_utc": "2026-07-28T20:00:00"
  },
  "model": {
    "probability": 0.3421,
    "threshold": 0.326
  },
  "gates": {
    "passed_threshold": true,
    "passed_session": true,
    "passed_cooldown": true
  },
  "agents": {
    "technical": {
      "decision": "CONFIRM",
      "confidence": "HIGH",
      "justification": "Price below EMA50, MACD negative, -DI > +DI at ADX 24. Deviation sum -1.45, post-event window active. 3 confirm conditions met.",
      "regime_flags": {"strong_dollar_bid": false, "d1_uptrend": false, "volatility_spike": false}
    },
    "fundamental": {
      "decision": "CONFIRM",
      "confidence": "MODERATE",
      "justification": "ISM miss and DXY fading post-FOMC. ECB held hawkish tone. No EUR-positive event in next 4h.",
      "regime_flags": {"macro_event_active": false, "fed_hawkish": false, "dxy_uptrend": false, "risk_off": false},
      "news_sources": ["https://reuters.com/...", "https://fxstreet.com/..."]
    }
  },
  "final_decision": "FIRED",
  "final_confidence": "HIGH",
  "veto_reason": "",
  "gate_type": "standard"
}

## Shadow Mode

GBPUSD and USDCHF are in **shadow mode** — their models have not yet passed the deployment gate (EV positive, Wilson CI lower bound ≥ 0.35, minimum 60-day live sample).

Shadow pairs run the identical full pipeline but:

- [final_decision](vscode-file://vscode-app/c:/Users/david/AppData/Local/Programs/Microsoft VS Code/e4c7e7b1d6/resources/app/out/vs/code/electron-browser/workbench/workbench.html) is stored as `"SHADOW_FIRED"` in the JSONL (never `"FIRED"`)
- No trade recommendation is printed to the console
- All agent reasoning, trade levels, and gate results are still written for statistical accumulation

------

## Per-Pair Summary

| Property                | EURUSD     | GBPUSD     | USDCHF            |
| ----------------------- | ---------- | ---------- | ----------------- |
| Direction               | SELL       | SELL       | SELL              |
| Threshold               | 0.326      | 0.369      | 0.376             |
| Features selected       | 22         | 12         | 15                |
| Central banks (Agent B) | ECB vs Fed | BoE vs Fed | SNB vs Fed + gold |
| Sealed-test precision   | 0.500      | 0.423      | 0.435             |
| Sealed-test EV          | +0.155R    | −0.052R    | −0.014R           |
| Live status             | **LIVE**   | Shadow     | Shadow            |

------

## Complete Checklist: All Conditions for a Signal to Fire

1. ML ensemble probability ≥ pair threshold on the current closed H1 bar
2. Bar falls in London (07:00–15:59 UTC) or New York (13:00–21:59 UTC) session
3. No signal of any type fired in the last 4 bars (cooldown clear)
4. Agent A returns CONFIRM (or NEUTRAL in standard mode when Agent B confirms)
5. Agent B returns CONFIRM or NEUTRAL (a REJECT is an unconditional veto unless 3-strike soft-veto is active)
6. The Senior's decision table resolves to FIRED
7. The pair is not in shadow mode

Only when every condition is met does the trade recommendation print with entry, SL, TP, and confidence level.

------

*Document last updated: 2026-08-04. Covers Frival v2 with calendar integration (Iteration 3 Phase 1 deployed).*