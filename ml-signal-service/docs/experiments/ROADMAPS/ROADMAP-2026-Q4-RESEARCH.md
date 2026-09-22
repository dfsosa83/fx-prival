# Frival Research Roadmap — 2026 Q4

**Created:** 2026-09-18
**Status:** DISCUSSION CONTRACT — baseline methodology approved; this document lists
only additive corrections and new experiments, not a rewrite.
**Scope:** FX-ML + XAUUSD-rules (both in paper trading) → next experiments, labels,
universes, validation, structure, dashboard evolution.

---

## 0. Executive summary

> **Status as of 2026-09-22 (read this first):** every item in the numbered list
> below has been executed and resolved — see **§0.1** (evidence table) and
> **§0.2** (portfolio conclusions and decision-gated next steps) for the
> current, authoritative status. The list is kept as the historical plan as
> first written on 2026-09-18; do not read it as a pending to-do. A full audit
> of this document, including gaps/inconsistencies/risks and a re-prioritized
> next-steps list, is in the companion document
> `ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md` (2026-09-22).

The existing ML training methodology (chronological split, ATR-barrier labels,
threshold-vs-breakeven calibration, purged embargo CV already present in the
production notebooks) is sound and is the **default foundation**. The same
three additive deficiencies as before were confirmed on read (Section 2); the
bootstrap-methodology correction (labels/trades are serially overlapping, so a
naive per-trade IID bootstrap understates uncertainty) is folded into Issue B
rather than counted separately. Each issue keeps its smallest-practical fix.
The most important next experiments, in order **(as planned 2026-09-18 — see
status note above for what actually happened)**:

1. **Shared cost + bootstrap infrastructure** (`experiments/_core/costs.py`,
   `experiments/_core/bootstrap.py`) — prerequisite plumbing for everything below;
   one source of truth for per-pair round-trip friction and for a block bootstrap
   that respects label/trade overlap.
2. **Cost-adjusted label** (spread + slippage aware TP barrier) — the highest-
   information, smallest-delta experiment. Directly answers "profitable *after*
   realistic costs". Full execution spec in §9, P0.1 — this is the recommended
   first implementation task.
3. **Block-bootstrap CI on EV/R** for every backtest output, using the shared
   `_core/bootstrap.py` (not a naive IID resample — see Issue B).
4. **Liquid-cross book** (EURGBP, GBPJPY, EURJPY) — for *diversification* first,
   edge second.
5. **Single equity-index ML experiment** (NAS100 or US30) on a parallel demo
   account — tests whether our stack finds edge outside FX, gated on confirming
   CFD-specific execution mechanics (financing, dividend adjustments) first.

Everything below is the full contract behind these priorities. §9 now specifies
each backlog item to implementation-agent standard: objective, files, inputs,
outputs, validation checks, and an explicit go/hold/stop decision gate.

---

## 0.1 Evidence table — experiments completed (authoritative status)

All experiments executed with pre-registered manifests (Issue A), a frozen cost
source (`experiments/_core/costs.py`), block-bootstrap 95% CIs (Issue B), and a
single one-shot sealed-test scoring per the GO/HOLD/STOP gates in §9.

| EXP | Instrument / question | Verdict | Sealed-test evidence | Where recorded |
|---|---|---|---|---|
| **05** | EURUSD SELL, cost-adjusted TP | **HOLD** | precision 0.387 vs 0.40 breakeven; **EV/R −0.03, CI [−0.52, +0.45]** (straddles zero — insufficient evidence, not dead) | `experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/` |
| **06** | EURUSD BUY, cost-adjusted TP | **STOP** | precision 0.355, roc_auc 0.504 (≈coin flip); **EV/R −0.111, CI [−0.197, −0.021]** (wholly below zero — significant) | `experiments/EXP-2026-06-EURUSD-BUY-COSTLABEL/` |
| **P0.2** | Retrofit cost+CI into *all* reporting | **DONE** | cost-adjusted EV/R flipped all 4 backtest pairs to STOP net of cost; friction ≈0.4R on ~3-pip stops | `frival/dashboard/backend/tag_metrics.py`, `frival/fx_rules_backtest/report.py` |
| **07** | Crosses (EURGBP, GBPJPY, EURJPY) | **ABORTED (economics)** | spread 4.7/13.6/10.6 pips = **0.53–0.56R per trade** → ~62% breakeven precision required; no TP/SL geometry rescues (label rate collapses below 15% floor); **no scoring spent** | `experiments/EXP-2026-07-CROSSES-COSTLABEL/` |
| **08** | US30 (Dow) SELL, cost-adjusted TP, account A3 | **STOP** | precision 0.329 vs 0.40; **EV/R −0.178, CI [−0.261, −0.104]**; **roc_auc 0.660 = real ranking skill** at 0.03R friction | `experiments/EXP-2026-08-EQUITY-INDEX-COSTLABEL/` |
| **09** | US30 SELL, label-geometry redesign (TP 2.0/SL 1.0) | **STOP — hypothesis falsified, informatively** | precision 0.268 (worse); **roc_auc 0.687 (better!)**; **EV/R −0.197, CI [−0.292, −0.093]** | `experiments/EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN/` |
| **manual** | Operator's real gold trading (live a/c 81486396) — the "real recorded PnL" premise | **NET LOSS** | 139 trades, **net −815.25**, PF 0.94, 55.4% win, avg win 166.68 vs avg loss −220.15, **max DD 107%** | `notebooks/xauusd/ReportHistory-81486396.xlsx` (statement summary) |
| **10** | Gold exit-management (operator-SL-anchored policies) | **STOP** | every policy far worse than actual (EV −$155…−$180/trade; win rate collapses to 12–29%) — **confounded**: operator SLs (median 8 pts) are below typical M5 bar range (4.15) / H1 ATR (5.0) | `experiments/EXP-2026-10-GOLD-EXIT-MANAGEMENT/` |
| **11** | Gold exit-management (ATR-anchored, fair anchor) | **STOP (gate overridden by robustness)** | only 1×ATR/3R positive (+$8,689, PF 1.15) — but **3 trades drive it** (−$4,325 without them), **all profit in one week** (wk38 +16,941), **simulated max DD −$58,697** | `experiments/EXP-2026-11-GOLD-EXIT-ATR/` |

