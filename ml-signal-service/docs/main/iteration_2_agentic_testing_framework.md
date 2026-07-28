# Frival — Agentic Testing Framework: Architecture & Implementation Plan

*Internal planning document · July 28, 2026 · Status: Planning · Depends on: Iteration 1 SELL ensemble (complete)*

---

## 1. Motivation

The Iteration 1 SELL ensemble achieves 0.411 gated precision (above the 0.400 breakeven), but the vector backtest reveals a structural vulnerability: **+1.2R total return over 6 months with −18.9R max drawdown.** April 2026 alone lost −8.9R with a 19% win rate — a clean regime failure where the model fired SELL into a strong USD uptrend driven by macro/tariff events.

The model has a genuine directional edge (ROC-AUC 0.674) but is context-blind. It cannot see the macro regime. Iteration 2 addresses this by surrounding the ML probability with a multi-agent contextual veto layer: specialized LLM agents evaluate every candidate signal and reject those fired into conditions matching the April failure pattern.

This document describes the architecture, workflow, and phased implementation plan for a testing framework that combines the calibrated ML ensemble with OpenRouter-powered agentic evaluation. No order execution — output is a structured signal log designed for paper trading and backtest validation.

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        main.py (Orchestrator)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │ MT5 Data │→ │ model.py │→ │ Signal   │→ │ Agent Hierarchy  │ │
│  │ Fetcher  │  │ Ensemble │  │ Gate     │  │ (OpenRouter)     │ │
│  └──────────┘  └──────────┘  └────┬─────┘  └────────┬─────────┘ │
│                                   │                   │           │
│                              probability         CONFIRM/REJECT   │
│                              ≥ threshold              │           │
│                                   │                   ▼           │
│                                   │          ┌──────────────────┐ │
│                                   │          │ Decision Synth   │ │
│                                   │          │ (consensus/veto) │ │
│                                   │          └────────┬─────────┘ │
│                                   │                   │           │
│                                   ▼                   ▼           │
│                          ┌─────────────────────────────────────┐  │
│                          │     signal_output.jsonl              │  │
│                          │  {symbol, direction, probability,    │  │
│                          │   agent_votes, confidence, tp/sl,   │  │
│                          │   timestamp, regime_flags}          │  │
│                          └─────────────────────────────────────┘  │
│                              │                                     │
│                              ▼                                     │
│                    ┌──────────────────┐                            │
│                    │ Backtest Logger   │                           │
│                    │ / Decision Audit  │                           │
│                    └──────────────────┘                            │
└──────────────────────────────────────────────────────────────────┘
```

### 2.1 Design Principles

1. **Separation of signal from execution.** This framework generates signals. A separate system (manual trader, execution bot, or future automated module) consumes them. No MT5 order placement.

2. **Config-driven.** Agent roster, model selection, thresholds, and backtest parameters are defined in YAML, not hardcoded. Enables rapid A/B experimentation.

3. **Every module is independently toggleable.** Run with 0, 1, or 2 agents. Run with or without backtest evaluation. The config controls which path is active.

4. **The sealed test set remains sealed.** Agent system prompts and decision rules are tuned on validation data (2025-07 → 2025-12) only. The sealed test (2026-01 → present) is evaluated exactly once at Phase 2 completion and never used for development.

5. **Structured agent outputs only.** Agents return JSON via OpenRouter's structured output / JSON mode. No regex parsing of free text. Schema violations are rejected and logged, not silently patched.

---

## 3. Component Specification

### 3.1 `main.py` — Orchestrator

Stateless runner. Reads a YAML config, bootstraps MT5 connection, coordinates the async pipeline, and persists the decision audit trail.

**Responsibilities:**
- Parse CLI args and config file
- Initialize MT5 connection with health check
- Coordinate async execution: data → model → gate → agents → synthesis → output
- In backtest mode, loop over a date range and replay bars sequentially with no lookahead
- Aggregate and log all decisions (fired + shelved)

**Modes:**
- **Live mode**: Run once on the current H1 candle. Used for paper trading.
- **Backtest mode**: Replay a date range, evaluate every bar's signal against forward outcomes. Used for precision/EV measurement.

**Config structure (YAML):**
```yaml
symbol: EURUSD
timeframe: H1
threshold: 0.306
cooldown_bars: 4
session_filter: true
mode: backtest
backtest:
  start: "2026-01-01"
  end: "2026-07-24"
