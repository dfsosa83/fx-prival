# Iteration 3 — Economic Calendar Integration: Features + RAG

*Internal planning document · July 30, 2026 · Status: Planning · Depends on: Iterations 1–2*

---

## 1. Dataset

**Source:** `EconomicCalendarEvents-YYYY.csv` (2007–2026, yearly files, 20 years of historical data)

**Schema:**

| Field | Type | Example | Description |
|---|---|---|---|
| `Date` | datetime | 01/05/2026 | Event date |
| `Time` | string | 18:00 | Event time (UTC) |
| `Name` | string | ISM Manufacturing PMI | Event description |
| `Impact` | string | HIGH/MEDIUM/LOW/NONE | Importance level |
| `Currency` | string | USD, EUR, GBP, CHF | Target currency |
| `Actual` | string | 47.9 | Released value |
| `Deviation` | float | −1.39 | Actual — Consensus (surprise) |
| `Consensus` | float | 48.3 | Expected value |
| `Previous` | float | 48.0 | Prior period value |
| `Sentiment` | string | LOCKED/ALL DAY/REPORT/SPEECH | Event type classifier |

**Coverage:**

| Currency | Events/year (2026) | Notes |
|---|---|---|
| EUR | 3,441 | Eurozone-wide data |
| USD | 2,606 | US economic calendar |
| GBP | 929 | UK releases |
| CHF | ~100 | Swiss releases |
| JPY | 869 | Japanese data |

**Data loading strategy:** Load all yearly CSVs once at module import or pipeline start. Parse dates, filter by currency pair, index by datetime. Memory: ~270K rows × 20 years × ~200 bytes/row ≈ 54 MB — manageable.

---

## 2. Phase 1 — Feature Engineering

### 2.1 Objective

Add 10–12 calendar-derived features to the `compute_features()` function in `frival/model/features.py`. The noise-injection voting pipeline will determine which features carry predictive signal. If they survive, they improve the model. If not, they're automatically excluded — zero downside.

### 2.2 Features to Engineer

For each H1 bar at time `T`, compute the following from the event calendar:

#### Event presence features

| Feature | Type | Description |
|---|---|---|
| `high_events_next_1h` | int | Count of HIGH-impact events in (T, T+1h] for the pair's currencies |
| `high_events_next_4h` | int | Count of HIGH-impact events in (T, T+4h] |
| `high_events_next_24h` | int | Count of HIGH-impact events in (T, T+24h] |
| `med_events_next_1h` | int | Medium-impact events in next hour |
| `any_event_next_1h` | bool | Any event (HIGH/MED/LOW) in next hour |

#### Surprise (deviation) features

| Feature | Type | Description |
|---|---|---|
| `usd_deviation_sum_24h` | float | Sum of all USD event deviations in last 24 hours |
| `eur_deviation_sum_24h` | float | Sum of all EUR event deviations in last 24 hours |
| `gbp_deviation_sum_24h` | float | Sum of all GBP event deviations in last 24 hours |
| `net_deviation_24h` | float | USD deviation — counter-currency deviation (pair-specific) |

#### Event flag features

| Feature | Type | Description |
|---|---|---|
| `is_fomc_day` | bool | FOMC announcement day (USD) |
| `is_ecb_day` | bool | ECB announcement day (EUR) |
| `is_boe_day` | bool | BoE announcement day (GBP) |
| `is_snb_day` | bool | SNB announcement day (CHF) |
| `hours_since_last_usd_high` | float | Hours since the last HIGH-impact USD event |
| `hours_since_last_eur_high` | float | Hours since the last HIGH-impact EUR event |

### 2.3 No-Lookahead Guarantee (Critical for Backtesting)

For each bar at time `T`:

- **Forward features** (events_next_Xh): Use only events with `Date+Time > T`. This is forward-looking by design — it measures upcoming event risk.
- **Backward features** (deviation_sum, hours_since): Use only events with `Date+Time ≤ T`. The Actual and Deviation values were published before T — no leak.
- **Event flag features** (is_*_day): Use only the Date field. If today is an ECB day, every bar today knows it — the date is public.

### 2.4 Implementation Steps

1. **Create `frival/data/calendar.py`** — Calendar data loader
   - `load_calendar(start_year, end_year, pair)` → DataFrame indexed by datetime
   - `compute_features_for_bar(bar_dt, calendar_df, pair)` → dict of feature values
   - Cache-loaded data in memory (54 MB, load once)
   - Filter by pair currencies (EURUSD → events where Currency in {EUR, USD})

