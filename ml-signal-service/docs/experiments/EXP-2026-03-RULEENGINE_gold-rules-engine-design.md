# Experiment: Structural Rule Engine — XAUUSD (M15/M30/H1)

**Document ID:** EXP-2026-03-RULEENGINE
**Created:** 2026-09-15
**Status:** DESIGN APPROVED — READY TO IMPLEMENT
**Type:** Standalone experiment. Does NOT use the ML pipeline. Does NOT use AI agents.

## 0. Document Control

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-09-15 | Initial design, approved. |
| v1.1 | 2026-09-15 | **Audit pass.** Closed every ambiguity found by cross-referencing this document against `session-ses_056e.md` (the brainstorming session that produced it), `xauusd-manual-trading.md` (the source evidence), and `project_last_state.md` (the live system this engine runs alongside). Added: formal structural-level detection spec, formal H1-bias definition, SL/invalidation buffer logic, $-risk formula with contract-size verification, position-identification (comment-tag) scheme, manual/automated XAUUSD conflict policy, daily-loss-accounting scope (and its documented coupling limitation with the ML pipeline), gold session/maintenance-break handling, process-resilience requirement, and a corrected WATCH_ZONE rule (single-direction arming per H1 bias, not a "pair of levels"). No parameter in Section 5 changed; this pass adds precision, not new risk.
| v1.2 | 2026-09-15 | **Operator decisions (live-direct).** Per explicit operator instruction: (1) **no shadow run — the experiment goes straight to LIVE** with real risk capital; (2) the gold engine is provisioned against a **$500 live risk-capital account** (separate from the main ~$3,287 account if the separate-account model in §1.3.1 is executed); (3) `run_daily.bat` ML pipeline continues unchanged on its configured window; (4) the two systems are to be independent. §1.1, §1.3/§1.3.1, §4, §7, §8, §9 updated. Risk parameters in §5 are **unchanged**; the $50 daily cap on a $500 account is 10%/day — arithmetic flagged in §1.3.1, accepted by the operator.
| v1.3 | 2026-09-15 | **Pre-flight results (live broker, read-only).** Connected to 81486396/FPMarketsSC-Live: **balance $531.78, equity $531.78, zero open positions** — the "separate account" hypothesis (A1–A5) is **void**; this IS the $500-scale risk-capital account, already funded to target. XAUUSD spec validated against the broker: contract size **100.0 oz/lot ✓**, digits 2 ✓, point 0.01 ✓, volume_min 0.01 ✓, tick value $1 per $1 price move at 1.0 lot ✓, 0.01-lot margin ≈ $8.60 ✓, spread 19 pts ($0.19), trade_mode full. §1.3.1 rewritten to the resolved reality: single account, single terminal, A5 fallback engaged, and the ML-pipeline cross-throttle limitation (§2.4.3, §9) is **live**, not moot. **Flagged observation (operator decision required):** `max_daily_loss: 200.0` in the ML execution bot's `settings.yaml` is ~37.6% of the current $532 balance — untouched in this pass, recorded for review. Roadmap steps 0–1 marked done (≥ 2 of their checks completed via this pre-flight).

This document is the audit contract for the experiment. Any parameter change must be logged in version control with a reason, and any correction to this document's own logic must bump the Document Control table above.

---

## 1. Purpose & Scope

### 1.1 Why this experiment exists

The manual gold trading experiment (2026-09-04 → 09-09) grew the account from ~$1,000 to ~$3,287, but did so with wild lot sizes (as high as 0.55 lots on at least one order — see §1.1.1), repeated margin calls, and a near-blowup on the 0.55-lot trade. We cannot tell from that record whether the *rules* were profitable or the *sizing* was gambling. This experiment separates those two claims:

- **Claim A (rules have edge):** the structural rules — candle-close discipline, break-and-retest, break-even-at-50%, structural SL — produce positive expected value.
- **Claim B (edge exists at sane risk):** the same edge is visible at 0.01 lots with strict risk caps.

If A and B both hold, we scale deliberately. If A fails, no lot size fixes it. If B fails, we stop gold entirely. Acceptance criterion **A** in §7 answers Claim A; acceptance criterion **B** answers Claim B. They are graded independently — see §7.

**Operator decision (2026-09-15): no shadow phase.** The 1-week simulated validation that v1.0/v1.1 contemplated (old §8 step 10) is **removed**. The experiment launches directly into LIVE with real risk capital at 0.01 lots. Rationale recorded: the manual experiment already ran live (with wild sizing); the discipline layer this engine adds (0.01 lot, $25/trade, $50/day, 1 position) is the same set of bounds in either mode, and the cost of skipping the simulation is bounded by the daily loss cap. The consequence is that the Claim-A/B measurement starts with the first live trade, and the statistical caveats that apply to any small live sample (§7) apply from day one — there is no "safe" warm-up streak to look back on. The session-report contamination check (§6.3) and the manual-trading stop rule (§1.4) remain in force; they protect the *measurement*, not the capital.

#### 1.1.1 Provenance of the evidence

`xauusd-manual-trading.md` is a 9,455-line transcript of an LLM (Perplexity/GPT via chat) analyzing live M15/H4 gold screenshots and proposing trades, September 4–9, 2026 (249 trades per the accompanying MT5 HTML report). Inside that transcript, the LLM repeatedly cites section numbers ("Sección 9.1", "Sección 3", "Sección 10", etc.) belonging to **a separate operational manual the user owns** ("tu manual operativo") — that manual itself is *not* a file in this repository; only the LLM's paraphrased citations of it survive in the transcript. The section numbers used throughout this document (S3, S4.1, S5.2, S8.1, S9.1–9.3, S10) are **the transcript's citations of that external manual**, not literal headers inside `xauusd-manual-trading.md`. This is noted so a future auditor searching `xauusd-manual-trading.md` for a "Section 9.1" heading does not conclude the citation is fabricated — the rule text quoted next to each citation (verified against the transcript, e.g. line 65, 192, 2422, 3640) is the actual evidence; the section *numbers* are one level removed.

Two verified verbatim quotes anchoring the two most-cited rules:
- S3 (golden rule): *"Vela M15 abierta → No entras"* / *"Una mecha no es una señal de entrada"* (transcript lines 192, 2422, 2597, 2657).
- S4.1 (trend alignment): *"No operar en contra de la tendencia mayor"* (transcript line 1678).

### 1.2 Explicit non-goals (what this experiment is NOT)

| Non-goal | Why excluded |
|---|---|
| NOT an ML model | The ML pipeline on gold failed three times (USDX, TIPS/VIX, 6H H1). This is rules-based, not probability-based. |
| NOT the existing Frival signal pipeline | Different entry logic (structural levels vs ML probabilities). Different cadence (M15 vs H1). Different risk book. |
| NOT using AI agents | Agents introduced inconsistency, cost, and no measured improvement in the original experiment. All decisions in this engine are deterministic. |
| NOT trading FX pairs | Scope is XAUUSD only, to isolate the gold structural behavior that actually made money. |

### 1.3 System boundary

This experiment runs **alongside** the existing `run_daily.bat` ML pipeline, independently:

- `run_daily.bat` → ML pipeline (EURUSD/GBPUSD/USDCHF/USDCAD/EURUSD_AGNOSTIC) — unchanged.
- `run_gold_rules.bat` (NEW) → this rule engine, XAUUSD only — new process.