agents:
  technical:
    enabled: true
    model: "anthropic/claude-3.5-sonnet"
    temperature: 0.1
  fundamental:
    enabled: true
    model: "perplexity/sonar-pro"
    temperature: 0.2
    web_search: true
```

### 3.2 Data Fetcher — MT5 Integration

Pulls the latest H1 bar(s) and D1 context from MetaTrader 5. Modeled on DeafAgent's `update_H1_database()`.

**What it must produce:**
- H1 OHLCV for the current bar + 200-bar lookback window (feature computation)
- D1 OHLCV for regime context (D1 RSI, D1 ADX, close vs EMA200)
- Optional: H4 data for intermediate timeframe context

**Cache-first pattern:**
On first run, pull the full date range from MT5 → store as CSV. Subsequent runs read CSV and only fetch incremental bars. This eliminates redundant MT5 calls and enables offline backtesting.

### 3.3 `model.py` — Prediction Layer

Loads the trained 4-model ensemble (LogReg + RF + XGB + LGBM), computes 20 features, and outputs a calibrated SELL probability. Pure function from (DataFrame) → (prediction dict). No side effects.

**Output:**
- `probability`: calibrated soft-vote mean
- `threshold`: operating threshold from the `.joblib` bundle (0.306)
- `signal_fired`: boolean
- `features_used`: the 20-feature vector with SHAP values for top-5 contributors
- `individual_probabilities`: per-model breakdown for agreement scoring

**Model freshness check:** On load, compare `.joblib` training date to current date. Warn if model is >90 days old. Retraining is a separate pipeline, not part of this framework.

### 3.4 Signal Gate

First-pass filter. Only passes signals through to agent evaluation when criteria are met.

**Gates:**
1. Probability ≥ threshold (0.306)
2. Cooldown: max 1 signal per N bars (4)
3. Session filter: London (07:00–15:59 UTC) + NY (13:00–21:59 UTC) only
4. Minimum signal count: skip if this bar would produce fewer than historically expected signals

In a single-direction (SELL-only) framework, there is no cross-filter and no conflict resolution. This eliminates the structural problem where the dead BUY lane suppressed SELL signals in the original combiner.

### 3.5 Agent Hierarchy — OpenRouter-Powered

Two specialized evaluators run in parallel via `asyncio.gather`. A programmatic Senior Agent coordinates their outputs into a final decision.

#### Agent A — Technical Context

Evaluates whether the technical picture supports a SELL signal. Receives the feature vector, top-5 SHAP contributors, D1 context, and model probability.

**System prompt core:**
- Current price, D1 close vs EMA200, D1 RSI, D1 ADX, volatility regime (ATR percentile)
- Model probability and which features drove it
- **Explicit April-detection rule**: "If D1 close is above EMA200 AND D1 ADX > 30 AND DXY is in a confirmed uptrend, this is a 'strong dollar bid' regime. Reject any SELL signal in this regime unless there is a clear reversing catalyst."

**Output schema:**
```json
{
  "decision": "CONFIRM|REJECT|NEUTRAL",
  "confidence": "HIGH|MODERATE|LOW",
  "justification": "string",
  "regime_flags": {
    "strong_dollar_bid": false,
    "d1_uptrend": false,
    "volatility_spike": false,
    "oversold_bounce_risk": false
  }
}
```

#### Agent B — Fundamental / Macro Context

Evaluates the macro regime via web search. Checks for Fed/ECB divergence, DXY direction, active high-impact news, and risk sentiment.

**System prompt core:**
- ECB vs Fed policy stance divergence (rate differentials)
- DXY direction and strength
- Active news / event risk in the next 1–4 hours
- Risk sentiment (risk-on favors EUR; risk-off favors USD)
- **Explicit April-detection rule**: "If there is an active tariff announcement, Fed hawkish surprise, or geopolitical shock favoring USD, reject any SELL signal unconditionally."

**Output schema:** Same as Agent A, plus `news_sources` array of URLs.

#### Senior Agent — Coordination Layer

Not a third LLM call. A programmatic rule engine:

| Technical | Fundamental | Result |
|---|---|---|
| CONFIRM | CONFIRM | **FIRED** (confidence = max) |
| CONFIRM | NEUTRAL | **FIRED** (confidence = LOW) |
| NEUTRAL | CONFIRM | **FIRED** (confidence = LOW) |
| REJECT | * | **SHELVED** (reason = technical rejection) |
| * | REJECT | **SHELVED** (reason = fundamental rejection) |
| NEUTRAL | NEUTRAL | **SHELVED** (reason = "ambiguous") |

Fundamental rejection is an unconditional veto. This is the single most important rule — it directly targets the April failure pattern. If Agent B detects macro event risk, the signal is shelved regardless of how strong the technical picture looks.

### 3.6 Decision Synthesis & Output

Consolidates model prediction + agent verdicts into a standardized signal.

**Output schema (v1.0):**
```json
{
  "signal_id": "EURUSD_H1_SELL_2026-07-28T15:00:00Z",
  "symbol": "EURUSD",
  "direction": "SELL",
  "timestamp_utc": "2026-07-28T15:00:00Z",
  "model": {
    "probability": 0.42,
    "threshold": 0.306,
    "ensemble_agreement": 0.75,
    "top_features": {
      "ADX_14": 0.73,
      "D1_RSI": -0.58,
      "rolling_std_50": 0.41
    }
  },
  "agents": {
    "technical": {
      "decision": "CONFIRM",
      "confidence": "HIGH",
      "regime_flags": {"strong_dollar_bid": false, "d1_uptrend": false}
    },
    "fundamental": {
      "decision": "CONFIRM",
      "confidence": "MODERATE",
      "regime_flags": {"macro_event_active": false},
      "news_sources": ["https://www.fxstreet.com/..."]
    }
  },
  "final_decision": "FIRED",
  "final_confidence": "HIGH",
  "veto_reason": null,
  "throughput_time_ms": 8423
}
```

**Persistence:**
- `output/signals/YYYY-MM/YYYY-MM-DD.jsonl`: Append-only. One JSON object per line. Immutable audit trail.
- `output/reports/backtest_YYYYMMDD_HHMMSS.csv`: Flat CSV with precision columns for vector backtest integration (compatible with the existing combiner's R5/R7 cells).

### 3.7 Backtest Framework

Date-range looper that replays historical bars, evaluates agent-filtered signals against forward outcomes, and generates a standardized evaluation report.

**Report contents (per run):**
- Agent-confirmed precision with Wilson 95% CI
- Raw (unfiltered) precision for comparison
- EV per signal (net pips, incorporating spread assumption)
- Monthly breakdown (trades, win rate, total R)
- Rejection rate (% of candidate signals shelved)
- Throughput metrics (avg agent latency, total runtime)
- Apr 2026-specific section (did agents catch the regime break?)

**Config-driven A/B testing:**
Two config files, same date range, different agent rosters. Run both. Diff the reports. Answer: "Did adding Agent B improve precision over Agent A alone?"

---

## 4. Implementation Phases

### Phase 0 — Foundation (Estimated: 3 days)

**Goal:** Skeleton that loads the ensemble and fires signals without agents.

**Deliverables:**
- `main.py`: CLI entry point with argparse, config loader (YAML), async runner skeleton
- `config/default.yaml`: Pair, timeframe, threshold, agent roster (empty), mode (live/backtest)
- `model/features.py`: Feature computation extracted from `eurusd_sell_improved.ipynb`. Pure function: `compute_features(df_h1, df_d1) → DataFrame`
- `model/ensemble.py`: Load `.joblib` bundle, compute soft-vote probability, return prediction dict with SHAP top-5
- Signal gate: threshold check + cooldown + session filter
- Output: JSONL signal log writer
- `data/fetcher.py`: MT5 data acquisition with cache-first pattern (CSV read first, MT5 fallback for incremental fetch)

**Validation criteria:**
- Run on April 2026 data. Must reproduce the 21 candidate signals from the sealed test.
- Verify probability values match the notebook output exactly.
- Model freshness check warns if bundle is >90 days old.

**Files created:**
```
frival/
├── main.py
├── config/default.yaml
├── model/__init__.py
├── model/features.py
├── model/ensemble.py
├── model/models/          # symlinked .joblib files
├── data/__init__.py
├── data/fetcher.py
├── output/signals/
├── output/reports/
└── pyproject.toml
```

### Phase 1 — Single Agent (Estimated: 4 days)

**Goal:** One technical agent evaluates signals via OpenRouter. Measure precision lift.

**Deliverables:**
- `agents/__init__.py`
- `agents/base.py`: OpenRouter client abstraction
  - Async HTTP client with retry (exponential backoff, max 3 attempts)
  - Structured output enforcement (JSON mode / function calling)
  - Timeout: 30s per call
  - Cost tracking (token usage per request)
- `agents/technical.py`: Load system prompt, inject feature vector + D1 context + SHAP values, parse structured response
- `agents/prompts/technical.txt`: System prompt with April-detection rule
- Decision synthesis: single-agent version (agent confirms → fired; rejects → shelved)
- Backtest runner: basic date-range looper (no walk-forward folds yet)

**Validation criteria:**
- Run on validation period (2025-07 → 2025-12, ~385 candidate signals).
- **Rejection rate between 30% and 60%.** If >60%, prompt is too aggressive. If <30%, agent adds insufficient value.
- Agent-filtered precision > raw precision with non-overlapping Wilson CI.
- Zero unhandled schema violations from agent responses.
- Average agent latency < 15s.

**Files created:**
```
frival/agents/
├── __init__.py
├── base.py
├── technical.py
└── prompts/
    └── technical.txt
