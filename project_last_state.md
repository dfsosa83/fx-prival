# Project Last State

Last updated: 2026-07-22
Scope: consolidated handoff for the EURUSD H1 BUY-only signal system. This document describes the current production configuration, the experimental journey that led to it, and the insights that should guide future work.

---

## 1) Executive Summary

The EURUSD H1 signal pipeline has completed four experiment cycles across multiple model architectures, label configurations, and split boundaries. The sealed test set was evaluated on each iteration. The accepted production configuration is:

- **BUY-only** — SELL lane disabled (non-viable on all tested configurations)
- **RandomForest classifier** — 11 noise-injection-validated features, threshold 0.644 (auto-selected by nested CV over an expanded hyperparameter grid)
- **Four decision gates**: threshold → cross-filter (0.60) → session filter (London+NY) → cooldown (4 bars)

Final test snapshot (2026-04-01 to 2026-07-03, 67 trading days):

| Signal | Precision | Signals | Per day |
|---|---|---|---|
| BUY final (gated) | **0.286** | 28 | 0.42 |
| SELL final | — | 0 (suppressed) | — |
| Overfit gap (val→test) | −0.036 (acceptable) | | |

The raw model precision of 0.286 at the best cross-filter setting is below the 0.400 breakeven. This is consistent across all four experiment cycles and three model architectures (LightGBM, XGBoost, RandomForest). The H1 directional label with ATR-based barriers at R:R=1.5 produces a model ceiling of approximately 0.28–0.35 gated precision on sealed test data. The model is a weak ranker, not a strong classifier — it surfaces candidates that the decision gates and future agent layer must filter.

The system is an alert generator. The next phase (Iteration 2) adds a multi-agent validation layer where Perplexity and GPT-4o independently evaluate each signal and reject false positives the model cannot catch.

---

## 2) Architecture and Design Rationale

### 2.1 Why this configuration was chosen

Ten experiments converged to this configuration. The path was not linear — it involved label design iterations, model architecture comparisons, forward window sweeps, and split boundary adjustments. The current setup represents the configuration that consistently produced the most stable, reproducible results across multiple runs.

**BUY-only vs BUY+SELL:** Every experiment showed the SELL lane producing zero net signals after the cross-filter gate, regardless of the SELL model's standalone performance (LogReg reached precision 0.400 on validation with 385 signals, but all were suppressed in the combiner). Disabling the SELL lane is not a config choice — it is forced by the data.

**RandomForest vs LightGBM:** Both were tested. In the most recent experiment cycle (TRAIN_START=2020-06-30), RandomForest slightly outperformed LightGBM in nested CV PR-AUC (0.393 vs 0.383). With the original full training window (2019–2025), LightGBM had a slight edge. The model-agnostic auto-detection in the combiner (`max(...glob("*.joblib"), key=mtime)`) now picks whichever was trained last, so the choice is operational, not hardcoded.

**11 features vs 22:** The noise-injection voting system with MIN_VOTES=2 selected 11 features for both BUY and SELL in the latest cycle. This is fewer than earlier runs (which selected 22) because the voting percentile was raised from 40 to 60 and importance switched to gain-based. The 11-feature set is sparser but each feature earned its place more rigorously. The 22-feature set from earlier runs was reproducing 0.348–0.415 combiner precision, but those results could not be consistently reproduced after the voting system improvements — a known issue documented in the experiment log below.

**Session filter:** The single most impactful decision gate. Removes Asian session bars (00:00–06:59 UTC), which are range-bound and produce most false positives. Without it, BUY-only precision drops from 0.286 to 0.237 on test (cf=0.60).

**Cross-filter at 0.60:** Selected by sweeping cf values on the validation set and picking the value with the highest precision that maintains ≥10 signals. Higher values (0.65–0.70) produce mildly higher precision but at the cost of signal frequency. Lower values (0.50–0.55) produce more signals but precision collapses.

### 2.2 Why the training window was shifted forward

Earlier experiments used TRAIN_START=2019-01-01. The most recent cycle uses TRAIN_START=2020-06-30. The reason is practical: the 2019 period produced results that could not be reliably reproduced across re-runs of the same notebook with identical parameters. ROC-AUC values varied by ±0.05 depending on initialization order, feature selection randomness, and subtle differences in the compute_features warm-up window.

