# EURUSD H1 Signal System — Performance Improvement Recommendations

Last updated: 2026-07-22
Scope: actionable improvements for the BUY/SELL/combiner pipeline based on the final experiment state
(`project_last_state.md`, `outputs_buy.txt`, `outputs_sell.txt`, `outputs_combiner.txt`, and the three notebooks).

---

## 1. Current Performance Summary

| Component | Metric | Value | Read |
|---|---|---|---|
| BUY model (RandomForest) | Nested CV PR-AUC | 0.393 (baseline 0.368) | **Barely above chance** |
| BUY model | Val ROC-AUC | **0.495** | **Effectively random** |
| BUY model | Val precision @ thr 0.644 | 0.429 @ recall **0.005** (7 signals) | Threshold picked from noise |
| SELL model (LogReg) | Nested CV PR-AUC | 0.346 (baseline 0.246) | **Meaningfully above chance** |
| SELL model | Val ROC-AUC | **0.613** | Real (weak) signal |
| SELL model | Val precision @ thr 0.599 | 0.400 @ recall 0.225 (385 signals) | **Hits breakeven at volume** |
| Combiner BUY final (test) | Precision / signals | 0.286 / 28 (0.42/day) | Below 0.400 breakeven |
| Combiner SELL final | — | 0 (lane disabled) | Abandoned |
| Cross-filter | Conflicts suppressed | **0** on val AND test | Inert gate |

### Identified improvement opportunities (highest leverage first)

1. **The BUY threshold is calibrated on statistical noise** — 7 validation signals (recall 0.005) cannot generalize; this alone explains the unstable val→test behavior.
2. **The stronger model (SELL) was abandoned before a clean sealed-test evaluation** — it is the only lane that reaches breakeven precision at real volume.
3. **The test set is too small** (28 signals) to distinguish 0.286 from 0.400 — the 95% CI is roughly [0.13, 0.48]. Conclusions rest on noise.
4. **The label ceiling is real but unexplored at its best point** — the FW=2 / lower-TP region hit ROC-AUC 0.735 and was never carried through to a combiner test.
5. **The Bloomberg macro pipeline is built but never used as features** — the largest untapped source of genuinely new signal.
6. **The cross-filter is dead code** — it suppresses nothing and adds complexity/confusion.

---

## 2. Detailed Recommendations

### R1 — Fix threshold calibration with a minimum-support floor
- **Change:** In the "Threshold Calibration" cell of both `eurusd_buy.ipynb` and `eurusd_sell.ipynb`, stop selecting "highest recall with precision ≥ breakeven." On a near-random model this picks a handful of lucky bars. Add a hard floor of **≥ 50 validation signals (≈ 0.5/day)** before a threshold is eligible, and among eligible thresholds pick the one maximizing `precision × log(signals)` (or simply the highest precision with ≥50 signals).
- **Expected impact:** Threshold that survives to the test set instead of collapsing. Turns the current 7-signal BUY threshold into a stable, tradeable operating point; removes the largest source of val→test variance.
- **Pros:** Trivial code change; directly attacks the reproducibility problem flagged in the state doc. **Cons:** Reported validation precision will drop toward the true ceiling (~0.33) — honest, but less flattering.
- **Notebook edits:** `eurusd_buy.ipynb` + `eurusd_sell.ipynb`, threshold-calibration cell only (`viable_df` filter + selection line).
- **Features / dates / config:** No feature or date change. New constant `MIN_VAL_SIGNALS = 50`.
- **Priority: HIGH · Difficulty: LOW**

