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

## 8. Cross-System Technical Review — 2026-08-03 (Findings + Next-Step Roadmap)

*This section supersedes items 8+ of prior planning and consolidates the findings from a full-stack review conducted on 2026-08-03 covering: `project_last_state.md`, EURUSD/GBPUSD/USDCHF `{buy|sell|combiner}_outputs.txt`, `frival/agents/prompts/*`, and `frival/output/logs/2026-08-03_live.log`. It defines the corrective work that must precede any further calendar-integration effort.*

### 8.1 State Snapshot (as of 2026-08-03)

| Item | Value | Source |
|---|---|---|
| Live pairs | EURUSD SELL, GBPUSD SELL, USDCHF SELL | `project_last_state.md` §11 |
| Live signals fired since 2026-07-29 | **0** across 3 pairs / 5 trading days | `frival/output/logs/*.log` |
| EURUSD SELL sealed test | n=24, prec 0.500, EV +0.155R, +3.7R | [eurusd/sell_outputs.txt](../../notebooks/eurusd/sell_outputs.txt) |
| GBPUSD SELL sealed test | n=26, prec 0.423, EV **−0.052R**, −1.4R, val→test gap **+0.115** (overfit) | [gbpusd/sell_outputs.txt](../../notebooks/gbpusd/sell_outputs.txt) / combiner |
| USDCHF SELL sealed test | n=23, prec 0.435, EV **−0.014R**, −0.3R | [usdchf/sell_outputs.txt](../../notebooks/usdchf/sell_outputs.txt) |
| EURUSD BUY combined test | n=596, prec 0.221, **−307.2R** | [eurusd/combiner_outputs.txt](../../notebooks/eurusd/combiner_outputs.txt) |

### 8.2 Bugs and Logical Errors (Ranked by Severity)

#### P0 — Blocking Signal Production or Producing Wrong Reasoning

1. **Borderline lane structurally cannot fire (Agent A Rule 2 auto-trigger).**
   The technical prompts state:
   > *"REJECT only if the ensemble is clearly conflicted: 0 or 1 of the 4 sub-models have probability ≥ threshold."*
   In borderline mode the gate admits bars where `ensemble_p < threshold`. When the ensemble average is below the threshold, it is mechanically likely that 0 sub-models exceed the threshold, so Rule 2 fires automatically. The 2026-08-03 log confirms this: **6/6 sessions** report *"0 out of 4 sub-models above the threshold"* and Agent A returns REJECT. The borderline lane, as instrumented today, is dead-on-arrival — it can only produce SHELVED outcomes.
   - Fix: split Rule 2 into (a) *standard mode*: 0/4 or 1/4 → REJECT, and (b) *borderline mode*: REJECT only if the ensemble is fully collapsed (e.g., 0/4 above `threshold − 0.05`, or max per-model p < `threshold − 0.10`).

2. **USDCHF prompts encode BUY reasoning while the deployed model is SELL.**
   Files `agents/prompts/technical_usdchf.txt` and `fundamental_usdchf.txt` are written for BUY USDCHF (Rule 1 rejects on D1 downtrend, Rule 4 confirms on `price above EMA50 / RSI > 55 / +DI > −DI / risk-on / gold falling`). Per `project_last_state.md` §11 the production direction has been SELL since 2026-07-30. Agents receive the direction in the user message and manage to invert case-by-case, but the *system* prompt still trains the model on the wrong ruleset. Reasoning quality is degraded and the veto logic is inconsistent.
   - Fix: rewrite both USDCHF prompts for SELL direction, mirroring the EURUSD SELL prompt structure with CHF-specific overlays (SNB dovishness, gold weakness → *confirm* SELL USDCHF only when CHF gains, not weakens).

3. **Deployment gate not enforced for GBPUSD and USDCHF.**
   The project's own gating criteria (`project_last_state.md` §12.3) require *"EV > 0 with a CI that clears breakeven (0.400 with Wilson CI low > 0.350)"*. Neither pair meets this:
   - GBPUSD SELL: EV −0.052R, CI95 [0.255, 0.611] — CI straddles breakeven.
   - USDCHF SELL: EV −0.014R, CI95 [0.256, 0.632] — CI straddles breakeven.
   - GBPUSD combiner also flags **overfit** (val→test gap +0.115).
   Both are running live nonetheless. This violates the gate.
   - Fix: downgrade GBPUSD and USDCHF to shadow-only (write JSONL, suppress FIRED status and prints) until either (a) retrain lifts EV positive with CI clearing breakeven, or (b) 60-day live sample confirms edge.

#### P1 — Reasoning Blindspots and Configuration Drift

