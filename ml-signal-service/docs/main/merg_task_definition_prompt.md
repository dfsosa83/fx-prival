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

---

## Next Steps and Exploration Plan

### 1. Overall Target

**Goal:** Build a MERG model that predicts the post-event directional move **before** it happens — using only information available *at the moment of the release* — and validate that the signal survives without peeking at post-event data.

The current `MERG_v1` (ROC-AUC 0.97/0.98) is inflated: it consumes **all 15 windows** of candlestick anatomy, which include the 10 post-event bars (windows 9 → 1). A model that sees the first several minutes of the post-release move is not *predicting* the move — it is *observing* it. The exploration plan below defines how to build an honest, leak-free model and how to measure the true predictive power that remains.

The **target model** (call it `MERG_v2`):

- Uses **only pre-event + event-bar windows** (windows 15 → 10), i.e. the last 5 pre-release minutes plus the release bar itself.
- Is evaluated against the **sealed 2026 test set** exactly once, after all feature/model decisions are frozen.
- Produces a defensible ROC-AUC / PR-AUC number that we can trust when deciding whether to promote MERG beyond shadow mode.

### 2. Understanding "Incompleto" Models

The dataset's 15 windows are not a single homogeneous series. They are anchored to the event release and split into three segments:

```
Window:  15  14  13  12  11  |  10  |  9  8  7  6  5  4  3  2  1
Meaning: ──── pre-event ────  | event | ──── post-event ─────────
          5 minutes before    | bar   | 10 minutes after release
```

The **event bar (window 10)** is the M1 bar during which the economic release actually prints. Everything before it (windows 15 → 11) is information available *before* the news. Everything after it (windows 9 → 1) is information only available *after* the market has begun reacting.

#### 2.1 What "Incompleto" means

An **"Incompleto" model** is a model variant trained with a *prefix* of the 15-window sequence — it deliberately withholds the later (post-event) windows. The name comes from the dataset owner's own terminology: the model only has an *incomplete* view of the full 15-window candle sequence at training/prediction time.

The key insight is that **"incomplete" refers to time, not to quality.** An Incompleto model is *less informed*, not *worse*: it is trained to make the prediction at a point in time when the future windows genuinely have not happened yet. This is what makes it deployable in production — you can actually run it at T−5 min or T+0 min, because those are real moments that exist before the outcome is known.

#### 2.2 The Incompleto variants

The dataset owner defined progressive variants by how many windows each model is allowed to see:

| Variant | Windows used | What it knows | Production feasibility |
|---|---|---|---|
| `incompleto5` | 15 → 11 | Only the 5 pre-event bars. **True blind prediction.** No reaction data at all. | Run at T−5 min to T−1 min, *before* the release |
| `incompleto6` | 15 → 10 | 5 pre-event bars + the event bar itself. Sees the first volatile reaction. | Run at T+1 min, right after the release bar closes |
| `incompleto7` | 15 → 9 | + the 1st post-event bar. Sees initial follow-through. | Run at T+2 min |
| `incompleto10` | 15 → 6 | + 5 post-event bars. The move is mostly realized by now. | Run at T+6 min |
| `incompleto15` | 15 → 1 | All 15 bars. Sees the full post-event sequence. | Not a prediction — retrospective classification |

#### 2.3 Why they are "incomplete" and how they differ from "complete" models

- **Incomplete models** see a **prefix** of the 15-window sequence. Their input ends at the window corresponding to the moment the prediction is being made. They answer: *"given what I can see right now, where is price going next?"*

- **Complete models** (`incompleto15`, and by extension our current `MERG_v1`) see the **entire** 15-window sequence, including post-event bars. They answer: *"given everything that already happened, what was the net outcome?"* This is a classification/labeling task, not a forward prediction.

The critical distinction is **information availability at decision time**:

- An `incompleto5` prediction can be acted upon **before** the release — it generates alpha.
- An `incompleto15` prediction is only available **after** the move has already occurred — it cannot be traded.

Our current `MERG_v1` sits at the wrong end of this spectrum. It reports 0.97 ROC-AUC because it is essentially an `incompleto15` model: it looks at the post-event bars and "predicts" the direction they already show. To be deployable as a gate, MERG must be re-framed as an **`incompleto5` or `incompleto6`** model.

#### 2.4 The expected performance curve

As the model sees more windows, accuracy should monotonically improve — but the *value* of each prediction decreases:

```
                 predictability ▲
                                │              ● incompleto15 (0.97)
                                │          ● incompleto10
                                │      ● incompleto7
                                │   ● incompleto6
                                │● incompleto5  ← true forward prediction
                                └───────────────────────────► tradability
                    (not tradable)                      (tradable)
```

The exploration plan below is designed to measure this curve — specifically, to find out what ROC-AUC survives at the tradable end (`incompleto5` / `incompleto6`). If the tradable variants fall below the gate thresholds (Stage 1 ≥ 0.58, Stage 2 ≥ 0.55), then MERG has no live value and should stay in shadow/disabled mode.

### 3. Specific Tasks and Step-by-Step Actions

#### Task 1 — Rebuild the dataset with window masks

**Objective:** Refactor `build_dataset` so that each model variant can select a window prefix without touching the raw data.