### R2 — Properly evaluate the SELL lane on the sealed test set before abandoning it
- **Change:** In `signal_combiner.ipynb`, run a dedicated pass with `BUY_ONLY = False`, SELL lane active, and the cross-filter **off** for SELL (or set only to suppress on strong BUY). The SELL model reaches 0.400 precision with 385 validation signals — it must get a clean standalone sealed-test number before being discarded. The current "non-viable" verdict came from a run where `BUY_ONLY=True` zeroed the lane, not from a fair SELL test.
- **Expected impact:** Potentially recovers an entire trading direction. Even at ~0.38–0.40 test precision with 3+/day, SELL alone would exceed the current BUY-only output in both precision and volume.
- **Pros:** Uses the strongest model already trained; config-only. **Cons:** Val→test drift may still pull SELL below breakeven; needs the R7 CI check to trust the result.
- **Notebook edits:** `signal_combiner.ipynb` config cell (`BUY_ONLY`, `CROSS_FILTER`, SELL cooldown) + evaluation cell to report SELL standalone test precision.
- **Features / dates / config:** `BUY_ONLY = False`; evaluate SELL at its own threshold 0.599; keep splits unchanged.
- **Priority: HIGH · Difficulty: LOW**

### R3 — Carry the FW=2 / lower-TP label configuration through to the combiner
- **Change:** The state doc records FW=2, TP≈1.0–1.25 producing ROC-AUC up to 0.735 (the best of any config) but it was never evaluated end-to-end in the combiner because label rate fell to ~16%. Re-run the full pipeline at **FORWARD_BARS = 2** with a **joint TP×SL sweep targeting both label-rate ≥ 22% AND breakeven-reachable precision** — e.g. TP=1.0/SL=1.0 (breakeven 0.50, needs strong ranker) vs TP=1.25/SL=1.0 (breakeven 0.44). Pick the pair where the model's achievable precision clears breakeven with ≥1 signal/day.
- **Expected impact:** This is the only lever that changed the *model's discriminative power* (ROC-AUC 0.50→0.735). If even part of that lift survives labeling, it breaks the 0.286 ceiling.
- **Pros:** Attacks the true bottleneck (the label, not the classifier). **Cons:** Lower R:R shrinks per-trade profit; short horizon may be noisier live; requires full retrain of both lanes.
- **Notebook edits:** `eurusd_buy.ipynb` + `eurusd_sell.ipynb` config cell (`FORWARD_BARS`, `ATR_TP_MULT`, `ATR_SL_MULT`) and re-run Sections 5–10; then re-run `signal_combiner.ipynb`.
- **Features / dates / config:** `FORWARD_BARS = 2`; sweep `ATR_TP_MULT ∈ {1.0, 1.25}`, `ATR_SL_MULT = 1.0`; splits unchanged.
- **Priority: HIGH · Difficulty: MEDIUM**

### R4 — Wire the Bloomberg macro / rate-differential features into the model
- **Change:** The macro pipeline (`build_macro_dataset.py`) exists but its output never enters `compute_features`. Add, as of the prior daily close (no leakage): EUR–US 2Y and 10Y **rate differentials**, DXY level/return, and a EURUSD–DXY rolling correlation. Merge them the same way D1 context is merged (shift(1), join on date).
- **Expected impact:** The current 11-feature set is purely price-derived and yields ROC-AUC ≈ 0.50 for BUY. Rate differentials are the dominant EURUSD driver in the 2020–2025 tightening regime — the most credible route to genuinely new signal rather than reshuffling price noise.
- **Pros:** Adds an orthogonal information source; pipeline already built. **Cons:** Introduces a data dependency and alignment/timezone risk; macro data cadence (daily) is coarse for H1.
- **Notebook edits:** `compute_features` cell in both `eurusd_buy.ipynb` and `eurusd_sell.ipynb` (new merge block after the D1 block); re-run feature selection.
- **Features / dates / config:** New features `rate_diff_2y`, `rate_diff_10y`, `dxy_ret`, `eurusd_dxy_corr20`; keep splits.
- **Priority: HIGH · Difficulty: MEDIUM**

