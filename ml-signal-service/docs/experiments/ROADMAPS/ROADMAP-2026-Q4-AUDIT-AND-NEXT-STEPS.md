# ROADMAP-2026-Q4 — Audit & Prioritized Next Steps

**Audit date:** 2026-09-22
**Auditor scope:** `ROADMAP-2026-Q4-RESEARCH.md` (all sections) cross-checked against
the actual files in `ml-signal-service/experiments/`, `experiments/_core/`,
`frival/dashboard/`, `frival/execution_bot/`, and the pytest suites. Every
number quoted below was re-verified against disk on the audit date, not copied
from prior chat summaries.
**Companion to:** `ROADMAP-2026-Q4-RESEARCH.md` (§0.1/§0.2 hold the experiment
evidence table and portfolio conclusions this audit builds on — read those first).
**Execution plan for Priority 3:** `GOLD-ENGINE-EVIDENCE-PLAN.md`.
**Quarter capstone:** `ROADMAP-2026-Q4-SYNTHESIS.md` (the falsification ledger,
the no-edge map, and what was durably built — read it after §6.4 for the close-out).

---

## 1. Verification pass — what checks out

| Claim in the roadmap | Verification method | Result |
|---|---|---|
| `experiments/_core/tests` — cost sign, bootstrap convergence, AR(1) widening | `pytest experiments/_core/tests -q` | **31 passed** |
| `frival/dashboard/tests` + `frival/execution_bot/tests` — Stage-2 tags, §6.1 diagnostics | `pytest frival/dashboard/tests frival/execution_bot/tests -q` | **25 passed** |
| EXP-2026-05/06/07/08/09 each have `experiment.yaml` + `RUN_LOG.md` + `reports/*.json` | directory listing, all 5 folders | **confirmed**, with exceptions noted in §2 (Gaps) |
| Sealed-test numbers in §0.1's evidence table (EV/R, CI, precision, roc_auc, n) | re-read each `reports/*_test_metrics.json` | **all four numeric rows match exactly** |
| Production model bundles carry no `cost_pips`/`label` keys (never touched by cost-label forks) | `joblib.load` on `EURUSD_H1_sell_Ensemble.joblib` / `..._buy_Ensemble.joblib` | **confirmed untouched** |
| Only one MT5 account was used for every experiment | `credentials.env` inspection + download/training logs | **confirmed** — account 7409623 (demo) only; no A2/A3 ever provisioned |

The evidence table and portfolio conclusions in the main roadmap's §0.1/§0.2 are
**accurate as written**. The problems found below are about staleness elsewhere
in the same document, structural drift between the plan and what was actually
built, and forward-looking gaps — not about the correctness of the completed work.

---

## 2. Audit findings

### 2.1 Gaps — real, unresolved, currently untracked as action items

