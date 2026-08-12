# MERG Module — Task Definition Prompt

**Context:** We are building a new module called **MERG** (Macro Event Response Gate) within the Frival trading system. The module trains a specialized classifier on pre-event candlestick microstructure to predict short-horizon price reactions after high-impact economic releases, then deploys the model as a conditional gate in the live signal pipeline.

**Reference notebook:** `ml-signal-service/notebooks/eurusd/eurusd_buy_improved.ipynb` — we want MERG to follow the **identical training strategy** (noise-injection feature selection, purged nested CV, recency weighting, soft-vote calibrated ensemble, threshold tuning on validation only, sealed test).

**Dataset:** `ml-signal-service/data/raw/macro/ExportedData.xlsx` — 4,793 rows × 51 columns. 183 event types, 19.5 years (2007-02-13 → 2026-07-31). Features are 45 integer columns of pre-event M1 candlestick anatomy: `tWick_i`, `body_i`, `bWick_i` for windows `i ∈ {15, 14, ..., 1}`. Targets: `targetSimple` (3-class: U/D/N, naturally imbalanced at 61.6% N / 19.7% U / 18.7% D). Zero missing values.

---

## Task Request

Define the implementation tasks to build the MERG training pipeline. The pipeline must produce two serialized models (`MERG_v1_reaction.joblib`, `MERG_v1_direction.joblib`) ready for runtime inference via a companion `macro_event_responder.py` module.

The core architecture is a **two-stage binary classifier** (not a single 3-class model):

- **Stage 1 — Reaction Detector:** binary classifier `y_reaction = 1 if targetSimple != "N" else 0`. Answers: "will this event produce any directional move?"
- **Stage 2 — Direction Classifier:** binary classifier `y_direction = 1 if targetSimple == "U" else 0`, trained only on rows where `y_reaction == 1` (n=1,841). Answers: "if it moves, which way?"

Runtime composition: `p_U = p_reaction × p_up`, `p_D = p_reaction × (1 − p_up)`, `p_N = 1 − p_reaction`. Predicted class = `argmax(U, D, N)`. Model only fires when confidence exceeds a configurable threshold and a HIGH-impact event is scheduled within 60 min.

---

## Requirements

### R1 — Data leakage prevention

The notebook uses these leakage-prevention measures. MERG must replicate them:

1. **Chronological split only — no random shuffling.** Time-based holdout (train → val → test in forward chronological order) to prevent forward-looking information from leaking across periods.
2. **Feature engineering restricted to train set.** Any derived features (e.g., `body_ratio`, `wick_asym`, cumulative momentum sums) must be computed on the full dataset but their distribution statistics (means, quantiles for any normalization) must be fitted on train only.
3. **Feature selection restricted to train set.** If noise-injection voting is used, noise probes must be injected into train only. Validation and test sets must never influence which features are selected.
4. **Threshold calibration on validation only.** The optimal probability threshold must be fitted on validation data — test data is sealed until the final evaluation.
5. **Test set is sealed.** It is loaded exactly once at the end for the final ROC-AUC / PR-AUC / precision report. Never used for model selection, feature selection, or threshold tuning.
6. **Purged CV if nested folds are used.** If cross-validation is used for hyperparameter tuning, folds must respect chronology with a purge gap (e.g., 30-day embargo between train and validation folds within CV) to prevent label overlap from forward-looking windows.

### R2 — Alternative datetime split strategies

The integration plan specifies: Train = pre-2023, Val = 2023, Test = 2024-01-01 → 2026-07-31. However, the plan notes that alternative split strategies should be considered and documented. Please include a section in the task definition that presents **at least two alternative split strategies** with rationale:

| Strategy | Train | Val | Test | Rationale |
|---|---|---|---|---|
| **A) Default (plan)** | pre-2023 | 2023 | 2024–2026-07 | Matches plan. Broad train window covers 2008 GFC, 2014 QE, 2020 COVID. Test covers recent regime (post-Fed hiking). |
| **B) Equal-period** | pre-2020 | 2020–2022 | 2023–2026-07 | Balances train (~13 years) / val (~3) / test (~3.5). Includes COVID in val instead of train — tests regime-robustness harder. |
| **C) Recency-biased** | pre-2019 | 2019–2021 | 2022–2026-07 | Sacrifices pre-2010 data (different market microstructure) in favor of more recent validation and a larger test window. Use if early data shows structural break. |

The tasks should support selecting a strategy via a config parameter (`SPLIT_STRATEGY = "A" | "B" | "C"`), defaulting to Strategy A.

### R3 — Feature engineering alignment with notebook

The notebook uses noise-injection voting for feature selection. MERG should follow the same pattern:

1. Compute the 45 base features + derived features (body_ratio, wick_asym, cumulative momentum sums, body_sign consistency — ~60 total). Document the derived feature list explicitly.
2. Inject 9 synthetic noise columns (Gaussian, Uniform, Poisson, random walk, sinusoidal — same as the notebook) seeded with `np.random.seed(42)`.
3. Train 3 ranking models on train set only: RandomForest (300 trees), LightGBM (500), scaled LogisticRegression.
4. Vote: keep features with support from ≥ `MIN_STRATEGY_SUPPORT` strategies (configurable, default 2), stripping noise.
5. Output: final feature list as a `.txt` or `.json` artifact saved alongside the model bundles.

### R4 — Model architecture alignment with notebook

MERG should replicate the notebook's ensemble approach:

1. Nested CV with purged expanding TimeSeriesSplit (outer folds = 4–5, inner folds = 4–5, purge days = 30).
2. 4 candidates compared by PR-AUC: LogisticRegression (baseline), RandomForest, XGBoost (scale_pos_weight), LightGBM (class_weight="balanced").
3. Recency sample weights: `w = exp(−0.15 × years_ago)`, normalized to sum to n.
4. Winner selection: best mean outer-fold PR-AUC.
5. Final model: soft-vote VotingClassifier of all 4 models, each wrapped in CalibratedClassifierCV (isotonic, cv=3).
6. Threshold calibration: scan PR-curve thresholds with minimum-signal floor, pick threshold that maximizes `(precision − breakeven) × log(n_signals)`. For Stage 1, breakeven is not applicable (binary reaction detector) — instead maximize F1 or use a fixed 0.50 threshold.
7. Serialize both stage models as separate `.joblib` bundles containing: `{model, features, threshold, metadata}`.

### R5 — Evaluation and reporting

Produce a structured evaluation report (`merg_v1_report.md`) containing:

- ROC-AUC and PR-AUC for both stages on test set
- Calibration curves (reliability diagrams)
- Confusion matrices per event family (top 20 events)
- Feature importance (top 10, with stability across CV folds)
- Per-event-family precision: no single event type accounts for > 30% of Stage-2 accuracy
- Comparison of performance across the 2-3 split strategies (which strategy generalizes best?)

---

## Deliverable

A prioritized, sequenced list of implementation tasks. Each task should include:

1. **Task name** (short, action-oriented)
2. **Input artifacts** required
3. **Output artifacts** produced
4. **Acceptance criteria** (how to verify the task is done correctly)
5. **Estimated effort** (hours)
6. **Dependencies** (which tasks must be completed first)

The task list should cover the full pipeline from data ingestion to serialized model bundles ready for runtime deployment. Group tasks by phase (Setup, Build Dataset, Train Stage 1, Train Stage 2, Evaluate, Deploy).

---

## Constraints

- Python environment: `deaf_agent` conda env (scikit-learn 1.5.2, lightgbm, xgboost, joblib 1.3.2)
- Add `openpyxl>=3.1` to requirements — only new dependency
- All outputs go under `ml-signal-service/steps/06_merg/`
- Model bundles go under `ml-signal-service/models_bin/`
- Report goes under `ml-signal-service/docs/experiments/`
- Training data artifact goes under `ml-signal-service/data/features/merg_v1.parquet`
- No new API keys, no new services, no new infrastructure — this is a pure Python training pipeline