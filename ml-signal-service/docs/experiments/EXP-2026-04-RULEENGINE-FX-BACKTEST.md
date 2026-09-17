# Experiment: Rule-Engine Cross-Instrument Measurement — FX Adaptation Study

**Document ID:** EXP-2026-04-RULEENGINE-FX-BACKTEST
**Created:** 2026-09-17
**Status:** SPEC — AWAITING APPROVAL (no code yet)
**Type:** Backtest / measurement study. Reuses the EXP-2026-03 gold rules engine logic
as read-only simulation over existing FX history. **No live orders. No new positions.**

---

## 1. Purpose & Scope

### 1.1 Why this study exists

The gold rules engine (EXP-2026-03) is mostly instrument-agnostic logic: M30 5-bar
fractal levels, H1 EMA(20/50) bias, a WATCH→BREAK→RETEST→ENTRY→MANAGE state machine,
R:R / risk / concurrency gates, and BE-50 / structural-trail / invalidation management.
The operator proposal (2026-09-17): can these *same rules* trade other pairs — e.g.
EURUSD — as a complementary, deterministic "second column" beside the existing ML+LLM
pipeline?

This study answers that question **on paper, at zero capital risk**, by running the
deterministic rules over the FX history we already own and measuring:
  - Would-be entry frequency over a realistic window (is the setup too rare?)
  - R-multiple outcomes per entry (win/loss distribution under the engine's atomics)
  - EV/R per pair, computed the same way as the gold engine's claims
  - Setup cadence vs the gold benchmark (~0.4 setups/day) for tradeability

### 1.2 Explicit non-goals (what this study is NOT)

| Non-goal | Why |
|---|---|
| NOT a live experiment | No positions, no orders, no money at risk. Purely measured. |
| NOT a rebranding of the ML pipeline | The FX ML book (EURUSD/GBPUSD/USDCHF/USDCAD) already exists and is untouched by this study. |
| NOT a threshold/parameter workshop | We test the v1 gold atomics (with per-symbol unit re-normalization only — §3.3), not a parameter sweep. |
| NOT building a second live engine yet | If the paper measurement is positive, a separate Claim-D experiment is specified and gated (§6). |

### 1.3 Why this is cheap and honest

- We already hold ~315,000 H1 bars/pair (~3.5 years) for EURUSD, GBPUSD, USDCAD,
  USDCHF, USDJPY (plus USDX/WTI/XAUUSD).
- The engine is deterministic (no randomness, no LLM in the loop), so the backtest is
  **exactly reproducible** — same inputs → same decision sequence, every run.
- The cost of the measurement is bounded: one read-only MT5 fetch of M15/M30 history
  per pair, plus CPU minutes. No capital. No exposure.

---

## 2. Data & Timeframes

### 2.1 Existing assets (verified on disk 2026-09-17)

| Symbol | H1 CSV rows | Span | Note |
|---|---|---|---|
| EURUSD | 47,992 | 2019-01-02 → 2026-09-17 | Offline data current to today |
| GBPUSD | 47,992 | 2019-01-02 → 2026-09-17 | Same span |
| USDCAD | 47,992 | 2019-01-02 → 2026-09-17 | Same span |
| USDCHF | 47,992 | 2019-01-02 → 2026-09-17 | Same span |
| USDJPY | 47,152 | 2019-01-02 → **2026-07-30** | Stops at the ML-kill date (consistency check: the exact weekend the model was killed) |
| XAUUSD | ~290,000 | (reference) | Engine already validated live here |

(`fetch_ohlcv` was writing ~315K-row estimates to these CSV paths via `symbol_H1.csv`;
the actual on-disk files hold the 47,992-row live caches. The spec uses the file
that exists, and re-verifies the span before each run.)

### 2.2 Missing lower timeframes — the blocking requirement

The gold engine's structural core consumes **M30** (fractal levels) and **M15**
(decision bars). Neither is on disk for FX pairs, and they are **not derivable from
H1** (downsampling H1→M30 loses bars; the opposite direction is impossible).

**Required acquisition (read-only, one-time per pair, via the existing
`frival/gold_rules/tests/fetch_data.py` pattern):**
- M30 history: ≥ 200 completed bars warm-up + measurement window after it
- M15 history: ≥ 15 mm bars warm-up + full measurement window
- H1 history: already present; used for bias warm-up (≥ 50 bars)

MT5 `copy_rates_range` returns closed bars already; the G1 "no forming bar" filter
(§G1 fix, live) is applied identically.

### 2.3 Window structure (per pair)

```
[ warmup: 200 M30 + 50 H1 + 15 M15 ]   [ MEASUREMENT WINDOW: last N closed bars ]
```

- **Measurement window target:** ~60–90 **calendar days** of closed M15 bars per
  pair (≈ 5,700–8,600 M15 bars), chosen to produce a statistically useful count of
  would-be confirmations at the gold-observed cadence (~0.4/day → ~24–36 per 60–90d).
  This is the count target; the exact value is capped by data availability.
- Window end: **the most recent closed bar at fetch time** (fresh markets, not dated).

---

## 3. Method (exactly mirroring the gold engine)

### 3.1 Rules and constants — 1:1 reuse

The engine object (`GoldRulesEngine`) is instantiated **unmodified**. Every rule is
taken from the gold contract:

| Group | Source |
|---|---|
| H1 bias | EMA(20/50) + price position (§2.1.1) |
| Levels | 5-bar M30 fractal, 200-bar lookback, merge at 0.5×ATR_M30, consumption on solid-body close (§2.1.2) |
| Entry | Variants B (break→retest) and R (rejection→break); Claim C (breakout) is **excluded from the base spec** (§3.4) |
| Gates | location ≤ 0.15×ATR_M15 (floor), R:R ≥ 1.5, risk ≤ $25-equivalent, ≤1 position, daily cap |
| SL | invalidation level + buffer (`max(0.05×ATR_M15, floor)`), §2.7.1 |
| Management | BE at 50% of entry→TP1; structural trail; invalidation close |
| G1/G2/G3 | closed-bar only; wick ≠ signal; no anticipation |

### 3.2 Simulation loop (deterministic)

For each closed M15 bar t in the window:
1. Feed (M15[..t], M30[..t], H1[..t]) to the engine → decision.
2. Record `action`, `reason`, `state`, `bid/ask`, `gate_results`.
3. On `ENTRY` (would-be fill): simulate entry at that close, **open a simulated
   position**, and replay subsequent bars until:
   - SL hit (broker SL from the engine config) → R = −1 (plus buffer effect),
   - TP hit → R = |entry−TP| / |entry−SL|,
   - invalidation close → R computed at the close price,
   - or window ends → mark EMPTY (position still open at end).
4. Apply the concurrency gate: one simulated open position blocks subsequent
   would-be entries. Apply the `$50/day` equivalent cap to the simulated book.
5. Emit a per-pair ledger: `{entry_time, entry_px, sl, tp, exit_time, exit_px,
   close_kind, R, sim_pnl_usd}`.

### 3.3 Unit re-normalization (the ONLY permitted deviation from gold)

Price-scaled floors are **re-based to the pair's own price scale**, because a `$1.00`
floor means nothing on EURUSD (pip = 0.0001). The mapping:

| Gold constant | FX-equivalent rule |
|---|---|
| `location_tolerance_min_usd: 1.00` | `1.00 × standard deviation of paired M15 close-to-close` computed per pair (≈ a "natural pip" unit), floored at 1 pip |
| `sl_buffer_min_usd: 0.30` | same per-pair unit scale ×0.3 |
| `max_risk_usd: 25.00` | expressed as **R-relative, not $-relative**: simulated risk = |entry−SL| × lot × contract; lot = **0.01** fixed, contract = per-pair `symbol_info` (100,000 for FX). $ cap = 25.00 × (ATR_EURUSD / ATR_XAUUSD) reference? **NO** — see note below. |

**Critical decision — dollar cap on FX:** at 0.01 lots, EURUSD $25 risk ≈ 250 pips of
distance — the cap would never bind, which makes the backtest *too permissive*. The
spec preserves the engine's *risk posture*, not its raw dollars: **the $25 cap scales
to the pair's ATR:** `cap_usd_pair = 25 × ATR_M15_pair ÷ ATR_M15_XAUUSD` computed once.
This keeps "max ~2.5× ATR of loss" philosophically identical to gold. The scalar is
logged and fixed before the run — not tuned after seeing results.

### 3.4 Claim C excluded from the base spec (for clean attribution)

The breakout-continuation variant (Claim C) is a *new* hypothesis with its own F2 gate
on gold. Including it in this first FX measurement would mix two unproven hypotheses
at once. **Base spec runs A/B only.** A follow-up spec (v2) can enable C and compare.

### 3.5 Data leakage controls

- Warm-up precedes window; no bar used for both warm-up and simulation start.
- Levels are recomputed **only from bars already closed** at bar t (the engine's own
  lookahead-free design; no future information).
- No parameter is tuned against the window's outcomes. The run is one-pass.

---

## 4. Measurements & Outputs

Per pair, the study emits:

| Metric | Definition |
|---|---|
| Setup cadence | confirmed-before-gates entries per day (the gold benchmark: ~0.4) |
| N entries (would-be fills) | count of `ENTRY` actions with gates passing |
| Win% | positive-R simulated exits / N |
| EV/R | mean simulated R (the gold claims use this exact statistic) |
| Median R, best/worst | tail shape (are losses tight −1R? are wins fat?) |
| Sim PnL $ | sum of simulated PnL at fixed 0.01 lot × per-pair contract |
| Sim $50/day violations | days where simulated book exceeded the daily cap (safety check) |
| Empty exits | positions still open at window end (censoring note) |

A per-trade CSV + a journal-style decision log are emitted per pair for audit.

### 4.1 Pair list for the first pass

| Pair | Why included |
|---|---|
| EURUSD | Operator request; deep liquidity; direct comparison vs the ML book |
| USDJPY | ML-killed; zero engine overlap — cleanest independent Claim-D candidate |
| GBPUSD | 2-trade +EV evidence in the current FX book; different quote scale |
| USDCAD | Alternative quote scale (CAD); smallest FX book near-flat EV |

(USDCHF, USDX, WTI, XAUUSD available; not in first pass to keep the study bounded —
XAUUSD is the validated reference, not a test.)

---

## 5. Acceptance / Interpretation

**Decision rule (paper version of Claim D):**

| Outcome | Interpretation |
|---|---|
| EV/R > **+0.3** AND cadence ≥ 5 entries/window-month | Rules plausibly tradeable on this pair → proceed to a Claim-D LIVE spec at 0.01 lots with shadow-first recommendation (§6) |
| EV/R in (−0.2, +0.3] | Inconclusive — expand window, do NOT proceed to live without more data |
| EV/R ≤ −0.2 | Rules do not transfer to this pair as configured — do NOT proceed; document regression vs gold |

### 5.2 Ownership rule (operator decision 3 — RECORDED 2026-09-17)

**One engine owns a pair at a time. No sharing, ever.**

Generalizes the gold §1.4 no-overlap rule to the symbol level: two books trading
the same symbol in the same window make win/loss attribution unreadable, so the
rules book and the ML book never trade the same pair simultaneously.

| Pair | Owned by today | Rules-book live path |
|---|---|---|
| USDJPY | **Nobody** (ML killed 2026-07-30; history stops exactly at the kill date) | **First live target** if paper EV/R > +0.3 — cleanest measurement (zero overlap) |
| EURUSD | ML book (core + AGNOSTIC shadow) | Requires formal **ownership transfer** (ML yields for a full measurement period) before rules book goes live |
| GBPUSD | ML book | Same transfer rule, gated on that pair's paper result |
| USDCAD | ML book | Same transfer rule, gated on that pair's paper result |

Evidence basis for the transfer posture: the 8-trade current-window measurement on
the ML book put EURUSD at EV/R ≈ **+0.05** (statistical zero). A rules-book tender on
EURUSD would therefore be an evidence-based transfer, not a grab — but it still
requires ML to yield, and the yield is the cost of clean attribution.

**Sequence:** (1) backtest all four now (ownership-agnostic, read-only);
(2) first live Claim-D pilot → USDJPY if its paper EV/R clears +0.3;
(3) any ML-owned pair goes live in the rules book only via documented transfer;
(4) if the ML side's evidence on a pair is stronger, the pair stays ML-owned and the
rules book does not touch it.

---

## 6. Follow-on (only if the paper says yes)

A v2 spec / new EXP for a **Claim-D live pilot** would require, separately:

1. Symbol deconfliction decision (EURUSD conflicts with the ML book — would need an
   ownership rule: e.g. rules book and ML book on the same pair is disallowed; if
   EURUSD is the target, ML must yield the pair or a schedule must split it).
2. Its own comment tag (`RULES_D_<PAIR>`), its own $50/day cap accounting, its own
   concurrency book, and its own 30-trade F2 gate (mirror of gold §7).
3. A shadow-first period on the *specific pair* (paper backtest is not live shadow —
   this is a NEW instrument for a NEW claim; the review standard is stricter, not
   looser: gold skipped shadow because it replayed known rules at 0.01; FX D would be
   a new application of those rules and the operator has already shown the capability
   that makes manual overlap the actual uncontrolled variable).

---

## 7. Known limitations (said out loud)

1. **Backtest ≠ live.** Liquid FX has fast fills, wider M15 microstructure than gold,
   and session gaps (weekends). Simulated fills at M15 closes are an approximation.
2. **0.5×ATR merge and 0.15×ATR location tolerances were tuned on gold's volatility
   shape.** FX ATR_M15 is far smaller relative to price; the re-normalization (§3.3)
   keeps the *form* but is itself an assumption until the run says otherwise.
3. **Session structure.** The gold engine idles through the daily halt via
   bar-freshness. FX has weekend/35-hour gaps; the same pause logic applies, but the
   study must confirm it doesn't mis-flag a Friday-close as a broker halt.
4. **Small counts are possible.** At ~0.4/day-style cadence, even 90 days may yield
   <20 would-be entries per pair. That result is *itself a finding* (too rare to be a
   useful trading system at these rules) — and it is reported as such, not hidden.

---

## 8. Deliverables

| # | Deliverable | Done when |
|---|---|---|
| 1 | Data acquisition script (read-only M15+M30 fetch per pair, warm-up+window cache) | Bars cached; closed-bar filter applied; reproducibility check (same run → same bars) |
| 2 | Single-pair backtest runner (engine, unmodified + unit-normalization wrapper) | One pass over the window emits the §4 ledger + decision log |
| 3 | Per-pair report (metrics table §4 + trades CSV + EV/R summary + journal) | Numbers reproducible across runs |
| 4 | Cross-pair comparison sheet + interpretation memo | EV/R decision rule (§5) applied; explicit proceed/hold/stop per pair |
| 5 | Spec v1.1 amendment if C or a 4th pair is added post-review | Documented, not silent |

---

## 9. Operator decisions required before build

1. **Approve the pair list** (EURUSD, USDJPY, GBPUSD, USDCAD) — **APPROVED 2026-09-17**.
2. **Approve unit re-normalization** (§3.3) — including the ATR-scaled $25 cap
   rule, the one deliberate deviation from gold's raw constants — **APPROVED 2026-09-17**.
3. **Confirm the no-touch rule for the measurement window** — no manual or ML
   trades on the measured pairs during the fetch + run — **plus the ownership
   rule RECORDED at §5.2** (one owner per pair, no sharing; USDJPY = first live
   target; EURUSD/GBPUSD/USDCAD = transfer-only) — **approved 2026-09-17**.

---

*End of spec. No code is written. This document is a measurement contract: the run
is one-pass, deterministic, and auditable — same inputs, same verdict, every time.*