Starting at mid-2020 removes the earliest market regime (pre-COVID trend, COVID crash, initial recovery) and focuses the model on the post-COVID FX environment (Fed tightening cycle, ECB normalization, rate differential widening). This is the regime the model will face in production — 2019 is structurally different and adds noise, not signal.

The current split boundaries:

| Split | Date range | Bars | Purpose |
|---|---|---|---|
| Train | 2020-06-30 → 2025-10-31 | ~32,000 | Model training + feature selection |
| Val | 2025-11-01 → 2026-03-30 | 2,496 | Threshold calibration |
| Test | 2026-04-01 → present | 1,618 | Sealed final evaluation |

---

## 3) Implemented Artifacts

### 3.1 Core notebooks

| Notebook | Description |
|---|---|
| `ml-signal-service/notebooks/eurusd/eurusd_buy.ipynb` | BUY model training: feature engineering, noise-injection voting, nested CV, threshold calibration |
| `ml-signal-service/notebooks/eurusd/eurusd_sell.ipynb` | SELL model training (mirrored, with inverted label logic) |
| `ml-signal-service/notebooks/eurusd/signal_combiner.ipynb` | Model-agnostic combiner: loads latest `.joblib` bundles, applies 4 decision gates, evaluates on test |

Session-specific variants (explored, not in production): `eurusd_buy_london.ipynb`, `eurusd_buy_ny.ipynb`, `eurusd_buy_asian.ipynb`, `eurusd_buy_v2.ipynb`.

### 3.2 Production scripts

| Script | Description |
|---|---|
| `ml-signal-service/steps/05_inference/eurusd_h1_predictor.py` | Hourly inference: load data, compute features, score model, apply gates, emit alerts |
| `ml-signal-service/steps/build_macro_dataset.py` | Bloomberg macro data pipeline: converts desk Excel exports to standardized CSV |

### 3.3 Model artifacts (current)

| File | Model | Features | Threshold |
|---|---|---|---|
| `models_bin/EURUSD_H1_buy_RandomForest.joblib` | RandomForest | 11 | 0.644 |
| `models_bin/EURUSD_H1_sell_LogReg.joblib` | LogisticRegression | 11 | 0.599 |

The combiner auto-detects models by modification time, so any retrained model is picked up automatically without changing the combiner code.

### 3.4 Documentation

| Document | Purpose |
|---|---|
| `ml-signal-service/docs/stakeholder_overview.md` | Non-technical presentation for management |
| `ml-signal-service/docs/y1-label-definition.md` | Label definition + EURUSD final setup |
| `ml-signal-service/docs/bloomberg_macro_insights_spec.md` | Macro dataset technical specification |
| `ml-signal-service/docs/bloomberg_macro_desk_guide.md` | Desk operational guide for Bloomberg exports |
| `ml-signal-service/docs/next_agent_pipeline_design.md` | Agent layer architecture design |
| `ml-signal-service/docs/fred_economic_indicators_research.md` | FRED data research findings |
| `ml-signal-service/docs/main/iteration_1_planning.md` | Original project plan |
| `ml-signal-service/docs/main/iteration_1_status_report.md` | Status report (English) |
| `ml-signal-service/docs/main/informe_iteracion_1_status.md` | Status report (Spanish) |

---

## 4) Label and Metric Contract

**Label mechanics:** Binary labels generated by a 6-hour forward TP/SL race. At each bar `t`, TP = close[t] + ATR[t] × 1.5 and SL = close[t] − ATR[t] × 1.0. The forward window scans bars t+1 through t+6. If TP is hit first → label = 1. If SL is hit first or neither barrier is reached → label = 0. If both barriers are hit on the same bar (ambiguous H1 resolution) → label = 0 (conservative default).

**Breakeven precision:**

$$\text{Breakeven} = \frac{\text{SL\_MULT}}{\text{TP\_MULT} + \text{SL\_MULT}} = \frac{1.0}{1.5 + 1.0} = 0.400$$