| # | Gap | Why it matters |
|---|---|---|
| **G1** | **Slippage never measured.** `_core/costs.py`'s `SLIPPAGE_PIPS` is `0.0` for every pair. §6.1 diagnostics are *instrumented* (`order_bot.py` logs slippage/latency/spread-at-fill), but since no experiment ever reached GO, no fills ever accrued to measure. | Any future GO decision would still be flying on a spread-only cost model — exactly the Issue C gap the roadmap flagged, still open. |
| **G2** | **Session-conditioned spread never modeled.** `SESSION_MULTIPLIER` is flat 1.0 everywhere; every cost figure is a single point-in-time snapshot (majors 2026-09-18; crosses/indices 2026-09-21). | The crosses' 0.53–0.56R friction and US30's 0.03R friction — the numbers that drove ABORT and the pivot to indices — could shift materially if spread widens in thin sessions. Not re-validated. |
| **G3** | **Swap/financing never subtracted in any FX backtest.** Only EXP-2026-08/09 (index CFDs) got a swap *answer* (via the broker checklist), and even there it's logged as a diagnostic, not netted into EV/R. | If any FX or index experiment is ever revived, swap remains an unquantified confound. |
| **G4** | **Account isolation matrix (§6) was never built.** A2/A3 are described as "new demo" accounts; in reality every experiment ran as an offline backtest against historical H1 data pulled through the single existing account. | Not a defect today (nothing ever reached live/paper), but if Option B or a gold extension reaches GO, A2/A3 provisioning is a **new**, unstarted task — not something already in place. |
| **G5** | **No execution-ready spec exists for the option the evidence favors most (the gold engine).** §0.2 recommends "move research budget to the gold engine," but there is no manifest, no label/data design, no decision gate for it — unlike every FX/index experiment, which is fully specified. | This is the single largest asymmetry in the roadmap: the *least*-evidenced option (a brand-new US30 label redesign) has more procedural detail than the *most*-evidenced one (gold, the only asset with real recorded PnL). |
| **G6** | **`EXP-2026-10` (the proposed label redesign) has no spec** — mentioned only as one paragraph in §0.2. | Issue A discipline requires pre-registration *before* any code; a paragraph is not a manifest. If Option B is chosen, the spec must be written first — it does not exist yet. |
| **G7** | **CRITICAL — the "gold has real recorded PnL" premise is FALSE, and the gold engine's demo evidence loop is broken.** The roadmap (and this audit's own first pass) repeatedly called gold "the only asset with real recorded PnL." Verified 2026-09-22 against `frival/gold_rules/`: `settings.yaml trading.mode: demo` → `OrderManager` **simulates** orders (`"DEMO MODE - Simulated execution"`, `order=0`, `deal=0`); but the engine's exit logic (`engine.py:786`) reads **real** broker positions, which are always 0 in demo → every trade self-closes on the next tick. The journal confirms: **2 `ENTRY` events on 2026-09-22, both `CLOSE`d ~1 minute later with `pnl: 0.0`.** The `--dry` path simulates the position slot but never realizes `dry_pnl` (stays 0). **Net: the gold engine has produced ZERO usable PnL evidence — neither mode measures anything.** | It invalidates the stated rationale for pivoting to gold ("proven asset"). Gold is *also* unproven. Before any gold research budget is spent, its demo evidence loop must be fixed so it can actually accumulate a track record. This is now the top technical task (revised Priority 3, §3). |

### 2.2 Inconsistencies — within the roadmap document itself

| # | Inconsistency | Fix applied in this pass |
|---|---|---|
| **I1** | §0 Executive summary lists five "next experiments" as if still pending; §0.1 (two sections later) shows all five are done/resolved. A first-time reader gets a false to-do framing. | §0 rewritten below to point at §0.1/§0.2 as the current status, keep the original list only as "the plan as first written." |
| **I2** | §9 backlog numbering is broken: P1 items numbered 4,5,6,7; P2 restarts at 7,8 (duplicate "7"). | Renumbered in the main roadmap (see change log at the end of this doc). |
| **I3** | §4.2 still frames equity indices as "Highest priority alternative" in future tense — EXP-2026-08 has since scored STOP on exactly that recommendation. | Table row annotated with the outcome. |
| **I4** | §10 "Honest triage" is written in pre-test framing ("Worth testing: ...") for things that have since concluded with results. | Section rewritten to report outcomes. |
| **I5** | §7's experiment-folder tree doesn't match disk: `data/`, `features/`, `models/`, `backtests/`, `papertrading/` subfolders exist but are **empty/unused** in every experiment (05, 06, 07, 09); notebook forks actually live in the shared `notebooks/eurusd/` or `notebooks/crosses/`, and trained bundles live in the shared `models_bin/`. EXP-2026-08 is also missing a `README.md` that 05/06/07 have. | §7 rewritten to describe the *actual* structure; a cleanup task for the empty scaffold folders is filed under Priority 6 below (low urgency). |

### 2.3 Risks — identified, most already mitigated, all worth recording