### R5 — Replace precision-only evaluation with an expected-value (net-pips) backtest
- **Change:** Add a cell to `signal_combiner.ipynb` that converts each signal to realized R (net of a fixed spread, e.g. 0.8 pip) and reports **expected value per signal** and **cumulative net pips**, not just precision. A 0.28-precision / R:R=1.5 stream can be borderline; the current metric hides whether it is actually EV-negative.
- **Expected impact:** Correct optimization target. A lower-precision/higher-R:R config may be net positive and would be wrongly rejected by precision alone.
- **Pros:** Aligns the metric with the business goal; small addition. **Cons:** Requires a spread/slippage assumption; still a simplification of live fills.
- **Notebook edits:** `signal_combiner.ipynb` — new evaluation cell computing `EV = P·TP_R − (1−P)·SL_R − spread`.
- **Features / dates / config:** New constant `SPREAD_PIPS = 0.8`; no date change.
- **Priority: HIGH · Difficulty: LOW**

### R6 — Calibrate probabilities before thresholding
- **Change:** Wrap the final model in `CalibratedClassifierCV` (isotonic, fit on a validation slice) so probabilities are monotonic and comparable across runs. `class_weight="balanced"` currently distorts the probability scale, which is part of why the threshold is unstable.
- **Expected impact:** More reliable, reproducible thresholds and a cleaner cross-filter/EV computation; reduces the run-to-run threshold jitter noted in the state doc.
- **Pros:** Standard fix; improves every downstream gate. **Cons:** Consumes some validation data for calibration; modest added complexity.
- **Notebook edits:** Model-fit cell in `eurusd_buy.ipynb` + `eurusd_sell.ipynb` (calibration wrapper) and the saved bundle.
- **Features / dates / config:** No feature/date change; optionally carve a small calibration slice from the end of train.
- **Priority: MEDIUM · Difficulty: LOW**

### R7 — Report precision with confidence intervals via purged walk-forward evaluation
- **Change:** A single 67-day / 28-signal test window cannot separate 0.286 from 0.400. Add **purged, embargoed walk-forward** evaluation (multiple rolling test folds) and report precision with a Wilson 95% CI and total signal count across folds.
- **Expected impact:** No performance gain by itself, but it is the guardrail that prevents accepting/rejecting configs (R2, R3, R4) on noise — the core failure mode in the experiment log.
- **Pros:** Makes every other recommendation trustworthy. **Cons:** More compute; more code in the combiner.
- **Notebook edits:** `signal_combiner.ipynb` — new walk-forward evaluation section.
- **Features / dates / config:** Rolling test folds across 2025-11 → present; keep TRAIN_START=2020-06-30.
- **Priority: MEDIUM · Difficulty: MEDIUM**

### R8 — Soft-vote ensemble of the four base models
- **Change:** All four models sit within 0.01 PR-AUC. Average their (calibrated) probabilities instead of picking one winner in `MANUAL_MODEL`. Save the ensemble as the bundle.
- **Expected impact:** Lower variance, more stable threshold and test precision; typically +0.005–0.02 PR-AUC for near-tied learners.
- **Pros:** Cheap; reduces the "which model won this run" instability. **Cons:** Slower inference; harder to interpret; gain may be marginal if models are correlated.
- **Notebook edits:** Model-selection/fit cells in both training notebooks.
- **Priority: MEDIUM · Difficulty: LOW**

### R9 — Loosen feature selection (more candidate features survive)
- **Change:** The model is *under*-fit (ROC-AUC ≈ 0.50), not over-fit, yet only 11 features survive. Lower `VOTING_PERCENTILE` from 60 back to 40 and/or `MIN_STRATEGY_SUPPORT` handling so ~22 features pass, matching the earlier runs that reported 0.348–0.415 combiner precision.
- **Expected impact:** Restores the richer feature set associated with the best historical combiner numbers; gives the model more to work with.
- **Pros:** One-line change; reversible. **Cons:** Risk of reintroducing noise features; must be validated with R7, not a single test window.
- **Notebook edits:** Feature-selection cells in `eurusd_buy.ipynb` + `eurusd_sell.ipynb`.
- **Features / dates / config:** `VOTING_PERCENTILE = 40`; splits unchanged.
- **Priority: MEDIUM · Difficulty: LOW**