frival/backtest/
├── __init__.py
├── runner.py
└── report.py
```

### Phase 2 — Dual Agent + Full Synthesis (Estimated: 5 days)

**Goal:** Add fundamental agent. Parallel evaluation. Complete decision synthesis. Run sealed test.

**Deliverables:**
- `agents/fundamental.py`: Web-search-enabled prompt, structured output parsing
- `agents/prompts/fundamental.txt`: System prompt with macro event risk detection
- `agents/senior.py`: Coordination layer (rule engine implementing the 6-rule table)
- Parallel execution via `asyncio.gather` (both agents run simultaneously)
- Full decision synthesis → structured output
- Backtest runner enhancement: supports purged walk-forward folds for Wilson CI

**Validation criteria — sealed test (2026-01 → 2026-07, ~578 candidate signals):**
1. **Primary:** Agent-confirmed subset precision ≥ 0.420 with Wilson CI lower bound > 0.400 (breakeven)
2. **Secondary:** No single month worse than −3R under agent filtering (target: April ≤ −2R)
3. **Rejection rate:** 30–60%
4. **April-specific:** Agent B (fundamental) must have rejected ≥50% of April signals. If it confirmed most April signals, the prompt is insufficient.
5. Agent A + Agent B filtered precision must exceed Agent-A-only precision by a non-trivial margin (demonstrating fundamental adds value beyond technical alone)

**CRITICAL:** The sealed test set must not have been used during Phase 1 agent development. If it was, the CI bounds are invalid and the framework must be re-validated on a future period. This is the single most important governance rule in the entire project.

**Files created:**
```
frival/agents/
├── fundamental.py
├── senior.py
└── prompts/
    └── fundamental.txt