| # | Risk | Status |
|---|---|---|
| **R1** | **Shared, mutable fork path.** `build_costlabel_fork.py` writes one shared filename per (pair, direction). While building EXP-2026-09, an early version of the builder briefly **overwrote EXP-2026-08's already-scored fork** (`us30_sell_costlabel.ipynb`) before the `_geom` suffix was added to disambiguate. | **Mitigated at the time** — caught immediately, the file was regenerated deterministically (same production notebook + same `_core/costs.py` inputs) to match what had actually been scored. **Underlying design gap remains**: there is no automated guard preventing this from happening again, and no byte-for-byte input hash tying a `scored_at` result to the exact fork that produced it (the `_executed.ipynb` copy captures outputs, not a locked input diff). |
| **R2** | **Compute/environment fragility.** EXP-2026-06 needed three attempts (OS reboot, then an OOM crash mid-training, then a hardened rerun with `LOKY_MAX_CPU_COUNT=4` / `OMP_NUM_THREADS=2`) before it scored. The hardening was applied **ad hoc, per-experiment**, only after failures — duplicated by hand into 05/06/08/09's separate `run_exp.py` files rather than centralized. | **Live risk** — any future experiment run on this machine while other memory-heavy processes are active (VS Code, browser, the dashboard, the live scheduler) risks the same failure mode. Not centralized into `_core/`. |
| **R3** | **Cost measurements are single point-in-time snapshots**, frozen for each experiment's lifetime (correct per Issue A — don't remeasure mid-experiment) but never re-validated afterward. The 0.53–0.56R (crosses) and 0.03R (US30) figures that drove ABORT and the index pivot are trusted numbers from one measurement each. | **Acceptable for the experiments as run**; **must be re-checked before reusing these numbers to justify a new decision** (e.g., before starting `EXP-2026-10` on US30). |
| **R4** | **Swap is not modeled in any FX backtest** even though `FORWARD_BARS=6` H1 bars can span a daily rollover. Never mattered in practice (zero experiments reached paper/live), but remains an unquantified confound for any revival. | Same underlying issue as G3, listed here because it is a risk to a *future* decision, not just a documentation gap. |
| **R5** | **Housekeeping debris**: `EXP-2026-06-EURUSD-BUY-COSTLABEL/__pycache__/` and a stray `status.py` (an ad hoc monitoring script) are sitting inside the experiment folder. | Cosmetic; harmless; filed under Priority 6 (cleanup). |

---

## 3. Prioritized next steps

Scored on four axes — **Impact** (research/decision value), **Effort**, **Dependency**
(what blocks it / what it blocks), **Urgency** (why now vs. later) — each High/Medium/Low.

| # | Action | Impact | Effort | Dependency | Urgency | Gate/Risk addressed |
|---|---|---|---|---|---|---|
| **1** | **Operator decision: Option A (close directional-ML, pivot to gold) vs Option B (one more structural redesign, `EXP-2026-10` on US30) vs both** | **H** | **L** (a decision, not code) | **Blocks everything below** | **H** | Resolves §0.2's open decision point |
| **2** | **Fix roadmap staleness** (§0 executive summary, §9 numbering, §4.2, §10, §7 tree) | M | L | None — do immediately | M–H | I1–I5 |
| **3** | **Strategic decision (revised by §6.4):** (a) accept that no edge is demonstrated and stop deploying capital on these approaches, or (b) fund a *genuinely new* hypothesis with a sceptical prior (~10 falsifications accumulated). | **H** | **L** (a decision, not code) | Follows the exit study (§6.4) | **H** | Supersedes G5/G7 as moot |
| **4** | ~~If Option B chosen: pre-register the US30 label redesign~~ | — | — | **CLOSED** — Option B closed by the diagnostic (§6.1) | — | G6 |
| **5** | **Close remaining Issue-C gaps** the moment any experiment reaches paper/live: measure slippage (G1), model swap explicitly (G3/R4), consider session-conditioned spread (G2) | M | L–M (infra already built, mostly measurement) | Needs real fills → needs a GO first | Low now → High the moment any GO happens | G1, G2, G3, R4 |
| **6** | **Harden shared experiment infrastructure**: builder overwrite guard (R1), centralize `LOKY_MAX_CPU_COUNT`/`OMP_NUM_THREADS` hardening into one `_core` runner base (R2), delete `__pycache__`/`status.py` debris (R5) | L–M | L | None | Low — do opportunistically, or before #4 if Option B proceeds | R1, R2, R5 |
| **7** | **Account isolation matrix (A2/A3) provisioning** (G4) | L today | M (new MT5 terminal instances + demo accounts + dashboard wiring) | **Strictly gated on a future GO** (from #4 or a gold extension) | **Lowest — defer entirely** | G4 |

### Why this order

1. **Nothing else should proceed until #1 is decided.** Six experiments produced zero GO; writing more specs or fixing more documentation before the operator chooses a direction risks wasted or misdirected work — this is the same discipline the roadmap itself used at every experiment gate (§9's non-goals sections).
2. **#2 is cheap, has no dependency, and protects the credibility of the audit trail itself** — a document with a stale executive summary and duplicate section numbers undermines trust in everything else it reports. Doing it now costs nothing and can run in parallel with #1.
3. **#3 was re-scoped after G7 was discovered mid-audit.** Originally "write the
   gold research plan." The evidence check showed gold has **no** real PnL and a
   broken demo evidence loop — so writing a research plan for an engine that
   cannot measure itself would repeat the roadmap's original mistake (treating an
   unverified premise as fact). #3 is now the concrete engineering fix that must
   precede any gold research, followed by the plan. This keeps the "verify before
   you build on it" discipline that caught the original false premise.
