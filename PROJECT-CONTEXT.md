# Frival Trading System — Project Context

**Purpose:** One file to let a fresh chat understand the whole system, its current state, what was recently done, and what's next — without reconstructing from `project_last_state.md` (which is the detailed historical record) or the conversation logs.

**Last updated:** 2026-09-22 (2026-09)-22 20:15 local
**Authoritative detail:** `project_last_state.md`, `frival/DAILY_ROUTINE.md`, the gold design doc, and:
- Research outcome/next steps → `ml-signal-service/docs/experiments/ROADMAPS/ROADMAP-2026-Q4-SYNTHESIS.md` (quarter capstone: falsification ledger + no-edge map)
- Experiment status → `ml-signal-service/experiments/EXP-2026-05…-14/` (manifest-first, one folder per experiment)
- Portfolio feasibility plan → `ml-signal-service/docs/experiments/ROADMAPS/PORTFOLIO-DEMO-SPEC.md`
- Audit & prioritized next steps → `ml-signal-service/docs/experiments/ROADMAPS/ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md`

---

## 1. One-paragraph summary

We run **three trading/research systems** on a single FPMarkets account (currently **DEMO / paper**, account `7409623`, $5,000):

1. **FX ML pipeline** (`run_daily.bat`) — 4 SELL-direction pairs (EURUSD, GBPUSD, USDCHF, USDCAD) + 1 direction-agnostic shadow (EURUSD_AGNOSTIC). ML ensemble → gates (threshold, session, cooldown, MERG, candle-close) → dual-LLM agents → JSONL → execution bot.
2. **Gold rules engine** (`run_gold_rules.bat`) — deterministic, no-ML, no-LLM engine for XAUUSD (Claims A/B level-test + Claim C breakout variant).
3. **Research dashboard** (`start_dashboard.bat`) — read-only book-visibility UI (positions, gross/net, per-currency USD exposure, engine health) built on FastAPI + React + Docker/cloudflared, following the operator's bond-dashboard pattern from a previous project.

Both engines currently run on **FPMarketsSC-Demo (7409623, $5,000 paper)**. The **live account 81486396 is parked**.

**Research status (2026-09-22):** the Q4 research line is **formally closed — no
edge demonstrated** in the tested families (see §6). The demo systems continue as
**observability/feasibility** (and now record real virtual PnL via the shared
ledger), not as an edge-search portfolio.

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

## 3. Current state (2026-09-22)

| Area | State |
|---|---|
| MT5 account | **DEMO** FPMarketsSC-Demo 7409623, $5,000. Live 81486396 **parked**. Same terminal binary; one login at a time. Demo password == live password. |
| FX pipeline | Running (paper). 4 SELL pairs + AGNOSTIC shadow. **Demo PnL now measurable** post-2026-09-22 fix (virtual-fill ledger, `execution_bot/data/demo_trades_ledger.jsonl`); ~0 meaningful trades still. |
| Gold engine | Running (paper). **Demo PnL loop fixed 2026-09-22** (engine no longer self-closes at `pnl 0`; realized R/$ land in the shared ledger). **0 real trades since inception** — research verdict on gold lines is negative (see §6). |
| Dashboard | Running, read-only. Shows account, exposure, gold state, engine health, Stage-2 per-tag metrics. **2026-09-22 hotfix:** `import sys` added to `portfolio.py` (was raising `NameError: name 'sys' is not defined`). |
| Research program | **Q4 research line formally closed 2026-09-22 — no edge demonstrated** in any tested family (see §6). Demo systems continue as observability/feasibility, not edge-search. |
| Repo | `main@…` — working tree clean of uncommitted work at last save; see §7 for the doc tree. |
| Environment | conda `deaf_agent` python, FPMarkets terminal path pinned in multiple places. |

### Known open issues / flags
- **Research:** no positive edge has been demonstrated (Q4 synthesis §6: formally close the tested families; do not deploy real capital; resume only under a genuinely new mechanism with full pre-registration).
- **Demo PnL:** fixed 2026-09-22 (FX virtual fills + gold lifecycle PnL). The paper book now produces auditable evidence; run ≥ 4-week feasibility window per `PORTFOLIO-DEMO-SPEC.md` if the verified-components portfolio is tested.
- **Cost data:** slippage still 0.0 (unmeasured — needs ~30 real fills); swaps not netted in FX backtests; session-conditioned spreads not modeled. These are conservative (bias against GO), not blocking.
- **A2/A3 isolation accounts:** never provisioned — only needed if a future hypothesis earns a paper GO.
- **`max_daily_loss`:** **RESOLVED 2026-09-21** → `100.0` (2% of $5k demo) in `execution_bot/config/settings.yaml`, `run.py` fallback, README (roadmap §6.2).

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
- **Tests** `dashboard/tests/` (20 passing) pin the exposure signature semantics (e.g., SELL EURUSD = short EUR/long USD; SELL USDCAD = short USD because USD is base; four SELLs net +0.04 USD), plus Stage-2 per-tag metric tests.
- **Start:** `frival/start_dashboard.bat` (starts backend :8000 + frontend :3000 + opens browser).
- **Public:** `cloudflared.exe tunnel --url http://localhost:80` (or :3000).

---

## 6. Research program — outcome & next steps (2026-09-22)

### Outcome: no demonstrated edge in the tested families (formally closed)

The Q4 research line executed **EXP-2026-05 … EXP-2026-14** with manifest-first
pre-registration, block-bootstrap CIs, one-shot sealed scoring, and a GO/HOLD/STOP
gate per experiment. **Result: no statistically robust, net-of-cost, positive edge
was demonstrated in any tested family.**

