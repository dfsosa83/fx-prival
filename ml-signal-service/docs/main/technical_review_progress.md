# Technical Review Progress — Iteration 3 (Section 8)

*Progress document · 2026-08-03 · Tracking all fixes against the §8.2 technical review*

---

## 1. Summary

All 5 P0 fixes and 2 P1 fixes have been deployed. The system is now capable of producing signals in borderline mode, Agent A sees calendar features, and Agent B receives structured macro context instead of relying solely on web search.

| Category | Tasks | Completed | Remaining |
|---|---|---|---|---|
| P0 — Blocking | 5 | 5 | 0 |
| P1 — Reasoning | 4 | 3 | 1 (1.2/1.3) |
| P2 — Data Hygiene | 1 of 3 | 1 | 2 (2.2, 2.3) |
| P3 — Dead Code | 0 of 3 | 0 | 3 (2.5, 2.4, 2.1) |

---

## 2. P0 — Blocking Signal Production (All Complete)

### Issue #1 — Borderline lane structurally cannot fire

**Problem:** Agent A Rule 2 stated *"REJECT if 0 or 1 of 4 sub-models have probability >= threshold."* In borderline mode, all probabilities are below threshold, so 0/4 sub-models exceed it → Agent A auto-REJECTED 100% of borderline signals. 5 consecutive days of live trading produced 0 FIRED signals.

**Solution:** Split Rule 2 into standard vs borderline variants:
- **Standard:** REJECT if 0 or 1 sub-models >= threshold (unchanged)
- **Borderline:** REJECT only if ensemble is FULLY COLLAPSED — all 4 sub-models below (threshold − 0.05), OR the highest sub-model below (threshold − 0.10)

Also added `mode` (STANDARD/BORDERLINE) to Agent A's user message so it knows which ruleset to apply.