**Production artifacts verified untouched** at every scoring (cost-label forks write
`<PAIR>_<dir>_costlabel_<model>.joblib`; never the live bundles).

---

## 0.2 Portfolio-level conclusions and next steps (2026-09-22)

### What six experiments established

1. **Costs dominate FX directional edge.** EURUSD BUY/SELL and the P0.2 retrofit
   all show the same pattern: at 2–8 pip targets and 1.2–1.6 pip spreads plus
   0.4R friction on ~3-pip stops, the raw EV/R numbers never survived realistic
   friction.
2. **Crosses are geometrically unwinnable at this label.** 0.53–0.56R of spread
   per trade on 8–26 pip ATRs forces ~62% breakeven precision (vs the 35–39%
   this model family actually achieves). Not a tuning problem — an arithmetic one.
3. **Not the instrument, and not friction.** US30 — the clean-lab instrument
   (0.03R friction, 30× lower than crosses) — still failed precision, **but
   showed the best ranking skill in the whole program (roc_auc 0.660→0.687)**.
4. **The label geometry is the binding constraint — and widening it is not the
   fix.** The TP2.0/SL1.0 redesign *improved* skill (0.660→0.687) while
   *worsening* precision (0.329→0.268): the model can rank H1 trades, but cannot
   convert that ordering into breakeven precision under the ATR-triple-barrier
   hit/miss label, at any geometry.

**Bottom line:** six experiments, zero GO. The findings narrow the fault line to
a single target: the **triple-barrier hit/miss label** itself — not costs, not
instrument, not barrier width.

### Next steps — decision-gated (per the P2 rule: only proceed if the gate opens)

> **Decision taken 2026-09-22: Option A.** The directional-ML program is closed —
> a read-only diagnostic on the already-scored US30 ledgers showed no usable
> operating point in the tradeable region (see
> `ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md` §6.1), on top of six experiments with
> zero GO. **Correction:** the phrase below, "the only asset with real recorded
> PnL," was **wrong** — the gold engine is in demo mode, its orders are simulated,
> and its trades self-close with `pnl: 0.0` (audit finding G7). Nothing in this
> project has real recorded PnL. The gold pivot is therefore re-scoped to start
> with fixing the gold engine's demo evidence loop.

| Option | Description | Status |
|---|---|---|
| **A. Close the directional-ML program** | Record the negative; re-point research budget at the gold engine or a structurally different signal family (e.g., mean-reversion/range, exit-timing). **Correction: gold is *not* a proven asset — it has no usable PnL record (G7). The first gold task is fixing its demo evidence loop, then accumulating a track record.** | **CHOSEN 2026-09-22** |
| **B. One structurally different label design** | NOT another variant of this one. Candidate: rank/precision-oriented target (train on ranking loss or precision-at-threshold), or spread-relative targets, or regression to expected R. Same one-shot gate, US30 (where skill is documented). *(The ID `EXP-2026-10` was later used for the gold exit-management study, not this.)* | **CLOSED by diagnostic** (no operating point in the tradeable region — audit §6.1) |
| **C. Operational refinements (no new hypothesis)** | §6.1 measurement (slippage/spread-at-fill) once real fills exist; demo continues; journal the (low) swap/session evidence. | Open, non-blocking |

The recommendations do **not** include: more TP/SL multiplier variants (falsified),
EURUSD/GBPUSD variants of the same label (Issue-A budget exhausted), or reopening
EXP-2026-07 (arithmetically dead).

---

## 1. Baseline methodology — APPROVED (read as truth)

### 1.1 The label currently in production (verified from notebooks)

Both FX models use a **triple-barrier-style TP-hitting label**, not plain
directionality. This is a genuine strength — no change proposed.

| Parameter | BUY model | SELL model |
|---|---|---|
| Notebook | `notebooks/eurusd/eurusd_buy_improved.ipynb` | `notebooks/eurusd/eurusd_sell_improved.ipynb` |
| Entry | `close[t]` (simulated long) | `close[t]` (simulated short) |
| TP | `close + ATR(14) × 1.5` | `close − ATR(14) × 1.5` |
| SL | `close − ATR(14) × 1.0` | `close + ATR(14) × 1.0` |
| Forward window | `FORWARD_BARS = 6` (H1 bars) | `FORWARD_BARS = 6` (H1 bars) |
| Label = 1 | TP touched first, no SL before, within 6 bars | mirror |
| Label = 0 | SL first / timeout / no outcome | mirror |
| Ambiguous same-bar | **excluded as NaN** (not 0) in `eurusd_buy_improved` | same convention per code comments |
| R:R | 1.5 : 1.0 | 1.5 : 1.0 |
| Breakeven win-rate | `SL/(TP+SL) = 1.0/2.5 = 40%` | 40% |

**Chronological split (varies by notebook — verify per fork):**
```
SELL:  TRAIN 2020-06-30→2025-06-30 | VAL 2025-07-01→2025-12-31 | TEST 2026-01-01→present
BUY:   TRAIN 2020-06-30→2025-10-31 | VAL 2025-11-01→2026-03-31 | TEST 2026-04-01→present
```
*(The BUY notebook uses a newer boundary than SELL; each fork inherits its own
production notebook's dates. Caught during EXP-2026-06 — manifest initially
documented SELL's dates, corrected in the experiment's RUN_LOG.)*

The threshold is calibrated against the **40% breakeven precision** implied by the
R:R — every threshold value in this project's history (`0.276`, `0.334`, `0.365`,
`0.5`) is measured against that 40% bar. Good. This is the metric architecture the
roadmap preserves.

