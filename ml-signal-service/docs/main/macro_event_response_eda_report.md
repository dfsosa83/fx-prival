# Macro Event Response Dataset — EDA & Integration Report

**Date:** 2026-08-10
**Analyst:** Kilo (Frival Pipeline)
**File:** `ml-signal-service/data/raw/macro/ExportedData.csv` (40.3 MB, 3,790 rows × 1,773 columns)

---

## 1. Data Validation

### 1.1 Schema

| Attribute | Value |
|---|---|
| Rows | 3,790 |
| Columns | 1,773 |
| Time range | 2007-02-14 → 2026-07-31 (~19.5 years) |
| Unique events | 27 macro event types |
| Target | 3-character code (e.g., `NUU`, `DUU`, `UNU`) — 27 classes |
| Missing data | 0.14% (negligible) |
| Price pair | EURUSD (close1 range: 0.9552–1.5973, mean: 1.1807) |

### 1.2 Column Structure

Each row represents one macro event release. The 1,773 columns decompose as:

| Category | Count | Description |
|---|---|---|
| Metadata | 3 | `event`, `time`, `target` |
| OHLCV per window | 90 | `open`, `high`, `low`, `close`, `tick_volume`, `spread` × 15 windows |
| Candlestick structure | 45 | `tWick`, `body`, `bWick` × 15 windows |
| MT5 indicators (Int) | ~360 | Qualitative interpretation (`normal`, `high`, `low`, `oversold`, `downtrend`, etc.) |
| MT5 indicators (Val) | ~360 | Numeric value for each indicator |
| Candlestick patterns | ~915 | 61 pattern types × 15 windows (each: `Up`, `Down`, bare) |
| **Total** | **1,773** | |

### 1.3 Time Windows

Indicators are computed at **15 sequential windows** before each event (numbered 15 → 1, with 15 being furthest from the event and 1 being closest). This creates a 15-bar pre-event technical profile.

### 1.4 Target Encoding

The target is a 3-character ternary code where each position encodes the direction of a forward bar after the event:

| Position | Meaning | Encoding |
|---|---|---|
| 1 | Bar +1 direction | U=Up, D=Down, N=Neutral |
| 2 | Bar +2 direction | U=Up, D=Down, N=Neutral |
| 3 | Bar +3 direction | U=Up, D=Down, N=Neutral |

Distribution is perfectly balanced (1,260–1,268 per directional class, 140–141 per 3-bar combination) — artificially balanced, likely via resampling or synthetic generation.

### 1.5 Top Events

| Event | Count |
|---|---|
| Retail Sales | 325 |
| ECB's President Lagarde speech | 276 |
| Consumer Price Index | 248 |
| Core Harmonized Index of Consumer Prices | 218 |
| ECB Main Refinancing Operations Rate | 187 |
| Harmonized Index of Consumer Prices | 185 |
| ECB's President Draghi speech | 178 |
| HCOB Composite PMI | 176 |
| ISM Manufacturing PMI | 159 |
| GDP (Annualized) | 150 |

Heavily weighted toward USD and EUR macro events — directly relevant to the EURUSD, GBPUSD, and USDCHF pairs.

---

## 2. Comparative Analysis vs. Existing Pipeline

### 2.1 Current Calendar Architecture

The current pipeline has **two independent consumers** of calendar data:

**Consumer 1 — ML Model Features** (`frival/data/calendar.py` → `model/features.py`):

Three calendar features survived feature selection and are used by the models:

| Feature | EURUSD | GBPUSD | USDCHF |
|---|---|---|---|
| `deviation_sum_24h` | ✅ (rank #1, 3/3 votes) | ❌ | ❌ |
| `hours_since_last_high` | ✅ (rank #9, 2/3 votes) | ✅ (rank #7) | ✅ (rank #5) |
| `high_events_next_24h` | ✅ (rank #10) | ✅ (rank #15) | ✅ (rank #21) |

Other 11 calendar features (`high_events_next_1h`, `is_fomc_day`, etc.) were **rejected by all models** — ranked below noise probes with zero importance.

**Consumer 2 — Agent B Context** (`frival/agents/calendar_context.py`):

`build_macro_context()` constructs a rich text summary of recent events (Actual vs Consensus deviations) and upcoming events. This is injected into Agent B's Perplexity prompt for qualitative macro analysis. Agent B can CONFIRM, REJECT, or stay NEUTRAL, and its REJECT acts as a hard veto on the signal.

### 2.2 What the Current Pipeline Lacks

The current pipeline has **zero event-response prediction capability**:

- Calendar features are aggregate counts (`N events in next 24h`), not event-specific predictions
- The model sees "there will be a high-impact event" but has no mechanism to predict **what will happen** as a result
- CB/NFP day flags (`is_fomc_day`, `is_ecb_day`, etc.) are computed but **rejected by all models** — the model found them useless for prediction
- Agent B provides qualitative assessment but relies on web search, which is slow, rate-limited, and non-deterministic

### 2.3 How the New Dataset Complements

| Dimension | Current Pipeline | ExportedData.csv | Gap Filled |
|---|---|---|---|
| Event awareness | Aggregate counts | Per-event profiles | ⬤⬤⬤⬤⬤ |
| Pre-event context | None | 15-window technical profile | ⬤⬤⬤⬤⬤ |
| Post-event prediction | None | 3-bar directional target | ⬤⬤⬤⬤⬤ |
| Quantitative event response | Agent B only (qualitative) | Trainable classifier | ⬤⬤⬤⬤⬤ |
| Event-specific indicators | Not available | 70+ MT5 indicators per window | ⬤⬤⬤⬤⬤ |

The new dataset answers the question the current pipeline cannot: **"Given the current technical structure, what is the most likely post-event price response?"**

---

## 3. Integration Strategy

### 3.1 Recommendation: Macro Event Response Model (MERM) + Agent Gate

**Architecture:**

```
                    ┌──────────────────────┐
                    │  calendar_context.py │
                    │  (existing)           │
                    │  Detects approaching  │
                    │  HIGH-impact event    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  macro_responder.py   │  ← NEW MODULE
                    │  Extracts 15-window   │
                    │  technical profile    │
                    │  from live MT5 data   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  MERM Model           │  ← NEW MODEL
                    │  Predicts 3-bar       │
                    │  post-event direction │
                    │  (U/D/N per bar)      │
                    └──────────┬───────────┘
                               │
                    ┌───────────▼───────────┐
                    │  Event Gate Decision  │
                    │                       │
                    │  MERM ↑ + Model ↑     │
                    │    → AMPLIFY          │
                    │  MERM ↓ + Model ↑     │
                    │    → BLOCK (event     │
                    │      risk override)   │
                    │  MERM ↑ + Model ↓     │
                    │    → promotional gate │
                    │      (if borderline)  │
                    └───────────────────────┘
```

**Why a separate model rather than adding features to the main model:**

1. **Context mismatch**: The main model trains on ALL H1 bars (not just event bars). Adding event-specific features would mean they're NaN for 95%+ of training rows, creating noise.
2. **Specialization**: The MERM is a specialized classifier for a narrow but high-impact use case (macro event response). Keeping it separate allows independent retraining and evaluation.
3. **Gate integration**: A separate model can act as a gate — blocking trades when the event outlook contradicts the model signal, or amplifying when they align.

### 3.2 Implementation Plan

#### Phase 1 — Model Training (in `ml-signal-service/`)

**New file:** `ml-signal-service/macro_response_model.py`

```
Input:  15-window technical profile from ExportedData.csv
        Features to use: top-20 indicators by importance from each window
        Total features: ~300 (20 indicators × 15 windows)
Output: 3-bar post-event direction classification (U/D/N per bar)
        → 3 separate binary classifiers OR 1 multi-output classifier

Model:  LightGBM or XGBoost (matches existing ensemble)
        OR simple Logistic Regression (interpretable, fast inference)
        OR Ordinal classifier (U=1, N=0, D=-1)

Target simplification:
  - Bar 1 direction: 3-class → 2-class (Up vs Not-Up)
  - Bar 2 direction: 3-class → 2-class (same direction as Bar 1 vs reversal)
  - Bar 3 direction: 3-class → 2-class (extend vs fade)

Evaluation: ROC-AUC per bar, precision@1, calibration
```

**Training data:** 3,790 events × 27 event types. Split 70/15/15 by time (not random) to test generalization to unseen market regimes.

**Feature selection:** Use noise-injection voting (same method as existing pipeline) to identify which indicators in which windows carry signal.

#### Phase 2 — Runtime Integration (in `frival/agents/`)

**New file:** `frival/agents/macro_event_responder.py`

```python
def predict_event_response(bar_dt, pair, calendar, mt5_data):
    """
    1. Check if a HIGH-impact event is scheduled in the next 1h
       (reuse calendar_context's event detection)
    2. Extract 15 H1 bars of technical indicators from MT5 cache
    3. Run MERM inference → 3-bar directional prediction
    4. Return {bar1: U/D/N, bar2: U/D/N, bar3: U/D/N, confidence: 0-1}
    """
```

**Entry points:**

A. **In `main.py`'s `_run_live_inner()`:** After model probability is computed, before gate check:
   - If calendar_context detects an approaching HIGH event, run MERM
   - Pass MERM prediction to gate logic

B. **In `signal_gate.py`:** New gate: `event_risk_gate()`
   - If MERM predicts same direction as model → AMPLIFY (boost probability for gate threshold)
   - If MERM predicts opposite direction → BLOCK regardless of model probability
   - If MERM predicts neutral → pass through (no override)

C. **In Agent B's context:** Inject MERM prediction into `build_macro_context()` output:
   ```
   [MERM Prediction] Based on pre-event technical structure:
     - Bar +1: SELL (confidence: 0.72)
     - Bar +2: SELL (confidence: 0.58)
     - Bar +3: NEUTRAL (confidence: 0.45)
   ```

#### Phase 3 — Training Flow Integration

**Option A: Pre-processed (Recommended for v1)**

Train MERM once on ExportedData.csv, serialize to `.joblib`, deploy alongside other models.

- Pro: Fast inference, no retraining needed, predictable behavior
- Con: Static — won't adapt to new market regimes

**Option B: Dynamic retraining**

Periodically retrain MERM on updated ExportedData.csv (if the data source provides updates).

- Pro: Adapts to regime changes
- Con: Requires data pipeline maintenance, adds complexity

**Recommendation:** Start with Option A (pre-processed). Add dynamic retraining in Phase 2 if MERM proves alpha-generating.

### 3.3 Indicator Mapping

The ExportedData.csv uses MT5 internal indicator names (e.g., `iACInt15`, `iRSIVal15`). These map to:

| CSV Column Pattern | MT5 Indicator | Available in `features.py`? |
|---|---|---|
| `iRSIVal*` | Relative Strength Index | ✅ `rsi` |
| `iMACDVal*` | MACD | ✅ `macd`, `macd_signal`, `macd_hist` |
| `iATRVal*` | Average True Range | ✅ `atr` |
| `iADXVal*` | ADX | ✅ `adx` |
| `iBandsVal*` | Bollinger Bands | ✅ `bb_upper`, `bb_lower`, `bb_middle` |
| `iOBVVal*` | On Balance Volume | ✅ `obv` |
| `iSARVal*` | Parabolic SAR | ✅ `sar` |
| `iCCIVal*` | Commodity Channel Index | ✅ `cci` |
| `iMomentum*` | Momentum | ✅ `momentum` |
| `iForce*` | Force Index | ✅ `force_index` |
| `iAlligator*` | Alligator | ✅ `alligator_jaw`, `teeth`, `lips` |
| `iIchimoku*` | Ichimoku Cloud | ✅ `ichimoku_tenkan`, `kijun` |
| `iStochastic*` | Stochastic | ✅ `stoch_k`, `stoch_d` |
| `candlestick patterns` | Doji, Harami, etc. | ❌ Not currently computed |

For MERM inference at runtime, we extract the same indicators from the `compute_features()` output (already available) rather than recomputing from scratch.

### 3.4 Minimum Viable Feature Set

Based on the MT5 indicators available in both the dataset and our feature pipeline, the v1 MERM should use:

| Indicator | Windows | Features |
|---|---|---|
| RSI | 15, 10, 5, 1 | RSI values + overbought/oversold flags |
| ADX | 15, 10, 5, 1 | ADX values + trend strength |
| ATR | 15, 10, 5, 1 | ATR values (volatility compression/expansion) |
| MACD | 15, 10, 5, 1 | MACD line, signal, histogram |
| BB Width | 15, 10, 5, 1 | Bollinger Band width (volatility) |
| OBV | 15, 10, 5, 1 | OBV slope (accumulation/distribution) |
| Candlestick structure | 15, 10, 5, 1 | tWick, body, bWick ratios |

**Total: ~84 features** (7 indicators × 4 windows × 3 components)

This is a tractable feature space for 3,790 training samples.

---

## 4. Profitability Assessment

### 4.1 Expected Alpha Sources

| Mechanism | Expected Impact | Rationale |
|---|---|---|
| **False signal filtering** | +0.5–1.5 signals/month prevented | MERM blocks trades where model fires but event setup predicts reversal |
| **Missed signal recovery** | +0.2–0.5 signals/month recovered | MERM promotes borderline signals (p < threshold but near it) when event setup aligns |
| **Confidence amplification** | +5–15% precision on event-day signals | When MERM and model agree, historical precision on such consensus signals tends to be higher |
| **Agent B augmentation** | Faster, deterministic macro judgment | MERM provides quantitative event prediction without web search latency or API costs |

### 4.2 Quantitative Estimate (Conservative)

Current pipeline metrics (EURUSD v3, 25-feature model):
- ROC-AUC: 0.674
- Precision: 0.411
- Signals/month: 4–6 (during live trading hours)

**If MERM achieves even 0.55 ROC-AUC** (modest for binary classification):

| Scenario | Without MERM | With MERM | Delta |
|---|---|---|---|
| Monthly signals | 5.0 | 4.5 | -10% (less trades) |
| Precision | 0.411 | 0.480 | +16.8% |
| Expected winning trades/month | 2.06 | 2.16 | +0.10 |
| Expected losing trades/month | 2.94 | 2.34 | -0.60 |

The MERM acts primarily as a **false-positive filter** — it blocks ~0.5 signals/month that would have lost, while sacrificing ~0.5 signals/month that might have won. The net effect is fewer but higher-quality trades.

**Risk-adjusted return improvement: ~15–25%** (from higher precision, assuming similar win/loss magnitudes).

### 4.3 Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Overfitting to 3,790 samples | Medium | Time-based split (train on pre-2024, test on 2024-2026) |
| Balanced dataset → biased classifier | Medium | Use probability calibration (Platt scaling) |
| MERM blocks valid signals (false negative) | Medium | Soft gate: block only when MERM confidence > 0.7 |
| Indicator drift between MT4 (source) and MT5 (runtime) | Low | Validate using our own `compute_features()` output |
| Event type mismatch (MERM trained on CPI but runtime sees GDP) | Low | Train per-event-type models OR use event type as feature |
| Inference latency | Low | LightGBM inference < 1ms; 15-window extraction < 10ms |

### 4.4 Success Criteria

- **Gate 1 (Training):** MERM ROC-AUC ≥ 0.60 on holdout (2024-2026) — confirms signal exists
- **Gate 2 (Backtest):** MERM-augmented backtest on April-July 2026 data shows precision improvement ≥ 10%
- **Gate 3 (Demo):** 2-week shadow run — MERM predictions logged but not acted on; review alignment with actual price action
- **Gate 4 (Live):** MERM blocks verified as correct at > 60% rate after 20 event-day observations

---

## 5. Conclusion

**The ExportedData.csv dataset is high-value and directly complementary to the current pipeline.** It fills a critical gap — event-response prediction — that the current pipeline cannot address quantitatively.

**Recommended path:**

1. **Week 1:** Train v1 MERM on top-20 indicators × 4 windows (~80 features), evaluate on time-based holdout
2. **Week 2:** Integrate MERM into `signal_gate.py` as an event risk gate, shadow-run in demo mode
3. **Week 3:** If shadow results are positive, activate MERM gate in live mode with soft-block threshold (confidence > 0.7)
4. **Week 4:** Review, calibrate, and decide whether to promote to hard gate or keep as soft gate

**Integration touchpoints (files to create/modify):**

| File | Action | Description |
|---|---|---|
| `ml-signal-service/macro_response_model.py` | **CREATE** | Training pipeline for MERM |
| `ml-signal-service/models_bin/MERM_v1.joblib` | **CREATE** | Serialized MERM model |
| `frival/agents/macro_event_responder.py` | **CREATE** | Runtime inference module |
| `frival/agents/calendar_context.py` | MODIFY | Add MERM prediction to context text |
| `frival/signal_gate.py` | MODIFY | Add `event_risk_gate()` |
| `frival/main.py` | MODIFY | Call MERM before gate evaluation |
| `ml-signal-service/.gitignore` | MODIFY | Ensure `.joblib` tracked (already fixed) |

---

## 6. Post-Report Review — Direct Dataset Inspection (2026-08-10)

Re-audit of `ExportedData.csv` on 2026-08-10 (3,790 rows, 1,773 columns) surfaced several facts that materially change the recommendations in Sections 3–5. This section documents what was verified against the raw file, what needs correcting, and the revised integration path.

### 6.1 Timeframe Correction — Data is M1, not H1

Section 3.2 assumes the 15 pre-event windows are **H1 bars** ("Extract 15 H1 bars of technical indicators from MT5 cache"). Direct measurement of the OHLCV columns contradicts this:

| Metric | Measured value | H1 expectation | M1 expectation |
|---|---|---|---|
| Median `high–low` per window | **2–3 pips** | 8–15 pips | 1–3 pips |
| Median `tick_volume` per window | **72–83** | 400–1,500 | 40–150 |
| Median `close_i – close_{i+1}` | **≈ 1 pip** | 5–10 pips | ≈ 1 pip |
| Event times end in `:30`, `:45` | yes | not H1-aligned | consistent |

The 15 windows are **M1 (1-minute) bars covering the 15 minutes immediately before the event**. The 3-character target therefore encodes the **next 3 minutes** after the release, not the next 3 hours.

**Consequences for the proposed architecture:**

- MERM is a **micro-structure spike predictor** with a 3-minute horizon — it does NOT forecast the H1 direction our live models trade.
- The proposal in §3.2 to feed MERM with output from `compute_features()` (which is H1) would create a timeframe mismatch that invalidates any live inference. MERM inference must be sourced from **M1 MT5 bars**, not the H1 cache.
- The "amplify / block" gate logic in §3.1 needs reframing: MERM predicts *whether the first 3 M1 candles after release move against our SELL signal*, not whether the H1 direction is right. Its natural role is a **release-moment veto** (skip trading in the 5–10 min after a high-impact event when MERM disagrees), not a directional confirmation.

### 6.2 Feature-Level Data Quality

Full-dataset inspection of the 1,140 indicator columns (570 `*Val*` + 570 `*Int*`) and 360 candlestick columns:

| Column class | Total | Dead (constant or all-zero) | Effective |
|---|---|---|---|
| MT5 `*Int*` (categorical) | 569 | **135** (23.7%) | 434 |
| MT5 `*Val*` (numeric) | 570 | **120** (21.1%) | 450 |
| Candlestick patterns | 360 | **102** (28.3%) | 258 |
| **Total indicator/pattern width** | **1,499** | **357 (23.8%)** | **1,142** |

Examples of dead columns: `iACInt15`, `iADInt15`, `iAOInt15`, `iFractalsInt15`, `iGatorInt15`, `iMomentumInt15`, `iOsMAInt15`, `iRVIInt15`, `iTriXInt15` (all constant across 3,790 rows).

**Action:** Drop dead columns **before** feature selection. The report's §3.4 minimum viable set (~84 features) is a good starting point precisely because it avoids most of the dead surface, but a full-data dead-column filter is a one-line preprocessing step that shrinks memory footprint by ~24% and removes noise probes disguised as features.

### 6.3 Missing "Surprise" Signal — the Feature That Already Works Live

The current EURUSD live model's **#1 ranked calendar feature** is `deviation_sum_24h` (Actual − Consensus normalized over 24h). ExportedData.csv **does not contain Actual or Consensus values** — only the technical setup and the post-event direction.

Implication: MERM as designed learns *"given this technical setup, what does price do after any event of this type"*. It cannot distinguish a CPI beat from a CPI miss, or a hawkish Fed cut from a dovish one. The two most information-rich variables (surprise magnitude, surprise direction) are absent.

**Options:**

1. **Enrich at training time.** Left-join `EconomicCalendarEvents-YYYY.csv` (already used by `frival/data/calendar.py`) onto ExportedData.csv on `(event, time)` to add `actual`, `consensus`, `deviation`. This turns MERM from "technical-only" to "technical + surprise" — same information class the ML model already values highly.
2. **Accept the limitation and position MERM narrowly** as a "post-release M1 volatility filter" that does not attempt to predict the H1 direction, just the immediate M1 chop.

Option 1 is strongly preferred and should be part of Phase 1.

### 6.4 Balanced Target — Verify Not Synthetic Before Trusting Base Rates

Section 1.4 already notes the target is "artificially balanced". Direct count confirms **exactly 140–141 rows per 3-character class** (27 classes × ~140 = 3,780 ≈ 3,790). This is not natural — real event responses are heavily biased toward `N`-heavy codes because most 1-minute post-event moves are small.

**Before training MERM**, we must determine whether the balancing came from:

- Resampling (weighted duplication of minority classes) → **calibration will be biased**, precision on live imbalanced data will collapse
- Synthetic data (SMOTE-like generation) → **features may not reflect a real technical setup**
- Selection from a much larger population → benign but reduces effective sample size

Run: check for exact-duplicate rows (rebalanced), near-duplicate rows in feature space (synthetic), or row-count vs true event count from `EconomicCalendarEvents` files (selection).

### 6.5 Time-Zone Ambiguity

Event `time` is stored as `YYYY.MM.DD HH:MM` with no timezone marker. The current pipeline runs on UTC. Before joining ExportedData.csv with our calendar or MT5 data, we must confirm:

- Is `time` in UTC, broker time (typically UTC+2/+3), or event-country local time?
- Fast check: for a fixed event with a known release time (e.g., US NFP is 08:30 ET = 13:30 or 12:30 UTC depending on DST), inspect stored `time` and reconcile.

Getting this wrong misaligns MERM inference by 1–3 hours and silently breaks the gate.

### 6.6 Training/Test Split — Avoid Leaking Into Live Test Window

Row distribution by year: 3,335 rows in 2007–2024, 455 rows in 2025–2026.

The current EURUSD ensemble was **trained** through 2025-06-30 and **validated** on 2025-07-01 → 2025-12-31. The live test window is 2026-01-01 onward. If MERM is trained on data through 2025-12-31 and its predictions are then used to gate live signals, the gate is fair. But if MERM is evaluated on 2026 data and that same window is used to measure the *combined* MERM+model precision, we conflate two test sets.

**Recommended MERM split:**

- **Train:** 2007-02-14 → 2024-06-30 (~3,050 rows)
- **Validation:** 2024-07-01 → 2025-12-31 (~440 rows)
- **Sealed test:** 2026-01-01 → 2026-07-31 (~155 rows, aligned with live model's test window)

The 155-row sealed test is small — Wilson 95% CI on any precision estimate will be wide. Plan for a follow-up evaluation once 2026-Q4 data is available.

### 6.7 Convention Alignment

Section 5 proposes `ml-signal-service/macro_response_model.py` as a top-level script. Existing convention in this repo is:

- Training/exploration → `ml-signal-service/notebooks/<pair>/` or `ml-signal-service/steps/`
- Serialized artefacts → `ml-signal-service/models_bin/`
- Runtime consumers → `frival/`

Suggested placement:

| Original | Revised |
|---|---|
| `ml-signal-service/macro_response_model.py` | `ml-signal-service/notebooks/macro/merm_v1_training.ipynb` |
| — | `ml-signal-service/steps/06_macro/train_merm.py` (once notebook is stable) |
| `frival/agents/macro_event_responder.py` | keep as proposed |

Also: the report's §5 table says "`ml-signal-service/.gitignore` — MODIFY — Ensure `.joblib` tracked (already fixed)". This should be verified against the current `.gitignore` — the new `MERM_v1.joblib` may or may not match existing include patterns.

### 6.8 Revised Integration Path

Given 6.1–6.7, the concrete revisions to Sections 3–5:

1. **Reframe MERM's role** in §3.1 as a **release-window micro-structure filter** (0–15 min post-event), not an H1 directional predictor. The gate should suppress signal firing when a HIGH-impact event is within a short window AND MERM predicts adverse M1 chop.
2. **Correct §3.2** to state: "Extract 15 **M1** bars from MT5 (not H1)" — this is a different data source than the H1 cache `compute_features()` reads. Runtime module must pull M1 bars directly.
3. **Add a §3.5** — feature enrichment: left-join calendar Actual/Consensus onto training data.
4. **Add a §3.6** — dead-column filter as a preprocessing step (removes ~357 columns).
5. **Downgrade §4.2 numeric projections** to "illustrative only, pending §6.4 base-rate audit". The current numbers assume MERM predicts on the same horizon as the model, which is not the case.
6. **Add success gate 0 to §4.4**: "Verify time-zone, balance origin, and feature enrichment feasibility before training v1."
7. **Modify §5 file table** per §6.7 conventions.

### 6.9 What Remains Correct

Despite the corrections above, the report's core thesis is sound:

- The dataset **does** provide event-specific pre-event technical profiles that the current pipeline does not encode.
- A separate specialized model **is** the right architectural choice (justifications in §3.1 stand).
- The event risk gate concept **is** the right integration point.

The corrections narrow the claim from "MERM predicts H1 event response" to "MERM predicts M1 post-release micro-structure and vetoes trades during high-risk release windows" — a smaller but still valuable role, and one that composes cleanly with the existing Agent B calendar gate.