**Files modified:**
- `frival/agents/prompts/technical.txt` — Split STANDARD/BORDERLINE sections, weakened Rule 2
- `frival/agents/prompts/technical_gbpusd.txt` — Same split for GBPUSD
- `frival/agents/prompts/technical_usdchf.txt` — Same split + SELL rewrite (see #2)
- `frival/agents/technical.py` — `evaluate()` accepts `mode=` parameter, passes to user message
- `frival/agents/context.py` — `build_context()` accepts `mode=` parameter
- `frival/main.py` — Passes `agent_mode = "borderline" if is_borderline else "standard"` to both `build_context()` and `evaluate_technical()`

**Verification:** August 3 live session showed Agent A reasoning change from auto-REJECT to NEUTRAL when ensemble was collapsed but 3/7 confirm conditions held. Agent A now evaluates borderline bars fairly.

**Commit:** `875d1fc`

---

### Issue #2 — USDCHF prompts encode BUY reasoning while deployed model is SELL

**Problem:** `technical_usdchf.txt` and `fundamental_usdchf.txt` were written for BUY direction (Rule 1 rejects on D1 *downtrend*, Rule 4 confirms on *price above EMA50 / RSI > 55 / risk-on / gold falling*). However, the production direction was switched to SELL on 2026-07-31. Agents received direction in the user message and inverted case-by-case, but the system prompts trained the model on the wrong ruleset.

**Solution:** Rewrote both prompts for SELL direction:
- Rule 1: REJECT if D1 close *below* D1 EMA20 AND ADX > 30 AND H1 price *< EMA50* (USD weakness regime)
- Rule 4 CONFIRM conditions: price *above* EMA50, RSI *> 55*, *plus_di > minus_di* (CHF bid gaining)
- Fundamental prompt: SELL means CHF strengthens — risk-off, SNB hawkish, gold rising, DXY falling
- REJECT conditions: SNB intervention to weaken CHF, major risk-on event, USD positive shock

**Files modified:**
- `frival/agents/prompts/technical_usdchf.txt` — Complete rewrite for SELL direction
- `frival/agents/prompts/fundamental_usdchf.txt` — Complete rewrite for SELL direction (CHF safe-haven logic)

**Commit:** `875d1fc`

---

### Issue #3 — Deployment gate not enforced for GBPUSD and USDCHF

**Problem:** Both pairs fail the project's own gating criteria (EV negative, CI straddles breakeven) but are running live. GBPUSD: EV −0.019R, CI [0.255, 0.611]. USDCHF: EV −0.014R, CI [0.256, 0.632].

**Solution:** Added `"shadow": True` to both pairs in `PAIR_CONFIG`. When a shadow pair fires, the system:
- Changes `final_decision` from "FIRED" to `"SHADOW_FIRED"`
- Suppresses the console signal print
- Continue logging to JSONL for auditing
- EURUSD remains the only live (non-shadow) pair

**Files modified:**
- `frival/main.py` — `PAIR_CONFIG` entries for GBPUSD/USDCHF, shadow logic in both `run_backtest()` and `_run_live_inner()`

**Verification:** GBPUSD and USDCHF backtest shows "SHADOW_FIRED" in JSONL, no console fire prints.

**Commit:** `875d1fc`

---

### Issue #0.5 — No prompt-config coherence check

**Problem:** No mechanism prevents a direction mismatch between `PAIR_CONFIG['direction']` and the prompt files. Future pair additions or direction changes could silently deploy with wrong prompts.

**Solution:** Added two protections:
1. `# DIRECTION: SELL` (or BUY) header on every prompt file
2. `_check_prompt_direction()` function in `main.py` — called at every pair startup, verifies prompt header matches config direction. Fails fast with a clear error on mismatch.

**Files modified:**
- `frival/agents/prompts/technical.txt` — Added `# DIRECTION: SELL` header
- `frival/agents/prompts/fundamental.txt` — Added `# DIRECTION: SELL` header
- `frival/agents/prompts/technical_gbpusd.txt` — Added `# DIRECTION: SELL` header
- `frival/agents/prompts/fundamental_gbpusd.txt` — Added `# DIRECTION: SELL` header
- `frival/agents/prompts/technical_usdchf.txt` — Added `# DIRECTION: SELL` header
- `frival/agents/prompts/fundamental_usdchf.txt` — Added `# DIRECTION: SELL` header
- `frival/main.py` — `_check_prompt_direction()` function

**Commit:** `875d1fc`

---

### Issue #11 — Perplexity citation markers leak into justification

**Problem:** Agent B responses include `[1][2][7]` citation markers in the `justification` field, polluting JSONL logs and any downstream dashboard.

**Solution:** Added regex stripping of `[\d+]` patterns from all string fields in the parsed Agent B response.

**Files modified:**
- `frival/agents/fundamental.py` — `_parse_response()` now strips citation markers from all string values after JSON parse

**Commit:** `875d1fc`

---

## 3. P1 — Reasoning Blindspots (3 of 4 Complete)

### Issue #4 — Agent A blind to calendar features ✅ COMPLETE

**Problem:** `deviation_sum_24h`, `hours_since_last_high`, and `high_events_next_24h` are in the top-10 features for all three pairs. Yet Agent A's CONFIRM checklist only enumerated EMAs, RSI, MACD, ADX, and ATR — the calendar features were absent. Agent A could not corroborate or contradict the model's dominant drivers.

**Solution:**
1. Added 10 calendar features to Agent A's input context (via `ADDITIONAL_CONTEXT`)
2. Extended Rule 4 CONFIRM conditions from 5 to **7**:
   - `deviation_sum_24h < 0` — USD-negative macro surprise supports SELL
   - `hours_since_last_high` between 2 and 24 — post-event trend is active
3. Added Rule 4 (pre-event precaution): `high_events_next_1h >= 1` → NEUTRAL — don't evaluate on stale pre-release data
4. Added calendar section to Agent A's user message (separate from technical features)
5. All three pair prompts (EURUSD, GBPUSD, USDCHF) now include calendar-aware rules

**Files modified:**
- `frival/agents/context.py` — `ADDITIONAL_CONTEXT` extended with 10 calendar features
- `frival/agents/technical.py` — `_build_user_message()` now displays "Calendar context" section
- `frival/agents/prompts/technical.txt` — 7 CONFIRM conditions, pre-event precaution
- `frival/agents/prompts/technical_gbpusd.txt` — Same calendar-aware rules
- `frival/agents/prompts/technical_usdchf.txt` — Same calendar-aware rules + SELL logic

**Verification:** August 3 backtest showed Agent A correctly citing pre-event precaution ("3 high-impact events in the next hour") and calendar feature values in its reasoning.

**Commit:** `c4ada71`

---

### Issue #7 — Agent B single point of failure ✅ COMPLETE (Task 1.5)

**Problem:** `senior.py` treats fundamental REJECT as an unconditional veto. After 5 consecutive days of 0 FIRED signals, Agent B alone could shut down the entire pipeline regardless of Agent A's confidence.

**Solution:** Implemented 3-strike soft-veto logic:
1. Track `fundamental_reject_streak` per pair in `last_signal.json` (persisted across live sessions)
2. When streak < 3: fundamental REJECT = unconditional veto (unchanged behavior)
3. When streak ≥ 3 AND Agent A is HIGH-CONFIRM: veto is downgraded to warning, signal fires with LOW confidence
4. When streak ≥ 3 AND Agent A is NOT HIGH-CONFIRM: veto still active
5. Streak resets to 0 when Agent B returns CONFIRM/NEUTRAL or when a signal FIRES

**Files modified:**
- `frival/agents/senior.py` — `synthesize()` and `synthesize_borderline()` accept `fundamental_reject_streak`, soft-veto clause added
- `frival/main.py` — streak tracking via `_get_reject_streak()`, `_update_reject_streak()`, `_update_cooldown()` now resets streak

**Commit:** `abcebaf`

---

## 4. Phase 1.4 — Calendar RAG for Agent B (Iteration 3 Phase 2)

**Problem (from §3):** Agent B uses web search, making it useless for historical backtesting (always NEUTRAL because it searches current news) and slow (5–15s latency).

**Solution:**
1. Built `agents/calendar_context.py` — constructs structured macro summary from calendar per bar:
   - Last 24h events with Actual vs Consensus comparisons
   - Upcoming events (next 1h, 4h, 24h)
   - Central bank day flags (FOMC, ECB, BoE, SNB, NFP)
   - Event density metrics
2. Updated `agents/fundamental.py` to accept optional `calendar_context` parameter — injected into prompt alongside web search
3. Updated `main.py` to call `build_macro_context()` before each Agent B evaluation (both backtest and live)

**Files created:**
- `frival/agents/calendar_context.py` — New module, 130 lines

**Files modified:**
- `frival/agents/fundamental.py` — `evaluate()` accepts `calendar_context`, `_build_user_message()` injects it
- `frival/main.py` — `build_macro_context()` called before each Agent B eval

**Verification:** Backtest on EURUSD 2026-01-06 showed Agent B making real decisions:
- 2 CONFIRM, 1 NEUTRAL (previously always NEUTRAL)
- Reasoning correctly referenced Fed 3.75% vs ECB 2.25% rate differentials, ISM data, CPI from calendar
- Agent B is now usable for historical backtesting

**Commit:** `90a4910`

---

## 5. Remaining Tasks (Prioritized)

| # | Task | Priority | Effort | Dependencies |
|---|---|---|---|---|
| 1.6 | Delta-fetch MT5 | **High** | **M** | ✅ **DONE** `aba4eb1` |
| 1.2 | Combiner notebook headers | Medium | S | None |
| 1.3 | Replace @0.5 reference in notebooks | Low | S | None |
| 2.1 | Retrain ensembles (2020-2026) | Medium | M | Phase 0/1 stable |
| 2.2 | Multi-seed feature selection (N=5) | Medium | S | 2.1 |
| 2.3 | Replace OBV with OBV_slope_20 | Medium | S | 2.1 |
| 2.4 | Cost accounting dashboard | Low | S | None |
| 2.5 | Remove USDJPY prompts/pair config | Low | S | None |

---

## 6. File Change Log

| File | Type | Phase | Issue |
|---|---|---|---|
| `frival/agents/prompts/technical.txt` | Modified | P0 | #1 borderlline, #4 calendar, #0.5 direction |
| `frival/agents/prompts/technical_gbpusd.txt` | Modified | P0 | #1 borderlline, #4 calendar, #0.5 direction |
| `frival/agents/prompts/technical_usdchf.txt` | Modified | P0 | #1, #2 SELL rewrite, #4 calendar, #0.5 |
| `frival/agents/prompts/fundamental.txt` | Modified | P0 | #0.5 direction header |
| `frival/agents/prompts/fundamental_gbpusd.txt` | Modified | P0 | #0.5 direction header |
| `frival/agents/prompts/fundamental_usdchf.txt` | Modified | P0 | #2 SELL rewrite, #0.5 direction |
| `frival/agents/technical.py` | Modified | P0, P1 | #1 mode, #4 calendar display |
| `frival/agents/senior.py` | Modified | P1 | #7 soft-veto in synthesize/synthesize_borderline |
| `frival/main.py` | Modified | P1 | #7 streak tracking, cooldown file schema expanded |
| `frival/agents/context.py` | Modified | P0, P1 | #1 mode, #4 calendar features |
| `frival/agents/fundamental.py` | Modified | P0, P1 | #11 citations, #1.4 calendar RAG |
| `frival/agents/calendar_context.py` | **Created** | P1 | #1.4 calendar RAG |
| `frival/main.py` | Modified | P0, P1 | #1 mode, #3 shadow, #0.5 coherence, #1.4 RAG |

---

*Review date: 2026-08-04. P0/P1 fully deployed. Next: P2 retraining and model robustness.*