4. **#4 is explicitly gated** — no code, no data pull, no notebook fork for `EXP-2026-10` until the operator has chosen Option B. This preserves the same "manifest before implementation" discipline used successfully in 05/06/08/09.
5. **#5 and #7 are both "the moment a GO happens" items** — correctly low urgency *today* because no GO exists, but they are called out explicitly so they are not forgotten or rediscovered under time pressure later (that's exactly how G1–G4 became gaps in the first place: they were true dependencies of a GO that never materialized, so they were never revisited).
6. **#6 is pure hygiene/robustness** — worth doing, but it changes no verdict and blocks nothing; it's ordered last because effort-to-impact is the lowest of the seven.

---

## 4. What NOT to do (carried over from the roadmap, reaffirmed by this audit)

- Do **not** run more TP/SL multiplier variants of the triple-barrier label (falsified by EXP-2026-09: skill up, precision down, at any geometry).
- Do **not** open EURUSD/GBPUSD variants of the cost-adjusted label (Issue-A testing budget already spent across six experiments with zero GO).
- Do **not** reopen `EXP-2026-07` (crosses) — arithmetically dead at current spreads (R3 flags that this could change, but re-checking the number is a five-minute task, not a reason to re-score).
- Do **not** provision A2/A3 (#7) or spend infra-hardening effort (#6) before #1 is decided — both are zero-urgency until a GO exists or is imminent.

---

## 5. Change log applied to `ROADMAP-2026-Q4-RESEARCH.md` as part of this audit

- §0 Executive summary: added a pointer to §0.1/§0.2 as the authoritative current
  status; the original numbered plan is kept as historical record, explicitly labeled.
- §9: renumbered the P1/P2 backlog items to remove the duplicate "7".
- §4.2: annotated the equity-index row with the EXP-2026-08 outcome.
- §10: rewritten from pre-test framing to outcomes.
- §6: added a note that the A2/A3 account matrix was never provisioned (G4).
- §7: rewritten the folder tree to describe the actual structure (shared
  `notebooks/` and `models_bin/` paths, referenced by manifest — not nested
  inside each experiment folder), and flagged the empty scaffold subfolders.

---

## 6. Decision record — 2026-09-22

### 6.1 Option B closed by diagnostic (no re-score; pre-registered STOP verdicts stand)

A read-only feasibility check on the **already-scored** US30 ledgers
(`reports/US30_sell_test_signals.csv`, both experiments) asked whether *any*
operating point in the tradeable region is profitable. Sorting each ledger by
the model's own `prob_sell`:

| | EXP-2026-08 (TP1.5) | EXP-2026-09 (TP2.0) |
|---|---|---|
| mean realized R, top-30 / top-50 / top-100 | −0.333 / −0.250 / −0.225 | **0.000 / +0.020** / −0.250 |
| mean realized R, overall | −0.178 | −0.197 |
| `corr(prob_sell, outcome)` | −0.012 | +0.002 |
| best quintile vs worst (mean R) | no monotonicity | no monotonicity (Q5 −0.153, Q3 −0.347) |

**Reading:** the roc_auc of 0.66–0.69 is real but lives *between the vetoed bars
and the fired bars* (a coarse top-~29% split), not **inside** the tradeable
region. Once the model decides to fire, its probability ordering carries ≈ zero
information (corr ≈ 0). The single "+0.020" cell is n=50 noise — non-monotone,
with neighbouring buckets deeply negative. **There is no usable operating point
to recover.** The model's skill is *veto discrimination ("when not to trade")*,
not trade selection — and a strategy needs the latter. Option B (a
rank/precision-oriented redesign on the same features) is therefore not
supported: it would have to extract signal from features whose fitted score has
none left in the confident region.

*Caveat:* this analyzes the fired subset (the ledger contains `signal==1` rows);
a redesign could in principle select a different subset, but on the same feature
set that is a long-odds bet, not a promising one.

### 6.2 Operator decision: **Option A — close the directional-ML program**

Chosen 2026-09-22 on the evidence above plus six prior experiments with zero GO.
The directional H1 triple-barrier ML line is closed. Its artifacts (data, forks,
`_core` methodology, all reports) remain as the permanent record.

### 6.3 Consequence: the gold premise was false — destination corrected

Pivoting to gold was recommended on the premise that gold has "real recorded
PnL." That premise was **false** (G7). The pivot destination is therefore
re-scoped: **first fix the gold engine's demo evidence loop (revised Priority
3), then let it accumulate a real track record, then decide whether a gold
research program is warranted.** No research budget should be committed to gold
until it can measure itself.