Different symbols, different cadence, different processes. **Account model: see §1.3.1 — the operator's stated independence between the two systems is only true, and the $500 risk-capital statement is only meaningful, if the gold engine runs on a separate MT5 account with a separate terminal instance.** §1.3.1 resolves the three-way contradiction between "use the same credentials", "balance will be $500", and "systems independent of each other".

### 1.3.1 Account & provisioning model — **RESOLVED by live pre-flight (2026-09-15)**

The three operator statements made on 2026-09-15 — *(a) use the same credentials as the main project, (b) account balance will be $500 risk capital, (c) the two systems will be independent of each other* — were analyzed in the provisional form below. **The read-only pre-flight (v1.3) then resolved them empirically**: connected to account **81486396 / FPMarketsSC-Live, balance $531.78, equity $531.78, no open positions**. The "separate $500 account" hypothesis (A1–A5 below) is **void** — this account *is* the $500-scale risk capital, already funded at target. Consequences, now fixed in this contract:

| # | Resolved reality | Detail |
|---|---|---|
| R1 | **Single live account, $532** | The gold engine trades the same account `81486396` as the ML pipeline. The $50 daily cap is an *accounting-only* bound for the gold engine (comment-tagged PnL, §2.4.2); it does not isolate PnL from the rest of the account. |
| R2 | **Single terminal instance** | `mt5.initialize(path=…)` with the discovered FPMarkets terminal (`C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe`) — `MT5_TERMINAL_PATH` in `credentials.env` is empty and **must be set** for this engine (and is recommended for the ML pipeline too; the pre-flight only succeeded via path discovery). |
| R3 | **"Independence" is process-level only** | Separate processes, separate cadence, separate symbols — but **shared equity and a shared data-only daily-loss visibility**: the ML pipeline's daily-loss check is account-wide (§2.4.3) and will see this engine's losses. Cross-throttle risk is **LIVE**, documented in §2.4.3/§9. |
| R4 | **Wrong-account guard kept** | Still enforced: the engine compares the connected login against the configured `MT5_LOGIN` at startup and every reconnect, refusing to trade on mismatch. Cheap insurance on a machine with three MT5 terminals installed (FPMarkets, FXChoice, RoboForex all discovered). |
| R5 | **Cash buffer check** | On a $532 balance, the $25/trade and $50/day atomics are 4.7% and 9.4% of equity respectively. Margin per 0.01 XAUUSD lot ≈ **$8.60** at ~$4,300 (measured live) — no margin pressure at 1 position. |

**Risk-capital arithmetic (accepted):** at the measured $532 balance — per-trade max risk **$25 ≈ 4.7%** of equity, daily max loss **$50 ≈ 9.4%**, single 0.01-lot position, margin ≈ $8.60. A flat week at ~0.4 trades/day with a losing streak has absorbable but non-trivial drawdown velocity; this is the envelope agreed in §2.4, stated here at the real balance so the numbers are not optimistic.

**Flagged for operator decision (not changed in this pass):** the ML execution bot's `settings.yaml` still carries `max_daily_loss: 200.0`, which was calibrated when the account was ~$3,287 (~6%). On the current $532 balance that is **37.6% of equity in one day**, and a day where both systems lose (ML $200 + gold $50) is ~47% of the account. Recommendation if the operator agrees: lower it to ~$50 (~9.4%) to match the gold engine's cap — but this is outside the gold experiment's scope and is deliberately *not* modified without explicit approval.

### 1.4 Operational precondition — manual XAUUSD trading must stop while this engine runs

The manual experiment (§1.1) and this engine both trade the **same symbol** on the **same account**. If the user continues to open discretionary XAUUSD trades by hand while the engine is live:

- MT5 `positions_get(symbol="XAUUSD")` will return both the engine's position and the manual one; the engine's "max 1 concurrent position" gate (§2.4, Gate 3) cannot tell them apart by symbol alone, and — as designed — must treat *any* open XAUUSD position (regardless of who opened it) as occupying the one allowed slot (§2.4.1).
- A manual loss will consume the engine's independent $50 daily cap's *intent* even though it is not counted in the engine's own $ accounting (§4, position-identification), because the account's real equity is shared.

**Rule:** while `run_gold_rules.bat` is running (live, per the v1.2 direct-live decision), no manual XAUUSD orders are placed. This is a discipline requirement, not a code gate — the engine cannot enforce it. If it is violated, the live run's data is contaminated for Claim A/B purposes and must be footnoted in the session report (§6.3).

---

## 2. The Trading Rules (The Playbook)

These are the exact rules extracted from the manual experiment and normalized into deterministic logic. Each rule has an objective definition so it can be coded and audited.

### 2.1 Timeframe hierarchy

| Timeframe | Role | Used for |
|---|---|---|
| **H1** | Bias filter — the dominant direction | Whether we're in a buy or sell regime (formal definition in §2.1.1) |
| **M30** | Structural zone — support/resistance levels | Where major levels are defined (formal detection in §2.1.2) |
| **M15** | Decision engine — confirmation & entry triggers | Every trade decision happens at an M15 close |

This is a deliberate simplification of the manual experiment's H4→M15→M5 hierarchy (bias→zone→trigger), shifted one timeframe coarser (H1→M30→M15) because v1 fetches no M5 data and §2.8 explicitly excludes H4. The *relationship* (three tiers, each one deciding a narrower question) is preserved; the absolute timeframes are not.

#### 2.1.1 H1 bias — formal definition

Computed once per M15 evaluation cycle, from the most recently **completed** H1 bar (never the forming one):

```
ema_fast = EMA(H1 close, period=20)
ema_slow = EMA(H1 close, period=50)

if ema_fast > ema_slow and H1_close > ema_slow:      bias = BULLISH
elif ema_fast < ema_slow and H1_close < ema_slow:    bias = BEARISH
else:                                                bias = FLAT
```

- `BULLISH` bias arms BUY setups only. `BEARISH` bias arms SELL setups only. `FLAT` bias arms nothing — no WATCH_ZONE is created in either direction; the engine idles until bias resolves.
- This directly encodes S4.1 (*"No operar en contra de la tendencia mayor"*) as a hard precondition, not a soft agent opinion. It is also why the state-machine table in §2.2 no longer allows both a buy level and a sell level to be watched simultaneously (see the correction in §2.2).
- EMA(20/50) on H1 is chosen for continuity with the existing Frival feature conventions (`close_vs_ema200`, `d1_close_vs_ema20` in `frival/model/features.py` use the same "fast vs slow EMA + price position" idiom) — not because the manual transcript specifies a period. **This is a new operational definition, not an extraction from the transcript**, because the transcript never states numeric EMA periods; it only says "EMA relationship" in prose. Flagged here so it is not mistaken for extracted evidence.

#### 2.1.2 Structural level detection — formal definition (fills the gap left by "swing high/low detection" being undefined in v1.0)

Computed on the most recent **200 completed M30 bars** (~4.2 trading days; gold trades ~23h/day, so this is roughly 4 calendar days of history — long enough to hold a stable level, short enough to stay current).

**Fractal pivot rule** (5-bar fractal, confirmed 2 bars after the pivot — never uses an unclosed bar):

```
bar[i] is a confirmed SWING HIGH if:
    high[i] > high[i-1] and high[i] > high[i-2]
    and high[i] > high[i+1] and high[i] > high[i+2]
    (confirmed only once bar i+2 has closed)

bar[i] is a confirmed SWING LOW if:
    low[i] < low[i-1] and low[i] < low[i-2]
    and low[i] < low[i+1] and low[i] < low[i+2]
    (confirmed only once bar i+2 has closed)
```

