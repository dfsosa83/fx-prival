# Frival Trading System — Project Context

**Purpose:** One file to let a fresh chat understand the whole system, its current state, what was recently done, and what's next — without reconstructing from `project_last_state.md` (which is the detailed historical record) or the conversation logs.

**Last updated:** 2026-09-18 (19:55 local / 00:55 UTC)
**Authoritative detail:** `project_last_state.md`, `frival/DAILY_ROUTINE.md`, the gold design doc, and the Q4 roadmap — links at the end.

---

## 1. One-paragraph summary

We run **three trading/research systems** on a single FPMarkets account (currently **DEMO / paper**, account `7409623`, $5,000):

1. **FX ML pipeline** (`run_daily.bat`) — 4 SELL-direction pairs (EURUSD, GBPUSD, USDCHF, USDCAD) + 1 direction-agnostic shadow (EURUSD_AGNOSTIC). ML ensemble → gates (threshold, session, cooldown, MERG, candle-close) → dual-LLM agents → JSONL → execution bot.
2. **Gold rules engine** (`run_gold_rules.bat`) — deterministic, no-ML, no-LLM engine for XAUUSD (Claims A/B level-test + Claim C breakout variant).
3. **Research dashboard** (`start_dashboard.bat`) — read-only book-visibility UI (positions, gross/net, per-currency USD exposure, engine health) built on FastAPI + React + Docker/cloudflared, following the operator's bond-dashboard pattern from a previous project.

Both engines currently run on **FPMarketsSC-Demo (7409623, $5,000 paper)**. The **live account 81486396 is parked**.

---

## 2. System map

```
                    ┌─────────────────────────────────────────────────────────┐
                    │ FPMarkets MT5 terminal (host IPC / one login at a time)│
                    └──────────────┬───────────────────────┬──────────────────┘
                                   │                       │
        ┌──────────────────────────┴──────────┐   ┌────────┴──────────────────────────┐
        │ FX ML pipeline (run_daily.bat)      │   │ Gold rules engine (run_gold_rules)│
        │ - run_daily_scheduler.py            │   │ - run_gold_rules.py  (24/7 loop)  │
        │   hourly :01 in 02:01–16:01 Panama  │   │ - engine.py  state machine        │
        │ - main.py: gates + agents + signals │   │ - bias.py / levels.py (EMA+fract) │
        │ - execution_bot/order_bot.py        │   │ - journal/ .. state/ …            │
        │ - signal_gate.py (threshold/session/│   └────────────────────────────────────┘
        │   cooldown/candle-close)            │
        └──────────────────────────────────────┘
                                   │
        ┌──────────────────────────┴──────────────────────────────┐
        │ Research dashboard (start_dashboard.bat)                │
        │ - FastAPI backend :8000 (read-only)                     │
        │ - React frontend :3000 (Vite)                           │
        │ - exposure lens: per-currency USD factor exposure       │
        │ - journals/state/MT5 account read-only                  │
        └─────────────────────────────────────────────────────────┘
```

**Ports:** `8000` backend · `3000` frontend · `80` nginx (docker) · cloudflared tunnel used for public exposure.

---

## 3. Current state (2026-09-18)

| Area | State |
|---|---|
| MT5 account | **DEMO** FPMarketsSC-Demo 7409623, $5,000. Live 81486396 **parked**. Same terminal binary; one login at a time. Demo password == live password. |
| FX pipeline | Running (paper). 4 SELL pairs + AGNOSTIC shadow. **No cash PnL meaningful yet** (flat book, ~0 meaningful trades). |
| Gold engine | Running (paper). **0 trades** since inception — WATCH_ZONE/BULLISH, no setups completing. Claims A/B/C still unmeasured. |
| Dashboard | Running, read-only. Shows account, exposure, gold state, engine health. **One known-fixed display bug:** deposit was counted as "today PnL" until 2026-09-18; fixed (filters DEAL_TYPE_BALANCE). |
| Repo | `main@ffa344d` (latest push). All fixes committed. |
| Environment | conda `deaf_agent` python, FPMarkets terminal path pinned in multiple places. |

### Known open issues / flags (operator decisions pending)
- `max_daily_loss: 200.0` in execution-bot settings (was set for $3.2k live; on ~$500 equity ≈ 37–40% — **recommendation to lower to ~$50 pending operator approval**).
- Gold / FX are in **demo** to gather clean paper evidence before any live decision.
- The FX ML book has near-zero live trade count; only gold manual experiment gave what data exists.

---

## 4. The ML training methodology (baseline — approved)

- **Labels (BUY and SELL):** TP-hitting "triple-barrier-like" label. In both
  `notebooks/eurusd/eurusd_buy_improved.ipynb` and `eurusd_sell_improved.ipynb`:
  - `FORWARD_BARS = 6` (H1 bars), `TP = ATR(14) × 1.5`, `SL = ATR(14) × 1.0`,
  - label = 1 if TP touched first within window; 0 otherwise; ambiguous same-bar → NaN (excluded).
  - Breakeven precision = `SL/(TP+SL) = 1.0/2.5 = 40%` — every threshold in the project is measured against this 40% bar.
- **Temporal split:** train 2020-06→2025-06, val 2025-07→2025-12, test 2026-01→present.
- **Features:** 90+ H1 indicators in `frival/model/features.py`; `AGNOSTIC_FEATURES` 62.
- **Models:** ensemble (XGBoost + LightGBM etc) via `frival/model/ensemble.py`. Thresholds tuned per pair; precision at threshold vs 0.40 breakeven.
- **Agnostic model:** predicts which side of a symmetric R=1.0 envelope is hit first; direction resolved `P(up)>0.5 → BUY else SELL`. ROC-AUC 0.619. Currently shadow.