### 6.4 Exit-management study (EXP-2026-10 / 11) — and the strategic consequence

Prompted by the operator's observation that the ~55% win rate might be salvaged by
better SL/TP handling. Tested on the **real manual gold entries** (131 trades from
the live statement), holding entries fixed and replaying the XAUUSD M5 path.

- **EXP-2026-10 (operator-SL-anchored):** every mechanical policy far worse than
  the actual exits (EV −$155…−$180/trade vs −$8.68 actual; win rate 12–29% vs
  55%). **Confounded** — the operator's own stops are below typical volatility
  (median 8.0 pts vs M5 bar range 4.15 / H1 ATR 5.0), so they are noise-stopped by
  construction.
- **EXP-2026-11 (ATR-anchored, the fair test):** only `1×ATR SL / 3×ATR TP` is
  positive (+$8,689, EV +$66/trade, PF 1.15, win 29.8%), and it is **monotone in
  target width** (1.5R −12.4k → 2R −3.9k → 3R +8.7k) — a coherent-looking signal.
  **But the robustness test kills it:** removing the **top 3 trades** turns
  +$8,689 into **−$4,325**; **all** the profit is in a **single week** (wk38
  +$16,941 vs wk35–37 −$8,252 combined); and the **simulated max drawdown is
  −$58,697** (~6.8× the profit). Pre-registered gate said CONTINUE; the
  robustness evidence **overrides it → STOP**.

**Conclusion:** the exit-management hypothesis is **not supported**. No mechanical
exit policy extracts a robust edge from the manual entries. Combined with
everything else, the honest strategic position is now:

> **No demonstrated edge exists in any approach this project has tested** — FX-ML
> (6 experiments, 0 GO), crosses (arithmetically dead), the gold rules engine
> (never traded), manual gold trading (net −$815, PF 0.94), and exit management
> (no robust policy). This is the true starting point.

**Consequence for the roadmap:** Priority 3 (fix the gold engine's evidence loop)
is **demoted** — fixing the measurement of a line with no demonstrated edge is not
where the next dollar should go. The decision is now strategic, not technical:
either (a) accept that no edge has been demonstrated and stop deploying capital on
these approaches, or (b) fund a *genuinely new* hypothesis (a different market
mechanism, data source, or horizon), with the explicit acknowledgement that ~10
falsifications have accumulated and the prior should be sceptical.

---

*This document is the forward-looking companion to `ROADMAP-2026-Q4-RESEARCH.md`.
Update the priority table (§3) whenever an item's status changes; do not let this
document and the main roadmap's §0.1/§0.2 drift apart — re-run the verification
pass in §1 before trusting either after any further experiment.*