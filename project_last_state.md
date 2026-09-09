# Project Last State — Frival Trading System

**Last updated:** 2026-09-09T17:10-05:00
**Status:** LIVE — 5-pair pipeline (4 SELL + 1 agnostic in shadow). Execution bot in live mode ($3,287 balance). MERG volatility gate active in shadow. Daily scheduler operational (double-click `run_daily.bat`). Candle-close gate + break-even monitor deployed.

---

## 1. What We Built

### 1.1 Frival Signal Pipeline (`frival/`)

**Purpose:** Agentic H1 signal system. ML ensemble → gates → dual-agent validation → JSONL output → execution bot.

**Supported pairs (v5):**

| Pair | Direction | Threshold | ROC-AUC | Test Precision | Lot Size | Status |
|---|---|---|---|---|---|---|
| EURUSD | SELL | 0.276 | 0.674 | 0.411 | 0.08 | **Live Core** |
| GBPUSD | SELL | 0.334 | 0.673 | 0.436 | 0.08 | **Live** |
| USDCHF | SELL | 0.365 | 0.608 | 0.435 | 0.04 | **Live** |
| USDCAD | SELL | 0.341 | — | 0.424 | 0.08 | **Live** |
| **EURUSD_AGNOSTIC** | **AGNOSTIC** | **0.5** | **0.619** | — | **0.04** | **Shadow** (1-week validation) |
| USDJPY | — | — | <0.60 | <0.400 | — | **KILLED** |
| XAUUSD | — | — | — | 0.258 | — | **KILLED** (needs TIPS/VIX) |

### 1.2 Direction-Agnostic Model (NEW)

**Question:** *"Will EURUSD hit the upper or lower R×ATR target first in the next 6 hours?"* Symmetrical envelope (R = 1.0). Replaces separate BUY/SELL models with one model that trades in either direction.

- **Label:** `y_agnostic = 1` if UP target hit before DOWN target, else 0. Base rate ~50%.
- **Features:** Same 90+ H1 technical indicators. 62 selected by noise-vote (ROC-AUC 0.619 on sealed 2026 test).
- **Direction logic:** `P(up) > 0.5 → BUY, P(up) ≤ 0.5 → SELL`. No threshold gate — always fires a prediction.
- **Agent prompts:** `technical_agnostic.txt` + `fundamental_agnostic.txt` — directional consistency checks (not SELL-only rules).
- **Shadow validation:** 1 week, log-only. Track directional accuracy. Flip `shadow: false` after validation.
- **Bundle:** `EURUSD_H1_agnostic_Ensemble.joblib`.

### 1.3 Execution Bot (`frival/execution_bot/`)

- **Mode:** LIVE (`settings.yaml`: `trading.mode: live`).
- **Risk:** max_daily_loss $50, max 1 position per pair, max 5 total positions, deviation_points=5.
- **Break-even monitor (NEW):** After order placement, polls MT5 every 30s. When price covers 50% of distance from entry to TP1, moves SL to break-even. Max 10 min. Toggled via `settings.yaml` → `break_even.enabled`.
- **Safety:** `confirm_live_orders: true` (manual confirmation each trade). Emergency stop file at `frival/data/emergency_stop.txt`.

### 1.4 MERG — Macro Event Response Gate

| Component | Status |
|---|---|
| Stage 1 (reaction) | ✅ Trained, leak-free, test ROC 0.721, deployed in shadow |
| Stage 2 (M1 direction) | ❌ Failed (ROC 0.490 = noise). Deleted. |
| H1 event-direction (6h) | ❌ Failed (ROC 0.598). Deleted. |
| Runtime wiring | ✅ `macro_event_responder.py` ← `EURUSD_MERG_v2_stage1_Ensemble.joblib` |
| Gate logic | ✅ Undirectional veto: `P(reaction) ≥ 0.60` → BLOCK |

### 1.5 Candle-Close Gate (NEW)

Runs after MERG passes and before agents evaluate. Fetches the most recently **completed** M15 bar from MT5:

