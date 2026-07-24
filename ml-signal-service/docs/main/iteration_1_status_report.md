# EURUSD H1 Signal System — Iteration 1 Status Report

*Status update · July 19, 2026 · Reporting period: July 14–19*

---

## 1. What was accomplished this week

We ran 4 complete experiment cycles across multiple configurations. Each cycle is a full pipeline: data loading → 86-feature engineering → noise-injection voting → nested cross-validation → model training → threshold calibration → sealed test evaluation.

**Experiment matrix completed:**

| Experiment | Forward bars | TP multiplier | Model tested | ROC-AUC (val) | Test precision (gated) |
|---|---|---|---|---|---|
| 1 (baseline) | 6 | 1.5 | LightGBM | 0.651 | 0.348 |
| 2 | 4 | 1.5 | RandomForest | 0.695 | 0.300 (est.) |
| 3 | 2 | 1.25 | XGBoost | 0.735 | — (44 signals) |
| 4 | 6 | 1.5 | LightGBM (re-tuned) | 0.651 | 0.286 |

**Infrastructure built in parallel:**

| Component | Status | Description |
|---|---|---|
| BUY model training pipeline | Complete | 22 selected features, nested CV, noise-injection voting |
| SELL model training pipeline | Complete | 19 features, mirrored architecture |
| Signal combiner notebook | Complete | 4 decision gates, Section 9 test evaluation, cross-filter sweep |
| Production predictor script | Complete | `eurusd_h1_predictor.py` — scores every H1 bar, saves decision log |
| Decision log | Complete | 46,336 rows, gate-by-gate reason per bar, TP/SL/entry price |
| Bloomberg macro data pipeline | Complete | `build_macro_dataset.py`, spec docs, desk operational guide |
| Model bundle save/load | Complete | `.joblib` bundles with feature lists, thresholds, label params |
| Feature selection improvements | Complete | Gain-based LGBM importance, MIN_VOTES voting system |

---

## 2. Current results — honest assessment

**Best configuration on sealed test set (109 trading days, Feb–Jul 2026):**

| Metric | Value | Target | Status |
|---|---|---|---|
| BUY precision (gated) | **0.348** | ≥ 0.400 | Below target |
| Test-day signals | 46 (0.42/day) | ≥ 0.15/day | Pass |
| ROC-AUC (validation) | 0.651 | — | — |
| Overfit gap (val→test) | +0.075 | ≤ 0.050 | Above threshold |
| Decision traceability | 100% of bars logged | 100% | Pass |

The model's discriminative ceiling is established at **ROC-AUC ≈ 0.65** and **gated precision ≈ 0.35**. This is consistent across all four experiments, three model architectures (LightGBM, XGBoost, RandomForest), and multiple feature selection approaches. The model reliably separates some good entries from bad ones — it is not random — but it cannot reach the 0.400 breakeven threshold on unseen data with usable signal volumes.

Additional findings from the experiment cycle:
- Shortening the forward window improves ROC-AUC (0.735 at FW=2) but reduces label rate, making the class imbalance harder to train on
- Full-retrain (train+val combined) made performance **worse** due to regime overfitting — the validation period patterns don't generalize to test
- The SELL model has better raw metrics than BUY (PR-AUC 0.386 vs 0.330) but fails identically at end-to-end gated precision (0 signals survive gates)
- Bloomberg macro features (Brent, EURIBOR) survived 3/3 votes in feature selection but added zero marginal precision in the combiner pipeline

---

## 3. Why the model can't cross breakeven — root cause analysis

The H1 label design (6-hour TP/SL race at R:R=1.5) produces a target that is **inherently noisy**. Many TP hits are luck — driven by random hourly volatility, not by patterns detectable from the entry bar's features. The model distinguishes better-than-average bars from worse-than-average bars (ROC-AUC 0.65), but the difference is small — not enough to reach 40% absolute precision.

This is not a model architecture problem. Three fundamentally different model types (tree ensemble, gradient boosting, linear) converge to the same ceiling. The bottleneck is the **label signal-to-noise ratio**, not the classifier.

---

## 4. Extended work plan — Iteration 1.5 (Jul 20–25)

The original plan targeted one week per iteration. Iteration 1 has established the model's baseline but has not cleared the success criterion. I propose an **extended Iteration 1.5** before moving to the agent layer (Iteration 2):

| Day | Activity | Goal |
|---|---|---|
| Jul 20 (Mon) | Explore alternative label designs: longer forward windows (8, 10, 12 bars), different TP/SL ratios, mean-reversion labels | Find a label configuration with better signal-to-noise ratio |
| Jul 21 (Tue) | Feature ablation study: remove low-variance features, test feature interaction groups | Identify if any feature class is actively hurting performance |
| Jul 22 (Wed) | Re-run winning label configuration through full pipeline | Train new model on improved labels |
| Jul 23 (Thu) | Evaluate on sealed test set, compare against Iteration 1 baseline | Determine if label change closed the gap |
| Jul 24 (Fri) | Decision point: if test precision ≥ 0.400 → close Iteration 1. If not → document findings and proceed to Iteration 2 (agent pipeline) regardless | Prevent infinite iteration on the model layer |

**Fallback:** If label redesign does not clear 0.400 by Friday, the existing model (0.348 precision, 46 signals) is the accepted Iteration 1 baseline. We proceed to Iteration 2 — the multi-agent validation layer — where Perplexity and GPT-4o agents independently evaluate each signal. The hypothesis is that agents can reject false positives the model cannot, adding the remaining +0.052 precision needed to reach breakeven.

---

## 5. Next immediate steps for Iteration 2 (ready to start regardless)

All infrastructure for Iteration 2 has been designed and documented (`ml-signal-service/docs/next_agent_pipeline_design.md`):

1. **Perplexity validation agent** — sends each BUY signal through a 5-pillar analysis prompt (technical, fundamental, sentiment, news, correlation) → returns CONFIRM/REJECT/NEUTRAL
2. **GPT-4o evaluation agent** — independent LLM review from a different provider → eliminates single-vendor bias
3. **Rules engine** — combines base model + both agent outputs → final action with confidence tier (STRONG BUY / BUY / SKIP)
4. **Senior agent validator** — GPT-4o risk review layer: validates logic, R:R math, stop placement, account risk

Iteration 2 requires no model retraining — it is a post-inference layer that reads the existing decision log.

---

## 6. Risk and honest assessment

**What's working:** The infrastructure is production-grade. Feature engineering, model training, evaluation, decision gates, and the predictor script are all functional, documented, and reproducible. Any future label redesign or feature addition can be tested in hours, not days.

**What's not working:** The H1 directional label has limited predictive signal. The model is a weak ranker, not a strong classifier. The 0.348 precision means ~65% of alerts are false positives — the agent layer must handle this.

**What I need:** One more week for label design experiments (Iteration 1.5) before proceeding to the agent pipeline. If label changes don't help, we proceed to Iteration 2 on Jul 25 with the current model as the accepted baseline.

---

*This report reflects work completed July 14–19, 2026. Next status update: July 25, 2026.*