# Frival Research Roadmap — 2026 Q4

**Created:** 2026-09-18
**Status:** DISCUSSION CONTRACT — baseline methodology approved; this document lists
only additive corrections and new experiments, not a rewrite.
**Scope:** FX-ML + XAUUSD-rules (both in paper trading) → next experiments, labels,
universes, validation, structure, dashboard evolution.

---

## 0. Executive summary

The existing ML training methodology (chronological split, ATR-barrier labels,
threshold-vs-breakeven calibration) is sound and is the **default foundation**.
Three additive deficiencies were identified and each has a smallest-practical fix.
The most important next experiments, in order:

1. **Cost-adjusted label** (spread-aware TP barrier) — the highest-information,
   smallest-delta experiment. Directly answers "profitable *after* realistic costs".
2. **Bootstrap CI on EV/R** for every backtest output (20 lines, no re-fit).
3. **Liquid-cross book** (EURGBP, GBPJPY, EURJPY) — for *diversification* first,
   edge second.
4. **Single equity-index ML experiment** (NAS100 or US30) on a parallel demo
   account — tests whether our stack finds edge outside FX.

Everything below is the full contract behind these priorities.

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

**Chronological split (both notebooks):**
```
TRAIN: 2020-06-30 → 2025-06-30   (5y)
VAL:   2025-07-01 → 2025-12-31   (6mo)
TEST:  2026-01-01 → present      (remaining)
```

The threshold is calibrated against the **40% breakeven precision** implied by the
R:R — every threshold value in this project's history (`0.276`, `0.334`, `0.365`,
`0.5`) is measured against that 40% bar. Good. This is the metric architecture the
roadmap preserves.

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

### Issue B — Single fixed test window, no robustness band

- **What.** One hold-out = one point estimate of precision/EV.
- **Why it biases.** Fat tails + a 6-month window can be one lucky/unlucky regime
  (the Aug–Sep 2026 USD move biased the current small FX sample).
- **Severity.** High for any "proven edge" claim; low for the workflow itself.
- **Smallest fix.** Bootstrap (1,000 resamples) the per-trade EV/R and report the
  95% CI on every backtest output. ~20 lines; no re-fit.

### Issue C — Cost model is optimistic (confirmed live)

- **What.** Backtests historically used `ask=bid` (zero spread); live Standard
  account pays spread embedded in ask/bid with **no commission line**.
- **Why it biases.** At 2–8 pip targets and 1.2–1.6 pip spreads, a large share of
  signals are below friction; paper PnL (+$5/−$6 per trade) reflects this.
- **Severity.** High — the largest research↔paper gap.
- **Smallest fix.** Per-pair `round_trip_cost_pips` = live median spread + slippage,
  subtracted in backtests *and* embedded in the cost-adjusted label (Section 3).

**Conclusion.** The three fixes are additive parameters/plumbing, not architecture
changes. The label framework, split design, and threshold philosophy stand.

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
then EURUSD BUY, then crosses when added.

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
| **Equity indices** (NAS100, US30, GER40, UK100) | **Highest priority alternative.** Same H1 pipeline, richer factor structure, cheap on MT5 CFD demo. Start single-index directional ML, paper-first. |
| Sector ETFs (if broker offers as CFD) | Medium; useful for rotation research. |
| Commodities (WTI, copper) | Medium; fits framework, cost/carry caveats. |
| Rates/futures (bund, SOFR) | Low with this stack. |
| Crypto CFDs | Medium after a clean equity result; vol is flattering, crowded. |

---

## 5. Validation improvements (small, targeted)

- **Walk-forward** — formalize the existing retrain cadence as expanding-window,
  evaluate unseen trailing segment only. Smallest change to workflow.
- **Purged/embargo CV** — needed *only if* K-fold is used on H1 (purge 1 bar).
  Current chronological splits do not need it.
- **Cost model** — Issue C fix (Section 2).
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

---

## 7. Experiment structure & reproducibility

```
ml-signal-service/experiments/
├── _core/                     # shared: labels, features, split, cost model, metrics, bootstrap CI
├── EXP-2027-001-EURUSD-SELL-costlabel/
│   ├── experiment.yaml        # pair, label, features_hash, model_id, thresholds, costs, account
│   ├── config.yaml
│   ├── data/  features/  notebooks/  models/  backtests/  papertrading/  reports/
│   ├── README.md              # primary metric, variants tried, kill/fund thresholds
│   └── RUN_LOG.md
```

`_core/` holds the methodology once; each experiment only redefines its manifest
+ config. Existing artifacts (`notebooks/**`, `gold_rules/`, EXP docs) are
*registered* by manifest, not moved.

---

## 8. Dashboard → experiment registry

- **Stage 1 (done)** — book visibility (positions, exposure lens, gold state).
- **Stage 2 (next)** — per-comment-tag performance: EV/R, win%, cost, trade count
  for `GOLD_RULES_v1`, `_C`, FX-ML. From journals/deals we already have.
- **Stage 3** — regime registry: status (research/paper/live), model version,
  primary metric + 95% CI, costs, account, artifact links.

Rule stays: dashboard is read-only and never executes.

---

## 9. Prioritized research backlog

**P0 (highest information per effort):**
1. Cost-adjusted label — EURUSD SELL (Section 3, #1)
2. Bootstrap CI on EV/R everywhere (Issue B)
3. Apply spread cost model to all backtests (Issue C)

**P1 (new data, clean evidence):**
4. Liquid-cross book — EURGBP, GBPJPY, EURJPY (demo-only, diversification-first)
5. Single equity-index ML — NAS100 or US30 (parallel account, paper-first)

**P2 (only if P0/P1 shows signal):**
6. Regime-conditioned gating (as falsification test, not headline)
7. Commodity or crypto extension

---

## 10. Honest triage

**Worth testing:** cost-adjusted label · bootstrap CIs · liquid crosses · single
equity index · spread cost model.

**Likely overfit (test only as falsification):** regime labels as standalone
targets · feature-selection competitions · threshold-tune-until-40%.

**Impractical for this stack:** EM/exotic FX (spreads) · multi-stock stat-arb via
MT5 CFD · crypto HFT/arbitrage.

---

## 11. References

- **BUY label (production):** `ml-signal-service/notebooks/eurusd/eurusd_buy_improved.ipynb`
- **SELL label (production):** `ml-signal-service/notebooks/eurusd/eurusd_sell_improved.ipynb`
  — both: `FORWARD_BARS=6`, `TP=1.5×ATR(14)`, `SL=1.0×ATR(14)`, breakeven 40%,
  split 2020-06→2025-06 / 2025-07→2025-12 / 2026-01→present.
- **Lived experiment:** `docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md`
- **FX-rules transfer test (CLOSED):** `docs/experiments/EXP-2026-04-RULEENGINE-FX-BACKTEST.md`
- **Agnostic model:** `ml-signal-service/notebooks/agnostic/agnostic_sell_improved.ipynb`
- **Gold ML (killed, 3rd attempt):** `ml-signal-service/notebooks/xauusd/xauusd_sell_macro_improved.ipynb`
- **Manual-trading evidence base:** `ml-signal-service/notebooks/xauusd/xauusd-manual-trading.md`

---

*End of roadmap. Baseline methodology stands; this document adds only corrections
and new testable experiments, each with a kill/fund threshold to be recorded in
its own manifest before it starts.*