- Model predicts SELL but M15 closed bullish → **BLOCK**
- Model predicts BUY but M15 closed bearish → **BLOCK**
- Doji/neutral (body < 30% of range) → PASS
- MT5 unavailable → PASS (fail-open)

Prevents momentum-chase entries — the pattern identified from the XAUUSD manual trading experiment as a consistent source of losses.

### 1.6 Break-Even-at-50% Monitor (NEW)

After execution bot places a trade, polls current price every 30s for up to 10 min. When price covers 50% of distance from entry to TP1, moves SL to break-even. Trades that had early momentum and later reversed now close at zero loss instead of hitting original SL. Toggled via `break_even.enabled` in settings.yaml.

### 1.7 Daily Scheduler (NEW)

`run_daily.bat` (double-click) → `run_daily_scheduler.py`:
- First run immediately on double-click
- Then at every :01 from 08:01 to 11:01 AM Panama (13:01–16:01 UTC)
- Countdown display between runs
- Exits after final 11:01 execution
- All 5 pairs + execution bot at each :01

---

## 2. Key Files

| File | Purpose |
|---|---|
| `frival/main.py` | CLI orchestrator + `_merg_event_risk_gate()` + candle-close gate + AGNOSTIC direction logic |
| `frival/model/features.py` | `compute_features()` — 90+ H1 features + D1 context + aux (WTI/USDX) + calendar merge. `AGNOSTIC_FEATURES` (62 features). |
| `frival/model/ensemble.py` | load_model() + predict() |
| `frival/signal_gate.py` | Threshold → session → cooldown → **candle-close** gates |
| `frival/agents/technical.py` | Agent A — GPT-4o. `direction + prob_up` params for agnostic pairs |
| `frival/agents/fundamental.py` | Agent B — Perplexity. `direction + prob_up` params for agnostic pairs |
| `frival/agents/senior.py` | Synthesize + borderline + 3-strike soft-veto |
| `frival/agents/calendar_context.py` | build_macro_context() + get_next_high_event() |
| `frival/agents/macro_event_responder.py` | MergInference — Stage-1 reaction detector |
| `frival/agents/prompts/technical_agnostic.txt` | Agent A prompt — directional consistency check |
| `frival/agents/prompts/fundamental_agnostic.txt` | Agent B prompt — directional macro assessment |
| `frival/run_daily.bat` | Double-click launcher for daily scheduler |
| `frival/run_daily_scheduler.py` | Scheduler loop: :01 executions, countdown, 5 pairs |
| `frival/DAILY_ROUTINE.md` | Documentation — all commands + gates + thresholds |
| `frival/execution_bot/` | Execution bot (watcher + order bot + MT5 + **break-even monitor**) |
| `ml-signal-service/models_bin/` | All model bundles (7 sell + MERG Stage 1 + agnostic) |
| `ml-signal-service/notebooks/agnostic/` | Direction-agnostic training notebook |
| `ml-signal-service/notebooks/merg/` | MERG Stage 1 + H1-direction experiment notebooks |
| `cloud-deployment-learning/` | GCP/Docker learning path (4-phase guide) |

---

## 3. Daily Routine

**Prerequisites:** MT5 terminal running with EURUSD, GBPUSD, USDCHF, USDCAD, WTI, USDX in Market Watch.

**Execution:** Double-click `frival/run_daily.bat`. The scheduler window opens, runs immediately, then at every :01 from 08:01 to 11:01 AM Panama (13:01–16:01 UTC). Countdown displayed between runs. Exits after 11:01.

**Pairs processed per session:** EURUSD → GBPUSD → USDCHF → USDCAD → EURUSD_AGNOSTIC → execute_pending()

**Gate chain (in order):** Threshold → Session → Cooldown → MERG (if enabled) → Candle-Close → Agents → Senior

---

## 4. MERG — Deep Dive

### 4.1 Dataset

`ml-signal-service/data/raw/macro/ExportedData.csv` — **4,793 high-impact EURUSD releases (2007-02 → 2026-07)**. 45 M1 candle-anatomy columns (tWick/body/bWick × 15 windows) + 4 target columns (`target`/`targetSimple`/`target1`/`target2`).