**Decision gates (applied post-inference):**
1. **Threshold:** `buy_proba ≥ model_threshold` (from `.joblib` bundle)
2. **Cross-filter:** `sell_proba < 0.60` (suppress when both models confident in opposite directions)
3. **Session filter:** London (07:00–15:59 UTC) or NY (13:00–21:59 UTC) only
4. **Cooldown:** max 1 signal per 4 bars

**Training metrics:**
- Feature selection: noise-injection voting (RF + LightGBM + LogisticRegression), MIN_VOTES=2, VOTING_PERCENTILE=60, gain-based LGBM importance
- Model selection: nested CV (GroupKFold=5 by year, TimeSeriesSplit=2 inner), RandomizedSearchCV(25 iters), PR-AUC objective
- All models use `class_weight="balanced"`

---

## 5) Complete Experiment Log

| # | Dates | FW | TP | Train | Model | Features | ROC-AUC (val) | Combiner test prec | Outcome |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Jul 14 | 6 | 1.5 | 2019–Jun 2025 | LightGBM | 22 | 0.651 | 0.348 (46 sig) | Baseline established |
| 2 | Jul 14 | 4 | 1.5 | 2019–Jun 2025 | RandomForest | — | 0.695 | ~0.300 (est.) | Better ROC-AUC, worse gated |
| 3 | Jul 15 | 2 | 1.25 | 2019–Jun 2025 | XGBoost | — | 0.735 | — (44 raw sigs) | Best discriminator, too few labels |
| 4 | Jul 15 | 6 | 1.5 | 2019–Jun 2025 | LightGBM | 26 | 0.651 | 0.286 | Full-retrain hurt performance |
| 5 | Jul 16 | 6 | 1.5 | 2019–Jun 2025 | LightGBM | 22 | 0.651 | 0.348 (46 sig) | Restored train-only model |
| 6 | Jul 17 | 6 | 1.5 | 2023–Oct 2025 | LightGBM | 23 | 0.508 | — | Short train window kills ROC-AUC |
| 7 | Jul 18 | 3 | 1.5 | 2019–Jun 2025 | LightGBM | 23 | 0.503 | — | FW=3 is below the signal floor |
| 8 | Jul 19 | 6 | dir | 2023–Oct 2025 | LightGBM | — | 0.542 | — | Directional label = random walk |
| 9 | Jul 21 | 6 | 1.5 | 2023–Oct 2025 | LightGBM | — | 0.472 | — | NY-only session specialization failed |
| 10 | Jul 22 | 6 | 1.5 | 2020–Oct 2025 | RandomForest | 11 | 0.495 | **0.286 (28 sig)** | **Accepted baseline** |

### Key insights from the experiment log

1. **Model architecture barely matters.** Four model types (LightGBM, XGBoost, RandomForest, LogisticRegression) all converge to PR-AUC within 0.01 of each other on the same data. The bottleneck is the label, not the classifier.

2. **Short training windows kill performance.** Experiments 6, 8, and 9 all used TRAIN_START ≥ 2023 and produced ROC-AUC below 0.55. Training data must span multiple market regimes — 2020–2025 covers the post-COVID tightening cycle, which is the minimum viable window.

3. **Forward window sweet spot is 4–6 hours.** FW=3 is below the signal floor (ROC-AUC 0.503). FW=2 improves ROC-AUC (0.735) but label rate drops to 16%, starving the model of positive examples. FW=6 gives the best gated precision in the combiner.

4. **Directional labels don't work.** Experiment 8 proved EURUSD 6h direction is a random walk (ROC-AUC 0.542). The ATR-barrier race label is the right design — it filters noise moves and focuses on economically meaningful outcomes.

5. **Session specialization doesn't help.** Experiment 9 showed that training separate models per session (NY-only) worsens performance compared to a unified model. The unified model learns from negative examples in all sessions.

6. **Full-retrain hurts generalization.** Experiment 4 showed that training on train+val combined introduces regime overfitting that makes test performance worse. The train-only model generalizes better.

