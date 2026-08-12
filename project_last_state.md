# Project Last State — Frival Trading System

**Last updated:** 2026-08-12T14:35-05:00
**Status:** Live (DEMO mode). 3-pair pipeline operational. Execution bot integrated with defense-in-depth hardening.

---

## 1. What We Built

### 1.1 Frival Signal Pipeline (`frival/`)

**Purpose:** Agentic H1 signal system. ML ensemble → gates → dual-agent validation → JSONL output.

**Supported pairs (v3):**

| Pair | Direction | Threshold | Features | ROC-AUC | Test Precision | Lot Size | Status |
|---|---|---|---|---|---|---|---|
| EURUSD | SELL | 0.333 | 25 (3 calendar) | 0.674 | 0.411 | 0.08 | **Core** |
| GBPUSD | SELL | 0.381 | 15 (2 calendar) | 0.673 | 0.436 | 0.08 | **Monitoring** |
| USDCHF | SELL | 0.365 | 22 (2 calendar) | 0.608 | 0.435 | 0.04 | **Experimental** |
| USDJPY | — | — | — | <0.60 | <0.400 | — | **KILLED** |

### 1.2 Execution Bot (`frival/execution_bot/`)

**Purpose:** Monitors Frival JSONL output and auto-executes FIRED signals via MT5.

**Architecture:**
```
signal_watcher.py → polls output/signals/ for FIRED signals
      ↓
order_bot.py      → risk gates (shadow, PnL, duplicate position, margin)
      ↓
core/order_manager.py → MT5 order_send (DEMO or LIVE)
core/mt5_connector.py → MT5 terminal connection
core/config_manager.py → settings/credentials loader
```

**Defense layers (post-audit hardening):**
1. `read_new_signals()` — 24h recency filter, zero-entry skip, signal_id dedup
2. `validate_signal()` — trade block existence, required fields, expiry check
3. `handle_signal()` — zero-level rejection gate (F2 fix)
4. Gate 1: shadow pair check
5. Gate 2: daily PnL limit ($50)
6. Gate 3: duplicate position check
7. Gate 4: margin check
8. Execution result: ticket invariant enforcement (F3 fix)

**State tracking:** `watcher_state.json` persists `last_signal_id` and `signals_processed` across restarts.

### 1.3 Integration Bridge

`main.py::execute_pending()` — runs execution bot in `--once` mode after signal generation. Single command runs all 3 pairs + auto-execution.

---

## 2. Key Files

| File | Lines | Purpose |
|---|---|---|
| `frival/main.py` | 765 | CLI orchestrator (backtest + live + --all --execute) |
| `frival/model/features.py` | ~310 | compute_features() — 80+ features + calendar merge |
| `frival/model/ensemble.py` | 126 | load_model() + predict() |
| `frival/signal_gate.py` | 159 | Threshold → session → cooldown gates |
| `frival/agents/technical.py` | 130 | Agent A — GPT-4o technical evaluation |
| `frival/agents/fundamental.py` | 156 | Agent B — Perplexity Sonar Pro macro |
| `frival/agents/senior.py` | 145 | Synthesize + borderline + 3-strike soft-veto |
| `frival/agents/calendar_context.py` | 138 | Macro text context + RAG |
| `frival/agents/context.py` | 72 | Agent input builder |
| `frival/data/fetcher.py` | 171 | fetch_ohlcv() — CSV + MT5 |
| `frival/data/calendar.py` | 200+ | Load + compute calendar features from 20-year CSVs |
| `frival/output_writer.py` | 76 | JSONL signal log + JSON reports |
| `frival/live_logger.py` | 73 | Tee terminal output to daily log files |
| `frival/DAILY_ROUTINE.md` | 106 | Step-by-step live execution guide |
| `frival/execution_bot/run.py` | 155 | Entry point (--once + watch_loop) |
| `frival/execution_bot/signal_watcher.py` | 200 | JSONL polling + validation + dedup |
| `frival/execution_bot/order_bot.py` | 250 | Risk gates + OrderManager integration |
| `frival/execution_bot/core/order_manager.py` | 820 | Order preparation + MT5 send |
| `frival/execution_bot/core/mt5_connector.py` | 300+ | MT5 terminal connection wrapper |
| `frival/execution_bot/config/settings.yaml` | 50 | Pair config, risk controls |
| `ml-signal-service/models_bin/` | 11 files | All model bundles (Git LFS tracked) |
| `ml-signal-service/notebooks/` | 9+ files | Per-pair training notebooks (v3 with calendar + OBV) |

---

## 3. Daily Routine

**Prerequisites:** MT5 terminal running with EURUSD, GBPUSD, USDCHF in Market Watch.

```bash
cd "/c/Users/david/OneDrive/Documents/fx-prival/frival"
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe -u -c \
  "import sys; sys.path.insert(0, '.'); from main import run_live, execute_pending; run_live(borderline=True, pair='EURUSD'); run_live(borderline=True, pair='GBPUSD'); run_live(borderline=True, pair='USDCHF'); execute_pending()"
```

**Schedule:** 8:01, 9:01, 10:01, 11:01 AM Panama (UTC-5) = 13:01–16:01 UTC.

**What happens:**
1. All 3 pairs run sequentially (~15-20s each)
2. If any signal fires (p ≥ threshold and agents confirm), JSONL written to `output/signals/`
3. `execute_pending()` starts execution bot, processes pending FIRED signals, places MT5 orders
4. If no signals fire (SHELVED/BLOCKED), bot reports `0 executed, 0 rejected`

---

## 4. Live Status (Aug 12, 2026)

**Account:** 81486396 (FPMarketsSC-Live, Standard, $1,021.52, 1:500)