### 4.2 Window semantics

`15..11` = 5 pre-event bars (15 = t−5 min oldest, 11 = t−1 min closest), `10` = release bar, `9..1` = 10 post-event bars (leaky). Stage 1 uses prefix 5 (pre-event only, leak-free).

### 4.3 Stage 1 — Reaction Detector

- **Label:** `y_reaction = 1 if targetSimple ∈ {U, D} else 0`.
- **Features:** window-prefix 5 M1 anatomy + derived ratios + event one-hot (top-20 + OTHER) + `is_speech`. 59 total, **17 selected**.
- **Results:** test ROC-AUC **0.721**, PR-AUC **0.526** (base 0.315). At threshold **0.60** → ~0.70 precision, ~15 vetoes/year.
- **Bundle:** `EURUSD_MERG_v2_stage1_Ensemble.joblib`.

### 4.4 Runtime wiring

- `macro_event_responder.py` — loads Stage-1 bundle, replicates notebook feature engineering (prefix 5, ddof=1 std, event one-hot + normalization). `REACTION_THRESHOLD = 0.60`.
- `main.py::_merg_event_risk_gate()` — fetches 5 completed M1 bars, blocks on `P(reaction) ≥ 0.60` (undirectional).
- `calendar_context.py::get_next_high_event()` — fixed from broken column names (`date_time`→`event_dt`, `impact`→`Impact`).

---

## 5. USDCAD — Fundamental Driver Integration

### 5.1 The WTI hypothesis