**Level lifecycle:**
1. All confirmed swing highs/lows in the 200-bar window form the *candidate level set*.
2. Levels closer than `0.5 × ATR_M30` to an already-kept level are merged (keep the more recent one) to avoid watching two near-identical lines as separate zones.
3. A level is **consumed** (removed from the active set) when price closes (M15 or M30, solid body — §2.1.3) beyond it — that consumption event is exactly what drives `WATCH_ZONE → WAIT_CANDLE_CLOSE` in §2.2.
4. A **broken-but-not-yet-retested** level stays in a `PENDING_RETEST` sub-state (part of `WAIT_CANDLE_CLOSE`/`CONFIRMED`, not a new top-level state) for a maximum of **20 M15 bars (5 hours)**. If no retest confirms within that window, the level is dropped as stale and the engine returns to `WATCH_ZONE` on the next remaining candidate.
5. **Directional filter (the S4.1 fix):** only levels consistent with the current H1 bias (§2.1.1) are watched. `BULLISH` bias → watch only swing **lows** below current price (support, for BUY). `BEARISH` bias → watch only swing **highs** above current price (resistance, for SELL). The opposite-side level set is computed (for logging/audit) but never armed for entry.
6. If multiple candidate levels qualify, the engine watches the **nearest one to current price** only. One armed level at a time — this matches "one position at a time" in spirit and keeps the journal (§6) unambiguous about which level a given trade came from.

#### 2.1.3 "Solid body" — the one candle-shape threshold used everywhere

Reused verbatim from the already-deployed Candle-Close Gate (`frival/signal_gate.py::check_candle_alignment`) for consistency across the whole system:

```
body = abs(close - open)
range = high - low
solid_body  := body >= 0.30 * range   (directional close — counts as a break/rejection/invalidation trigger)
doji        := body <  0.30 * range   (no conviction — never triggers a state transition)
```

Every place this document says "closes with solid body" or "solid-body close" means this test, on a **completed** bar only (never the forming bar — this is G1, §2.3).

### 2.2 State machine

```
             ┌──────────────────────────────────────────────────────────────┐
             │                                                              │
             ▼                                                              │
      ┌──────────────┐    retest holds    ┌──────────────┐                  │
      │  WATCH_ZONE  │ ─────────────────▶ │  ENTRY_READY  │                  │
      └──────────────┘                    └──────────────┘                  │
             │ level broken                        │ entry executed         │
             │ (no retest yet)                     ▼                        │
             ▼                              ┌──────────────┐                 │
      ┌──────────────┐                     │  IN_TRADE     │                 │
      │ WAIT_CANDLE  │ ──▶ CONFIRMED ─────▶ │  (managed)    │                 │
      └──────────────┘                     └──────────────┘                 │
                                                      │ trail/BE/exit       │
                                                      ▼                      │
                                               ┌──────────────┐             │
                                               │     DONE     │ ────────────┘
                                               └──────────────┘
    Any state, any time: a defined level breached → INVALIDATED → position closed.
```