4. **Agent A is blind to calendar features despite them being top-3 signal drivers.**
   Feature-selection outputs show `deviation_sum_24h`, `hours_since_last_high`, and `high_events_next_24h` in the top-10 for all three pairs. Yet the technical prompt only enumerates EMAs, RSI, MACD, ADX, ATR — the calendar features are absent from the CONFIRM checklist and never influence Agent A. Agent A cannot corroborate or contradict the model's dominant driver.
   - Fix: extend Rule 4 confirm-conditions with calendar checks (e.g., *"`hours_since_last_high` between 2 and 24"* → confirm post-event trend continuation; *"`high_events_next_1h ≥ 1`"* → REJECT for pre-event fade risk).

5. **Combiner notebook config is stale for all 3 pairs.**
   The header comments in `{eurusd,gbpusd,usdchf}/combiner_outputs.txt` still read:
   > *"BUY_ONLY = False # drop SELL lane — non-viable on test set"*
   > *"Drop SELL lane entirely — test set shows SELL model is non-viable (3 signals, 0.333 prec)."*
   These comments predate the SELL pivot (EURUSD) and the Iteration-3 BUY→SELL flip (USDCHF). The combiner still evaluates BUY+SELL uniformly and reports EURUSD BUY-only precision 0.218 (−307.2R) as its default. Reviewers reading these files will draw the wrong conclusions.
   - Fix: rewrite each combiner header block to reflect per-pair production direction (EURUSD SELL-only, USDCHF SELL-only, GBPUSD dual with EV audit). Remove obsolete comments. Add an explicit `PRODUCTION_LANE` variable.

6. **`Precision: 0.000` at `@0.5` reference in all SELL notebooks.**
   Every SELL notebook prints `Precision : 0.000  Recall : 0.000` at the 0.5 reference and a confusion matrix with zero predicted-positive column. This is mechanically correct (isotonic-calibrated ensembles push mass below 0.5, and the operating threshold is 0.306–0.376), but it obscures the model quality readout. A misreading suggests the model is broken.
   - Fix: change the reference-threshold print in the notebook to `@ operating_threshold` (already computed lower down) and remove the misleading `@0.5` block, or wrap it with a note.

7. **Agent B (Perplexity) is an unconditional single point of failure.**
   `senior.py` treats fundamental REJECT as a hard veto that cannot be overridden. On 2026-08-03 Perplexity uniformly returned USD-negative macro context and vetoed 4/6 sessions. Whether the read was correct or not, the current architecture cannot recover from an Agent B misread. Combined with issue #1 (borderline auto-reject), the system had zero-degrees-of-freedom for 5 straight days.
   - Fix: introduce a 3-strike softening — after N consecutive fundamental REJECTs against a same-direction signal that would otherwise pass every other gate, downgrade the veto to a *warning* and require Agent A HIGH confidence to override.

#### P2 — Data Hygiene and Efficiency

8. **`noise_random_walk` importance is nearly at parity with the top real feature (EURUSD BUY: 1056 vs 1106).**
   The noise-injection cut is fragile — one bad seed could exclude a real feature or admit a noise feature. Feature selection stability is not measured.
   - Fix: run the selection with `N=5` random seeds and require features to survive `≥ 3/5` runs. Reject any feature whose margin over the best noise is under 5%.

9. **`obv` is a non-stationary cumulative sum and appears in every model's top features.**
   Its absolute level depends on the starting date of the series. Adding a year of data will shift the whole feature distribution and silently degrade the fit at retrain time.
   - Fix: replace `obv` with `obv_slope_20` (linear-fit slope over 20 bars) or `obv_zscore_100`. Retrain and re-select.

10. **MT5 fetch inefficiency: full 47,200-bar download per hourly run.**
    The 2026-08-03 log shows every session refetches ~47k bars (20–25s per pair) despite `EURUSD_H1_live_cache.csv` existing. Three pairs × 4 sessions/day = 12 full downloads/day.
    - Fix: implement delta-fetch — read cache, request only `(cache_max_dt → now)`, append, dedupe on datetime.

11. **Perplexity citation markers (`[1][2][7]`) leak into JSON `justification` field.**
    Cosmetic but pollutes downstream reports and any dashboard rendering.
    - Fix: strip `[\d+]` runs from the JSON `justification` string during parse in `agents/fundamental.py`.

#### P3 — Dead Code, Cost, and Model Freshness

