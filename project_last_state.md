# Project Last State — Frival Trading System

**Last updated:** 2026-09-15T20:50-05:00
**Status:** LIVE — 5-pair ML pipeline (4 SELL + 1 agnostic in shadow) + **NEW standalone rule-based Gold Engine (XAUUSD) LIVE** since 2026-09-15 20:40 UTC. Single account 81486396 (~$536–550 balance). Daily scheduler operational (`run_daily.bat`). Gold engine operational (`run_gold_rules.bat`) — Step 11 of EXP-2026-03-RULEENGINE in progress (first live trade pending), Step 12 (20–30 trade review) pending.

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
| XAUUSD (ML) | — | — | — | 0.258 / 0.346 | — | **KILLED** — superseded by rule-based Gold Engine (§10) |

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
- **Risk:** max_daily_loss $200 (raised 50→200 on 2026-09-15 per operator request; **flagged as 37.6% of the current ~$536 balance** — see §10.9), max 1 position per pair, max 5 total positions, deviation_points=5.
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

## 6. XAUUSD — ML Attempted & Killed → Superseded by Rule Engine

USDX was insufficient for gold. The model **did select** USDX features (ranked #4–6 in the noise-vote), but test precision stayed at 0.258 — below breakeven. Gold is primarily driven by **real yields** (TIPS 10Y), not the dollar index alone.

**Final ML retrain (2026-09-15, `xauusd_sell_macro_improved.ipynb`):** added FRED TIPS (`DFII10`) + VIX (`VIXCLS`) via `ml-signal-service/scripts/fetch_fred.py` → `ml-signal-service/data/macro/tips10y_daily.csv`, `vix_daily.csv`. Sealed test precision 0.346 < 0.400 breakeven, EV −0.135R, 71% of signals clustered in Jan 2026 (regime capture, not edge). **XAUUSD ML killed a third time.**

**Decision (2026-09-15):** gold moves to a **100% rule-based, deterministic engine** — no ML, no agents. See §10 (EXP-2026-03-RULEENGINE).

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
- **ML `max_daily_loss: 200.0` is ~37.6% of the current ~$536 balance** (was ~6% at $3,287). See §10.9 — recommendation to lower to $50 pending operator decision.
- **Gold engine Step 11 (first live trade) + Step 12 (20–30 trade review):** pending; see §10.6–§10.8.

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

### XAUUSD — path to viability (superseded 2026-09-15)
- ML path (TIPS/VIX retrain) FAILED a third time — test precision 0.346, regime capture. **ML gold is dead.**
- The rules path is now the answer: **the rule-based Gold Engine (EXP-2026-03-RULEENGINE) went LIVE 2026-09-15** — it operationalizes exactly what the manual experiment proved (multi-timeframe structure, break-and-retest, candle-close discipline) as a fully deterministic engine with no LLM in the loop (§10).

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

## 10. Gold Rules Engine — EXP-2026-03-RULEENGINE (NEW — LIVE 2026-09-15)

### 10.1 What this is

A **standalone, 100% rule-based XAUUSD trading engine** — **no ML, no AI agents** in the decision loop. Built because gold ML failed three times (USDX; TIPS+VIX; regime capture) while the manual experiment's *rules* appeared to have edge but were drowned out by reckless sizing (0.55 lots → margin calls, near-blowup). The engine isolates two claims:

- **Claim A** — the structural rules (candle-close discipline, break-and-retest, break-even-50%, structural SL) produce positive expected value.
- **Claim B** — the same edge exists at 0.01 lots with strict caps.

Runs **alongside** `run_daily.bat` (ML pipeline) on the same MT5 account/terminal, but as a separate process, separate symbol, separate cadence (M15 vs H1), and its own risk book.

### 10.2 Design contract

`ml-signal-service/docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md` — **v1.3**. The audit contract: every rule, parameter, and decision is specified there and must be changed only with a logged reason. Key operator decisions folded into v1.2/v1.3:

1. **No shadow run** — went straight to LIVE (operator decision 2026-09-15).
2. **$500-scale risk capital** — realized as the single existing account 81486396, balance $531.78 at pre-flight (observed $536–550 during operation; the "$500" is this account, not a new one).
3. **Independent systems** — true only at process level: separate processes/symbols/cadences, but **shared account equity** and the ML bot's account-wide daily-loss check will still see gold losses (§2.4.3, §9 of the design doc).
4. **Pre-flight verified live** (read-only, 2026-09-15): XAUUSD contract size **100.0 oz/lot ✓**, digits 2 ✓, point 0.01 ✓, volume_min 0.01 ✓, 0.01-lot margin ≈ **$8.60** ✓, spread ~19 pts ($0.19).

### 10.3 How it trades — the playbook (v1 atomics)

| Component | Definition |
|---|---|
| Timeframes | M15 decision / M30 structural levels / H1 bias |
| H1 bias (§2.1.1) | EMA(20) vs EMA(50) + price position → BULLISH/BEARISH/FLAT; only bias-consistent direction armed (S4.1) |
| Structural levels (§2.1.2) | 5-bar M30 fractal (wing=2, confirmed 2 bars after pivot), 200-bar lookback, merge within 0.5×ATR, consumption on solid-body close beyond level, nearest-only arming |
| Entry | **Break-and-retest, market order at retest confirmation** (variant B or R). No pending orders. |
| Golden rules (§2.3) | G1 no action on open M15; G2 a wick is not a signal (next close must break the confirm-candle extreme); G3 never anticipate |
| Gates (§2.4) | G1 location ≤ 15% ATR_M15 (floor $1); G2 R:R ≥ 1.5; G3 risk: **0.01 lot, ≤ $25/trade, ≤ 1 position (all XAUUSD positions), −$50/day (comment-tagged)** |
| SL (§2.7.1) | invalidation level + buffer `max(0.05×ATR_M15, $0.30)` — hard SL never sits exactly at invalidation |
| Management (§2.6) | M1 BE-50 (SL→entry at 50% of entry→TP1), M2 structural trail after BE, M3 TP1 broker-side / TP2 informational, M4 no averaging |
| Exit (§2.7) | any M15/M30 solid-body close beyond invalidation → close immediately |

### 10.4 Files & architecture

```
frival/
├── run_gold_rules.bat               # DOUBLE-CLICK TO RUN (live engine; leave window open)
└── gold_rules/
    ├── run_gold_rules.py            # main loop: MT5 wiring, journal, state, resilience, login guard
    ├── engine.py                    # state machine WATCH→WAIT_CANDLE_CLOSE→CONFIRMED→ENTRY_READY→IN_TRADE→DONE/INVALIDATED
    ├── bias.py                      # H1 EMA(20/50) bias — pure function
    ├── levels.py                    # M30 fractal detection, merge, consumption, watch-select, TP/SL helpers
    ├── config.yaml                  # all v1 atomics (§3.3.1 schema)
    ├── config/
    │   ├── credentials.env          # account 81486396 + MT5_TERMINAL_PATH (explicit)
    │   └── settings.yaml            # ConfigManager mirror (live mode)
    ├── state/engine_state.json      # §6.4 persistence — engine resumes after restarts
    └── journal/YYYY-MM-DD.jsonl     # §6.1 journal — every M15 evaluation, one line
```

Reused from the existing execution bot (`frival/execution_bot/`): `MT5Connector`, `ConfigManager` (`is_demo_mode()` already fixed to honor `settings.yaml`), `OrderManager.execute_order()` (called with `dynamic_sizing=False` + `comment="GOLD_RULES_v1"` so the 0.01 lot cannot be silently rescaled) and `close_position()`. The blocking `monitor_break_even()` poller is **not** reused — the gold engine does its own non-blocking per-cycle BE/trail/invalidation via `TRADE_ACTION_SLTP`.

### 10.5 Operational runbook (what the user does)

1. Keep the PC awake (disable sleep/hibernate) and the FPMarkets MT5 terminal running.
2. Double-click `frival\run_gold_rules.bat`.
3. Verify in the console: `connected account 81486396 balance …` and `entering loop`.
4. Leave the window open. It runs ~24h/day while gold is tradable, idles through the daily maintenance halt and weekends (§3.6), and re-evaluates every 60s on the latest completed M15 close.
5. On PC/terminal restart: restart MT5, re-double-click the `.bat`. State resumes from `engine_state.json`; an open trade is always protected by broker-side SL/TP.
6. **Manual XAUUSD trading is NOT allowed while the engine runs** (§1.4) — it contaminates the experiment and the 1-position gate.

### 10.6 Deployment state (2026-09-15)

- Roadmap steps 0–10: **complete** (skeleton, pre-flight, bias, levels, state machine, gates, entry, management, journaling/persistence/resilience, launcher).
- **Step 11 (LIVE directly): in progress** — engine is running live since ~20:40 UTC 2026-09-15. Completes when the **first live order** fires with a confirmed ticket + journal entry + correctly buffered SL.
- **Step 12 (review): pending** — acceptance review after 20–30 live trades.

### 10.7 Verification evidence

- **25/25 unit tests** (`frival/gold_rules/tests/`): bias orientation, fractal detection (5-bar + confirmation), consumption (wick ≠ break), directional watch selection, nearest-only arming, full Variant-B SELL→ENTRY lifecycle, gates (wide-SL rejection), BE-50, structural trail, invalidation close, external-position-close → DONE, bias-flip voiding, daily-loss gate.
- **Real-data sanity walk** (`tests/sanity_walk.py`): 900 live XAUUSD M15 bars → 1 gated ENTRY (R:R 3.6, $0.83 risk), zero ERROR actions.
- **Live cycle check:** one connected live cycle returned `ok`; engine correctly held WATCH_ZONE + BEARISH + resistance 4310.60, wrote journal + state, sent **zero orders** (correct).
- **Three real bugs found & fixed during build:** (1) bias-flip guard compared the value against itself; (2) break events were lost because re-arming ran before edge detection (would have starved the engine of entries); (3) `dec.action` was never set to `ENTRY` on the order decision (journal would never have seen it).
- **Fourth gap found & fixed (2026-09-15, §3.6):** `is_market_open()` returns `True` during the FPMarkets daily gold halt because `trade_mode` stays `4 (FULL)` — the heartbeat kept printing through a market closure. Fixed via **bar freshness**: if no new closed M15 bar appears for ~20 min, the engine reports `MARKET PAUSED (daily halt/weekend)` and idles, resuming automatically on the first new bar. Handles the daily halt, weekends, and holidays uniformly; supersedes the fixed-UTC-window design. **Console visibility added:** heartbeat on every new M15 bar + 10-min keep-alive with paused state + loud prints on ENTRY/BE/TRAIL/INVALIDATE/CLOSE + `gold_rules/status.py` status reporter.

### 10.8 Acceptance criteria (design doc §7)

- **PASS A (rules have edge):** ≥ 30 live trades with win-rate × R:R ≥ 1.
- **PASS B (edge at sane risk):** ≥ 20 trades, per-trade risk never > $25, no margin call.
- **FAIL→rebuild:** F1 < 15 trades in 4 weeks; F2 negative realized EV after 30 trades; F3 any margin call.
- **ABORT:** margin call, account drop > $150/day, or a §1.4 manual-trading contamination flag persisting across >1 session.

### 10.9 Known couplings & open flags (operator decisions pending)

1. **`max_daily_loss: 200.0` in `frival/execution_bot/config/settings.yaml`** — calibrated for the old ~$3,287 balance (~6%); on the current ~$536 balance it is **~37.6%/day** for the ML pipeline alone. Gold + ML worst case ≈ 47% of equity in one day. **Recommendation: lower to ~$50 (~9.4%). NOT changed without explicit operator approval.**
2. **Account-wide daily-loss check in the ML pipeline** (§2.4.3 of design doc): gold losses will still throttle ML pipeline trades on the same account (observed 2026-09-10 with manual gold losses: `daily loss limit: $-152.12`).
3. **Balance fluctuation:** pre-flight $531.78 → $550.02 → $536.36 across sessions (ML pipeline trades). The engine's own caps are dollar-based, so this is absorbed; the $50/day cap is ~9% of current equity.
4. **Three MT5 terminals on this machine** (FPMarkets, FXChoice, RoboForex) — the gold engine pins the FPMarkets path explicitly and has a **login-mismatch guard (R4)**: refuses to trade if the connected account ≠ configured `MT5_LOGIN`.

### 10.10 Key references

- **Design doc:** `ml-signal-service/docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md` (v1.3, audit contract)
- **Source evidence:** `ml-signal-service/notebooks/xauusd/xauusd-manual-trading.md` (9,455-line manual experiment transcript; §10 references cite this as "tu manual" via section numbers that live in the operator's external manual)
- **Killed gold ML:** `ml-signal-service/notebooks/xauusd/xauusd_sell_macro_improved.ipynb` (TIPS+VIX retrain, precision 0.346)
- **Engine code:** `frival/gold_rules/` (see §10.4)
- **Launcher:** `frival/run_gold_rules.bat`

---

## 11. Environment

- **Python:** `C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe` (conda `deaf_agent`)
- **Key packages:** pandas, numpy, scikit-learn 1.5.2, xgboost, lightgbm, joblib, MetaTrader5, openai, openpyxl, yaml
- **MT5:** Account 81486396, Server FPMarketsSC-Live, LIVE mode active (~$536 balance as of 2026-09-15 20:40 UTC — was $3,287 on 09-09; funds moved to a $500-scale risk envelope per operator decision)
- **MT5 terminal:** `C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe` (the only one the gold engine uses; FXChoice and RoboForex terminals also exist on this machine — three total)
- **API keys:** OpenRouter + Perplexity in `frival/config/.env` (gitignored)
- **Model storage:** `.joblib` files under `ml-signal-service/models_bin/`

---

*End of state.*