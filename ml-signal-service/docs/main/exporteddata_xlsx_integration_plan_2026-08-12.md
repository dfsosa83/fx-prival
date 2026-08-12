# ExportedData.xlsx — Integration Plan
**Date:** 2026-08-12
**Author:** Automated architectural review
**File under evaluation:** `ml-signal-service/data/raw/macro/ExportedData.xlsx`
**System of record:** [project_last_state.md](project_last_state.md)
**Prior EDA (superseded on file version, retained on methodology):** [macro_event_response_eda_report.md](ml-signal-service/docs/main/macro_event_response_eda_report.md)

---

## 1. Executive Summary

**Finding.** The `.xlsx` file supplied on 2026-08-12 is **not** the same artifact that was analyzed in the prior EDA (`ExportedData.csv`, 3,790 × 1,773). It is a **distilled, single-source variant**:

| Attribute | ExportedData.csv (prior) | ExportedData.xlsx (current) | Delta |
|---|---|---|---|
| Rows | 3,790 | **4,793** | +26.5% |
| Columns | 1,773 | **51** | −97% |
| Sheets | n/a (CSV) | `ExportedData` (1) | — |
| Feature families | OHLCV + 720 indicator columns + 915 candlestick patterns | **Only candlestick anatomy** (`tWick`, `body`, `bWick` × 15 windows) | Only 1 family retained |
| Metadata columns | `event`, `time`, `target` | `event`, `time` | — |
| Target columns | 1 (27-class code) | **4** (`target`, `targetSimple`, `target1`, `target2`) | Richer |
| Target granularity | 3-char U/D/N per bar (27 classes) | Full sequence pattern (**186 classes**) + `targetSimple` 3-class (U / D / N) | Much richer |
| Class distribution | Synthetically balanced (~140/class) | **Natural imbalance**: N=61.6%, U=19.7%, D=18.7% | Real, not resampled |
| Missing values | 0.14% | **0** | Cleaner |
| Time range | 2007-02-14 → 2026-07-31 | 2007-02-13 → 2026-07-31 | Same window |
| Unique events | 27 | **183** | Full taxonomy |

**Reading of the change.** The dataset owner (or upstream MT-generator) appears to have (a) dropped every derived indicator and pattern column, (b) kept the *rawest* microstructure signal — the anatomy of the last 15 pre-event M1 candles, (c) exposed a richer post-event **sequence target** in place of the 3-character summary, and (d) restored the natural class balance. This is objectively a **better training substrate** than the prior CSV for a first-generation model, because the 1,499 dead/noisy indicator columns identified in §6 of the prior EDA are simply gone.

**Recommendation (updated).** Integrate as a **Macro-Event Response Gate (MERG)** — a specialized inference module invoked *only* when a HIGH-impact release is imminent (≤ 60 min out) — rather than as a new feature block for the H1 models or as a fourth agent. Rationale is developed in §4.

**Effort.** ~1 week to v1 in shadow mode; ~3 weeks to hard-gated live behind `MERG_ENABLED` flag with backtest evidence.

---

## 2. Dataset Anatomy (Verified)

### 2.1 Shape and layout

```
Sheet          : ExportedData
Rows           : 4,793
Columns        : 51
Metadata       : event (str), time (str "YYYY.MM.DD HH:MM")
Features       : 45 numeric int64 (tWick_i, body_i, bWick_i for i in 15..1)
Targets        : 4 (target, targetSimple, target1, target2)
Missing        : 0 across all columns
```

The 15 windows are indexed in **descending order**: window 15 is furthest back in time; window 1 is closest to the release. This matches the prior CSV convention and preserves compatibility with the earlier analysis.

### 2.2 Feature statistics (spot-check)

| Column | min | 25% | 50% | 75% | max | interpretation |
|---|---|---|---|---|---|---|
| `tWick1` | 0 | 1 | 4 | 10 | 160 | upper wick, points-scaled |
| `body1` | −242 | −? | 0 | ? | +291 | signed body (D up / R down) |
| `bWick1` | 0 | 1 | 4 | 10 | 121 | lower wick |
| `body15` | −751 | −11 | 0 | +10 | +293 | earlier candles show wider anomalies |