**Verified-on-read, previously undocumented strengths** (from
`eurusd_sell_improved.ipynb`, confirmed 2026-09-18 — worth recording so future
audits don't re-flag them as gaps): the production notebook already runs (a) a
**purged expanding `TimeSeriesSplit`** with a 30-day embargo for internal
hyperparameter CV, (b) **noise-feature benchmarking** (real features must beat
random Gaussian/uniform/Poisson columns on importance before being kept), (c)
**isotonic probability calibration**, and (d) a **minimum-signal floor**
(`MIN_VAL_SIGNALS = 50`) before a threshold is eligible, specifically to avoid
"lucky handful of signals" overfitting. The threshold-selection code comment
documents a live example of Issue A below (a volume-weighted pick that looked
better on validation slipped below breakeven on the sealed test) — this is
direct evidence Issue A is real, not speculative.

### 1.2 The XAUUSD rules experiment (non-ML, separate)

- **EXP-2026-03 (`docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md`)**:
  deterministic A/B level-test + Claim C breakout, 0.01 lots, in paper/demo. It is
  a *rules* experiment, deliberately outside the ML label framework.
- **EXP-2026-04 (`docs/experiments/EXP-2026-04-RULEENGINE-FX-BACKTEST.md`)**: the
  FX compatibility backtest — measured negative EV/R on all 4 study pairs,
  USDJPY STOP. **Result already banked: the A/B gold rules do not transfer to FX
  as-is.** No live Claim-D was opened. This is a *closed* finding, not a gap.

---

## 2. Methodological audit — 3 additive corrections (NOT a rewrite)

Each is specific, material, and smallest-change.

### Issue A — Multiple-testing surface is unaccounted

- **What.** Many thresholds/features/labels have been tried across pairs and gold
  attempts; the fixed test set has been viewed more than once.
- **Why it biases.** Thresholds chosen on a seen test set overstate true OOS
  precision by a small but real amount; at the ~40% breakeven boundary, that can
  flip a verdict.
- **Severity.** Medium. It cannot fabricate a strong edge; it can make a marginal
  one look clean.
- **Smallest fix.** In each experiment manifest: pre-register the primary metric
  and *variants tried*, and before declaring a pair "go", score a **fresh calendar
  window never touched by tuning** (e.g., the last quarter withheld from all
  threshold decisions).

### Issue B — Single fixed test window, no robustness band, and trades are not IID

- **What.** One hold-out = one point estimate of precision/EV. In addition, the
  label construction (`FORWARD_BARS = 6` forward-scan) and the signal cadence
  mean consecutive trades can have **overlapping outcome windows** — trade `t`'s
  and trade `t+1`'s realized R are not statistically independent when they fire
  within `FORWARD_BARS` of each other (this is the classic "label overlap"
  problem: overlapping windows share the same underlying price path, so their
  errors are correlated). Production gating (`signal_gate.py` cooldown, 4 bars
  default) reduces this in **live** trading, but ad-hoc backtests that score
  every bar's hypothetical signal without the cooldown gate still overlap.
- **Why it biases.** Fat tails + a 6-month window can be one lucky/unlucky regime
  (the Aug–Sep 2026 USD move biased the current small FX sample). Separately, a
  **naive IID bootstrap over overlapping trades understates the true variance**
  of the EV/R estimate — it treats correlated outcomes as independent draws,
  producing a CI that is narrower than reality and can make a noisy result look
  like a confirmed edge.
- **Severity.** High for any "proven edge" claim; low for the workflow itself.
- **Smallest fix.** Two parts, both cheap:
  1. **Moving-block bootstrap**, not IID bootstrap: resample contiguous blocks of
     trades (block length = `max(FORWARD_BARS, median gap between signals in
     bars)`), 1,000 resamples, report the 95% CI on per-trade EV/R. This is the
     same 1,000-resample budget as before; the only change is sampling *blocks*
     of the ordered trade sequence instead of individual trades. Implemented
     once in `experiments/_core/bootstrap.py` (§7, §9 P0.0) and reused everywhere.
  2. Always report **both** the gated backtest EV/R (cooldown applied, what
     production actually sees) and the ungated raw hit-rate (diagnostic only,
     clearly labeled) — never blend the two into one number.

### Issue C — Cost & execution-realism model is optimistic and incomplete (confirmed live)

- **What.** Backtests historically used `ask=bid` (zero spread); live Standard
  account pays spread embedded in ask/bid with **no commission line**. The
  measured spread (2026-09-18: EURUSD 1.2 pips, GBPUSD 1.6, USDCHF 1.5, USDCAD
  1.5, USDJPY 1.3, XAUUSD ~0.28 gold-pips) is **spread only**. Three further
  friction/realism sources are currently absent from every backtest and from the
  paper-trading cost accounting:
  1. **Slippage** — the execution bot's `deviation_points: 5` (order_bot config)
     is a *tolerance*, not a measured cost; realized slippage (intended signal
     price vs. actual MT5 fill price) has never been logged separately from
     spread.
  2. **Financing/swap** — `order_manager.py` and `mt5_connector.py` already read
     `deal.swap` / `pos.swap` from MT5, but no backtest or label subtracts swap.
     `FORWARD_BARS = 6` H1 bars usually closes intraday, but a signal fired late
     in a session can hold through a daily (or triple, Wednesday) rollover — this
     is a real, currently unmeasured cost, not a theoretical one.
  3. **Session liquidity** — spread and slippage are not constant across
     sessions; the 1.2–1.6 pip figures above are point-in-time, not session-
     conditioned (Asian-session spread on EURUSD is routinely 2–3× the London/NY
     overlap spread). A single flat `round_trip_cost_pips` per pair silently
     averages this away and can flatter session-conditioned strategies.
- **Why it biases.** At 2–8 pip targets and 1.2–1.6 pip spreads, a large share of
  signals are below friction; paper PnL (+$5/−$6 per trade) reflects this even
  before slippage/swap are added. Ignoring session-conditioned spread understates
  cost for any signal that clusters in thin liquidity.
- **Severity.** High — the largest research↔paper gap, and it is currently
  *understated* even where it is modeled (spread-only, session-flat).
- **Smallest fix.** One shared module, `experiments/_core/costs.py` (§7, §9
  P0.0), holding per-pair, per-session `round_trip_cost_pips = spread + slippage`
  (slippage measured empirically from the first 30 live/paper fills per pair —
  do not guess it), subtracted in backtests *and* embedded in the cost-adjusted
  label (§3). Swap is **not** folded into the per-trade cost constant (it is
  regime- and direction-dependent, changing sign with rate differentials);
  instead it is tracked as a **separate diagnostic line** in the paper-trading
  report (§6) so a swap-driven drag is visible and attributable, not silently
  netted into EV/R.

**Conclusion.** The three fixes (A, B — now including the overlap-aware block
bootstrap — and C) are additive parameters/plumbing, not architecture changes.
The label framework, split design, and threshold philosophy stand.

---

## 3. Target variables to test (since the baseline label is already triple-barrier)

Baseline Y is **"TP-first within 6 bars at 1.5R"**. That obsoletes my earlier
suggestion to "test triple-barrier as new" — it exists. The genuine increments:

| # | Label | Definition | Verdict |
|---|---|---|---|
| 1 | **Cost-adjusted TP** | `label=1` only when `high[j] ≥ TP + spread` (BUY) / `low[j] ≤ TP − spread` (SELL); same 6 bars, same ATR, same split | **Test first.** One line in label loop; directly ties Y to net-of-friction profit. |
| 2 | **Margin-aware R** | Keep 1.5R but require `TP − ask ≥ SL − ask` *after* spread | Variant of #1 for ATR/price-space edge cases; lower priority than #1 |
| 3 | Time-to-barrier (regression) | Bars until TP touch | Informative for exit models, weak standalone; **defer** |
| 4 | Regime labels (trend/range) | Y = regime state | Only useful as a *feature/condition*, not a target; **defer** |
| 5 | Vol-adjusted opportunity | Forward vol-normalized return > z | Already implicit (ATR-adaptive barriers = vol-adjusted); **drop** |

**Priority: implement #1 on EURUSD SELL first** (smallest delta to production),
then EURUSD BUY, then crosses when added. Full execution spec: §9 P0.1.

**Note on overlap.** The cost-adjusted label inherits the same forward-scan
window structure as the baseline (only the TP threshold changes), so it does
not introduce a new label-overlap problem — the correction for overlap belongs
at the *evaluation* layer (Issue B's block bootstrap), not the label layer.

---

## 4. Asset-universe expansion

### 4.1 FX additions — honest trade-offs

| Universe | Candidates | Verdict |
|---|---|---|
| Liquid crosses | EURGBP, GBPJPY, EURJPY | **Yes, first.** USD-independent → genuine diversification for the 4-USD-pair book. Spreads 1–3 pips. |
| Commodity-linked | AUDNZD, AUDCAD | Yes after crosses. |
| EM / exotic | USDTRY, USDZAR, USDMXN | **No.** Wide spreads 10–100 pips; cost-aware label will reject most signals; data quality risk. |
| More USD-majors | AUDUSD, NZDUSD | Only after cross value is exhausted (they concentrate, not diversify). |

### 4.2 Beyond FX — intellectually honest

FX H1 with moderate-cost machinery is a hard area to beat; our evidence is
consistent with that (near-40% precision, thin EV/R, cost-dominated small trades).

| Asset class | Verdict |
|---|---|
| **Equity indices** (NAS100, US30, GER40, UK100) | ~~Highest priority alternative~~ **TESTED 2026-09-21/22 (`EXP-2026-08/09`): US30 SELL scored STOP both at TP1.5 and TP2.0 geometry.** The instrument's low friction (0.03R) delivered the program's best ranking skill (roc_auc 0.66→0.69) but precision never cleared breakeven — see §0.1/§0.2. Do not retest this exact label family on another index without a structural change. |
| Sector ETFs (if broker offers as CFD) | Medium; useful for rotation research. |
| Commodities (WTI, copper) | Medium; fits framework, cost/carry caveats. |
| Rates/futures (bund, SOFR) | Low with this stack. |
| Crypto CFDs | Medium after a clean equity result; vol is flattering, crowded. |

**Execution-realism prerequisite for the equity-index experiment (do not skip):**
index CFDs are not FX spot. Before any backtest number for NAS100/US30 is
trusted, confirm with the broker's contract spec: (a) **overnight financing
rate** (index CFDs roll daily, direction-dependent, and are typically larger
than FX swap), (b) **dividend-adjustment handling** (constituent dividends are
usually applied as a cash adjustment to open CFD positions on ex-date — if the
adjustment is not modeled, a SELL-side backtest can look artificially profitable
across dividend season), and (c) **session hours / halts** (index CFDs typically
have a daily maintenance break, unlike 24/5 FX — the existing `signal_gate.py`
session logic must be re-derived for the index's actual trading hours, not
copied from FX). This is a data-quality gate on the experiment, not a nice-to-have:
record the three answers in the experiment's `experiment.yaml` before backtesting.

---

## 5. Validation improvements (small, targeted)

- **Walk-forward** — formalize the existing retrain cadence as expanding-window,
  evaluate unseen trailing segment only. Smallest change to workflow.
- **Purged/embargo CV** — already present for internal hyperparameter folds
  (`PURGE_DAYS = 30`, expanding `TimeSeriesSplit`, verified in
  `eurusd_sell_improved.ipynb`). No change needed there. If K-fold is ever used
  directly on the train/val/test boundary (it currently is not — those are
  fixed chronological cuts), apply the same purge.
- **Overlap-aware significance** — Issue B fix (block bootstrap, not IID). This
  is the one true methodological gap: statistics have been computed as if
  trades were independent draws.
- **Cost & execution-realism model** — Issue C fix (Section 2): spread, slippage,
  swap, session-conditioning.
- **Multiple-testing control** — Issue A fix (Section 2).
- **Do not add** — adversarial validation, meta-labeling, feature-competition
  ensembles. Over-engineering for current capital.

---

## 6. Parallel MT5 demo accounts — isolation matrix

| Account | Purpose |
|---|---|
| A1 — `FPMarketsSC-Demo 7409623` | Current FX-ML (EURUSD/GBPUSD/USDCHF/USDCAD/AGNOSTIC) + gold rules. PnL attribution stays clean. |
| A2 — new demo | Cost-adjusted label experiments (EURUSD + crosses). |
| A3 — new demo | Equity-index experiment (when built). |

Constraint already proven on this machine: **one MT5 terminal = one logged-in
account.** Running 2–3 accounts means 2–3 portable MT5 terminal instances. The
dashboard reads all of them read-only.

> **Audit note (2026-09-22):** A2/A3 were never provisioned. All of
> EXP-2026-05 through 09 ran as offline backtests against historical H1 data
> pulled through the single existing account (7409623 demo) — none reached a
> GO, so no live/paper account was ever needed. If a future experiment (e.g. a
> `EXP-2026-10` redesign, or a gold-engine extension) reaches GO, A2/A3
> provisioning is a **new, unstarted task**, not something already in place.
> See `ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md` Priority 7.

### 6.1 Paper-trading diagnostics — separating signal quality from implementation quality

A negative paper result is ambiguous unless these are logged **per trade**,
starting with A2 (first cost-adjusted-label account) and required before any
GO decision in §9's decision gates:

| Metric | What it isolates | Source |
|---|---|---|
| Signal price vs. fill price (slippage) | Execution quality, not model quality | `order_bot.py` request price vs. MT5 `deal` price |
| Signal timestamp vs. order-sent timestamp (latency) | Pipeline/agent latency, not model quality | `signal_watcher.py` read time vs. `order_manager.py` send time |
| Spread-at-fill vs. spread assumed in backtest (`_core/costs.py` constant) | Cost-model drift, not model quality | MT5 tick at fill vs. static config constant |
| Gate rejection reasons (threshold/session/cooldown/MERG/candle-close) tallied per pair | Whether the model is firing but being filtered out, vs. not firing at all | `signal_gate.py` `failed` list, already emitted |
| Swap accrued per trade | Financing drag, direction- and regime-dependent | `deal.swap` (already read, not yet aggregated) |
| Requote/rejection rate | Broker-side execution risk | MT5 order result codes |
| Realized R vs. model-predicted probability (calibration-in-the-wild) | Whether live probabilities still track the validation calibration curve | paper trade ledger vs. saved `threshold`/`isotonic` bundle |

**Rule:** if paper EV/R is negative but slippage + latency + spread-drift
account for most of the gap to the backtest EV/R, the finding is "execution
needs fixing," not "the model has no edge" — and vice versa. Do not conflate
the two in any go/kill decision.

### 6.2 Risk-sizing — operator decision 2026-09-21: RESOLVED

`execution_bot/config/settings.yaml` previously set `max_daily_loss: 200.0`
(sized for a ~$3.2k live balance). Operator confirmed the demo account 7409623
holds **$5,000** and approved the resize: **`max_daily_loss: 100.0` (2% of
equity)** — sized above the ~$6/trade daily swing so it protects without
ending test days early and truncating a small sample non-randomly. Applied to
`settings.yaml`, the `run.py` env fallback (`MAX_DAILY_LOSS`), and this
document's execution-bot README gate table. The gold engine keeps its own
`daily_loss_cap_usd: 50.0` (independent cap, unchanged).

---

## 7. Experiment structure & reproducibility

```
ml-signal-service/
├── experiments/
│   ├── _core/                     # shared: labels, features, split, cost model, metrics, bootstrap CI
│   │   ├── costs.py                # per-pair, per-session round_trip_cost_pips; single source of truth
│   │   ├── bootstrap.py            # moving-block bootstrap CI (Issue B) — NOT a naive IID resample
│   │   ├── build_costlabel_fork.py # parameterized fork builder (--pair, --atr-tp/-sl-mult)
│   │   └── tests/                  # unit tests (assert cost sign; block→IID convergence; AR(1) wider CI)
│   ├── EXP-2026-05-EURUSD-SELL-COSTLABEL/      # HOLD
│   ├── EXP-2026-06-EURUSD-BUY-COSTLABEL/       # STOP
│   ├── EXP-2026-07-CROSSES-COSTLABEL/          # ABORTED (economics — no scoring spent)
│   ├── EXP-2026-08-EQUITY-INDEX-COSTLABEL/     # STOP (roc_auc 0.66 = skill)
│   └── EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN/  # STOP (hypothesis falsified)
│       └── each: experiment.yaml + RUN_LOG.md + smoke_*.py + run_exp.py + reports/
├── notebooks/eurusd/       # SHARED path: production notebooks + their cost-label forks
│                            # e.g. eurusd_sell_costlabel.ipynb — referenced by manifest, not copied in
├── notebooks/crosses/      # SHARED path: cross/index forks (eurgbp_sell_costlabel.ipynb, us30_*.ipynb)
└── models_bin/             # SHARED path: trained bundles, incl. <PAIR>_<dir>_costlabel_<model>.joblib
```

> **Audit note (2026-09-22):** the notebook fork and the trained model bundle
> live in the two **shared** paths above (`notebooks/eurusd|crosses/`,
> `models_bin/`), referenced from each experiment's `experiment.yaml` — they
> are **not** nested inside the experiment folder. The originally-planned
> per-experiment `data/`, `features/`, `models/`, `backtests/`, `papertrading/`
> subfolders exist on disk but are empty/unused in every experiment (05, 06,
> 07, 09); a cleanup pass should either populate them with real per-experiment
> copies or remove them (`ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md` Priority 6).
> EXP-2026-08 is also missing a `README.md` that 05/06/07 have.

Each experiment folder carries: `experiment.yaml` (pre-registration: pair, label,
frozen cost, primary metric, GO/HOLD/STOP gate, variants_tried), `RUN_LOG.md` (one
dated entry per run; sealed test scored once), `smoke_*.py` (label-layer
validation on real data, no training), `run_exp.py` (headless nbclient runner,
env-hardened for memory), and `reports/` (test_metrics.json + test_signals.csv).

Naming convention follows the existing docs: `EXP-2026-NN-<TAG>`, continuing
from the registered `EXP-2026-03` (gold rules), `EXP-2026-04` (FX-rules
backtest, closed), and the five completed ML experiments above. `_core/` holds
the methodology once; each experiment only redefines its manifest + config.
Existing artifacts (`notebooks/**`, `gold_rules/`, EXP docs) are *registered* by
manifest, not moved.

---

## 8. Dashboard → experiment registry

- **Stage 1 (done)** — book visibility (positions, exposure lens, gold state).
- **Stage 2 (next)** — per-comment-tag performance: EV/R, win%, cost, trade count
  for `GOLD_RULES_v1`, `_C`, FX-ML. From journals/deals we already have.
- **Stage 3** — regime registry: status (research/paper/live), model version,
  primary metric + 95% CI, costs, account, artifact links.

Rule stays: dashboard is read-only and never executes.

---

## 9. Prioritized research backlog — execution-ready specs

Each item below is written so a capable implementation agent can execute it
without inferring the objective, inputs, outputs, or stopping condition. Items
are sequential within P0 (each depends on the previous); do not parallelize
P0.1/P0.2 ahead of P0.0.

### P0.0 — Shared cost + bootstrap infrastructure (prerequisite for everything else)

- **Objective.** One reusable, unit-tested source of truth for round-trip
  trading cost and for overlap-aware confidence intervals, so every downstream
  experiment applies the same corrections instead of ad-hoc copies.
- **Files to create.**
  - `ml-signal-service/experiments/_core/costs.py` — `ROUND_TRIP_COST_PIPS: dict[pair, dict[session, float]]`
    seeded from the measured 2026-09-18 spreads (§2, Issue C) with a flat
    session multiplier of 1.0 until session-conditioned data exists (documented
    TODO, not silently assumed accurate); `to_price(pair, pips) -> float`;
    `apply_cost_to_barrier(entry, atr, mult, direction, cost_pips) -> float`.
  - `ml-signal-service/experiments/_core/bootstrap.py` — `block_bootstrap_ci(returns: Sequence[float], block_length: int, n_resamples: int = 1000, ci: float = 0.95) -> tuple[float, float, float]` returning `(point_estimate, lo, hi)`.
  - `ml-signal-service/experiments/_core/tests/test_costs.py`,
    `test_bootstrap.py`.
- **Inputs.** None beyond the measured spread table already in §2/PROJECT-CONTEXT.
- **Outputs/artifacts.** The two modules + passing unit tests. No experiment
  output yet — this is infra.
- **Validation checks (must pass before P0.1 starts).**
  1. `test_costs.py`: cost in price terms has the correct sign for BUY vs SELL
     (cost always makes the barrier *harder* to reach, never easier).
  2. `test_bootstrap.py`: on synthetic IID Gaussian returns, the block-bootstrap
     CI width converges to the IID-bootstrap CI width as `block_length → 1`
     (sanity check that the implementation reduces to the known-correct case).
  3. `test_bootstrap.py`: on synthetic AR(1)-correlated returns (autocorrelation
     ρ=0.5), the block bootstrap (`block_length > 1`) produces a **wider** CI
     than a naive IID bootstrap on the same data — proves the correction does
     something, not just that it runs.
- **Acceptance criteria.** All unit tests pass; both modules importable from an
  experiment notebook with no other dependency changes.
- **Stopping condition.** Done when tests pass and are committed. This task
  has no research decision gate — it is plumbing, not a hypothesis test.
- **Non-goals.** No new cost data collection yet (that is P0.1's job for
  slippage); no change to production `signal_gate.py` or `order_bot.py`.

### P0.1 — Cost-adjusted label, EURUSD SELL (`EXP-2026-05`) — recommended first task

- **Objective.** Determine whether the production EURUSD SELL model, retrained
  on a cost-adjusted label (TP must clear ATR barrier **and** round-trip
  friction, not just the ATR barrier), remains profitable on the sealed test
  window — holding the feature set, split dates, model family, and calibration
  procedure **byte-identical** to the production notebook so the cost variable
  is isolated with no confound.
- **Depends on.** P0.0 (`_core/costs.py`, `_core/bootstrap.py`).
- **Files to create.**
  - `ml-signal-service/notebooks/eurusd/eurusd_sell_costlabel.ipynb` — fork of
    `eurusd_sell_improved.ipynb`; the **only** logic change is in
    `generate_sell_labels`: `tp_level` is replaced by
    `apply_cost_to_barrier(...)` from `_core/costs.py` using
    `ROUND_TRIP_COST_PIPS["EURUSD"]`. `TRAIN_START/END`, `VAL_START/END`,
    `TEST_START`, `FORWARD_BARS`, `ATR_TP_MULT`, `ATR_SL_MULT`, the feature
    pipeline, the noise-benchmark selection, the purged-embargo CV, and the
    isotonic calibration are unchanged from the production notebook.
  - `ml-signal-service/experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/experiment.yaml`
    — records `label_id=cost_adjusted_v1`, `cost_pips` value used, split dates,
    `primary_metric=test_ev_per_r`, and an empty `variants_tried: []` list to
    append to (pre-registration, Issue A).
  - `ml-signal-service/experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/RUN_LOG.md`
    — one dated entry per run; the sealed test set is scored **once** per
    entry.
- **Inputs.** Existing `data/raw/mt5/H1/EURUSD_H1.csv`; `_core/costs.py` cost
  constant (do not hand-edit the constant inside the notebook).
- **Outputs/artifacts.**
  - `models_bin/EURUSD_H1_sell_costlabel_<model>.joblib` (bundle: model,
    features, threshold, ATR mults, forward_bars, cost_pips used).
  - `experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/reports/test_metrics.json`
    — `{precision, recall, roc_auc, n_signals, ev_per_r, ev_ci_95_lo, ev_ci_95_hi, breakeven, block_length_used}`.
  - `experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/reports/test_signals.csv`
    — per-signal ledger (timestamp, probability, realized R net of cost).
- **Validation checks.**
  1. Cost-adjusted label rate (% SELL=1) must be ≤ the baseline label rate for
     every calendar year in the dataset (a stricter barrier can only reduce
     positives) — assert in the notebook; a violation means a sign/unit bug,
     not a finding.
  2. Split boundaries and `FORWARD_BARS`/ATR multipliers assert-equal to the
     values in `eurusd_sell_improved.ipynb`.
  3. `ev_ci_95_*` computed via `_core/bootstrap.block_bootstrap_ci`, block
     length = `max(FORWARD_BARS, median bar-gap between signals)` — not a
     naive IID resample.
- **Acceptance / decision gate (evaluated once, on the first sealed-test scoring).**
  - **GO** → open a shadow-paper slot on account A2: `ev_per_r` point estimate
    `> 0` AND `ev_ci_95_lo > -0.05` AND `n_signals ≥ 30`.
  - **HOLD** → do not proceed, do not kill, document and wait for more test-
    window data: CI straddles zero beyond ±0.05R, or `n_signals < 30`.
  - **STOP** → kill this label variant for EURUSD SELL: `ev_per_r ≤ -0.05` with
    the CI upper bound also below zero.
  - **Hard rule:** re-running against the sealed test with a changed cost
    constant, threshold, or feature set after seeing test output requires a
    new experiment ID (`EXP-2026-05b`, etc.) and a `RUN_LOG.md` entry marking
    the prior run superseded — never silently overwritten (Issue A control).
- **Non-goals.** No retuning of `ATR_TP_MULT`/`ATR_SL_MULT`; no new features;
  no model-family change; no work on GBPUSD/USDCHF/USDCAD or EURUSD BUY in
  this experiment — those are `EXP-2026-06`+ and start only after this gate
  resolves.

### P0.2 — Retrofit cost + bootstrap into existing production reporting (Issue C/B applied everywhere)

- **Objective.** Every currently-live EV/R figure (EURUSD/GBPUSD/USDCHF/USDCAD
  SELL, dashboard Stage 2 per-tag performance) is reported net of the
  `_core/costs.py` constant and with a block-bootstrap CI, not the raw/zero-cost
  figures currently shown.
- **Depends on.** P0.0, and ideally the P0.1 decision (so the retrofit and the
  new-label experiment use the same cost constants and don't diverge).
- **Files to modify.** `frival/dashboard/backend/portfolio.py` (add EV/R + CI
  fields to the per-tag aggregation feeding Stage 2, §8); any existing backtest
  scripts under `ml-signal-service/steps/04_training/` and `05_inference/` that
  currently compute EV/R without a cost subtraction.
- **Outputs.** Updated dashboard Stage 2 panel showing `EV/R (net of cost)` and
  its 95% CI per pair/tag, sourced from `_core/costs.py` and
  `_core/bootstrap.py` — no duplicate cost logic in the dashboard backend.
- **Validation checks.** Existing `dashboard/tests/test_portfolio.py` (7
  passing) must still pass; add a test asserting the new EV/R field is always
  ≤ the zero-cost EV/R for the same trade set.
- **Acceptance criteria.** Dashboard Stage 2 shows cost-adjusted EV/R + CI for
  every currently-tagged pair; test suite green.
- **Stopping condition.** Done when the four production pairs show the
  corrected figures and no code path still reports a zero-cost EV/R as if it
  were final.
- **Non-goals.** No change to live trading logic, gates, or lot sizing.

### P1 — new data, clean evidence (start only after P0 resolves)

1. **`EXP-2026-06` — EURUSD BUY, cost-adjusted label.** Mirror of P0.1 on the
   BUY notebook. Same files/validation/decision-gate pattern; do not start
   before P0.1's gate has produced a GO/HOLD/STOP (sequential, per Issue A —
   running both directions simultaneously reintroduces the multiple-testing
   surface this roadmap is trying to shrink).
2. **`EXP-2026-07` — Liquid-cross book (EURGBP, GBPJPY, EURJPY).** Objective:
   diversification evidence, not a new edge claim. Files: new
   `data/raw/mt5/H1/<PAIR>_H1.csv` acquisition (reuse
   `ml-signal-service/steps/01_download/mt5_downloader.py`), one notebook per
   pair forked from `eurusd_sell_improved.ipynb` with `PAIR` changed only.
   Decision gate: reuse the EV/R interpretation table already specified in
   `EXP-2026-04` §5 (EV/R > +0.3 → proceed; (−0.2, +0.3] → inconclusive, expand
   window; ≤ −0.2 → do not proceed) — do not invent a new threshold set.
   Demo-only; account A2 per §6. Stopping condition: verdict recorded per pair
   in `RUN_LOG.md` within one measurement window; no re-running with different
   multipliers to chase a GO.
   **RESOLVED 2026-09-21 — ABORTED on economics before any scoring.** Data
   acquired + validated for all three crosses and the cost table extended, but
   the measured round-trip spreads (EURGBP 4.7, GBPJPY 13.6, EURJPY 10.6 pips)
   consume **0.53–0.56R per trade** at current ATRs, forcing ~62% breakeven
   precision (vs 44% EURUSD) — above what this model family has ever achieved.
   Widening TP collapses the cost-adjusted label rate below the 15% floor
   (EURGBP: 19.7% at TP1.5 → 7.5% at TP3.0), so no TP/SL geometry rescues it.
   The three sealed-test scorings were NOT spent; the handicap table is in the
   EXP-2026-07 RUN_LOG. Crosses remain available as data if a different label
   design (e.g., spread-relative targets) is ever pre-registered.
3. **`EXP-2026-08` — Single equity-index ML (NAS100 or US30), account A3.**
   Blocked until the §4.2 execution-realism prerequisite (financing rate,
   dividend-adjustment handling, session hours) is answered and recorded in
   `experiment.yaml`. **Checklist issued 2026-09-21**:
   `experiments/EXP-2026-08-EQUITY-INDEX-COSTLABEL/BROKER_RELEASE_CHECKLIST.md` —
   three broker questions (swap long/short, dividend ex-date handling, session
   hours + daily break) that must ALL be answered before any backtest. Same
   notebook-fork pattern; same P0.1 decision-gate structure applied to the new
   instrument's own breakeven (recompute breakeven from that instrument's TP/SL
   multipliers — do not assume 40% carries over). **Rationale for priority now:**
   index spreads are a tiny fraction of ATR (unlike crosses), so the
   cost-adjusted label is geometrically fair there — it is the cleanest test
   that the stack can find edge outside FX.
   **RESOLVED 2026-09-21 — US30 SELL scored: STOP.** All three broker questions
   authenticated from the MT5 terminal (swap answered; dividend adjudicated
   non-blocking at 0.05% of R/trade; session = 23h/day, quiet hour 00 UTC).
   Sealed test: n=1576, precision 0.329 vs breakeven 0.40, **ev_per_r −0.178,
   CI [−0.261, −0.104]** (wholly below zero → STOP, significant). KEY nuance:
   **roc_auc 0.660** shows the model ranks trades well — but precision still
   undercuts breakeven even at 0.03R friction. Portfolio conclusion: the ATR
   triple-barrier *label design*, not the cost environment, is the binding
   constraint on directional H1 ML in this stack. Five experiments, zero GO.

4. **`EXP-2026-09` — US30 label-geometry redesign (TP2.0/SL1.0, R:R 2.0).**
   Built directly on EXP-2026-08's roc_auc 0.66 (skill exists — precision is the
   bottleneck). Pre-registered with a 12-cell geometry sweep freezing TP2.0/SL1.0
   (label rate 15.6% usable; cost-adj breakeven 34.6% vs 41.5% — a −7pt relief).
   **RESOLVED 2026-09-22 — scored: STOP. HYPOTHESIS FALSIFIED, informatively.**
   Sealed test: n=1241, precision **0.268** (WORSE than TP1.5's 0.329), roc_auc
   **0.687** (BETTER — 0.660→0.687), **ev_per_r −0.197, CI [−0.292, −0.093]**
   (wholly below zero, significant at 95%). The data isolate the conclusion
   completely: widening the target *improved* the ranking skill but *worsened*
   precision — the model cannot convert skill into precision under this label
   family, at any geometry. **SIX experiments, ZERO GO, cost ruled out as the
   cause (highest skill on lowest-friction instrument), geometry ruled out as the
   fix (skill↑ precision↓).** Per the P2 gate, the evidence-based decision is to
   **close the directional-ML program** and move the research budget to the gold
   engine (the only asset with real recorded PnL) or a structurally different
   signal family. Decision point recorded; operator decision required.

### P2 — only if P0/P1 shows signal (falsification-oriented, not headline)

1. **Regime-conditioned gating** — test as a falsification exercise: does
   conditioning on a regime label (trend/range) change EV/R in the direction
   predicted, or is any apparent improvement explained by the regime label
   correlating with the multiple-testing surface already flagged in Issue A?
   If the latter cannot be ruled out, report negative and stop — do not
   iterate the regime definition until one "works."
2. **Commodity or crypto extension** — only after a P1 item clears its decision
   gate; no separate spec until then.

---

## 10. Honest triage — outcomes (updated 2026-09-22, see §0.1)

**Tested, resolved:** cost-adjusted label (HOLD, EURUSD SELL) · bootstrap CIs
(built, in production use) · liquid crosses (ABORTED on economics) · single
equity index (STOP, both geometries — but the program's best ranking skill) ·
spread cost model (built, live in `_core/costs.py`).

**Falsified, do not retry:** TP/SL geometry redesign on the same hit/miss label
family (`EXP-2026-09` — skill improved, precision worsened; no geometry fixes it).

**Never reached (no GO ever occurred, so these remain open, not resolved):**
regime labels as standalone targets · feature-selection competitions ·
threshold-tune-until-40% · slippage measurement (needs real fills) · swap
accounting in FX backtests.

**Impractical for this stack (unchanged verdict):** EM/exotic FX (spreads) ·
multi-stock stat-arb via MT5 CFD · crypto HFT/arbitrage.

---

## 11. References

**Audit & prioritized next steps (read this alongside §0.1/§0.2)**
- `ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md` — gaps, inconsistencies, risks
  identified 2026-09-22, and the re-prioritized next-steps list with
  impact/effort/dependency/urgency justification.
- `GOLD-ENGINE-EVIDENCE-PLAN.md` — execution plan for the chosen Option A:
  fix the gold engine's broken demo evidence loop (audit G7), then gather a real
  track record before any gold research decision.
- **`ROADMAP-2026-Q4-SYNTHESIS.md` — the quarter's capstone deliverable**:
  the falsification ledger, the no-edge map, and what was durably built, with a
  recommended close-out.

**Production labels & methodology**
- **BUY label (production):** `ml-signal-service/notebooks/eurusd/eurusd_buy_improved.ipynb`
- **SELL label (production):** `ml-signal-service/notebooks/eurusd/eurusd_sell_improved.ipynb`
  — both: `FORWARD_BARS=6`, `TP=1.5×ATR(14)`, `SL=1.0×ATR(14)`, breakeven 40%,
  split (production dates per notebook).
- **Agnostic model:** `ml-signal-service/notebooks/agnostic/agnostic_sell_improved.ipynb`
- **Gold ML (killed, 3rd attempt):** `ml-signal-service/notebooks/xauusd/xauusd_sell_macro_improved.ipynb`
- **Manual-trading evidence base:** `ml-signal-service/notebooks/xauusd/xauusd-manual-trading.md`

**Shared methodology (`experiments/_core/`)**
- `costs.py` — per-pair, per-session round-trip cost table (spreads measured
  2026-09-18 + crosses 2026-09-21 + US30/US100 index CFDs 2026-09-21).
- `bootstrap.py` + `tests/` — moving-block bootstrap CI (Issue B), 31 tests.
- `build_costlabel_fork.py` — parameterized fork builder (`--pair`, `--atr-tp`
  /`--atr-sl-mult`); used for EXP-2026-05/06/07/08/09.

**Completed experiments (authoritative status in §0.1)**
- **EXP-2026-03 (lived):** `docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md`
- **EXP-2026-04 (CLOSED):** `docs/experiments/EXP-2026-04-RULEENGINE-FX-BACKTEST.md`
- **EXP-2026-05 (HOLD):** `experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/` → `reports/test_metrics.json`
- **EXP-2026-06 (STOP):** `experiments/EXP-2026-06-EURUSD-BUY-COSTLABEL/` → `reports/test_metrics.json`
- **EXP-2026-07 (ABORTED):** `experiments/EXP-2026-07-CROSSES-COSTLABEL/` → `RUN_LOG.md` (friction table)
- **EXP-2026-08 (STOP):** `experiments/EXP-2026-08-EQUITY-INDEX-COSTLABEL/` →
  `BROKER_RELEASE_CHECKLIST.md`, `reports/US30_sell_test_metrics.json`
- **EXP-2026-09 (STOP, falsified):** `experiments/EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN/` →
  `reports/geometry_sweep.csv`, `reports/US30_sell_test_metrics.json`

---

*End of roadmap. Baseline methodology stands; this document adds only corrections
and new testable experiments, each with a kill/fund threshold to be recorded in
its own manifest before it starts.*