**Correction to v1.0:** the original `WATCH_ZONE` row said "Engine armed on a pair of levels from M30/H1", implying a buy level and a sell level are watched simultaneously (mirroring the manual experiment's "Setup A / Setup B" habit of always proposing both sides — explicitly called out as an anti-pattern in the session brainstorm and in §2.8-adjacent discussion: *"the agent proposed a BUY setup AND a SELL setup [every session]... this is not a strategy — it's a post-hoc narrative"*). **Corrected here: exactly one level is armed at a time, on the side consistent with H1 bias (§2.1.1, §2.1.2 rule 5).** The state table below reflects the correction.

**State definitions:**

| State | Meaning | Entry condition |
|---|---|---|
| `WATCH_ZONE` | The single structural level consistent with H1 bias is the current candidate (bias BULLISH → watching a support level for BUY; bias BEARISH → watching a resistance level for SELL) | Engine armed on one level, selected by §2.1.2 |
| `WAIT_CANDLE_CLOSE` | Current M15 bar must close before any action | Entered automatically when engine detects a level test in progress, or a break in progress |
| `CONFIRMED` | The M15 close validated the trade hypothesis | Close shows break-through (solid body beyond level) or rejection-with-wick at the level (§2.1.3) |
| `ENTRY_READY` | Retest confirmation complete; entry authorized | Confirmation candle closed + retest held (§2.5) |
| `IN_TRADE` | Position open; management rules active | Market order placed at retest confirmation |
| `INVALIDATED` | Defined invalidation level breached | M15/M30 close with solid body beyond invalidation (§2.7, §2.7.1 for the SL relationship) |
| `DONE` | Trade closed (TP, BE-trail stop, or invalidation) | Terminal state |

### 2.3 Golden rules (S3) — the entry discipline

These are the rules most often broken in the manual experiment, and every one is deterministic:

| # | Rule | Deterministic definition |
|---|---|---|
| G1 | **"Vela M15 abierta → No entras."** | If the newest completed M15 bar's timestamp != the current 15-min slot, the candle is still open → NO ACTION. Wait for close. |
| G2 | **"Una mecha no es una señal."** | A wick indicates rejection but does NOT confirm a trade. Confirmation requires: (a) the candle closes at the level with a rejection wick, THEN (b) the **next completed candle's close** — not an intrabar touch — breaks the wick's local extreme. Requiring a *close* beyond the extreme (not a touch) keeps G2 consistent with G1: neither confirmation step ever reacts to an open or intrabar price. |
| G3 | **"No anticipar."** | Entry trigger must fire strictly AFTER the event that justifies it. No pre-empting a break, a close, or a retest. |

### 2.4 The three hard gates (S9.1 / S9.2 / S9.3)

Applied to EVERY candidate entry. All three must pass or the candidate is discarded — no resizing, no relaxing, no override.

**GATE 1 — Location (S9.1):** No chasing.
- BUY only allowed at/near a defined support level, on the retest. Never during an upward expansion away from support.
- SELL only allowed at/near a defined resistance level, on the retest. Never during a downward dump away from resistance.
- *Deterministic check:* `abs(entry_price - structural_level) <= max(0.15 * ATR_M15, 1.00)` (in USD price units — gold quotes 2 decimals; verify `ATR_M15` and the constant `1.00` are both plain price units, not "pips", before go-live — see §5, "Units" row).

**GATE 2 — Space-to-target (S9.2):** R:R ≥ 1 (prefer 1.5).
- *Deterministic check:* `(TP1 - entry) / (entry - SL) >= 1.5` for BUY; inverted for SELL.
- `TP1` and `SL` are defined precisely in §2.6.1 and §2.7.1 respectively — both are structural, not ATR multiples, so this gate is arithmetic on real levels, not an assumption.

**GATE 3 — Risk/Capital (S9.3):** Position sizing is fixed and non-negotiable.
- Fixed lot: **0.01** XAUUSD. This must be passed into the order request with `dynamic_sizing: false` explicitly — the shared `OrderManager._calculate_position_size()` (reused for order placement, §3.4) defaults to `dynamic_sizing: true` and will scale the lot by risk profile/signal-tier multipliers (0.5×–2.0×) unless told not to. **This is a real bug risk if the flag is omitted; it is called out again in §9.**
- Max risk per trade: **$25 USD**, computed as `risk_usd = abs(entry_price - SL_price) * contract_size * lot_size` where `contract_size` is XAUUSD's `trade_contract_size` from `mt5.symbol_info` (assumed 100 oz/lot — **must be confirmed against the live FPMarkets symbol spec before go-live**, see §5 and Step 2 in §8). At the assumed 100 oz/lot and 0.01 lot, `risk_usd ≈ abs(entry_price - SL_price) * 1.0` — i.e. at 0.01 lots, one dollar of SL distance costs approximately one dollar of account risk. If the computed `risk_usd` for a structurally-correct SL exceeds $25, **the setup is discarded, not resized and not entered with a tighter, non-structural SL.** (Observed SL distances in the manual transcript ranged ~$10.55–$27; a $27 setup was explicitly flagged in the transcript itself as a FOMO violation, not a valid trade — so this cap is expected to reject a meaningful minority of otherwise-confirmed setups, by design.)
- Max concurrent positions: **1** (see §2.4.1 for how this is actually checked).
- Daily stop: engine halts if any trade closes at a loss and realized daily PnL for **this engine's own trades** ≤ **−$50**. Resumes next calendar day. See §2.4.2 for how "this engine's own trades" is identified and why that scoping matters.
- NO averaging down. NO adding to a loser. NO averaging up. NO martingale.

#### 2.4.1 "Max 1 concurrent position" — the actual check

`OrderManager._validate_order()` (reused for order placement, §3.4) only blocks a **same-direction** duplicate position (`pos.type == BUY and action == 'buy'`); it does **not** block opening a SELL while a BUY is already open on the same symbol, because FPMarkets accounts can run in hedging mode. That default behavior is insufficient for this engine's Gate 3. **The gold engine's own pre-entry check must query `positions_get(symbol="XAUUSD")` with no direction filter and reject entry if the count is ≥ 1, regardless of direction or who opened it** (this also enforces §1.4 — a manual position blocks the automated engine from adding a second one, which is the safe failure mode).

#### 2.4.2 Position identification — comment tag, not magic number

Nothing in `frival/execution_bot` currently sets an MT5 `magic` number on any order (`order_manager.py::_prepare_order` never populates `magic`; it defaults to 0 for every order the ML pipeline, this engine, and any manual trade would place). Magic-number filtering is therefore **not available** to distinguish this engine's trades from manual ones or from the ML pipeline's trades (the ML pipeline never trades XAUUSD, so the symbol filter alone separates it, but manual XAUUSD trades are indistinguishable from the engine's by symbol).

**Decision:** every order this engine places carries a fixed `comment` string, `"GOLD_RULES_v1"`. The engine's own daily-PnL accounting (§2.4, Gate 3 "Daily stop") sums `mt5.history_deals_get()` for today, filtered to `symbol == "XAUUSD" and comment == "GOLD_RULES_v1"`. Any manual XAUUSD deal (blank or different comment) is excluded from that sum — but is **still counted** for the concurrent-position check in §2.4.1, which must ignore comment entirely. This is deliberate: the $50 cap is a self-attribution accounting device (so we know if the *rules* are losing money), while the concurrency gate is a real-world safety device (so the engine never doubles up exposure regardless of who opened the first position).

#### 2.4.3 Known limitation: the ML pipeline's daily-loss check is account-wide, not per-symbol

This was observed directly in production on 2026-09-10: the ML execution bot skipped FIRED GBPUSD/USDCHF signals citing `daily loss limit: $-152.12`, which was actually the day's **XAUUSD manual loss** (−$115.56) plus other realized FX losses, added together at the account level (`project_last_state.md` §8, "Daily loss limit is the blocker" incident; this is also why `max_daily_loss` was subsequently raised 50→200). The ML pipeline's daily-loss check reads `config_manager` values and MT5 account-level realized PnL — it has no symbol filter.

**Consequence — LIVE since v1.3 (pre-flight confirmed single account 81486396, balance $532):** the ML pipeline's $200 account-wide daily-loss check will see this engine's losses on the same account, exactly as it saw the manual gold losses on 2026-09-10. The engine's *own* $50 cap remains comment-scoped (§2.4.2). Combined worst-case: ML $200 + gold $50 on the same equity (see R5/flagged note, §1.3.1). This coupling is accepted and documented; the only mitigation offered here is the flagged recommendation to review the ML `max_daily_loss` on the shrunken balance.

### 2.5 Entry trigger — Break-and-Retest (the winning pattern)

This is the single most consistent setup in the manual experiment, and it maps directly onto the state machine in §2.2: step 1 below is the `WATCH_ZONE → WAIT_CANDLE_CLOSE` transition; steps 2–3 are `WAIT_CANDLE_CLOSE → CONFIRMED`; step 4 is `CONFIRMED → ENTRY_READY → IN_TRADE`. Two variants:

**Variant B (break → retest → enter):**
1. Price breaks a structural level with solid M15 body (§2.1.3). *(→ `WAIT_CANDLE_CLOSE`, level marked `PENDING_RETEST`, §2.1.2 rule 4.)*
2. Wait for price to return toward the broken level.
3. Wait for an M15 candle to close showing absorption/rejection at the retest (a wick that does not close beyond the level, per G2). *(→ `CONFIRMED`.)*
4. Next candle's **close** breaks the retest's local extreme → **ENTER at market**. *(→ `ENTRY_READY` → `IN_TRADE`.)*

**Variant R (rejection → break → enter):**
1. Price reaches a structural level and an M15 wick rejects it (candle closes back off the level, still doji or opposite-colored). *(→ `WAIT_CANDLE_CLOSE`.)*
2. Candle closes at the level. *(→ `CONFIRMED`.)*
3. Next candle's **close** breaks the wick's local extreme → **ENTER at market**. *(→ `ENTRY_READY` → `IN_TRADE`.)*

**Entry is ALWAYS by market at the moment of retest confirmation. No pending orders.** This eliminates the order-expiry problem from the manual experiment (pending orders at levels expired unfilled, or filled on false retests before a close ever confirmed them).

### 2.6 Management rules (S10) — between entry and exit

| # | Rule | Deterministic definition |
|---|---|---|
| M1 | **Break-even at 50%** | When price covers 50% of the distance entry→TP1, DRAG SL to entry price. (This protects the trade from that point on.) |
| M2 | **Structural trail** | After BE, the SL follows the most recent swing extreme: for BUY, the low of the last completed M15 bar; for SELL, the high. |
| M3 | **TP1 → TP2 ladder** | See §2.6.1 for exact target definitions. Primary automation in v1: broker TP is set to TP1 at entry and left there; TP2 is a documentation/decision target only (v1 does not auto-extend the broker TP after BE — see §2.6.1). |
| M4 | **No winner averaging** | Never add size to a winning trade. |

#### 2.6.1 TP1 / TP2 — formal definition (fills the "next structural level" gap in v1.0)

- **TP1** = the nearest unconsumed swing point beyond entry, in the trade's direction, from the same M30 level set used for Gate 1 (§2.1.2) — for BUY, the nearest swing high above entry; for SELL, the nearest swing low below entry. This is the numeric TP sent to MT5 at order placement (`OrderManager.execute_order()` requires both `sl` and `tp` present — its safety block in `_prepare_order()` raises `OrderValidationError` otherwise, so TP1 must always resolve to a real number before an order is ever attempted).
- If Gate 2's R:R check on TP1 fails (< 1.5), the setup is discarded (§2.4, Gate 2) — TP1 is never widened artificially to pass the gate.
- **TP2** = the next unconsumed swing point beyond TP1, same direction. If none exists within the 200-bar lookback (§2.1.2), TP2 is undefined for that trade — this is expected to be rare but not impossible, and is logged as `tp2: null` rather than synthesized from an ATR multiple (keeping the "structure, not probabilities" principle intact even in the rare edge case).
- v1 does **not** implement automatic TP-extension to TP2 after BE triggers — that would require a second live order-modify path beyond what §3.4 reuses. TP2 is recorded for audit/decision purposes; if the position is still open and trailing (M2) when price reaches TP1, v1's behavior is to let the broker-side TP1 close the position. Auto-extension to TP2 is an explicit **v2 candidate**, not a v1 gap being silently skipped — see §2.8.

### 2.7 Invalidation (the explicit exit)

Every setup defines an explicit invalidation level. Deterministic rule: **if any M15 or M30 candle closes with solid body (§2.1.3) beyond the invalidation price, the trade is closed immediately — no averaging, no hope, no exception.**

Examples from the playbook:
- BUY setup: invalidation = lowest swing low below entry (if a candle closes below it, the buy thesis is dead).
- SELL setup: invalidation = highest swing high above entry.

#### 2.7.1 Invalidation vs. the broker-side hard SL — the buffer rule

The invalidation price above is *structurally* the same level as the trade's stop-loss (both are "the swing extreme that, if broken, proves the thesis wrong"). If the broker-side hard `SL` sent to MT5 were placed at exactly that price, an **intrabar touch** would stop the position out immediately — before any M15/M30 candle ever gets a chance to close and confirm the break with a solid body. That would silently defeat the entire "wait for close" discipline (G1) on the *exit* side, even though it is enforced on the *entry* side.

**Resolution:** the broker-side hard `SL` is placed a small buffer **beyond** the invalidation level, not at it:

```
sl_buffer = max(0.05 * ATR_M15, 0.30)      # USD price units, symbol-digit-rounded
SL_price  = invalidation_level - sl_buffer   (for BUY; + for SELL)
```

This makes the hard SL a true last-resort circuit breaker (protects against a gap, a disconnect, or the engine process being down when a genuine breakdown happens), while the *primary*, expected exit path is the soft invalidation check in §2.7 firing first, on the candle close, closing the position deliberately (via `OrderManager.close_position()`, §3.4) at a better price than the buffered hard SL would have given. `SL_price` (inclusive of the buffer) is the value used everywhere `SL` appears in Gate 2's R:R check and Gate 3's $-risk formula (§2.4) — the buffer is real risk and must be counted, not rounding error.

### 2.8 What is deliberately NOT in v1 (v2 candidate list)

| Concept | Why excluded from v1 | v2 status |
|---|---|---|
| Fair Value Gaps / Imbalance (260 refs) | Momentum argument; used only indirectly via "target = next structural level." Not a hard rule in v1. | Candidate — only if v1's four core rules (§2.3–§2.7) fail to clear breakeven *and* FVG can be given an objective, testable definition first. |
| Absorption wicks / institutional order flow language | No objective definition available; stays non-critical commentary, not a trigger. | Same bar as FVG — objective definition required before it can be coded, not before it can be discussed. |
| H4 timeframe | H1 is sufficient for bias in v1; H4 added marginal value and equivalent complexity. | Candidate if H1 bias (§2.1.1) proves too noisy on the live run. |
| Automatic TP1→TP2 extension after BE (§2.6.1) | Requires a second order-modify path not yet built; v1 keeps TP fixed at TP1. | Candidate for v1.2 once the base entry/exit path is proven. |
| Opposite-direction level tracking as a live WATCH_ZONE | Corrected out in §2.2 — this exact pattern ("propose both a BUY and a SELL setup every session") was identified as the manual experiment's own anti-pattern. | Not planned. Logging the opposite-side level for audit purposes only remains in scope. |

---

## 3. Architecture

### 3.1 Runtime flow (no ML, no agents)

```
run_gold_rules.bat
   └── run_gold_rules.py          ← loop: every M15 close, plus the resilience wrapper in §3.5
          ├── check gold session/maintenance window (§3.6) — skip cycle if closed
          ├── fetch XAUUSD M15+M30+H1 bars (MT5, via existing fetch_ohlcv — §3.2)
          ├── compute H1 bias (§2.1.1) + structural levels (§2.1.2)
          ├── evaluate state machine (current M15 close)
          │     ├── GATE 1 location
          │     ├── GATE 2 R:R
          │     ├── GATE 3 risk/sizing (incl. §2.4.1 concurrent-position check)
          │     └── golden rules G1/G2/G3
          ├── if ENTRY_READY → place market order @ retest confirmation
          │     (reuses OrderManager.execute_order(); dynamic_sizing=False, comment="GOLD_RULES_v1")
          ├── if IN_TRADE → evaluate M1 BE-50 / M2 trail / M4 exit / invalidation
          │     ONCE, synchronously, as part of this same M15-close cycle — see §3.4 for why
          │     the existing OrderManager.monitor_break_even() poller is NOT reused as-is
          └── log everything to journal (§6) + persist state (§3.3, §6.4)
```

### 3.2 Data & symbol

- MT5 symbol: `XAUUSD`, timeframes M15, M30, H1 — all fetchable via the existing `frival/data/fetcher.py::fetch_ohlcv` (`M15`/`M30`/`H1` are already mapped to `mt5.TIMEFRAME_*` constants there; verified, no new fetch code needed).
- No ML features. No calendar features. No FRED data. Pure OHLCV structure.
- Minimum warm-up: 200 completed M30 bars for level detection (§2.1.2) + 50 completed H1 bars for the slow EMA (§2.1.1). At M30/H1 native resolution this is available from the existing cache almost immediately; no special backfill step is required beyond what `fetch_ohlcv` already does for other pairs.

### 3.3 Where it lives

```
frival/
├── run_daily.bat                  (existing — ML pipeline, unchanged)
├── run_gold_rules.bat             (NEW — double-click launcher for this engine)
└── gold_rules/
    ├── run_gold_rules.py          (loop + orchestration + resilience wrapper, §3.5)
    ├── engine.py                  (state machine + rules)
    ├── levels.py                  (structural level detection, §2.1.2)
    ├── bias.py                    (H1 bias, §2.1.1)
    ├── config.yaml                (all thresholds, risk caps, symbol — schema in §3.3.1)
    ├── state/
    │   └── engine_state.json      (persisted state — schema in §6.4)
    ├── journal/
    │   └── 2026-09-15.jsonl       (every decision, one line per M15 close)
    └── README.md                  (operation notes)
```

`config.yaml` lives inside `gold_rules/`, not a separate `config/` subfolder mirroring `execution_bot` — v1.0 listed both `config.yaml` and a `config/` directory as siblings, which was redundant (MT5 credentials are already available via the existing `execution_bot/config/credentials.env` and `ConfigManager`, reused directly per §3.4; there is no second credentials file to store).

#### 3.3.1 `config.yaml` — concrete schema (fills the "all thresholds" placeholder in v1.0)

```yaml
symbol: XAUUSD

timeframes:
  bias: H1
  levels: M30
  decision: M15

bias:
  ema_fast: 20
  ema_slow: 50

levels:
  lookback_bars_m30: 200
  fractal_wing: 2            # bars each side for the 5-bar fractal
  merge_distance_atr_mult: 0.5
  pending_retest_max_bars_m15: 20

gates:
  location_tolerance_atr_mult: 0.15
  location_tolerance_min_usd: 1.00
  min_rr: 1.5

risk:
  fixed_lot: 0.01
  max_risk_usd: 25.0
  max_concurrent_positions: 1
  daily_loss_cap_usd: 50.0
  sl_buffer_atr_mult: 0.05
  sl_buffer_min_usd: 0.30

management:
  be_trigger_fraction: 0.5

order:
  comment: "GOLD_RULES_v1"
  dynamic_sizing: false

session:
  skip_minutes_before_close: 15   # see §3.6
  skip_minutes_after_open: 15

resilience:
  max_consecutive_errors: 5       # see §3.5
  error_backoff_seconds: 60
```

### 3.4 Reused vs. new code

| Component | Status |
|---|---|
| MT5 connection, symbol info, tick, positions, account info | **Reused** — `frival/execution_bot/core/mt5_connector.py::MT5Connector`, no changes. |
| Credentials / demo-vs-live resolution | **Reused** — `frival/execution_bot/core/config_manager.py::ConfigManager` (`is_demo_mode()` already prioritizes `settings.yaml` correctly per the fix documented in `project_last_state.md`). |
| Order placement (entry) | **Reused** — `OrderManager.execute_order()`, called with `dynamic_sizing: False`, `comment: "GOLD_RULES_v1"`, explicit `sl`/`tp` (§2.6.1/§2.7.1 supply both, satisfying the existing SL/TP safety block). |
| Position close (invalidation exit) | **Reused** — `OrderManager.close_position(ticket)`. |
| Break-even-at-50% *mechanism* | **NOT reused as a background poller.** `OrderManager.monitor_break_even()` is a **blocking** loop (polls every 30s for up to 600s, per `settings.yaml::break_even`) designed to run once, synchronously, right after the ML pipeline places one order per hour. This engine's IN_TRADE management (M1/M2/M4, §2.6) must persist for the **entire life of a trade**, which can span many M15 cycles (hours), not a 10-minute window. Calling the existing blocking poller would either (a) stall the M15 loop for up to 10 minutes per trade, missing subsequent M15 closes entirely, or (b) time out and stop monitoring long before the trade is done, silently disabling M2 (structural trail) and invalidation for the rest of the trade's life. **New code required:** the gold engine's own management step, evaluated once, non-blocking, per M15-close cycle, using the *same* underlying MT5 calls (`positions_get`, `symbol_info_tick`, `TRADE_ACTION_SLTP` modify) that `monitor_break_even()` uses internally, but without its own polling loop. |
| Structural levels, bias, state machine, gates, journal | **New** — `gold_rules/levels.py`, `bias.py`, `engine.py`. |

### 3.5 Process resilience (new requirement — v1.0 did not address this)

§10 (Definition of Done) requires `run_gold_rules.bat` to run **4+ consecutive weeks without manual intervention**. A bare `while True:` loop that raises on the first MT5 hiccup, calendar edge case, or transient network error would not survive a single day, let alone 4 weeks, on a Windows machine that is not a dedicated server. Requirement:

- The main loop wraps each M15-cycle evaluation in `try/except`. A caught exception is logged to the journal (§6.1) with `action: ERROR`, and the loop continues to the next M15 close rather than exiting.
- `resilience.max_consecutive_errors` (config, §3.3.1) caps how many cycles in a row may fail before the process **does** exit loudly (so a genuinely broken engine does not run blind for weeks producing empty journals) — recommended default 5 consecutive cycles (~75 minutes) before hard-stopping.
- MT5 disconnects specifically are retried using the existing `MT5Connector.reconnect()` before being counted as a cycle failure.
- This does not guarantee true 24/7 uptime (the terminal window and MT5 terminal must still be running — this is a desktop tool, not a service) but it does guarantee the process itself does not crash on ordinary transient errors, which is the realistic bar for "no manual intervention."

### 3.6 Gold session / maintenance-break handling (new — not addressed in v1.0)

Gold CFDs typically have a daily broker maintenance/rollover halt (commonly around 21:00–22:00 UTC, broker-dependent) plus the standard weekend closure. Two effects on this engine if unhandled:
- A structural level computed across the halt/rollover gap can be based on a distorted or missing M30/H1 bar.
- `IN_TRADE` management (M2 structural trail) should not use a gapped bar as "the most recent swing extreme."

**Rule:** before each cycle, call `MT5Connector.is_market_open("XAUUSD")` (already implemented) — skip the cycle entirely if false. Additionally, skip **new entries only** (not management of an already-open trade) within `session.skip_minutes_before_close` / `skip_minutes_after_open` of the actual daily halt boundary (config, §3.3.1), determined from the first gap ≥ 2× the median M15 bar interval seen in the recent data, rather than a hardcoded UTC time (broker halt times can shift with DST) — this keeps the rule robust without hardcoding a time that could silently drift wrong.

**Implementation note (v1.3, 2026-09-15):** the live broker revealed that `is_market_open()` alone is **insufficient** — FPMarkets keeps `trade_mode=4 (FULL)` on XAUUSD during the daily maintenance halt, so the connector check returns True while the market is actually closed (observed directly; the heartbeat kept printing during a halt). The engine therefore uses **bar freshness** as the operative detection: if no new closed M15 bar appears for ~20 minutes (≈ one bar interval + 5 min), the market is treated as paused and the engine idles automatically, resuming on the first new bar. This subsumes the `skip_minutes_before_close/after_open` window (now consolidated into the freshness threshold) and uniformly covers the daily halt, weekends, and broker holidays without any hardcoded UTC time.

---

## 4. Explicit Decisions

| Decision | Choice | Rationale |
|---|---|---|
| ML models used? | **NO** | Gold ML failed 3× on different feature sets. Rules are the only evidence of edge. |
| AI agents used? | **NO** | Agents added cost + inconsistency and no measured improvement. All logic deterministic. |
| Entry type | **Market at retest confirmation** | Eliminates pending-order expiry; enforces the "no chase" rule. |
| Lot size | **0.01 fixed**, `dynamic_sizing: false` explicitly passed | The only defensible starting size given the sizing-induced margin calls; must not be silently rescaled by the reused sizing helper (§2.4, §3.4). |
| Execution venue | **MT5 (FPMarkets), live account** | Already integrated; same account as the ML pipeline. |
| Position identification | **`comment: "GOLD_RULES_v1"`** on every order (no magic number — none is used anywhere in this codebase today) | Only available mechanism to self-attribute PnL for the $50 cap; concurrency checks still consider all XAUUSD positions regardless of comment (§2.4.1–§2.4.2). |
| Manual XAUUSD trading while engine is live | **Not allowed** (§1.4) | Same symbol; manual trades contaminate the concurrency gate and the Claim A/B measurement even though they don't inflate this engine's own $ accounting. (On a dedicated account the contamination window is the symbol, not the whole account.) |
| Correlation with ML pipeline | **Shared account (pre-flight confirmed); process-level independence only** | Same account (81486396, $532), same terminal, separate processes/symbols/cadences. The ML pipeline's account-wide daily-loss check will see gold losses (LIVE coupling, §2.4.3/§9); each system's own cap remains self-scoped. |
| Shadow run? | **NO — decided-out 2026-09-15** | The 1-week simulation planned in v1.0/v1.1 is removed; the engine goes straight to LIVE at 0.01 lots (§1.1). Bounded by the $25/$50 caps; measurement begins with live trades. |
| Account model | **Single existing account 81486396 — resolved by pre-flight (R1–R5, §1.3.1)** | The $500 statement was not a new account; the live balance is $532. Same account as the ML pipeline, so independence is process-level only. `MT5_TERMINAL_PATH` must be populated with the discovered FPMarkets terminal path. |
| Daily risk budget | **$50 max loss**, computed from this engine's own comment-tagged closed deals only | Adaptable in config; on a dedicated account this equals real account-level PnL for the gold book (§1.3.1). |
| SL vs. invalidation level | **SL = invalidation level + buffer** (§2.7.1), never exactly at the invalidation level | Keeps the "wait for close" discipline meaningful on the exit side while still providing a hard broker-side safety net for gaps/disconnects. |
| Contract size assumption | **100 oz/lot assumed; must be confirmed via `mt5.symbol_info("XAUUSD").trade_contract_size` before go-live** | The entire $25/$50 risk math in §2.4 depends on this constant being correct for FPMarkets specifically — see §5 and §8 Step 2. |

---

## 5. Risk Parameters (v1 — atomic)

| Parameter | Value | Source |
|---|---|---|
| Symbol | XAUUSD | Experiment |
| Timeframes | M15 (decision) / M30 (levels) / H1 (bias) | Experiment |
| Fixed lot | 0.01, `dynamic_sizing: false` | Experiment (strict sizing rule) + §2.4 bug-risk note |
| Contract size | Assumed 100 oz/lot — **verify against live `mt5.symbol_info` before go-live** | New — required for the $-risk formula in §2.4 to be correct |
| Max per-trade risk | $25 (`risk_usd = abs(entry - SL_incl_buffer) * contract_size * lot_size`) | Experiment R:R → $ distance, formula made explicit in §2.4/§2.7.1 |
| R:R minimum | 1.5, computed against TP1/SL as defined in §2.6.1/§2.7.1 | Experiment S9.2 |
| Break-even trigger | 50% of entry→TP1 | Experiment S10 |
| SL buffer beyond invalidation | `max(0.05 × ATR_M15, $0.30)` | New (§2.7.1) — closes the SL/invalidation race condition present in v1.0 |
| Max concurrent positions | 1, checked across **all** XAUUSD positions regardless of comment | Experiment risk discipline, scoping fixed in §2.4.1 |
| Daily loss cap | $50, computed from comment-tagged (`GOLD_RULES_v1`) closed deals only | Experiment risk discipline, scoping fixed in §2.4.2 |
| Entry tolerance to level | ≤ 15% of ATR M15, floor $1.00 | New (operational definition), units clarified in §2.4 Gate 1 |
| Invalidation | M15/M30 close beyond level, solid body per §2.1.3 | Experiment |
| H1 bias definition | EMA(20) vs EMA(50) + price position, §2.1.1 | New — operational definition, not an extraction from the transcript |
| Structural level definition | 5-bar M30 fractal, 200-bar lookback, directional filter, §2.1.2 | New — operational definition, fills a total gap in v1.0 |

> These are v1 atomic values. Every one is in `config.yaml` (§3.3.1), auditable, changeable only with a documented review.

---

## 6. Audit & Observability

Everything must be reconstructable. Requirements:

1. **Journal file** — one JSON line per M15 close evaluation:
   `{timestamp, state, price, h1_bias, levels: {watched_level, side}, gate_results: {loc, rr, risk, concurrency}, action: NONE|WATCH|CLOSE|CONFIRM|ENTRY|TRAIL|BE|INVALIDATE|CLOSE|ERROR, reason}`
2. **Trade log** — entry price, SL (incl. buffer), TP1, TP2 (nullable, §2.6.1), BE price, invalidation level, actual close price, PnL, `comment` tag.
3. **Session report** (§6.3) — end-of-day summary: signals fired, trades taken, wins/losses, realized PnL (this engine's own, comment-scoped), rationale summary, and an explicit flag if any manual XAUUSD activity was detected during the session (§1.4 violation check — compare all XAUUSD closed deals for the day against the comment tag; any non-`GOLD_RULES_v1` XAUUSD deal is logged as a contamination warning).
4. **State persistence** (§6.4) — engine restarts must resume the correct state (WATCH/IN_TRADE) from disk, not guess.
5. **Execute-pending parity** — the engine must never ghost-execute on disconnect: order placement requires a confirmed MT5 round-trip; failed round-trips are logged, not retried blindly.

### 6.4 State persistence — concrete schema (fills the "must resume" placeholder in v1.0)

`gold_rules/state/engine_state.json`, rewritten atomically after every cycle:

```json
{
  "updated_at": "2026-09-15T14:15:00Z",
  "state": "IN_TRADE",
  "h1_bias": "BEARISH",
  "watched_level": {"price": 4393.50, "side": "resistance", "confirmed_at_bar": "2026-09-15T09:30:00Z"},
  "active_trade": {
    "ticket": 123456789,
    "direction": "sell",
    "entry_price": 4371.45,
    "sl_price": 4376.30,
    "tp1_price": 4360.00,
    "tp2_price": 4350.00,
    "invalidation_level": 4376.00,
    "be_triggered": false,
    "comment": "GOLD_RULES_v1"
  },
  "pending_retest": null
}
```

On startup, the engine reads this file; if `active_trade` is non-null, it re-queries `positions_get(ticket=...)` to confirm the position still exists (if it was closed while the process was down, transition to `DONE`, log the outcome from `history_deals_get`, and resume `WATCH_ZONE`) before resuming management. If `active_trade` is null, the engine resumes `watched_level`/`pending_retest` as recorded.

---

## 7. Acceptance Criteria (stop/examine gates)

Graded independently, per §1.1's Claim A / Claim B split. **Since v1.2 (operator decision 2026-09-15) there is no shadow phase: these criteria are measured entirely on live trades from the first one onward.**

- **Claim A (do the rules have edge) — criterion A:** ≥ 30 live trades with win rate × R:R ≥ 1 (i.e., the EV is positive at 0.01 lots).
- **Claim B (does edge survive at sane risk) — criterion B:** ≥ 20 trades with per-trade risk never exceeding $25 (§2.4 Gate 3, using the confirmed contract-size formula) and no margin call.

The experiment is a **PASS** if EITHER A or B is met (per the original design intent — A alone proves the logic works; B alone proves the sizing discipline holds even if sample size for A is still thin).

The experiment is a **FAIL → rebuild** if:
- **F1:** < 15 trades in 4 weeks (setup too rare — needs rule relaxation), OR
- **F2:** realized EV is negative after 30 trades (the rules don't have edge — reroute to ML or stop), OR
- **F3:** any margin call occurs (risk controls broken — stop immediately).

The experiment is **ABORTED** on: a margin call, an unexpected account drop > $150 in a day, or a rule violation discovered in the journal (including a §1.4 manual-trading-contamination flag persisting across more than one session without correction).

---

## 8. Next Steps (implementation order)

| # | Step | Deliverable | Done when |
|---|---|---|---|
| 0 | **Account provisioning** | **DONE — pre-flight 2026-09-15 (v1.3):** single account 81486396/FPMarketsSC-Live, balance $531.78 (later observed $550.02 after ML activity — balance fluctuates; the $500-scale risk envelope holds), XAUUSD symbol verified (contract 100.0, digits 2, vol_min 0.01, margin 0.01 lot ≈ $8.60). No separate account/terminal needed (§1.3.1 R1–R5) | ✅ |
| 1 | **Pre-flight verification** | Contract size **confirmed live (100 oz/lot)** and recorded in `config.yaml`; XAUUSD trade_mode full. **Login-mismatch guard (R4) WIRED** into `run_gold_rules.py::connect()` — verified: refuses to trade on login mismatch; one live connected cycle returned account 81486396 correctly. `confirm_live_orders` confirmed unused in code (audit §A; no code path reads it) | ✅ |
| 2 | Decide & document rules table | This document (v1.3) | ✅ |
| 3 | Create `frival/gold_rules/` skeleton + `config.yaml` + `config/credentials.env` | Config per §3.3.1 (incl. `contract_size: 100.0`, `confirm_max_bars_m15: 3`); credentials = main account; `MT5_TERMINAL_PATH` populated in `gold_rules/config/credentials.env` | ✅ — config loads; connector authenticates as 81486396 |
| 4 | Implement `bias.py` + `levels.py` | H1 EMA(20/50) bias + M30 5-bar fractal levels (merge/consume/watch-select/TP-SL helpers) | ✅ — unit tests + real-data checks: BEARISH on live H1, 27–28 active levels, ATR(14) ≈ $10 |
| 5 | Implement `engine.py` state machine | WATCH→WAIT_CANDLE_CLOSE→CONFIRMED→ENTRY_READY→IN_TRADE→DONE/INVALIDATED; single-direction arming; G1–G3; bias-flip void; variant B/R + timeouts; consumed-level edge-event ordering (break detected before consumed check — bug found & fixed during testing) | ✅ — 11 engine tests incl. full Variant-B SELL → ENTRY order |
| 6 | Implement gates | location ≤ tol, R:R ≥ 1.5, risk ≤ $25 (contract-size formula), concurrency (all XAUUSD positions), daily -$50 comment-tagged | ✅ — gate unit tests incl. wide-SL rejection |
| 7 | Implement entry | Market at retest confirmation via `OrderManager.execute_order()`, `dynamic_sizing=False`, `comment="GOLD_RULES_v1"`, SL per §2.7.1, TP1 per §2.6.1 | ✅ (code) — not yet exercised with a live ticket (Step 11) |
| 8 | Implement management (BE-50, trail, invalidation) as **non-blocking per-cycle checks** | Position modify (`TRADE_ACTION_SLTP`) on conditions; invalidation → `close_position()` | ✅ (code) — BE/TRAIL/INVALIDATE/DONE unit tests pass; live-trade journal proof pending a real trade |
| 9 | Add journaling + session reports + state persistence + resilience wrapper | `journal/*.jsonl` per §6.1 + `state/engine_state.json` §6.4 (atomic write) + catch/log/continue + hard-stop after `max_consecutive_errors` | ✅ — dry-run and one live cycle both wrote journal + state correctly; restart resumes |
| 10 | Build `run_gold_rules.bat` launcher | Double-click entry at `frival/run_gold_rules.bat` | ✅ |
| 11 | **LIVE directly** (operator decision — no shadow, v1.2) | `run_gold_rules.bat` → real MT5 orders at 0.01 lot as soon as a confirmed setup fires post-deployment | **Pending — deploy step. All code is live-ready (verify: dry cycle produced zero orders while WATCH_ZONE).** |
| 12 | Review after 20-30 trades | Acceptance criteria review, graded per Claim A / Claim B (§7) | Pending — after live accumulation |

> **v1.2 removal:** the v1.1 step "10. SHADOW RUN (1 week, simulated only)" is **removed** by operator decision 2026-09-15. Its only surviving requirement ("confirm §1.4 — no manual XAUUSD trades") moves into the acceptance-review step (12) and the session-report contamination flag (§6.3).

---

## 9. Known Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Rules produce too few trades (setup too strict) | Medium | Acceptance gate F1: relax tolerance after 4 weeks with documented change |
| Fake retests (level holds then breaks) | Medium | G2/G3 confirmations + explicit invalidation; journal captures each case |
| MT5 disconnect mid-trade (trail/BE fails) | Medium | State persistence (§6.4); resume loop; resilience wrapper (§3.5); manual close verified |
| Correlation with ML pipeline (shared account) | **Medium — live, single account confirmed (v1.3)** | Pre-flight confirmed one account (81486396, $532). The ML pipeline's daily-loss check is account-wide (§2.4.3) and has already been throttled by XAUUSD-attributable losses on 2026-09-10. A bad day for this engine can silently block ML pipeline trades. Accepted for v1; the flagged recommendation to review `max_daily_loss: 200.0` on the shrunken balance (§1.3.1 R5) is the only proposed mitigation and remains an operator decision. |
| Manual XAUUSD trading during a live window | Medium (demonstrated user behavior, §1.1/§1.4) | Operational discipline rule (§1.4) + automated contamination flag in the session report (§6.3); the concurrency gate (§2.4.1) at least prevents the engine from *adding* exposure on top of a manual position |
| Engine connects to the **wrong** account/terminal | Low-medium, catastrophic if it happens | R4 (§1.3.1): login-mismatch guard at startup and every reconnect; three MT5 terminals discovered on this machine (FPMarkets, FXChoice, RoboForex) — only the FPMarkets path is used and the guard verifies the configured login |
| Terminal not running / not logged in when the engine starts | Medium (single-instance reality) | Engine idles and retries connection rather than erroring (§1.3.1 R4); the loop resumes the instant the terminal appears; `MT5_TERMINAL_PATH` explicit so no path-discovery ambiguity |
| `dynamic_sizing` silently rescaling the 0.01 lot | Medium (default behavior of the reused sizing helper is `true`) | Explicit `dynamic_sizing: false` in every order request (§2.4, §3.4, §4); unit test in Step 5/6 (§8) asserts the sent volume is exactly 0.01 |
| SL placed exactly at the invalidation level (race with the soft check) | Was unaddressed in v1.0 | §2.7.1 buffer rule; buffer distance included in all $-risk and R:R math |
| Contract size assumption wrong for FPMarkets XAUUSD | Low-medium, but high impact if wrong (the entire $25/$50 caps rescale) | Step 1 pre-flight verification (§8) against the **gold account's** live symbol spec before any order is placed |
| Process crash / unhandled exception ends the 4-week unattended run early | Was unaddressed in v1.0 | §3.5 resilience wrapper: catch, log, continue; hard-stop only after `max_consecutive_errors` |
| Gold structural edge is illusion (FVG regression) | Low-Medium | **Direct-live measurement now (v1.2):** no shadow phase — the risk is bounded to the $25/trade and $50/day caps while the acceptance review (§7) judges Claim A/B after 20–30 live trades |
| Engine bugs cause wrong sizing | Low | Fixed 0.01 lot is in config; journal verifies every order's volume before send |

---

## 10. Definition of Done (the experiment is finished when)

1. The journal contains ≥ 30 live trades with full decision trail.
2. Every trade obeyed the atomics (0.01 lot, ≤ $25 risk using the confirmed contract-size formula, R:R ≥ 1.5, BE at 50%).
3. The acceptance criteria (A or B, graded per §7) was triggered OR a documented FAIL/ABORT decision was recorded with rationale.
4. The account experienced zero margin calls.
5. `run_gold_rules.bat` ran 4+ consecutive weeks without manual intervention (per the resilience definition in §3.5 — the terminal and MT5 must still be running; "unattended" means the process survives ordinary transient errors without a human restarting it, not that no computer needs to be on).
6. No unresolved §1.4 manual-trading-contamination flag remains in any session report used to support the PASS/FAIL decision.

---

*End of design. This document is the audit contract for the experiment — any parameter change must be logged in version control with a reason.*