```

### Phase 3 — Backtest Framework & Governance (Estimated: 4 days)

**Goal:** Make the system self-measuring. Every run produces a standardized evaluation report. Config-driven A/B testing.

**Deliverables:**
- `backtest/runner.py`: Complete date-range looper with purged walk-forward folds, forward outcome resolution, vector backtest integration
- `backtest/report.py`: Auto-generate precision table, EV per signal, monthly breakdown, Wilson CI, rejection rate analysis
- A/B testing: run two configs on the same data range, produce diff report
- Report output: machine-readable `backtest_report.md` comparable across runs
- Config validation: reject invalid agent rosters, missing model bundles, inconsistent date ranges at startup
- Agent decision caching: hash (feature vector + D1 context) to avoid redundant API calls during re-runs

**Validation criteria:**
- Two consecutive runs with the same config on the same date range produce identical precision (cached agent decisions ensure reproducibility)
- A/B diff report correctly identifies which agent roster performed better
- Report generation completes in <2 minutes for a 6-month backtest window (excluding agent API calls)
- Walk-forward Wilson CI calculation matches manual calculation to 3 decimal places

### Phase 4 — Live Paper Trading (Estimated: 4 days, then 60–90 day observation period)

**Goal:** Run on current market data. No real money. Observe real-world latency and agent quality over time.

**Deliverables:**
- Windows Task Scheduler trigger: run `main.py --mode live` at :01 past each H1 candle close
- Error alerting: if MT5 connection fails, OpenRouter returns 5xx, or agent output fails schema validation, log prominently and continue (do not crash)
- Weekly review automation: aggregate past 7 days of signals, compute preliminary precision against actual market outcomes
- Signal dashboard: simple CSV/JSON summary of past 30 days (fired vs shelved, rejection reasons, agent latency trends)

**Success criteria (60–90 day observation):**
1. Agent-confirmed subset precision ≥ 0.420 on forward paper data
2. Rejection rate remains in 30–60% range
3. No unexplained spikes in agent latency (indicating API degradation)
4. No schema violations from agent outputs (prompt is stable)
5. April 2026-type months are caught (at least one month where rejection rate spikes above baseline, correctly identifying regime stress)

**Go / No-Go for live deployment:**
Only after all 5 criteria above are met on forward paper data — not on historical data. Live risk: 0.25–0.5% per signal max, hard monthly stop at −3R.

---

## 5. Bottleneck Analysis & Mitigations

| Bottleneck | Severity | Phase | Mitigation |
|---|---|---|---|
| **LLM latency in backtesting** (~1,156 API calls for 578 signals × 2 agents) | CRITICAL | Phase 2 | Batch multiple signals per prompt (evaluate 5–10 in one call). Hash-based agent decision caching for re-runs. Start with April-only subset first. |
| **OpenRouter cost** ($0.003–$0.015 per signal × 578 × 2 agents ≈ $3.50–$17.30 per full backtest) | LOW | Phase 2 | Trivial for development. In production, gate with cheaper model first; escalate to Claude/GPT-4o only on borderline signals (probability in [0.306, 0.35]). |
| **MT5 data availability** (terminal must be running, symbol visible in Market Watch) | MEDIUM | Phase 0 | Cache-first pattern: CSV as primary source, MT5 as fallback. Health check at startup with clear error message. |
| **Model drift** (ensemble trained on 2020–2025; market evolves) | HIGH | All | Model freshness check at startup (warn if >90 days old). Scheduled retraining is a separate pipeline, not part of this framework. |
| **Agent hallucination** (LLM invents prices, misinterprets context) | MEDIUM | Phase 1 | Structured output enforcement via JSON mode. Schema validation on every response. Reject + log on violation. Never silently patch. |
| **Non-deterministic backtesting** (LLM calls are inherently non-deterministic) | HIGH | Phase 2 | Accept this. Agent layer is a filter, not a ranker. Two runs may produce different subsets. Report precision with Wilson CI to quantify variance. For reproducibility, cache decisions by signal hash. |
| **Over-optimization on the sealed test set** | CRITICAL | Phase 1–2 | Sealed test is only evaluated ONCE per agent configuration. Agents are developed and prompt-tuned on validation data only (2025-07 → 2025-12). Any leak invalidates the experiment. |
| **OpenRouter model deprecation or API changes** | LOW | All | Abstract provider behind `agents/base.py` interface. Config-driven model selection. If a model is removed, swap in config, not in code. |

---

## 6. Success Criteria — Decision Gate Summary

| Gate | Metric | Threshold | Phase |
|---|---|---|---|
| **G1** | Model reproduction | Probability values match notebook output exactly | Phase 0 |
| **G2** | Rejection rate | 30% ≤ rejection rate ≤ 60% | Phase 1 |
| **G3** | Agent precision lift (validation) | Agent-filtered precision > raw precision; CIs non-overlapping | Phase 1 |
| **G4** | Agent precision lift (sealed test) | Agent-confirmed precision ≥ 0.420 with CI lower bound > 0.400 | Phase 2 |
| **G5** | Max monthly drawdown (sealed test) | No month worse than −3R under agent filtering | Phase 2 |
| **G6** | April 2026 detection | Agent B must reject ≥50% of April signals | Phase 2 |
| **G7** | Agent B adds value | Both-agent precision > Agent-A-only precision | Phase 2 |
| **G8** | Forward paper precision | ≥ 0.420 on 60+ days of live paper data | Phase 4 |

**Promotion rule:** Promote nothing without net-pips EV AND a non-overlapping Wilson CI versus the baseline. Report precision AND signals/day AND rejection rate together — never precision alone.

---

## 7. Directory Structure

```
frival/
├── main.py                          # Orchestrator entry point
├── pyproject.toml                   # Dependencies: pandas, numpy, mt5, openai (OpenRouter), pyyaml
├── config/
│   ├── default.yaml                 # Base config: EURUSD SELL, threshold 0.306
│   ├── backtest_validation.yaml     # Validation period (2025-07 → 2025-12)
│   └── backtest_sealed.yaml         # Sealed test (2026-01 → 2026-07)
├── model/
│   ├── __init__.py
│   ├── features.py                  # Feature computation (extracted from notebook)
│   ├── ensemble.py                  # Model loading, soft-vote inference, SHAP
│   └── models/                      # Symlinked .joblib bundles
├── agents/
│   ├── __init__.py
│   ├── base.py                      # OpenRouter client: async, retry, structured output, cost tracking
│   ├── technical.py                 # Agent A: technical context evaluator
│   ├── fundamental.py               # Agent B: macro/fundamental evaluator (web search)
│   ├── senior.py                    # Coordination layer (rule engine, 6-entry table)
│   └── prompts/
│       ├── technical.txt            # System prompt: features + D1 context + April detection rule
│       └── fundamental.txt          # System prompt: macro regime + event risk detection
├── data/
│   ├── __init__.py
│   ├── fetcher.py                   # MT5 data acquisition + cache-first CSV pattern
│   └── cache/                       # Cached CSVs, cached agent decisions (by signal hash)
├── backtest/
│   ├── __init__.py
│   ├── runner.py                    # Date-range looper, walk-forward folds, vector backtest
│   └── report.py                    # Precision/EV/CI report generator, A/B diff
├── output/
│   ├── signals/                     # JSONL signal log (YYYY-MM/YYYY-MM-DD.jsonl)
│   └── reports/                     # Generated backtest reports (Markdown + CSV)
└── tests/
    ├── test_features.py             # Verify feature parity with notebook
    ├── test_ensemble.py             # Verify probability parity with notebook
    ├── test_agents.py               # Schema validation, decision synthesis unit tests
    └── test_synthesis.py            # Senior Agent rule engine correctness