Values are **integers scaled in broker points** (10 points ≈ 1 pip on EURUSD 5-digit; multiplied by pip_multiplier). Signed `body` (negative = bearish, positive = bullish) removes the direction-ambiguity of the CSV's separate OHLC representation.

**Timeframe confirmation (repeat of the M1 finding in the prior EDA §6.1).** Body medians of 0 with 75% at ±10 points (1 pip), tick-volume-equivalent proportions, and event timestamps ending in `:30`, `:45`, `:00` are all consistent with **1-minute bars covering the 15 min immediately before the release**. The MERG's prediction horizon is therefore **the first few M1 candles after the release**, not H1 direction — a distinction that is architecturally critical.

### 2.3 Target semantics

Four target columns are present. Distributions confirm they encode the same event but at different granularities:

| Column | Unique classes | Top 3 |
|---|---|---|
| `target` | 186 | N (2,952), U (477), D (446) |
| `targetSimple` | **3** | N (2,952), U (943), D (898) |
| `target1` | 186 | same as `target` |
| `target2` | 186 | same as `target` |

`target`, `target1`, `target2` are identical (or near-identical) distributions — likely three snapshot views of the same sequence label (e.g. immediate post-event, +5 min, +10 min horizons). The 186 classes are **sequence patterns** of the form `N`, `U`, `D`, `2U`, `2D`, `3U`, `3D`, `U|D`, `D|U`, `2D|U`, `U|D|U`, etc., where:

- A bare `U`/`D`/`N` denotes a single-bar move
- A leading integer `2U`, `3D` denotes a run of consecutive same-direction bars
- A pipe `U|D` denotes a directional transition sequence
- `N` denotes non-move (below a noise threshold)

`targetSimple` collapses these 186 patterns into 3 classes (U / D / N) by taking the net direction of the sequence.

**Balance and base rate for prediction.**

| Class | Count | Fraction | Interpretation |
|---|---|---|---|
| N (neutral) | 2,952 | **61.6%** | Most releases do NOT produce a meaningful directional response |
| U (up) | 943 | 19.7% | ~1 in 5 releases produces a net up move |
| D (down) | 898 | 18.7% | ~1 in 5 releases produces a net down move |

The **natural base rate of no reaction is high** (~62%). Any useful model must beat 62% majority-vote accuracy on the multi-class problem, or beat 50% ROC-AUC on a binary "reaction vs. no-reaction" reframing.

### 2.4 Event coverage

- **183 distinct events**, of which the top 20 (Retail Sales, ECB Lagarde, CPI, Core HICP, ECB rate, HICP, ECB Draghi, HCOB PMI, ISM Manuf, GDP annualized, GDP s.a., FOMC minutes, NFP, ECB press conference, Michigan sentiment, Fed rate, Powell speech, ISM Services, Avg Hourly Earnings, Core PCE) account for ~3,100 rows (65%).
- Weekday distribution: **Thu 26%, Wed 25%, Fri 23%, Tue 16%, Mon 9%** — dominated by mid-week high-impact windows.
- Hour distribution: peak at 15 UTC (n=1,115) — 10:30 ET NY release window — and 16 UTC (n=670) — post-open US data. Both windows overlap with our current live trading schedule (13:01–16:01 UTC).

### 2.5 Predictive-value hypothesis

The candlestick anatomy of the last 15 M1 candles before a release is a **positioning-imbalance proxy**:

- **Wick asymmetry** (`tWick_i` ≫ `bWick_i` or vice-versa) → one-sided liquidity sweeps → short-term reversion likely.
- **Body compression** (small `abs(body_i)` with elongated wicks) → tight consolidation, higher probability of a break on the release.
- **Body expansion + direction persistence** → strong pre-release drift → likely to extend on positive surprise, fade sharply on negative.
- **Volume-weighted wick behavior** (proxied here by body magnitude, since the .xlsx dropped tick_volume) → participation levels immediately pre-release.