2. **Update `compute_features()` in `model/features.py`**
   - Add calendar features after the existing feature computation
   - Call `calendar.compute_features_for_bar()` for each bar (vectorized where possible)
   - Add new columns to the output DataFrame

3. **Verify no lookahead**
   - Test: pick a bar at 14:00 on FOMC day. The 18:00 FOMC Actual must NOT appear in features.
   - Test: pick a bar at 20:00 on FOMC day. The 18:00 FOMC Actual IS available.

4. **Re-run feature selection**
   - The noise-injection voting in the notebook will automatically include/exclude calendar features
   - If they carry signal (importance > noise threshold), they survive
   - If not, they're excluded — zero downside

5. **Deploy**
   - Update `MODEL_FEATURES` in `model/features.py` with surviving features
   - Retrain the ensemble with the expanded feature set
   - Compare ROC-AUC and precision vs baseline

### 2.5 Expected Impact

| Pair | Expected Benefit | Why |
|---|---|---|
| EURUSD | **High** — ECB/Fed events are the dominant drivers | 3,441 + 2,606 events/year |
| GBPUSD | **High** — BoE/Fed events | 929 + 2,606 events/year |
| USDCHF | **Moderate** — only ~100 CHF events/year | 100 + 2,606 events/year |

The deviation features (surprise) are the most promising. Markets react to how wrong forecasts were, not just whether an event happened. NFP at +50K deviation vs +10K creates different price responses — the model can learn this.

### 2.6 Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Calendar features add no signal (below noise threshold) | Medium | Noise-injection voting automatically excludes them. No harm done. |
| Lookahead leak in featurization | Medium | Thorough unit tests on known FOMC/ECB dates verify no leak |
| Per-pair calendar filtering is wrong | Low | Filter by Currency column — trivial |
| Memory inflation from calendar data | Low | 54 MB loaded once, shared across all pairs |

---

## 3. Phase 2 — RAG/Agent Knowledge Base

### 3.1 Objective

Replace or augment Agent B's web search with structured calendar context. This solves two problems:

1. **Backtesting blindness:** Agent B currently searches current news, making it useless for historical signal evaluation (always returns NEUTRAL).
2. **Latency:** Web search takes 5–15 seconds. Structured lookup is instant.

### 3.2 How It Works

For each signal evaluation, build a pre-computed macro context string from the calendar:

```
=== Macro Context (2026-01-05 13:00 UTC) ===

Last 24 hours:
  - GBP Consumer Credit (Nov): actual £2.077B vs previous £1.747B (+£0.33B beat)
  - GBP Net Lending: actual £6.6B vs consensus £5.8B (+0.84 beat)
  - USD ISM Manufacturing PMI (Dec): actual 47.9 vs consensus 48.3 (-1.39 MISS)
  - USD ISM Prices Paid: actual 58.5 vs consensus 59.0 (-0.31 miss)

Upcoming (next 24 hours):
  - EUR S&P Global Composite PMI (06:00 UTC Jan 6)
  - AUD S&P Global Services PMI (01:00 UTC Jan 6)

Today's flags: no FOMC, no ECB, no BoE.
```

This is injected into Agent B's prompt instead of (or alongside) web search results.

### 3.3 Implementation Steps

1. **Create `agents/calendar_context.py`** — Pre-computed macro summary builder
   - `build_macro_context(bar_dt, pair, calendar_df)` → string
   - Filter events to pair's currencies (EUR/USD for EURUSD)
   - Last 24h: HIGH and MEDIUM events with Actual vs Consensus comparison
   - Next 24h: all scheduled events
   - Flag days: FOMC, ECB, BoE, SNB binary markers

2. **Update `agents/fundamental.py`**
   - Add optional `context_data` parameter to `evaluate()`
   - If `context_data` provided, inject it into the user message instead of triggering web search
   - Keep web search fallback for live mode when no calendar data is available

3. **Update `main.py`**
   - Pass calendar summary to `evaluate_fundamental()` for every signal
   - In backtest mode: use historical calendar data
   - In live mode: use current calendar data (web search still available if needed)

4. **Test backtesting precision with structured context**
   - Re-run sealed test with Agent B receiving calendar context instead of web search
   - Compare agent precision/EV vs baseline (web search) and vs raw model

### 3.4 Agent B Prompt Adaptation

