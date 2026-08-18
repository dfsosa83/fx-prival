# Project Last State — Frival Trading System

**Last updated:** 2026-08-18T09:56-05:00
**Status:** LIVE — 4-pair SELL pipeline (EURUSD, GBPUSD, USDCHF, USDCAD). Execution bot in live mode ($1,000 account). MERG volatility gate active in shadow.

---

## 1. What We Built

### 1.1 Frival Signal Pipeline (`frival/`)

**Purpose:** Agentic H1 signal system. ML ensemble → gates → dual-agent validation → JSONL output → execution bot.

**Supported pairs (v4):**

| Pair | Direction | Threshold | ROC-AUC | Test Precision | Lot Size | Status |
|---|---|---|---|---|---|---|
| EURUSD | SELL | 0.333 | 0.674 | 0.411 | 0.08 | **Live Core** |
| GBPUSD | SELL | 0.381 | 0.673 | 0.436 | 0.08 | **Live** |
| USDCHF | SELL | 0.365 | 0.608 | 0.435 | 0.04 | **Live** |
| USDCAD | SELL | 0.341 | — | 0.424 | 0.08 | **Live** (borderline EV) |
| USDJPY | — | — | <0.60 | <0.400 | — | **KILLED** |
| XAUUSD | — | — | — | 0.258 | — | **KILLED** (USDX not enough) |

### 1.2 Execution Bot (`frival/execution_bot/`)

- **Mode:** LIVE (`settings.yaml`: `trading.mode: live`).
- **Risk:** max_daily_loss $50, max 1 position per pair, max 4 total positions, deviation_points=5.
- **Safety:** `confirm_live_orders: true` (manual confirmation each trade). Emergency stop file at `frival/data/emergency_stop.txt`.
- **Shadow:** no pairs in shadow (all live). USDCAD EV is borderline (−0.114R) — monitor closely.

### 1.3 MERG — Macro Event Response Gate

| Component | Status |
|---|---|
| Stage 1 (reaction) | ✅ Trained, leak-free, test ROC 0.721, deployed in shadow |
| Stage 2 (M1 direction) | ❌ Failed (ROC 0.490 = noise). Deleted. |
| H1 event-direction (6h) | ❌ Failed (ROC 0.598, signal = event identity). Not deployed. |
| Runtime wiring | ✅ `macro_event_responder.py` ← `EURUSD_MERG_v2_stage1_Ensemble.joblib` |
| Gate logic | ✅ Undirectional veto: `P(reaction) ≥ 0.60` → BLOCK |
| Calendar lookup | ✅ `get_next_high_event` fixed (was broken: wrong column names) |

MERG is **direction-agnostic** — blocks on reaction confidence alone. Active in shadow mode by default in the daily routine.

---

## 2. Key Files

| File | Purpose |
|---|---|
| `frival/main.py` | CLI orchestrator + `_merg_event_risk_gate()` (undirectional veto) |
| `frival/model/features.py` | `compute_features()` — 90+ H1 features + D1 context + aux (WTI/USDX) + calendar merge. `_merge_aux_symbols()` for USDCAD. |
| `frival/model/ensemble.py` | load_model() + predict() |
| `frival/signal_gate.py` | Threshold → session → cooldown gates |
| `frival/agents/technical.py` | Agent A — GPT-4o technical evaluation |
| `frival/agents/fundamental.py` | Agent B — Perplexity Sonar Pro macro |
| `frival/agents/senior.py` | Synthesize + borderline + 3-strike soft-veto |
| `frival/agents/calendar_context.py` | build_macro_context() + get_next_high_event() (FIXED) |
| `frival/agents/macro_event_responder.py` | MergInference — Stage-1 reaction detector (REWRITTEN) |
| `frival/data/fetcher.py` | fetch_ohlcv() — CSV + MT5. Also saves to training data folder |
| `frival/data/calendar.py` | load_calendar() + PAIR_CURRENCIES (includes XAUUSD, USDCAD) |
| `frival/DAILY_ROUTINE.md` | Step-by-step live execution guide (4 pairs) |
| `frival/execution_bot/*` | Execution bot (watcher + order bot + MT5, LIVE mode) |
| `ml-signal-service/models_bin/` | All model bundles (6 sell + MERG Stage 1 + failed experiments) |
| `ml-signal-service/notebooks/merg/` | MERG Stage 1 + H1-direction experiment notebooks |
| `ml-signal-service/notebooks/xauusd/` | XAUUSD buy/sell/combiner notebooks (with USDX aux features) |
| `ml-signal-service/notebooks/usdcad/` | USDCAD buy/sell/combiner notebooks (with WTI+USDX aux features) |

---

## 3. Daily Routine

**Prerequisites:** MT5 terminal running with EURUSD, GBPUSD, USDCHF, USDCAD, WTI, USDX in Market Watch.

```bash
cd "/c/Users/david/OneDrive/Documents/fx-prival/frival"
MERG_ENABLED=true MERG_SHADOW_ONLY=true \
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe -u -c \
  "import sys; sys.path.insert(0, '.'); from main import run_live, execute_pending; run_live(borderline=True, pair='EURUSD'); run_live(borderline=True, pair='GBPUSD'); run_live(borderline=True, pair='USDCHF'); run_live(borderline=True, pair='USDCAD'); execute_pending()"
```

**Schedule:** 8:01, 9:01, 10:01, 11:01 AM Panama (UTC-5) = 13:01–16:01 UTC.

**Execution:** LIVE orders placed in MT5. With `confirm_live_orders: true`, each trade requires manual confirmation. After comfort, set to `false` for full automation.

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
- **USDCAD EV borderline:** −0.114R is close to zero but still negative. Monitor closely in live mode; be ready to revert to shadow if EV doesn't improve.

### P2
- **Calendar reload per call:** `get_next_high_event()` reloads all 20 CSVs each time.
- **Gold real-yields missing:** XAUUSD killed because only USDX was added (no TIPS/VIX).

---

## 9. Environment

- **Python:** `C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe` (conda `deaf_agent`)
- **Key packages:** pandas, numpy, scikit-learn 1.5.2, xgboost, lightgbm, joblib, MetaTrader5, openai, openpyxl, yaml
- **MT5:** Account 81486396, Server FPMarketsSC-Live, LIVE mode active ($1,000)
- **API keys:** OpenRouter + Perplexity in `frival/config/.env` (gitignored)
- **Model storage:** `.joblib` files under `ml-signal-service/models_bin/`

---

*End of state.*