These features do NOT overlap with anything the current H1 model consumes (which sees 15+ candles' worth of H1 aggregation, plus RSI/MACD/ATR/ADX/etc.). The MERG occupies a **structurally orthogonal** predictive niche: **minute-level, event-triggered, reaction-classifying**.

---

## 3. Integration Decision — Rationale

Three integration modes were considered:

### Mode A — Feature into the existing H1 models

Add pre-event M1 candlestick anatomy as features into `frival/model/features.py` and retrain the EURUSD/GBPUSD/USDCHF v3 ensembles.

**Rejected.** Rationale:

1. **Temporal mismatch.** The main models train on H1 bars. Injecting M1 pre-event anatomy would be NaN for ≥95% of training rows (no event in most hours). Prior EDA §3.2 flagged exactly this.
2. **Sparse regime.** Only rows adjacent to macro events would carry non-null values. The tree ensembles would learn to condition on "feature present" rather than on the feature's magnitude, effectively degenerating into an event-day indicator — which we already have.
3. **Retraining cost.** All three v3 bundles would need to be retrained, revalidated, and redeployed — significant risk to a system that just stabilized (Aug 12 audit).

### Mode B — Standalone LLM/Agent (fourth agent in the senior chain)

Provide MERG prediction to Agent B or promote it to a full "Agent C — event responder".

**Partially adopted (as secondary integration).** Rationale:

1. Adding a fourth voting agent breaks the current 2-of-2 senior-chain semantics documented in [project_last_state.md](project_last_state.md#L143-L166) and would require re-tuning the 3-strike soft-veto logic.
2. However, **injecting the MERG numeric output as text context into Agent B** is trivial and safe — Agent B already reads a `build_macro_context()` block. This is retained in §5.4.

### Mode C — Specialized event-risk gate (RECOMMENDED)

Train a compact classifier on the .xlsx (45 features, 3-class target via `targetSimple`, optional 186-class via `target`), serialize as `MERG_v1.joblib`, and plug it into [frival/signal_gate.py](frival/signal_gate.py) as a new gate that fires **only** when a HIGH-impact event is scheduled within a configurable window (default 60 min). Behavior:

| Gate 5 (MERG) input | Behavior |
|---|---|
| No HIGH event in next 60 min | Pass-through (identity) |
| Event scheduled AND `P(D) - P(U) > τ_conf` for our SELL signal | **PASS** (aligned with SELL direction) |
| Event scheduled AND `P(U) - P(D) > τ_conf` for our SELL signal | **BLOCK** (contradicts our short thesis) |
| Event scheduled AND `argmax = N` (no reaction predicted) | Pass-through |
| Event scheduled AND `max(P) < τ_conf` (low-confidence prediction) | Pass-through |

**Adopted.** This is the recommended integration. Rationale:

1. **Architectural fit.** It slots into the existing gate stack ([frival/signal_gate.py](frival/signal_gate.py) currently has threshold → session → cooldown gates) as a fourth conditional gate — no changes to models, no changes to agent contracts.
2. **Timeframe honesty.** MERG fires on M1 pre-event structure and predicts short-horizon M1 response — its inputs and outputs live in the timeframe where the .xlsx was recorded. It does not pretend to be an H1 predictor.
3. **Bounded scope.** MERG only speaks when it has data (an imminent HIGH event). On any other bar it is silent, eliminating the sparse-regime problem in Mode A.
4. **Safe failure mode.** When MERG's confidence is low, the default is pass-through, not block. False negatives (blocking a good trade) are strictly bounded to event-window bars.
5. **Interpretable to the operator.** The gate log will read `[Gate MERG] BLOCK: EURUSD SELL — NFP release in 14 min, MERG predicts U (p=0.71)` — human-legible causality.
6. **Cheap to build and reverse.** ~45 features and 4,793 rows is a two-hour training exercise; a single joblib deploys the entire capability; a single `MERG_ENABLED=false` flag rolls it back.

---

## 4. Integration Findings — Summary

| Question | Answer |
|---|---|
| Is the data high-quality? | Yes. 0 missing, 19 years, 4,793 samples, 183 event types, natural class balance. |
| Does it overlap with existing calendar features? | **No** — calendar features are aggregate counts; MERG features are pre-event microstructure. Orthogonal. |
| Does it fit the H1 models? | **No** — timeframe mismatch (M1) and sparse regime. |
| Does it fit as a fourth agent? | **Partial** — as text context to Agent B, yes. As a full agent, no (breaks senior semantics). |
| Does it fit as a gate? | **Yes** — clean architectural drop-in behind existing gate chain. |
| Expected alpha source | False-positive filter on event-window signals + optional promotion of borderline signals when MERG aligns. |
| Realistic performance target | ROC-AUC ≥ 0.58 on the binary reaction (U/D vs N) at holdout; ≥ 0.55 on directional (U vs D) subset. |
| Risk if MERG misfires | Contained — only event-window signals are affected; hard fail-open (pass-through on any inference error). |

---

## 5. Implementation Plan

### 5.1 Phase 0 — Repository setup (½ day)

1. Add `openpyxl` to `ml-signal-service/requirements.txt` (already installed in `deaf_agent` env; must be pinned).
2. Confirm `.xlsx` is under Git LFS or gitignored. If tracked as plain file, add `*.xlsx` filter or check size. The current file is small (~1–2 MB) so plain tracking is fine.
3. Create `ml-signal-service/steps/06_merg/` for the training pipeline; create `frival/agents/macro_event_responder.py` scaffold; add `MERG_v1.joblib` slot under `ml-signal-service/models_bin/`.

**Files touched**
- `ml-signal-service/requirements.txt` (add `openpyxl>=3.1`)
- `ml-signal-service/steps/06_merg/__init__.py` (new)
- `ml-signal-service/steps/06_merg/build_dataset.py` (new)
- `ml-signal-service/steps/06_merg/train.py` (new)
- `ml-signal-service/steps/06_merg/evaluate.py` (new)
- `frival/agents/macro_event_responder.py` (new stub)

### 5.2 Phase 1 — Data ingestion and preprocessing (½ day)

**Objective:** produce a clean training matrix from the `.xlsx`.

**Steps**

1. **Load.** `pd.read_excel("ml-signal-service/data/raw/macro/ExportedData.xlsx", sheet_name="ExportedData", dtype={"event": str, "time": str})`.
2. **Parse time.** `pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M", utc=False)`. Store as `time_utc` with an explicit `tz_localize` decision — the prior EDA §6 flagged timezone ambiguity in ExportedData; default to broker time (UTC+2 winter / UTC+3 summer) and convert to UTC via `pytz` + DST-aware fixed-offset table, OR ask the data owner. **This is a P0 pre-training question and must be answered before models are trusted.** If unresolved by training day, tag all trained models `MERG_v1_tz_unverified` and shadow-only.
3. **Feature block.** Select the 45 candlestick columns. Cast to `float32`. Optionally derive:
   - `body_sign_i` = sign(body_i), 3-valued {−1, 0, +1}
   - `range_i` = tWick_i + |body_i| + bWick_i
   - `body_ratio_i` = |body_i| / range_i (guarded against 0)
   - `wick_asym_i` = (tWick_i − bWick_i) / range_i
   - Momentum-ish derivatives: sum(body_1..3), sum(body_1..5), body_1 − body_15
   → total ~ 45 + 60 = ~105 features. Manageable.
4. **Event as feature.** Encode `event` via **target encoding** (mean `targetSimple`-as-integer per event, with 10-fold OOF to prevent leak) OR one-hot for the top 20 events + `OTHER`. Prefer the latter for interpretability.
5. **Label.** Two label sets:
   - `y_reaction` = binary: 1 if `targetSimple != "N"`, else 0. Base rate = 38.4%.
   - `y_direction` = binary (conditional on `y_reaction=1`): 1 if `targetSimple == "U"`, 0 if `"D"`. Base rate = 51.2% (923 / 1841).
6. **Split.** Time-based split, not random. Train = pre-2023, Val = 2023, Test = 2024–2026-07.

**Files touched**
- `ml-signal-service/steps/06_merg/build_dataset.py` (implements 1–6, writes `data/features/merg_v1.parquet`)

### 5.3 Phase 2 — Model development (1 day)

**Two-stage classifier (RECOMMENDED)** rather than a single multi-class problem, because the 3-class task suffers from the N-majority pathology and because operationally we want two distinct probabilities: `P(any reaction)` and `P(direction=up | reaction)`.

**Stage 1 — Reaction detector**
- Task: binary `y_reaction`
- Candidates: LightGBM, XGBoost, LogReg (baseline)
- Success gate: **ROC-AUC ≥ 0.58** on the 2024–2026 holdout
- Calibration: Platt scaling (`sklearn.calibration.CalibratedClassifierCV`, method="sigmoid")

**Stage 2 — Direction classifier (conditional)**
- Task: binary `y_direction` on `y_reaction=1` subset (n=1,841)
- Same candidates
- Success gate: **ROC-AUC ≥ 0.55** on the 2024–2026 holdout (harder problem; a random baseline is 0.50, base rate ≈ 51.2%)

**Runtime composition**
For a live event scheduled T minutes out with predicted `p_reaction` and `p_up` from Stage 2:
```
p_U = p_reaction * p_up
p_D = p_reaction * (1 - p_up)
p_N = 1 - p_reaction
predicted_class = argmax({U: p_U, D: p_D, N: p_N})
confidence = max({p_U, p_D, p_N})
```

**Optional Stage 3 (backlog)** — a Stage-3 sequence classifier on the 186-class `target` for operators who want the full sequence pattern in Agent B context (see §5.4). Not required for v1.

**Files touched**
- `ml-signal-service/steps/06_merg/train.py` (fits Stage 1 and Stage 2, writes `models_bin/MERG_v1_reaction.joblib` and `MERG_v1_direction.joblib`)
- `ml-signal-service/steps/06_merg/evaluate.py` (ROC, PR, calibration curves, confusion matrix per event family, saved to `ml-signal-service/docs/experiments/merg_v1_report.md`)

**Success artifacts required for promotion beyond shadow:**
- `merg_v1_report.md` with ROC-AUC, calibration plot, per-event-family precision, feature importance
- Feature-importance stability: the top-10 features must be consistent across 5-fold CV
- No single event type accounts for more than 30% of Stage-2 accuracy (guards against overfit to Retail Sales or one Lagarde-speech cluster)

### 5.4 Phase 3 — Runtime module (½ day)

**File: `frival/agents/macro_event_responder.py`** (new)

```python
"""
MERG — Macro Event Response Gate inference module.

Loaded once at process start; queried on every H1 bar during live.
Silent unless a HIGH-impact event is within EVENT_WINDOW_MIN minutes.
"""

class MergInference:
    def __init__(self, model_dir: Path, event_window_min: int = 60,
                 confidence_threshold: float = 0.60):
        self.reaction_model = joblib.load(model_dir / "MERG_v1_reaction.joblib")
        self.direction_model = joblib.load(model_dir / "MERG_v1_direction.joblib")
        self.event_window_min = event_window_min
        self.tau = confidence_threshold

    def predict(self, bar_dt_utc, symbol, calendar_df, m1_bars) -> dict | None:
        """
        Returns None if no HIGH event in window (silent pass-through).
        Otherwise returns
          {"event": <name>, "minutes_to_event": int,
           "p_U": float, "p_D": float, "p_N": float,
           "class": "U"|"D"|"N", "confidence": float,
           "features_extracted": bool}
        """
        # 1. Look up next HIGH event via calendar_df (existing calendar module)
        # 2. If minutes_to_event > event_window_min: return None
        # 3. Extract last 15 M1 bars from m1_bars → build feature vector
        # 4. If m1_bars insufficient: return {"features_extracted": False, ...}
        # 5. Run reaction_model.predict_proba → p_reaction
        # 6. Run direction_model.predict_proba → p_up
        # 7. Compose and return the dict above
```

**M1 bar acquisition at runtime**

The current `frival/data/fetcher.py::fetch_ohlcv()` fetches H1. Add a companion helper:

```python
def fetch_m1(symbol, count=30):  # 30 to give a buffer beyond the 15 needed
    # Uses mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, count)
```

**Files touched**
- `frival/agents/macro_event_responder.py` (new)
- `frival/data/fetcher.py` (add `fetch_m1`)

### 5.5 Phase 4 — Gate integration (½ day)

**File: `frival/signal_gate.py`** — add `event_risk_gate()`.

Current gate order per [project_last_state.md](project_last_state.md#L128-L136):
1. Threshold gate
2. Session gate
3. Cooldown gate

Proposed new order (MERG last so it never overrides earlier PASS/BLOCK decisions unnecessarily):

```
threshold → session → cooldown → merg_event_risk
```

**Behavior contract** (`event_risk_gate`):

```python
def event_risk_gate(signal_dir: str,             # "SELL" | "BUY"
                    merg_pred: dict | None,      # from MergInference.predict()
                    borderline: bool) -> tuple[str, str]:
    """
    Returns (status, reason) where status ∈ {"PASS", "BLOCK"}.
    Never PROMOTES a below-threshold signal (that would break the existing
    threshold gate contract). Only blocks contradictory event-window signals.
    """
    if merg_pred is None or not merg_pred.get("features_extracted", True):
        return "PASS", "no HIGH event / MERG silent"
    conf = merg_pred["confidence"]
    if conf < TAU_CONF:
        return "PASS", f"MERG low-confidence ({conf:.2f})"
    predicted = merg_pred["class"]  # "U" | "D" | "N"
    if predicted == "N":
        return "PASS", f"MERG predicts no reaction (p_N={merg_pred['p_N']:.2f})"
    if signal_dir == "SELL" and predicted == "U":
        return "BLOCK", f"MERG predicts UP reaction (p={conf:.2f}) — contradicts SELL"
    if signal_dir == "BUY" and predicted == "D":
        return "BLOCK", f"MERG predicts DOWN reaction (p={conf:.2f}) — contradicts BUY"
    return "PASS", f"MERG aligned ({predicted}, p={conf:.2f})"
```

**Config** (`frival/config/settings.yaml` or a new `merg.yaml`):

```yaml
merg:
  enabled: false                # feature flag — default OFF until shadow evidence collected
  model_dir: ml-signal-service/models_bin
  event_window_min: 60
  confidence_threshold: 0.60
  shadow_only: true             # if true, log decision but never actually BLOCK
```

`shadow_only: true` is critical for phase 5.

**Files touched**
- `frival/signal_gate.py` (add gate; wire into `gate_signal()`)
- `frival/config/settings.yaml` (add `merg:` block)
- `frival/main.py` (instantiate `MergInference` once at start of `run_live`, thread through to the gate call site)

### 5.6 Phase 5 — Agent B context injection (¼ day)

**File: `frival/agents/calendar_context.py`** — extend `build_macro_context()`.

When MERG has a prediction for the current bar, append to the context text handed to Agent B:

```
[MERG Event-Response Model]
Approaching HIGH-impact event: {event_name} in {mins} min
Predicted first-window reaction: {class} (p_U={:.2f}, p_D={:.2f}, p_N={:.2f})
Confidence: {conf:.2f}
```

Agent B's REJECT / NEUTRAL / CONFIRM semantics are unchanged. This is purely an information injection. If MERG says nothing, the block is omitted.

**Files touched**
- `frival/agents/calendar_context.py` (add block; guard against MERG=None)
- `frival/agents/prompts/agent_b.txt` (or whichever prompt file) — add one line acknowledging the MERG block

### 5.7 Phase 6 — Deployment (1 day)

**Sequencing**

| Step | Action | Duration | Rollback |
|---|---|---|---|
| 6.1 | Deploy `merg.enabled: false` config + code changes to workspace | instant | `git revert` |
| 6.2 | Run `python steps/06_merg/train.py` to produce `MERG_v1_*.joblib`, LFS-track outputs | ~5 min training | delete .joblib |
| 6.3 | Set `merg.enabled: true, shadow_only: true` — log MERG output on every bar with an approaching event but do not block | ≥ 5 trading days | flip flags back |
| 6.4 | Review shadow log: for each recorded MERG BLOCK, would the trade have won or lost? Compute hypothetical precision uplift. | offline analysis | n/a |
| 6.5 | If uplift ≥ 10% relative precision AND no obvious event-family bias, flip `shadow_only: false`. MERG now hard-blocks. | live | flip back |
| 6.6 | Monitor daily: number of MERG blocks, false-block rate, and effect on aggregate PnL. | ongoing | flag-off if drift detected |

**Live checklist gate before flipping `shadow_only: false`**

- [ ] ≥ 10 event-window MERG activations recorded in shadow log
- [ ] MERG's predicted class matched the observed post-event M1 direction ≥ 60% of the time on 15-min window
- [ ] No single event type generated more than 30% of the shadow blocks
- [ ] Backtest re-run of April–July 2026 with MERG active shows ≥ 10% precision improvement OR ≤ 5% signal-count reduction with neutral precision

---

## 6. Files, Dependencies, and Architectural Changes

### 6.1 New files

| Path | Type | Purpose |
|---|---|---|
| `ml-signal-service/steps/06_merg/__init__.py` | new | package marker |
| `ml-signal-service/steps/06_merg/build_dataset.py` | new | ingest xlsx → parquet |
| `ml-signal-service/steps/06_merg/train.py` | new | two-stage classifier training |
| `ml-signal-service/steps/06_merg/evaluate.py` | new | metrics + report generation |
| `ml-signal-service/models_bin/MERG_v1_reaction.joblib` | new artifact | Stage-1 calibrated classifier |
| `ml-signal-service/models_bin/MERG_v1_direction.joblib` | new artifact | Stage-2 calibrated classifier |
| `ml-signal-service/docs/experiments/merg_v1_report.md` | new | training report |
| `frival/agents/macro_event_responder.py` | new | runtime inference module |

### 6.2 Modified files

| Path | Change | Risk |
|---|---|---|
| `ml-signal-service/requirements.txt` | add `openpyxl>=3.1` | none |
| `frival/config/settings.yaml` | add `merg:` block | none — feature flag defaults to `false` |
| `frival/data/fetcher.py` | add `fetch_m1()` helper | low — additive |
| `frival/signal_gate.py` | add `event_risk_gate()` and call it after cooldown | **medium** — new BLOCK path in critical decision code |
| `frival/main.py` | instantiate MergInference; pass to gate | low — behind flag |
| `frival/agents/calendar_context.py` | inject MERG block into Agent B context | low — additive text |
| `frival/agents/prompts/agent_b.txt` (or equivalent) | acknowledge MERG block | low — prompt tune |

### 6.3 Dependencies

Runtime — already in `deaf_agent` env:
- `openpyxl>=3.1` (for xlsx ingestion — installed)
- `scikit-learn>=1.5.2` (already used)
- `lightgbm` or `xgboost` (already used)
- `joblib>=1.3.2` (already used)

No new runtime library requirements beyond `openpyxl`. No new services, no new API keys, no additional Perplexity/OpenRouter quota.

### 6.4 Architectural changes

**Data flow — before**

```
H1 bar arrives → features.py → ensemble.py (p) → signal_gate (threshold, session, cooldown)
              → agent A (technical) → agent B (fundamental) → senior → JSONL
```

**Data flow — after**

```
H1 bar arrives → features.py → ensemble.py (p) → signal_gate
                                                    │
                            ┌───────────────────────┴──────────────┐
                            │  threshold → session → cooldown →    │
                            │                 event_risk (MERG)    │
                            └────────────────────┬─────────────────┘
                                                 │  (if event within 60 min)
                                                 ▼
                                       MergInference.predict()
                                                 │
                                       ┌─────────┴───────────┐
                                       │                     │
                                       ▼                     ▼
                              [Gate BLOCK]        agent B context injection
                                                             │
              → agent A (technical) → agent B (fundamental, w/ MERG note) → senior → JSONL
```

**Key invariants preserved**

- No change to model bundles or training data of the H1 ensembles.
- No change to Agent A.
- No change to the 2-agent senior semantics.
- No change to the execution bot (`frival/execution_bot/*`).
- Feature flag `merg.enabled: false` returns exact prior behavior.

### 6.5 Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Timezone ambiguity in `time` column (broker TZ vs UTC vs local) invalidates MERG feature alignment at runtime | **P0** | Explicit tz decision documented in `steps/06_merg/build_dataset.py` docstring; MERG shadow-only until confirmed with dataset owner |
| Class imbalance (N = 61.6%) leads Stage-1 to over-predict N | Medium | Two-stage architecture isolates reaction detection; use `class_weight="balanced"` in Stage 1 |
| Overfit to Lagarde/Draghi speeches (454 rows = 9.5% of dataset) | Medium | Per-event-family precision check in `evaluate.py`; block promotion if one family drives > 30% of accuracy |
| M1 bar fetch fails at runtime (MT5 gap, weekend) | Low | MergInference returns `features_extracted=False` → gate pass-through (fail-open) |
| MERG blocks all Fed-day trades (high-confidence contradictory prediction on every NFP) and turns out to be wrong | Medium | Shadow phase collects ≥ 10 event activations before hard-blocking; kill switch via `shadow_only: true` |
| The `.xlsx` is a stripped snapshot of a live-updated source and gets out of sync | Low | Retrain quarterly. Add hash of source .xlsx to `merg_v1_report.md` metadata. |
| The 186-class `target` is not what we think (e.g. encodes 4-bar sequences we haven't decoded) | Low | Use `targetSimple` for v1; leave `target` for a possible v2 sequence model |
| Adding a fifth gate slows the per-bar decision cycle | Negligible | MERG inference is < 5 ms per call; only invoked when calendar reports an approaching event |

### 6.6 Deferred / out-of-scope for v1

- Per-pair MERG models (v1 is EURUSD-only, matching the underlying data source). GBPUSD/USDCHF get the EURUSD MERG as an approximation; per-pair training deferred until a per-pair variant of the dataset is provided.
- 186-class sequence prediction (v2).
- Live retraining pipeline (v2).
- MERG-driven trade promotion (currently v1 only blocks; a "promote borderline" mode is left for v2 after real-world veto quality is measured).

---

## 7. Success Criteria (Operational)

| Metric | Target | Measurement |
|---|---|---|
| Stage-1 ROC-AUC | ≥ 0.58 | Time-based holdout 2024–2026 |
| Stage-2 ROC-AUC | ≥ 0.55 | Conditional on reaction=1 |
| Stage-1 calibration | Brier score ≤ 0.22 | Holdout |
| Feature-importance stability | Top-10 features overlap ≥ 80% across CV folds | 5-fold CV |
| Per-event-family concentration | No family > 30% of accuracy contribution | Ablation |
| Shadow phase | ≥ 10 MERG activations recorded; ≥ 60% predicted-class match to actual M1 direction | Live shadow log |
| Live phase precision uplift | ≥ 10% relative precision improvement on event-window signals | 30-day rolling |
| Rollback trigger | > 3 consecutive false BLOCK events on winning setups | Alert + auto flag-off |

---

## 8. Timeline

| Week | Milestone | Deliverable |
|---|---|---|
| 1 | Data ingestion + Stage 1/2 training + evaluation report | `merg_v1_report.md`, both `.joblib` files |
| 2 | Runtime module + gate wiring + Agent B context | code merged behind `merg.enabled: false` |
| 3 | Shadow deployment (`enabled=true, shadow_only=true`) | shadow log with ≥ 10 activations |
| 4 | Shadow review, backtest replay, decision to activate hard block | `shadow_only=false` if criteria met |

---

## 9. Bottom Line

The `.xlsx` provided today is materially different from the CSV analyzed a week ago — it is a **cleaner, more focused single-signal dataset** with a **richer target label** and a **realistic class distribution**. This is a net upgrade for what we want to build.

**Integrate as a specialized event-response gate, not as a feature block or an agent.** The gate integration path is the smallest architectural change that captures the dataset's specific predictive niche (short-horizon M1 reaction after a HIGH-impact release), is trivially reversible via a feature flag, and preserves every invariant of the current 2-agent senior chain. First live promotion of MERG should follow a shadow-only period with explicit acceptance criteria on both training metrics and observed activation quality.

The **single hard blocker before training** is the timezone provenance of the `time` column — the same finding flagged in §6.1 of the prior EDA. Resolve that with the dataset owner before shipping the first `.joblib`.

---

*End of plan.*