### R10 — Remove or repurpose the inert cross-filter
- **Change:** The cross-filter suppresses 0 conflicts on both val and test because BUY probabilities rarely exceed 0.60. Either delete it, or repurpose it as a **same-direction confidence booster** (require the opposing model's probability to be low, e.g. `sell_proba < 0.30`, as a quality gate rather than a conflict gate).
- **Expected impact:** Removes misleading dead logic; the repurposed version could add a small precision lift by filtering ambiguous bars.
- **Pros:** Simplifies the pipeline; clearer decision log. **Cons:** If repurposed, needs its own threshold sweep to avoid over-filtering.
- **Notebook edits:** `signal_combiner.ipynb` gate logic + config comment.
- **Priority: LOW · Difficulty: LOW**

### R11 — Fix the cooldown dtype FutureWarning in the combiner
- **Change:** Cast `buy_signal` to `int` before `df.at[i, "buy_signal"] = 0` (already fixed in the predictor script, still present in the notebook).
- **Expected impact:** Removes the warning; prevents a future pandas hard error.
- **Pros:** One line. **Cons:** None.
- **Notebook edits:** `signal_combiner.ipynb` `apply_cooldown` cell.
- **Priority: LOW · Difficulty: LOW**

---

## 3. Action Plan (prioritized)

**Phase 1 — Make the numbers trustworthy (do first, ~1 sitting):**
1. **R1** — add the minimum-support threshold floor (fixes the 7-signal artifact).
2. **R7** — add purged walk-forward + Wilson CI so every later change is judged fairly.
3. **R5** — add the net-pips / EV backtest as the real success metric.
4. **R11** + **R10** — clear the dead cross-filter and the cooldown warning.

**Phase 2 — Recover cheap upside (config-only, no retrain):**
5. **R2** — give the SELL lane a clean sealed-test evaluation; adopt it if it clears EV with a tight CI.
6. **R8** + **R6** — ensemble + calibrate to stabilize whichever lane(s) survive.

**Phase 3 — Attack the ceiling (retraining required):**
7. **R3** — re-run FW=2 with the joint TP×SL sweep; carry the best point through the combiner under R7/R5.
8. **R4** — wire in Bloomberg rate-differential / DXY features and re-select features.
9. **R9** — loosen feature selection and re-validate.

**Decision rule:** promote a change only if it improves **net-pips EV (R5)** with a non-overlapping **Wilson CI (R7)** versus the 0.286 / 28-signal BUY-only baseline. Report precision **and** signals/day every time, and keep validation vs test conclusions separate.

**Do not change:** `TRAIN_START = 2020-06-30` (shorter windows collapsed ROC-AUC below 0.55 in experiments 6/8/9), and keep the ATR-barrier race label design (directional labels were proven random-walk in experiment 8).

---

## 4. Results — Executed Outcomes & Next Steps

The recommendations above were implemented in three improved notebooks
(`eurusd_buy_improved.ipynb`, `eurusd_sell_improved.ipynb`, `signal_combiner_improved.ipynb`)
and run end-to-end. R1, R2, R5, R6, R7, R8, R9, R10 and R11 are all live; R4 (macro) is wired but
guarded/optional. This section records what the run actually produced.

### 4.1 What the improvements revealed

| Lane | Key metrics (post-improvement) | Verdict |
|---|---|---|
| **BUY** | Val ROC-AUC **0.495** (random). Test EV **−0.43R** (≈ −5.5 pips/trade, −131.7R total). Walk-forward pooled precision **0.258**, Wilson CI95 **[0.24, 0.27]** | **Non-viable — confirmed, not suspected.** The edge is measurably *below* the 0.400 breakeven with a tight CI. |
| **SELL** | Val ROC-AUC **0.649**, PR-AUC **0.401**. At calibrated threshold 0.285: precision **0.408** (above breakeven) at **~6.6 signals/day** | **Viable lane.** Clears breakeven at real volume — the only lane that does. |

**Interpretation:** the improvements did not "fix" BUY — no configuration can, because the BUY ranker
has no discrimination (ROC-AUC ≈ 0.50). Their real value is that **R5 (EV) + R7 (Wilson CI) now give a
decisive verdict instead of a noisy 28-signal guess**: BUY is EV-negative, SELL is genuinely above
breakeven. The min-support floor (R1) correctly exposed BUY's weakness by forcing the threshold down
until the flat precision curve was visible. Calibration (R6/R8) behaves as expected — a well-calibrated
model on a ~25 % base rate rarely exceeds 0.5, which is why operating thresholds land near 0.29–0.35.

### 4.2 Fixes applied during validation

- **Combiner crash (`KeyError: 'conflict'`)** in the R2 SELL evaluation — `apply_cooldown` now guards
  the conflict column so standalone SELL frames evaluate cleanly.
- **EV report formatting** — Wilson CI bounds cast to `float` (no more `np.float64(...)` noise).
- **`UndefinedMetricWarning`** at the 0.5 reference point — `zero_division=0` added, with a note that
  0.5 is only a reference; the true operating threshold is calibrated in the next cell.

### 4.3 Recommended next steps (in order)

1. **Flip the combiner to the SELL lane.** BUY is EV-negative; SELL clears breakeven. Set
   `BUY_ONLY = False` (or run SELL-only) and re-run the R2/R5/R7 cells to confirm SELL's **sealed-test
   EV is positive with a CI that clears 0.400** before committing. This is the single highest-leverage action.
2. **Retire or shelve the BUY lane** until it has a real signal source. Do not spend threshold/ensemble
   effort on a random ranker — attack its *inputs* instead (step 4), not its calibration.
3. **Lock SELL's operating point from walk-forward, not a single window.** Use the R7 folds to choose the
   SELL threshold and report precision + signals/day with its Wilson CI, so the live threshold is not
   fitted to one lucky test slice.
4. **Feed the BUY (and SELL) models genuinely new information — R4 macro.** Wire in the Bloomberg
   rate-differential / DXY features and re-select. This is the only untapped source likely to lift BUY
   ROC-AUC above 0.55; nothing in the current feature set does.
5. **Re-examine the label at its best point — R3 (FW=2 + joint TP×SL sweep).** The FW=2 / lower-TP region
   hit ROC-AUC 0.735 in earlier experiments and was never carried through the combiner. Re-run it under
   the R5/R7 guardrails.
6. **Promote nothing on a single test window.** Keep every future decision gated on **net-pips EV with a
   non-overlapping Wilson CI** versus the current SELL baseline. Report validation and test separately.

**Bottom line:** the experiment now has an honest verdict — **BUY does not trade, SELL does.** The
next milestone is a clean, walk-forward-validated, EV-positive SELL configuration promoted to the
combiner, followed by a macro-feature (R4) attempt to build a BUY lane that actually has an edge.

---

## 5. Second Validation Run — Deeper Findings & Adjustments (2026-07-23)

This run used **new, larger splits** (TRAIN 2020-06-30→2025-06-30, VAL 2025-07→2025-12 · 131 days,
TEST 2026-01→present · **130 days / ~3,130 bars**), so the test verdict now rests on real volume, not a
28-signal window. The R2 SELL sealed-test evaluation also completed for the first time. The picture is
now sharper — and it changes the recommended next move.

### 5.1 The three lanes, re-measured on the large sealed test

| Lane | Validation | Sealed test (R2 / EV) | Verdict |
|---|---|---|---|
| **BUY** | ROC-AUC **0.505**, PR-AUC 0.360 (*below* the 0.370 base rate) | prec **0.213**, EV **−0.533R** (−7.53 pips), total **−277.8R**. Walk-forward: **every one of 13 months below breakeven**, pooled 0.255, CI [0.24, 0.27] | **Dead. Random ranker.** Remove it. |
| **SELL** | ROC-AUC **0.674**, PR-AUC 0.389; thr 0.295 → prec **0.425** @ 6.3/day (0.306 → **0.447** @ 4.5/day) | raw prec **0.391**, EV **−0.114R**, CI95 **[0.352, 0.431]** (straddles breakeven) | **Real edge, marginally short.** Sits ~1 precision-point under the 0.400 breakeven. |
| Combiner **SELL final** | — | **2 signals** (not 578) | **Poisoned by BUY** — see 5.2 |

### 5.2 Two structural problems this run exposed

1. **The dead BUY lane is actively destroying the SELL lane.** In the combined pipeline SELL collapses
   from 834 candidates to **2 signals** because BUY (which fires ~21×/day at its near-random threshold
   0.354) triggers a *conflict* on almost every bar and cancels the SELL. The SELL model's true
   deployed performance is the **R2 standalone** figure (578 signals, 0.391), **not** the combined 2.
   → **SELL must be run standalone; BUY should not be in the pipeline at all.**

2. **The threshold objective was leaving profit on the table.** `precision × log(signals)` picked SELL
   thr **0.295** (val prec 0.425) over **0.306** (val prec 0.447) by a hair — and 0.295 then decayed to
   **0.391 (below breakeven)** on test. Because the strategy has a *fixed* breakeven, the precision
   *margin* is what determines EV, so a volume-greedy objective is exactly wrong near the breakeven line.

### 5.3 Adjustment already applied (notebooks)

**Changed the threshold objective in `eurusd_buy_improved.ipynb` + `eurusd_sell_improved.ipynb` (cell 40).**
When a profitable (≥ breakeven) region exists, thresholds are now ranked by
**`(precision − breakeven) × log(signals)`** instead of `precision × log(signals)`; when no threshold
clears breakeven (e.g. BUY) it falls back to the old rule and flags the model as a ranker. On this run's
validation numbers the new rule selects SELL thr **0.306 (prec 0.447)** instead of 0.295 — the
higher-precision point that has the best chance of clearing breakeven on the sealed test. *Re-run the SELL
notebook and the combiner R2 cell to confirm the new EV.*

### 5.4 Next steps (in priority order)

1. **Deploy SELL-only; drop BUY from the pipeline.** BUY is EV −0.53R and, worse, it suppresses SELL via
   conflicts. Run the combiner with the SELL lane alone (no BUY, no cross-filter) and read performance
   from the R2/EV cells. *(This is a config decision; the R2 cell already reports the correct numbers.)*
2. **Re-run with the new precision-margin threshold (§5.3) and re-check SELL EV.** Target: sealed-test
   precision ≥ 0.400 with a Wilson CI whose lower bound clears breakeven. If EV turns positive, SELL is
   promotable; if the CI still straddles 0.400, treat SELL as *break-even, not yet profitable*.
3. **If SELL is still ~1 point short, attack the breakeven itself (R3).** The 0.400 barrier is set by
   TP=1.5×ATR / SL=1.0×ATR (breakeven win-rate = risk/(risk+reward) = 1.0/2.5 = 0.400). A **higher** R:R
   lowers the required win rate — e.g. TP=2.0×ATR / SL=1.0×ATR drops breakeven to **0.333**, which SELL's
   0.391 precision already clears. The catch: a wider TP is hit less often, so precision falls too. Run a
   **joint TP×SL sweep**, re-label, and re-validate to find the R:R where SELL's precision curve sits
   above its own breakeven with positive EV. This is the most likely path to convert the existing edge
   into profit without a new signal source.
4. **Then add genuinely new signal — R4 macro (rate-differential / DXY).** This is the only untapped input
   likely to lift precision materially and is the sole realistic route to reviving a BUY lane.
5. **Governance unchanged:** promote nothing without net-pips EV **and** a non-overlapping Wilson CI on the
   sealed test; always report precision **and** signals/day; keep validation and test conclusions separate.

**Bottom line for this run:** BUY is conclusively dead and should be removed. **SELL has a genuine,
measurable edge that lands just short of profitability (0.391 vs 0.400, EV −0.11R).** The two levers most
likely to close that gap are already identified: the **precision-margin threshold** (applied above) and a
**TP/SL R:R sweep (R3)** to lower the breakeven the model has to beat.