This is the **default foundation** — do not propose replacing it unless a material flaw is found (per the roadmap).

---

## 5. Dashboard details (Stage 1 complete)

- **Backend** `frival/dashboard/backend/portfolio.py`:
  - `get_mt5_snapshot()`: read-only account+positions+deals (filters deposits/withdrawals, only BUY/SELL deal types count toward PnL).
  - `compute_exposure()`: gross/net + per-currency factor exposure (base currency +1 / quote −1 × sign × volume).
  - `build_book()`: assembled snapshot for `/api/book`.
- **Endpoints:** `/api/book`, `/api/exposure`, `/api/gold`, `/api/gold/journal`, `/api/fx/signals`, `/api/health/engines`.
- **Frontend** `frontend/src/App.jsx`: panels for book overview, currency exposure bars, gold engine, engine health, open positions table. Vite build, React 18, Recharts.
- **Tests** `dashboard/tests/test_portfolio.py` (7 passing) pin the exposure signature semantics (e.g., SELL EURUSD = short EUR/long USD; SELL USDCAD = short USD because USD is base; four SELLs net +0.04 USD).
- **Start:** `frival/start_dashboard.bat` (starts backend :8000 + frontend :3000 + opens browser).
- **Public:** `cloudflared.exe tunnel --url http://localhost:80` (or :3000).

---

## 6. Roadmap & next steps (ROADMAP-2026-Q4-RESEARCH.md)

**Approved baseline, three additive corrections:**
- **Pre-registration / multiple-testing control** (per-experiment manifest records primary metric + variants tried; fresh confirmation window before declaring "go").
- **Bootstrap 95% CI on EV/R** for every backtest output.
- **Cost model** — the live Standard account pays hidden spread (no commission line); measured 2026-09-18: EURUSD 1.2 pips, GBPUSD 1.6, USDCHF 1.5, USDCAD 1.5, USDJPY 1.3, XAUUSD ~0.28 "gold-pips". Apply per-pair `round_trip_cost_pips` in backtests AND in a cost-adjusted label.

**Prioritized backlog:**
- **P0:** cost-adjusted label (EURUSD SELL first) — label=1 only when TP clears barrier + spread. Same model, same split; directly tests "profitable after costs."
- **P1:** liquid-cross book (EURGBP, GBPJPY, EURJPY) for diversification; single equity-index ML experiment (NAS100/US30) on a separate demo account.
- **P2:** regime conditioning (falsification only), commodity/crypto extension.

**Explicitly excluded (impractical/overfit):** EM/exotic FX pairs, multi-stock stat-arb via MT5 CFD, crypto HFT/arbitrage.

---

## 7. Session history & useful references

- **This session (2026-09-15→18):** built/validated the gold rules engine, wrote EXP-2026-03 spec (+Claim C), added FX scheduler dynamic window, fixed multiple crashes (MT5 IPC / native-kill / deposit-as-PnL), wrote EXP-2026-04 FX-backtest spec (all negative EV/R), built the book dashboard, wrote Q4-2026 research roadmap.
- **Prior background (from session-ses_056e.md):** FRX ML build, agnostic model, MERG gate, agent prompts, scheduler, candle-close gate, break-even monitor; the manual XAUUSD experiment (Sep 4-9).

**Key files:**
```
frival/main.py                     → pipeline orchestrator + gates + AGNOSTIC direction
frival/model/features.py           → 90+ H1 features, AGNOSTIC_FEATURES, aux (WTI/USDX)
frival/model/ensemble.py           → load/predict
frival/signal_gate.py              → threshold/session/cooldown/candle-close
frival/run_daily.bat               → scheduler launcher (FX)
frival/run_gold_rules.bat          → gold engine launcher
frival/start_dashboard.bat         → dashboard launcher
frival/gold_rules/…                → engine, bias, levels, journal, state
frival/dashboard/…                 → backend, frontend, tests
ml-signal-service/docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md   → gold contract
ml-signal-service/docs/experiments/EXP-2026-04-RULEENGINE-FX-BACKTEST.md               → FX transfer study (closed result)
ml-signal-service/docs/experiments/ROADMAPS/ROADMAP-2026-Q4-RESEARCH.md                → research roadmap
ml-signal-service/notebooks/eurusd/eurusd_buy_improved.ipynb / eurusd_sell_improved.ipynb → label defs
ml-signal-service/notebooks/xauusd/xauusd-manual-trading.md → manual experiment evidence base
project_last_state.md → long-form history
frival/DAILY_ROUTINE.md → daily operational commands
```

---

## 8. Environment & credentials (operational)

- **Python:** `C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe`
- **MT5 terminal:** `C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe` (three terminals exist on machine; only FPMarkets used)
- **Acounts:** 
  - Demo: `7409623` / FPMarketsSC-Demo / $5,000
  - Live (parked): `81486396` / FPMarketsSC-Live
- **Credentials files (gitignored):**
  - `frival/config/.env` (FX), `frival/execution_bot/config/credentials.env`, `frival/gold_rules/config/credentials.env`
- **API keys:** OpenRouter + Perplexity in `frival/config/.env`
- **Models:** `ml-signal-service/models_bin/*.joblib`
- **Breakeven target:** 40% precision (from 1.5R label).
- **Node:** v22 (frontend build uses Vite); **Docker** present for dashboard/nginx.

---

*End of context. If more detail is needed, read `project_last_state.md` (long form) or the linked docs.*