| Family | Verdict | Key evidence |
|---|---|---|
| EXP-05 EURUSD SELL | HOLD (not GO) | prec 0.387, EV/R −0.03, CI [−0.52,+0.45] |
| EXP-06 EURUSD BUY | STOP | prec 0.355, AUC 0.504, EV/R −0.111 |
| P0.2 cost+CI retrofit | DONE | all 4 backtest pairs flipped to STOP net of cost (~0.4R friction) |
| EXP-07 crosses | ABORTED (economics) | 0.53–0.56R/trade, ~62% breakeven precision |
| EXP-08/09 US30 | STOP, STOP | AUC 0.66→0.69 (skill) but precision 0.33→0.27, EV/R < −0.17 |
| gold manual + rules + exits | net negative / unmeasured / not robust | −$815, PF 0.94; demo loop never traded; exit positives = 3 trades |
| EXP-12 cross-sectional momentum | not supported | net-negative 2025+, effect only in 2022 |
| EXP-13 event-driven | FX null + XAUUSD regime | FX priced-in within 1h; gold effect 2025-only |
| EXP-14 volatility-timing | REJECTED | CALM > VOL but still negative everywhere |

**Conclusion (detailed synthesis):** `ROADMAP-2026-Q4-SYNTHESIS.md` — the
specific no-edge map and why each family failed (costs vs. noise, ranking skill
without tradable precision, regime-only effects). The methodology outcomes (cost
model, block bootstrap, pre-registration, oven audit reflex) are durable assets.

### Next steps (decision-gated)

1. **Demo systems = observability/feasibility, not edge-search.** FX + gold run
   in demo with the new PnL fix; they produce a shared paper ledger
   (`execution_bot/data/demo_trades_ledger.jsonl`).
2. **Optional verified-components portfolio feasibility demo** (`PORTFOLIO-DEMO-SPEC.md`):
   trade rarely (top-conviction, CALM-only), avoid macro-event windows, cost-aware
   asymmetric exits, ≤2 positions, 4-week paper run, hard STOP rule. Pre-registered,
   not a claim of edge.
3. **Future research** may resume only under a genuinely new mechanism (different
   information source / horizon / cost structure), full manifest before code,
   sealed test, robustness checks (remove-top-trades, by-year, regime, cost-stress).
   Do **not** retest the closed families with parameter variations.

**Prohibited as incremental:** more TP/SL/threshold/pair/window variations on the
same families; "just add features/ML" on the same data; treating a high AUC as
deployment evidence; scaling manual gold on its win rate; re-opening crosses for
diversification.

---

## 7. Session history & useful references

- **Q4 research sessions (2026-09-18→22):** executed EXP-2026-05…14; key findings — cost-adjusted labels are structural negatives (Fx + US30), crosses arithmetically dead, gold manual/rules/exits all negative/never-traded, momentum and event-driven flat or regime-only; Q4 synthesis written; demo PnL loop fixed (FX virtual fills + gold lifecycle PnL in a shared ledger, 97 tests green); scheduler day-rollover bug fixed (2026-09-22); `max_daily_loss` resized to $100; dashboard `import sys` hotfix.
- **This session (2026-09-15→18, prior):** built/validated the gold rules engine, wrote EXP-2026-03 spec (+Claim C), added FX scheduler dynamic window, fixed multiple crashes (MT5 IPC / native-kill / deposit-as-PnL), wrote EXP-2026-04 FX-backtest spec, built the book dashboard, wrote Q4-2026 research roadmap.
- **Prior background (from session-ses_056e.md):** FRX ML build, agnostic model, MERG gate, agent prompts, scheduler, candle-close gate, break-even monitor; the manual XAUUSD experiment (Sep 4-9).

**Key files / docs:**
```
frival/main.py                     → pipeline orchestrator + gates + AGNOSTIC direction
frival/model/features.py           → 90+ H1 features, AGNOSTIC_FEATURES, aux (WTI/USDX)
frival/model/ensemble.py           → load/predict
frival/signal_gate.py              → threshold/session/cooldown/candle-close
frival/run_daily.bat               → scheduler launcher (FX)
frival/run_gold_rules.bat          → gold engine launcher
frival/start_dashboard.bat         → dashboard launcher
frival/execution_bot/core/demo_ledger.py          → virtual-fill ledger (demo PnL, 2026-09-22)
frival/execution_bot/data/demo_trades_ledger.jsonl → shared paper ledger (FX + gold)
frival/gold_rules/…                → engine, bias, levels, journal, state
frival/dashboard/…                 → backend (incl. Stage-2 tag metrics), frontend, tests
ml-signal-service/docs/experiments/ROADMAPS/ROADMAP-2026-Q4-SYNTHESIS.md            → quarter capstone (falsification ledger, no-edge map)
ml-signal-service/docs/experiments/ROADMAPS/ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md → audit + prioritized next steps
ml-signal-service/docs/experiments/ROADMAPS/PORTFOLIO-DEMO-SPEC.md                  → verified-components portfolio feasibility plan
ml-signal-service/docs/experiments/ROADMAPS/GOLD-ENGINE-EVIDENCE-PLAN.md            → gold observability plan
ml-signal-service/experiments/EXP-2026-05…-14/   → one manifest-first folder per experiment (manifest + RUN_LOG + reports/)
ml-signal-service/notebooks/eurusd/*.ipynb       → production label defs + cost-label forks
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