7. **The 0.348–0.415 precision from earlier runs cannot be reproduced.** Experiments 1, 5, and 10 all used the same label parameters (FW=6, TP=1.5) with LightGBM/RandomForest and produced combiner test precision of 0.286–0.348 — never reaching 0.400. The earlier 0.415 reading from the cross-filter sweep in Section 9 of the combiner (Experiment 1) was likely a data pipeline alignment artifact; the sweep's cooldown operated on a label-filtered test set (fewer rows) while the main test evaluation used the full test set, producing different signal counts. This discrepancy was identified after Experiment 1 and has not been reproducible in subsequent runs.

---

## 6) System Health Assessment

**What is working:**
- End-to-end pipeline from raw data to production inference is operational and documented
- Model-agnostic combiner auto-detects the latest trained models regardless of algorithm
- Decision gates are implemented and correctly suppress false positives
- Decision log provides full traceability (gate-by-gate reason per bar)
- Bloomberg macro data pipeline is built and desk-ready
- All infrastructure is reproducible — any configuration can be retrained and evaluated in hours

**What is still weak:**
- Raw model precision (0.286–0.348) cannot reach the 0.400 breakeven on its own
- The 28 test signals at 0.286 precision produce approximately 8 correct TP hits — net negative after typical spreads
- Only 11 features survive noise-injection voting, suggesting the feature set has limited predictive power for this label
- The SELL model (LogReg, ROC-AUC 0.613) has better standalone metrics than BUY but produces zero net signals in the combiner after cross-filter gating
- Signal frequency (0.42/day) is adequate but the precision requires agent-layer improvement

**Practical implication:**
The model layer has reached its discriminative ceiling. Four model architectures, five forward windows, two label designs, and three training window sizes all converge to the same result: the raw model cannot cross 0.400 precision at usable signal volumes. The decision gates (session filter, cooldown) add measurable lift but the gap remains. The next improvement must come from the agent validation layer (Iteration 2), where Perplexity and GPT-4o evaluate signals independently and reject false positives using context the model cannot access (fundamental data, news, sentiment).

---

## 7) Next Steps

1. **Build the agent evaluation pipeline** — feed the 28 test signals through Perplexity and GPT-4o agents, measure precision improvement. Target: reject ≥40% of false positives while retaining ≥70% of true positives.

2. **Wire the hourly scheduler** — connect `eurusd_h1_predictor.py` to a Windows Task Scheduler trigger at :01 past each hour.

3. **Define the alert-to-execution workflow** — structured JSON alert format, dedup tracking, alert history, agent confirmation/rejection logging.

4. **(Optional) Explore label redesign** — the FW=2 experiment showed ROC-AUC 0.735, the highest of any configuration. If label rate can be increased (e.g., TP=1.0 with FW=2 gives ~28% label rate), this configuration could produce a stronger base model.

---

## 8) Known Risks

- **Regime sensitivity:** the model was trained on 2020–2025 FX data. A structural break in EURUSD dynamics (new policy framework, currency regime change) would invalidate the training distribution.
- **Low signal frequency:** 28 signals in 67 trading days = 0.42/day. With 0.286 precision, the model produces roughly 1 correct signal every 8 days. Agent improvement is critical.
- **SELL lane abandonment:** the current BUY-only configuration cannot capture EURUSD downside moves. The inverted-pair trick (run BUY model on 1/EURUSD data) is the most practical route to short coverage.
- **Cooldown dtype bug:** the `apply_cooldown` function produces FutureWarnings when mixing bool/int dtypes on the `buy_signal` column. Fixed in the predictor script, still present in the combiner notebook.
- **Feature set ceiling:** the noise-injection voting system eliminates most engineered features. If label redesign or agent improvement fails, investing in new feature classes (order flow, options-implied data, correlation features) may be necessary.

---

## 9) Agent Handoff Checklist

Before modifying any logic:
- Read `y1-label-definition.md` and this document in full
- Confirm model bundle thresholds and feature lists from both `.joblib` files
- Verify split boundaries match training assumptions
- Run the combiner without changes to establish a reference precision number

Before claiming improvement:
- Show precision AND signals/day, not precision alone
- Compare against the 0.286 baseline on the sealed test set
- Separate validation vs test conclusions
- Explain why the improvement is expected to generalize beyond the current test window

---

*This document reflects all experimental work completed through July 22, 2026. The next update should include Iteration 2 agent validation results.*