**Steps:**
1. Add a `window_prefix` parameter to the feature-selection logic (values: `5`, `6`, `7`, `10`, `15`).
2. Implement a column selector that keeps only `{tWick_i, body_i, bWick_i}` for windows `i ∈ {15, ..., 16 − prefix}`.
3. Verify the mapping is correct by asserting:
   - `prefix=5` → 15 columns (5 windows × 3 components)
   - `prefix=6` → 18 columns
   - `prefix=15` → 45 columns
4. Write unit-level sanity checks: the `prefix=15` output must exactly match the current `MERG_v1` input.

**Acceptance:** Each prefix produces the exact expected column set; a quick spot-check of window 10 vs window 9 confirms the event bar is correctly included/excluded.

#### Task 2 — Train the "Incompleto ladder"

**Objective:** Produce one trained model per prefix (`5`, `6`, `7`, `10`, `15`) using the *identical* two-stage pipeline, so the only variable is the number of windows.

**Steps:**
1. For each prefix, run Stage 1 (reaction detector) and Stage 2 (direction classifier).
2. Keep every hyperparameter identical to `MERG_v1` (nested purged CV, recency weights, soft-vote ensemble, isotonic calibration, threshold on validation).
3. Record, for each prefix: ROC-AUC, PR-AUC, Brier, precision, and signal count on the **sealed 2026 test set**.
4. Serialize each prefix's bundles as `MERG_v2_inc5_*.joblib`, `MERG_v2_inc6_*.joblib`, etc.

**Acceptance:** A table plotting prefix (5→15) against test ROC-AUC. The curve should be monotonic (more windows → higher ROC). The `incompleto15` row should reproduce `MERG_v1` numbers.

#### Task 3 — Answer the leakage question (P0)

**Objective:** Determine whether the tradable variants (`5`, `6`) retain enough signal to be useful.

**Steps:**
1. Read the `incompleto5` and `incompleto6` ROC-AUC from Task 2.
2. Compare against the gate thresholds (Stage 1 ≥ 0.58, Stage 2 ≥ 0.55).
3. If `incompleto5` clears both thresholds → MERG is genuinely predictive *before* the event. Proceed to Task 4.
4. If only `incompleto6` clears → MERG is usable as a *post-release-bar* filter (still valid, but the entry is at T+1 min, not before).
5. If neither clears → MERG has no forward signal; the 0.97 was leakage. Disable the gate and document the finding.

**Acceptance:** A written verdict — "MERG predicts before the event (inc5)", "MERG predicts at the release bar (inc6)", or "MERG does not predict (both below threshold)" — with the numbers that support it.

#### Task 4 — Test event granularity

**Objective:** Determine whether the event name carries predictive signal beyond the candlestick anatomy.

**Steps:**
1. Train three variants on the best tradable prefix (from Task 3):
   - **Variant A:** no event feature (current baseline).
   - **Variant B:** target-encoded `event` (mean `targetSimple` per event, out-of-fold to prevent leakage).
   - **Variant C:** one-hot for top-20 events + `OTHER` bucket.
2. Evaluate all three on the sealed 2026 test set.
3. Report the delta. If B or C beats A by a meaningful margin (≥ +0.02 ROC-AUC), event granularity carries signal.

**Acceptance:** A comparison table with the three variants' ROC-AUC, plus a recommendation on whether to adopt event-aware features.

#### Task 5 — Rebuild the report and update the integration plan

**Objective:** Fold the exploration findings back into the official documentation.

**Steps:**
1. Update `merg_v1_report.md` (or create `merg_v2_report.md`) with the "Incompleto ladder" table and the leakage verdict.
2. Update `macro_event_responder.py` to load the correct tradable-prefix bundles and to expose which prefix is active.
3. Update `project_last_state.md` with the corrected MERG status.
4. Re-run the live smoke test with `MERG_ENABLED=false` to confirm no regression.

**Acceptance:** Docs are consistent; runtime module loads the correct model; the live pipeline runs unchanged with MERG disabled.

### 4. Tests to Run

| # | Test | Question it answers | Pass condition |
|---|---|---|---|
| T1 | Window-mask assertion | Is the prefix selection mapping correct? | Each prefix yields the exact expected column count |
| T2 | Incompleto ladder | Does ROC-AUC degrade smoothly as windows are removed? | Monotonic curve; inc15 reproduces v1 |
| T3 | Leakage verdict | Does MERG predict *forward* at all? | inc5 or inc6 clears gate thresholds |
| T4 | Event granularity A/B/C | Does event identity add signal? | B or C ≥ +0.02 ROC-AUC over A |
| T5 | Sealed-test discipline | Was the 2026 test set touched only once? | No model decision used test data |
| T6 | Live smoke test | Does the gate still run with MERG disabled? | `run_live` completes identically to pre-MERG |

### 5. Decision Matrix After Exploration

| Outcome | Action |
|---|---|
| inc5 clears thresholds, event-aware improves | Adopt `incompleto5` + event feature. Promote MERG to shadow, then hard gate. |
| inc6 clears, inc5 does not | Adopt `incompleto6`. Document T+1 entry timing. Keep in shadow until validated. |
| Only inc10/inc15 clear | MERG is retrospective — no live value. Disable gate permanently. |
| Event feature adds signal but inc5/6 do not | Event granularity is real but microstructure timing is not — do not deploy MERG. |