CAD is oil-driven (oil ≈ 40% of Canada's export revenue). Adding WTI H1 data as a daily context feature was the decisive improvement for USDCAD.

### 5.2 Before vs After WTI/USDX

| Metric | Before (no aux) | After (WTI+USDX) |
|---|---|---|
| SELL test precision | 0.333 (27 sig) | **0.424** (33 sig) |
| SELL EV | −0.345R | −0.114R |
| WTI feature rank | — | **#1** `wti_ret_1d` |
| Overfit gap | +0.157 | +0.138 |

### 5.3 Runtime feature engineering

`_merge_aux_symbols()` in `frival/model/features.py` loads `WTI_H1.csv` / `USDX_H1.csv`, resamples to daily, derives `{wti/dxy}_ret_1d, _ret_5d, _vs_ema20, _trend`, shifts 1 day (no lookahead), and merges into the H1 feature matrix. Called automatically for USDCAD (and XAUUSD if needed; currently EURUSD/GBPUSD/USDCHF skip it — no-op).

---

## 6. XAUUSD — Attempted & Killed

USDX was insufficient for gold. The model **did select** USDX features (ranked #4–6 in the noise-vote), but test precision stayed at 0.258 — below breakeven. Gold is primarily driven by **real yields** (TIPS 10Y), not the dollar index alone. USDX is a secondary driver. To revisit gold: add TIPS data from FRED (`DFII10`) plus VIX.

---

## 7. Agent Decision Flow

### Three-Tier System

| Tier | Range | Rule |
|---|---|---|
| **Standard** | p ≥ threshold | Single agent CONFIRM sufficient |
| **Borderline** | 0.20 ≤ p < threshold | BOTH agents must CONFIRM |
| **Blocked** | p < 0.20 | No agent evaluation |

**EURUSD_AGNOSTIC exception:** threshold = 0.5 (the decision boundary). No gate — model always fires a directional prediction every hour. Agent A/B evaluate directional consistency, then signal is logged as SHADOW_FIRED.

### Senior Synthesis

| Agent A | Agent B | Result |
|---|---|---|
| CONFIRM | CONFIRM | **FIRED** (HIGH) |
| CONFIRM | NEUTRAL | **FIRED** (MODERATE) |
| NEUTRAL | CONFIRM | **FIRED** (MODERATE) |
| REJECT | * | **SHELVED** |
| * | REJECT | **SHELVED** |
| NEUTRAL | NEUTRAL | **SHELVED** |

**3-strike soft-veto:** 3 consecutive Agent B REJECTs → one Agent A HIGH-confidence CONFIRM can override.

---

## 8. Known Gaps & Issues

### P0
- **Timezone unverified:** calendar times + H1/M1 bar times must share the same clock for the 60-min MERG window to be correct. Still open.

### P1
- **Calendar name normalisation:** live calendar `Name` vs dataset names. Best-effort normalisation in place; ~133/183 exact match.
- **Bundle threshold mismatch:** MERG bundle stores `threshold=0.2809` (F1-optimal), runtime uses hardcoded `REACTION_THRESHOLD=0.60`.
- **USDCAD EV borderline:** −0.114R is close to zero but still negative. Monitor closely in live mode.
- **Agnostic model in shadow:** 1-week validation in progress. Need 10–15 directional predictions to assess live accuracy before flipping to live.

### Signal-drought diagnosis & fixes (2026-08-18)

**Fixes applied:**
1. **Prompt logic bug** — pre-event NEUTRAL rule bypass (4+ → 3+ in borderline, 3+ → 2+ in standard)
2. **Event-window collision** — `high_events_next_1h >= 1` → `>= 3`
3. **GBPUSD threshold** — 0.381 → 0.334 (old threshold exceeded max observed live probability)

### EURUSD threshold reduction (2026-08-25)
- 0.333 → 0.276 to produce trades in the current regime. Precision decay from 0.448 to ~0.40 expected but unverified.

### Daily scheduler (2026-09-09)
- `run_daily.bat` / `run_daily_scheduler.py` operational. Tested on first EURUSD_AGNOSTIC execution.

### Candle-close gate + break-even monitor (2026-09-09)
- Candle-close gate: fetches last completed M15 bar, blocks trades where candle contradicts predicted direction. Prevents momentum-chase entries.
- Break-even monitor: after order placement, moves SL to break-even when price covers 50% of distance to TP1. Preserves capital on trades that had early momentum but later reversed.
- Both patterns extracted from the XAUUSD manual trading experiment (Sep 4-9, ~$3,287 balance, 0.01 lots).

### XAUUSD — path to viability
- Dominant drivers (TIPS real yields via FRED, VIX) still missing. USDX-only experiment failed (test precision 0.258).
- Manual experiment proved multi-timeframe structural analysis works but requires real-time LLM chart analysis — incompatible with our batched H1 pipeline architecture.
- Gold remains a future project after FRED/TIPS integration.

### P2
- **Calendar reload per call:** `get_next_high_event()` reloads all 20 CSVs each time.
- **Cloud deployment learning path:** `cloud-deployment-learning/` folder with 4-phase GCP/Docker guide. Phase 1 not started.

---

## 9. XAUUSD Manual Trading Experiment — Key Findings (2026-09-04 to 09-09)

A 6-day experiment where Perplexity/OpenAI analyzed gold M15/H4 charts in real-time and proposed structured setups. Three durable patterns extracted:

1. **Entry-after-candle-close:** never enter on an open candle. Wait for M15 close, confirm with M5 structure. Implemented as the Candle-Close Gate.
2. **Break-even at 50%:** when price covers half the distance to TP1, move SL to entry. Implemented as the Break-Even Monitor.
3. **Break-and-retest is the only trigger:** enter on the pullback after the level break, not the break itself. H4 sets bias, M15 sets zone, M5 sets trigger.

The experiment used 0.01 lots per trade (risk ~$10–25), had one major risk incident (0.55 lots = 88% account drawdown, caught and corrected), and produced a pattern of high win-rate entries on continuation trades that aligned with the higher-timeframe bias. Counter-trend entries consistently failed.

---

## 10. Environment

- **Python:** `C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe` (conda `deaf_agent`)
- **Key packages:** pandas, numpy, scikit-learn 1.5.2, xgboost, lightgbm, joblib, MetaTrader5, openai, openpyxl, yaml
- **MT5:** Account 81486396, Server FPMarketsSC-Live, LIVE mode active (~$3,287 balance)
- **API keys:** OpenRouter + Perplexity in `frival/config/.env` (gitignored)
- **Model storage:** `.joblib` files under `ml-signal-service/models_bin/`

---

*End of state.*