**Last FIRED signal:** 2026-08-07 15:00 UTC — EURUSD SELL at 1.15722 (p=0.3572). Executed in DEMO mode.

**Since Aug 8:** All signals SHELVED or BLOCKED. Agents are correctly filtering. No new FIRED signals.

**Execution bot state:** `watcher_state.json` tracks last processed signal. Execution log clean.

**Demo mode:** Active (`DEMO_MODE=true`). All orders simulated — no real broker fills.

---

## 5. Completed Fixes (Aug 7-12, 2026)

| Date | Fix | Description |
|---|---|---|
| Aug 7 | Initial build | Execution bot scaffolded from DeafAgent demo_bot |
| Aug 7 | Credential chain | Frival .env → os.environ → ConfigManager (bypassed load_dotenv) |
| Aug 7 | MT5 auto-detect | Empty `MT5_TERMINAL_PATH` — MT5Connector auto-detects terminal |
| Aug 7 | Timezone bug | Naive timestamps parsed as UTC in signal_watcher |
| Aug 7 | 24h filter + zero-entry skip | Stale and old-format signals filtered in read_new_signals |
| Aug 7 | Ticket display | Key name mismatch (order_id → order) fixed |
| Aug 7 | State tracking | --once mode saves watcher state to prevent duplicate execution |
| Aug 8 | --execute integration | execute_pending() added to main.py for single-command pipeline |
| Aug 8 | main() wrapper | Missing def main() restored — squashed -c argparser noise |
| Aug 8 | Git LFS | Model binaries tracked via LFS (345 MB across 11 files) |
| Aug 8 | Unshadowed pairs | GBPUSD/USDCHF shadow: false for demo testing |
| Aug 12 | Audit fixes F1-F4 | validate_signal in --once, zero-level rejection, ticket invariant, signal dedup |

---

## 6. Agent Decision Flow

### Three-Tier System

| Tier | Range | Rule |
|---|---|---|
| **Standard** | p ≥ threshold | Single agent CONFIRM sufficient |
| **Borderline** | 0.20 ≤ p < threshold | BOTH agents must CONFIRM |
| **Blocked** | p < 0.20 | No agent evaluation |

### Senior Synthesis

| Agent A | Agent B | Result |
|---|---|---|
| CONFIRM | CONFIRM | **FIRED** (HIGH confidence) |
| CONFIRM | NEUTRAL | **FIRED** (MODERATE) |
| NEUTRAL | CONFIRM | **FIRED** (MODERATE) |
| REJECT | * | **SHELVED** |
| * | REJECT | **SHELVED** (unconditional veto) |
| NEUTRAL | NEUTRAL | **SHELVED** |

**3-strike soft-veto:** After 3 consecutive Agent B REJECTs, one Agent A HIGH-confidence CONFIRM can override. Resets on any CONFIRM or NEUTRAL from Agent B.

---

## 7. Calendar Feature Pipeline

20-year economic calendar (2007-2026) loaded from `ml-signal-service/data/raw/macro/EconomicCalendarEvents-*.csv`:

- 92,616 EURUSD events, 55,907 GBPUSD, 43,333 USDCHF
- 14 features computed: event counts, deviation sums, CB day flags
- 3 features selected per pair by noise-injection voting
- `deviation_sum_24h` (#1 in EURUSD), `hours_since_last_high`, `high_events_next_24h`
- Agent B receives rich text context via `build_macro_context()` (replaces web search for event-specific data)

---

## 8. Macro Event Response Dataset (Analyzed, Not Yet Integrated)

`ml-signal-service/data/raw/macro/ExportedData.csv` — 3,790 events × 1,773 columns:

- Each row is a macro event with 15-window pre-event technical profile
- 3-bar post-event directional target (U/D/N per bar, 27 classes)
- Recommended: train Macro Event Response Model (MERM) as event risk gate
- Full analysis: `ml-signal-service/docs/main/macro_event_response_eda_report.md`

---

## 9. Known Gaps (from Entry Failure Audit)

### Fixed (P0)
- F1: `validate_signal()` in `--once` mode ✓
- F2: Zero-level rejection in `handle_signal` ✓
- F3: Ticket invariant on success ✓
- F4: Signal batch dedup ✓

### Not Yet Fixed
- **P1:** Shadow config contradiction — comments say shadow, flags say live (GBPUSD/USDCHF)
- **P1:** Timezone key mismatch (`timezone` vs `market_timezone`) → falls back to Asia/Qatar
- **P1:** `deviation_points` never propagated from settings.yaml
- **P1:** Emergency-stop path resolves relative to CWD, not config dir
- **P2:** Weekend/session-hour gate in market-open check
- **P2:** Persisted executed-signal-ids set for cross-restart dedup
- **P2:** Floating PnL in daily-loss gate (only realized PnL currently)
- **P2:** MT5 reconnection logic (only initial connect has retry)

---

## 10. Environment

- **Python:** `C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe` (conda `deaf_agent`)
- **Key packages:** pandas, numpy, scikit-learn 1.5.2, xgboost, lightgbm, joblib 1.3.2, MetaTrader5, openai
- **MT5:** Account 81486396, Server FPMarketsSC-Live, Demo mode active
- **API keys:** OpenRouter (`OPENROUTER_API_KEY`), Perplexity (`PERPLEXITY_API_KEY`) in `frival/config/.env` (gitignored)
- **Model storage:** Git LFS for all `.joblib` files in `ml-signal-service/models_bin/`

---

## 11. Git Info

**Branch:** `main` — up to date with `origin/main`
**Last commit:** `a3dbff5` — defense-in-depth hardening (F1-F4 from entry failure audit)
**LFS:** Active — 345 MB across 11 model files
**Clean working tree:** ✓

---

*End of state.*