The fundamental agent prompt receives new structured instructions:

```
You will receive a pre-computed macro context from the economic calendar.
Use this INSTEAD of web search for recent events.

The context shows:
- Recent events (last 24h): Actual vs Consensus, deviation direction
- Upcoming events (next 24h): scheduled releases
- Event flags: whether today is a central bank decision day

Evaluate whether the macro picture confirms or rejects the signal.
Only use web search if the context is sparse (few events) and you need
broader context (risk sentiment, geopolitics, central bank policy stance).
```

### 3.5 Expected Impact

| Area | Expected Change |
|---|---|
| Agent B backtest accuracy | Major — no longer returning NEUTRAL on all historical signals |
| Agent B live performance | Improved — structured data is more precise than web-scraped headlines |
| Agent B latency | Reduced from 5–15s to instant (no web search for event data) |
| Signal precision | Unknown — depends on whether Agent B correctly interprets macro context |
| Rejection rate | Should increase (Agent B has real data to REJECT on) |

### 3.6 Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Agent B ignores calendar context and still web-searches | Medium | Prompt explicitly prioritizes calendar over search |
| Historical calendar has missing events | Low | 20 years, 13K+/year per file, verified structure |
| Calendar too large for prompt token limits | Medium | Filter to pair's currencies only + limit to HIGH/MEDIUM impact |
| Context builder is slow for backtesting | Low | Pre-compute with vectorized pandas operations |

---

## 4. Execution Order

| Phase | Task | Prerequisites |
|---|---|---|
| **Phase 1.1** | Build `data/calendar.py` — calendar loader and feature builder | All yearly CSVs available |
| **Phase 1.2** | Integrate calendar features into `compute_features()` | 1.1 complete |
| **Phase 1.3** | Verify no lookahead leak (unit tests on known events) | 1.2 complete |
| **Phase 1.4** | Re-run feature selection + retrain ensembles | 1.3 complete |
| **Phase 1.5** | Integrate new features into Frival model config | 1.4 complete |
| **Phase 2.1** | Build `agents/calendar_context.py` — macro summary builder | 1.1 complete (shared calendar loader) |
| **Phase 2.2** | Update `agents/fundamental.py` to accept calendar context | 2.1 complete |
| **Phase 2.3** | Pass calendar context from `main.py` to Agent B | 2.2 complete |
| **Phase 2.4** | Re-run sealed test with calendar-powered Agent B | 2.3 complete |
| **Phase 2.5** | Compare precision/EV: calendar vs web-search vs raw model | 2.4 complete |

---

## 5. Dependencies

| Dependency | Status |
|---|---|
| 20-year calendar CSV data (2007–2026) | User acquiring files |
| Pandas datetime handling | Already in environment |
| `frival/model/features.py` | No architectural changes needed |
| `frival/agents/fundamental.py` | Minor addition of `context_data` parameter |
| Noise-injection voting pipeline (notebooks) | No changes needed — automatically handles new features |

---

## 6. File Plan

```
frival/
├── data/
│   └── calendar.py              # NEW — calendar loader + feature builder
├── agents/
│   ├── calendar_context.py      # NEW — macro summary for Agent B prompts
│   ├── fundamental.py           # MODIFIED — accept and use calendar context
│   └── prompts/
│       └── fundamental_*.txt    # MODIFIED — add calendar context instructions
├── model/
│   └── features.py              # MODIFIED — add calendar features to compute_features()
└── main.py                      # MODIFIED — pass calendar context to agents
```

**Total new files:** 2 (`calendar.py`, `calendar_context.py`). **Modified files:** 3 (`features.py`, `fundamental.py`, `main.py`).

---

## 7. Success Criteria

| Gate | Metric | Threshold |
|---|---|---|
| **G1** | Lookahead leak | Zero. Calendar features for bar at T must not contain Actual values from events at T+1 or later. |
| **G2** | Calendar features survive noise-injection | ≥ 2 calendar features in selected feature set with importance > noise threshold |
| **G3** | ROC-AUC improvement with calendar features | ≥ +0.01 improvement over baseline for at least one pair |
| **G4** | Agent B rejection rate (calendar context) | 30–60% (same as Phase 1 target) |
| **G5** | Agent B backtest precision lift | Calendar-fed Agent B precision > web-search Agent B precision (or > raw model) |

---

*This document defines the two-phase economic calendar integration plan. Implementation begins when all 2007–2026 yearly CSV files are available.*