```

---

## 8. Dependencies & Integration Points

### External Dependencies
- **MetaTrader 5**: Data source. Must be installed and running. Symbol must be visible in Market Watch.
- **OpenRouter API**: LLM provider. Requires API key. Models used: Claude 3.5 Sonnet (technical), Perplexity Sonar Pro (fundamental).
- **Existing `.joblib` bundles**: `EURUSD_H1_sell_*.joblib` from Iteration 1. Loaded at startup, not modified.

### Integration with Existing Project
- **Feature computation** extracted from `eurusd_sell_improved.ipynb` to `model/features.py`
- **Model inference** extracted from notebook to `model/ensemble.py`
- **Backtest evaluation** uses same R5 (net-pips EV) and R7 (Wilson CI) methodology as the combiner notebook
- **Output format** compatible with existing vector backtest cells for cross-validation
- **No dependency on DeafAgent**. The architectural patterns are borrowed, not the code.

---

## 9. What We Do Not Build

This framework is explicitly scoped to **signal generation**. The following are out of scope:

- **Order execution.** No MT5 order placement. No position sizing. No risk management.
- **Live trading.** Paper trading observes the signal output; no capital is deployed.
- **BUY lane.** The ensemble proved BUY is a random ranker (ROC-AUC 0.505). No BUY lane exists in this framework.
- **Multi-pair support.** EURUSD H1 only for Phase 0–4. Multi-pair is a future extension.
- **Model retraining.** The ensemble is loaded frozen. Retraining is a separate pipeline.
- **Real-time dashboard.** Weekly review is manual CSV/JSON inspection. A dashboard is a Phase 5+ extension.
- **Multi-timeframe signals.** H1 only. H4/D1 signal generation is future work.

---

## 10. Post-Phase 4 Extensions (Future)

1. **Multi-pair**: Extend to GBPUSD, USDJPY with pair-specific ensembles and agent prompts
2. **Model warm-start**: Retrain ensemble on an extended window (2020–2026) incorporating the sealed test period after Phase 4 completes
3. **R4 macro features**: Wire Bloomberg rate-differential / DXY features into the ensemble (improves base model before agent filtering)
4. **R3 TP×SL sweep**: Lower the breakeven from 0.400 to 0.333 by widening TP to 2.0×ATR (the current 0.391 raw precision already clears this)
5. **Live execution bridge**: Connect signal output to a position-sizing + order-execution module (separate system)
6. **Agent performance monitoring**: Track per-agent precision contribution, detect prompt drift, auto-flag when an agent's rejection rate moves outside 30–60%

---

## 11. Risk Log

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agents add zero precision lift (confirm everything or reject randomly) | MEDIUM | Blocks Phase 3 promotion | Rejection rate 30–60% is a hard gate in Phase 1. An agent that confirms/rejects at random will drift outside this range. |
| OpenRouter model deprecation | LOW | Requires config update | Provider abstracted behind interface. Model defined in config, not code. |
| Regime shift makes ensemble obsolete during paper trading | MEDIUM | Invalidates Phase 4 signals | Model freshness check. Scheduled retraining pipeline defined but separate. |
| Cost overrun from excessive API calls during backtesting | LOW | Budget impact | Rate limiting, batch-mode prompts, agent decision caching. |
| Prompt engineering overfits to validation data | HIGH | Degrades sealed-test performance | Sealed test evaluated exactly once per agent config. Any prompt changes require re-validation on unseen data. |
| Fundamental agent has no real-time data during live mode | MEDIUM | Agent B becomes a no-op | Web search via Perplexity provides current news. If search fails, agent returns NEUTRAL (not REJECT) to avoid false vetoes. |

---

*This document defines the architecture and phased implementation plan for Iteration 2. The next step is Phase 0: extracting feature computation and model inference from the notebook into testable Python modules. Start with `model/features.py` and verify parity against the notebook output before progressing to agent integration.*