12. **USDJPY prompts and pair config still exist** (`technical_usdjpy.txt`, `fundamental_usdjpy.txt`, `PAIR_CONFIG['USDJPY']`) despite the pair being decommissioned. Risk of accidental re-enablement.
13. **Zero-signal cost accounting.** Five days × 3 pairs × ~4 sessions × 2 agents ≈ 120 Perplexity + 120 OpenRouter calls with **zero FIRED signals**. Cost-per-signal is currently undefined (division by zero). No dashboard or log line tracks $/signal.
14. **Model freshness clock**: bundles trained through 2025-06-30; today is 2026-08-03 (~13 months stale). Iteration-3 v2 retrain shifted the training endpoint but not by much. Regime dynamics evolve; a rolling monthly retrain cadence is unspecified.

---

### 8.3 Prioritized Roadmap — Immediate Next Actions

**Legend:** effort **S** = under a day, **M** = 1–3 days, **L** = > 3 days.

#### Phase 0 — Unblock Live Signal Production (P0, this week)

| # | Action | File(s) | Effort | Exit criterion |
|---|---|---|---|---|
| 0.1 | Split Agent A Rule 2 into standard vs borderline variants (see §8.2 #1). Regenerate `technical.txt`, `technical_gbpusd.txt`, `technical_usdchf.txt` with a conditional block driven by `mode` in the user message. | `frival/agents/prompts/technical*.txt`, `frival/agents/technical.py`, `frival/agents/context.py` | S | Borderline session with a valid ensemble spread (e.g., 2/4 sub-models within 0.05 of threshold) does not auto-REJECT on Rule 2. |
| 0.2 | Rewrite USDCHF prompts for SELL direction with SNB/gold/safe-haven overlays. Add a `direction` marker at the top of every prompt so future audits catch mismatches. | `frival/agents/prompts/technical_usdchf.txt`, `fundamental_usdchf.txt` | S | USDCHF live session reasoning references SELL and CHF-supportive events as REJECT triggers, not the inverse. |
| 0.3 | Downgrade GBPUSD and USDCHF to shadow-live: continue evaluating and writing JSONL/logs but tag `final_decision = "SHADOW_FIRED"` and suppress console fire prints. Re-promote only when EV > 0 and Wilson CI lower ≥ 0.35 on either sealed retest or 60-day live sample. | `frival/main.py`, `frival/signal_gate.py`, `frival/agents/senior.py` | S | Live command still runs 3 pairs but only EURUSD can print/store a real FIRED. Report shows shadow status distinctly. |
| 0.4 | Strip Perplexity citation markers `[\d+]` from `justification` and `veto_reason` before JSON parse and log write. | `frival/agents/fundamental.py`, `frival/output_writer.py` | S | New JSONL entries contain no `[N]` markers in reason fields. |
| 0.5 | Enforce a startup "prompt-vs-config coherence" check: at `main.py` startup verify each pair's `PAIR_CONFIG['direction']` matches a `# DIRECTION: BUY|SELL` header in its two prompt files; fail fast on mismatch. | `frival/main.py`, prompts | S | Removing the DIRECTION header or flipping direction causes `main.py` to exit with a clear error. |

#### Phase 1 — Reasoning Quality and Config Hygiene (P1, next 2 weeks)

| # | Action | File(s) | Effort | Exit criterion |
|---|---|---|---|---|
| 1.1 | Extend Agent A CONFIRM/REJECT rules to reference `deviation_sum_24h`, `hours_since_last_high`, `high_events_next_1h`. Add pre-event fade REJECT and post-event trend CONFIRM branches. | prompts, `agents/context.py` (surface these features) | M | Sample 20 recent borderline bars → ≥ 8 change decision vs the pre-fix agent. Reasoning cites calendar values. |
| 1.2 | Rewrite combiner notebook headers for each pair with correct `PRODUCTION_LANE`, remove stale "SELL non-viable" comments, and add a top-of-notebook cell that asserts `production_lane == direction_used_downstream`. | `notebooks/{eurusd,gbpusd,usdchf}/*_signal_combiner_improved.ipynb` | S | Running any combiner prints the current production direction and precisely the metrics for that lane; the wrong-lane path is skipped. |
| 1.3 | Replace `@0.5` reference readout in SELL notebooks with `@operating_threshold`; keep the ROC-AUC/PR-AUC printout unchanged. | 3 SELL notebooks | S | Notebook no longer prints `Precision: 0.000` alongside a valid ensemble. |
| 1.4 | Ship Iteration-3 Phase 2 (calendar RAG for Agent B) per §3 of this document. This unlocks historical Agent B backtesting and removes the Perplexity SPOF for backtests. | `frival/agents/calendar_context.py` (new), `agents/fundamental.py`, `main.py`, `data/calendar.py` | M | Sealed 2026-01-01 → 2026-07-03 backtest with calendar-fed Agent B shows non-NEUTRAL decisions on ≥ 30% of gated bars and Wilson CI computed. |
| 1.5 | Implement 3-strike soft-veto for Agent B (see §8.2 #7). Track consecutive fundamental REJECTs per direction in `frival/data/last_signal.json`. | `agents/senior.py`, `data/last_signal.json` schema | S | After 3 consecutive Agent-B REJECTs on same-direction gated signals, next signal is allowed to fire if Agent A HIGH-CONFIRM and no macro-event flag active. |
| 1.6 | Delta-fetch MT5 data (see §8.2 #10). | `frival/data/fetcher.py` | M | Second+ hourly runs fetch ≤ 100 bars and complete in < 5 s per pair. |

#### Phase 2 — Model Robustness and Retrain (P2, next month)

| # | Action | File(s) | Effort | Exit criterion |
|---|---|---|---|---|
| 2.1 | Retrain all three ensembles with training end shifted to 2026-06-30 (recovering 12 months of data). Keep val 2026-07-01 → 2026-12-31 conceptually, but use walk-forward validation. | 3 `*_sell_improved.ipynb`, `models_bin/*_v3.joblib` | M | New bundles saved; per-pair ROC-AUC not worse than v2; EURUSD retains EV > 0 on the freshest 60-day slice. |
| 2.2 | Multi-seed feature selection (`N=5`, keep features surviving ≥ 3/5, require ≥ 5% margin over best noise). | notebooks feature-selection cells | M | Selected feature set reproducible across seeds; `noise_random_walk` never enters selection. |
| 2.3 | Replace `obv` with `obv_slope_20` and `obv_zscore_100`; re-run selection. | `frival/model/features.py`, notebooks | S | Retrained ensembles no longer depend on absolute `obv` level; feature set changes minimally otherwise. |
| 2.4 | Add cost-and-outcome accounting: log `api_calls`, `usd_cost_estimate`, `signals_fired`, `signals_shelved` per session; write daily rollup to `output/reports/cost_YYYY-MM-DD.json`. | `agents/base.py`, `agents/fundamental.py`, `output_writer.py` | S | Daily report shows $/signal or "no signals fired — Nc calls at ~$X". |
| 2.5 | Remove USDJPY prompts and `PAIR_CONFIG['USDJPY']` (or gate behind an `experimental=True` flag). | prompts, `main.py` | S | `python main.py --mode live` cannot select USDJPY without an explicit flag. |

#### Phase 3 — Statistical Validation and Automation (P3, next quarter)

| # | Action | Effort | Exit criterion |
|---|---|---|---|
| 3.1 | Monthly retrain cron: freeze training window at `today − 1 month`, run notebook, validate ROC-AUC ≥ v2, promote to `models_bin/` behind a canary flag. | L | New bundle deployed automatically once per month; canary compares first 20 signals against previous bundle. |
| 3.2 | Regime detector as a fourth gate: pre-classify bar into {trend-with, trend-against, range} using D1 EMA slope + ADX + realized-vol regime; block trend-against signals by default. | M | Sealed retest shows April-style drawdown months lose ≥ 60% of counter-trend signals. |
| 3.3 | Walk-forward CV with `TimeSeriesSplit(n_splits=6, gap=48)` (2-day purge) as the acceptance test for every retrain. | M | Val→test overfit gap < 0.05 for every pair before deployment; GBPUSD's current +0.115 gap becomes a hard fail. |
| 3.4 | Consolidated live dashboard: `output/reports/daily_YYYY-MM-DD.md` summarising per-pair signals, agent decisions, cost, and 30-day rolling precision/EV. | S | Dashboard generated automatically by end-of-day cron; human review takes < 5 minutes. |

### 8.4 Success Criteria (updates to §7)

| Gate | Metric | Threshold |
|---|---|---|
| **G6** | Borderline lane fires at least one signal per pair per week (given ≥ 1 borderline bar/day) | Non-zero FIRED count in a 5-day live window |
| **G7** | Prompt/config coherence | 0 pair-direction mismatches at `main.py` startup |
| **G8** | Shadow → live promotion | GBPUSD/USDCHF only promoted after EV > 0 with Wilson CI low ≥ 0.35 on ≥ 60-day live sample |
| **G9** | Agent B single-point-of-failure removed | Soft-veto logic engages ≥ once in backtest without lowering precision below 0.40 |
| **G10** | Cost transparency | Every day produces a `cost_YYYY-MM-DD.json` with call counts and $/signal (or "no signals") |

---

*Review date: 2026-08-03. Next review: after Phase 0 tasks land. This section is the authoritative work order for the next iteration cycle — do not start Iteration-3 Phase 2 (calendar RAG) until Phase 0.1–0.4 are merged, because Phase 2 depends on a working borderline lane to demonstrate calendar-context lift.*
