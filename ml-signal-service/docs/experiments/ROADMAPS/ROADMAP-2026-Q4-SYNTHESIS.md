# FRIVAL — 2026 Q4 Research Synthesis

**The verified outcome of a quarter of hypothesis-driven research: no demonstrable
edge exists in this stack under the tested families — and we now know precisely why,
for each family.**

**Status:** Capstone deliverable · 2026-09-22
**Scope:** every experiment in `ROADMAP-2026-Q4-RESEARCH.md`, its audit
(`ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md`), and the execution plans
(`GOLD-ENGINE-EVIDENCE-PLAN.md`).
**Reading guide:** §1 is the honest bottom line; §2 is the falsification ledger
(the evidence); §3 is the no-edge map (what each null rules out); §4 is what was
durably built; §5 is the method that made the nulls trustworthy; §6 is the
recommended close-out.

---

## 1. Bottom line (the honest quarter in 12 lines)

- We tested **every plausible edge family this stack can produce**: directional
  H1 ML on FX (both directions), index CFDs, cross-diversification, gold rules,
  the operator's own manual gold trading, mechanical exit management, cross-
  sectional momentum, and event-driven macro reaction.
- **Not one hypothesis produced a robust, persistently-positive, net-of-cost
  result.** The closest candidates were each decomposed — by the audit discipline,
  not by hindsight — into trend artifacts, regime effects, or tail luck.
- The failures are **not a generic "nothing works"** — they are a *map*. FX
  directions die to costs+noise; gold entries die to having no edge; momentum and
  event reactions don't exist in this universe at these horizons.
- In parallel we built a **methodology that makes a null trustworthy** — something
  this industry mostly lacks — and that infrastructure is the real asset the
  quarter produced. §4 owns it.
- The paper systems (ML+LLM FX, gold rules) were running in demo all along; their
  demo simulators do not record virtual PnL, so they were producing logs, not
  evidence. That gap, not a market, is ultimately what limited us.
- **Recommendation:** close the research line with the evidence intact; keep the
  demo systems running as operational monitoring; do not fund a further edge hunt
  on these families.

---

## 2. The falsification ledger

Every entry below is cross-checked against its own scored report and RUN_LOG.
Verdicts use the pre-registered GO/HOLD/STOP semantics. All monetary values are
net of cost unless noted.

### 2.1 Directional H1 ML (entry prediction, cost-adjusted labels)

| # | EXP | Question | Verdict | Sealed-test evidence |
|---|---|---|---|---|
| ex-04 | EXP-2026-04 | Do the gold A/B rules transfer to FX? | **negative (CLOSED)** | EV/R < 0 on all 4 pairs (USDJPY strongest negative) |
| ex-05 | EXP-2026-05 | EURUSD **SELL**, cost-adjusted TP | **HOLD** | n=62, prec 0.387 vs breakeven 0.40; **EV/R −0.032, CI [−0.52, +0.45]** (straddles 0 — genuinely inconclusive) |
| ex-06 | EXP-2026-06 | EURUSD **BUY**, cost-adjusted TP | **STOP** | n=2003, prec 0.355; roc_auc **0.504** (≈coin flip); **EV/R −0.111, CI [−0.197, −0.021]** (significant) |
| ex-08 | EXP-2026-08 | **US30** SELL, cost-adjusted TP | **STOP** | n=1576, prec 0.329; roc_auc **0.660** (skill!); **EV/R −0.178, CI [−0.261, −0.104]** |
| ex-09 | EXP-2026-09 | US30 SELL, geometry TP2.0/SL1.0 | **STOP (falsified)** | precision **0.268** (worse), roc_auc **0.687** (better); **EV/R −0.197, CI [−0.292, −0.093]** |

**The aggregate directional result, stated precisely:**
- Costs eat FX majors (≈0.4R friction on ~3-pip stops; P0.2 flipped all four
  backtest pairs to STOP when cost + block-CI were applied).
- The model family can rank (US30 roc_auc 0.66→0.69) but **cannot convert
  ranking into breakeven precision** at any target width. Precision is the
  ceiling, and it is structural, not tuned.
- A diagnostic on the fired-subset showed **no operating point exists in the
  tradeable region** (within-fired correlation ≈ 0); the skill lives between
  vetoed and fired bars, not inside.

### 2.2 Diversification and new-asset classes

| # | EXP | Question | Verdict | Evidence |
|---|---|---|---|---|
| ex-07 | EXP-2026-07 | EURGBP/GBPJPY/EURJPY crosses | **ABORTED (economics)** | spread 4.7–13.6 pips = 0.53–0.56R/trade; ~62% breakeven precision required; no geometry rescues; **no score spent** |

### 2.3 Gold — the "proven" line (all three legs tested, all rejected)

| # | Test | Question | Verdict | Evidence |
|---|---|---|---|---|
| g-01 | Manual account statement (live 81486396) | Does the operator's manual gold trade have a record? | **NET LOSS** | 139 trades, **−$815**, PF 0.94, 55.4% win, avg +167/−220, **max DD 107%** |
| g-02 | Gold rules engine (EXP-2026-03) | Do the automated A/B + Claim C rules trade? | **NEVER TRADED** | demo-mode loop bug: simulated orders, real-position exit check → every entry self-closes in ~1 min with pnl 0.0 |
| g-03 | EXP-2026-10 | Would mechanical exits on the operator's entries work, anchored to his SLs? | **STOP (confounded)** | all policies worse than actual (EV −$155…−$180); SLs (median 8 pts) below typical M5 range (4.15) → noise-stopped |
| g-04 | EXP-2026-11 | Same, anchored to volatility (ATR)? | **STOP (robustness)** | only 1×ATR/3R positive (+$8,689) — but top-3 trades ⇒ −$4,325; one week ⇒ all profit; simulated DD −$58,697 |

### 2.4 Exogenous/schedule-driven mechanism

| # | EXP | Question | Verdict | Evidence |
|---|---|---|---|---|
| m-01 | EXP-2026-12 | Cross-sectional momentum (relative strength, weekly) | **not supported (EV≈0)** | all 6 cells net-negative in 2025+; gross-positive only at L=20, and 2022-driven (+0.068 of +0.081) |
| e-01 | EXP-2026-13 | Event-driven macro reaction (scheduled surprise → price) | **FX null + XAUUSD regime** | FX 1h all ≤ 0 (−0.8…−1.8 bp): priced within the hour. XAUUSD 1h +4.9 bp in 2025 (CI [+2.3,+7.7]) → **+1.1 bp in 2026** (CI [−6,+8]): gone. 24h cells are half unconditional gold drift. |

---

## 3. The no-edge map (specific, not generic)

| Family | Ruled out in | Why (the verified mechanism) |
|---|---|---|
| Directional H1 entry ML | EURUSD (both directions), US30 (both geometries) | costs + irreducible precision floor; ranking skill exists but cannot clear breakeven at any target |
| Cross-diversification | EURGBP/GBPJPY/EURJPY | spread per risk-unit is arithmetic poison (0.5R+); none of the "diversification saves it" hope survived measurement |
| Gold automation (rules) | Automated gold rules | never traded (broken demo loop) — a measurement failure, not a market result |
| Gold automation (exits) | operator's manual gold entries | entries have no edge; exits do not create one (the one positive was 3 trades / one week / −58k DD) |
| Relative-strength momentum | 10-instrument universe, weekly | no persistence; the effect is ~0, not "present but costly" |
| Macro-event reaction | 6-pair FX + gold, 1/4/24h | FX prices surprises within the hour; gold's 1h edge was a 2025 regime, not a persistent signal |

The map answers the "why" for each family. That is the deliverable's core value:
a quarter from now, nobody needs to re-test a family — the ledger already knows
why it fails.

---

## 4. What was durably built (the asset that survives)

### 4.1 A methodology that makes nulls trustworthy
- **Pre-registration discipline (Issue A)** — every experiment declared its
  hypothesis, grid, metric, and GO/HOLD/STOP gate *before* code. No post-hoc
  threshold-walking (enforced across all 8 experiments).
- **Block-bootstrap CIs (Issue B)** — `experiments/_core/bootstrap.py`; every EV
  now carries an overlap-aware 95% CI. This alone converted several "looks
  positive" into "is not" (e.g., the top-k and 2025-only decompositions).
- **One-shot sealed scoring** — the eval window is touched once; re-scoring rules
  are explicit. All cross-checks in this document re-read the same frozen reports.
- **The audit reflex** — each apparent GO was stress-tested *before* acceptance:
  top-trade removal, per-year split, unconditional-trend controls. This caught the
  XAUUSD regime effect and the gold 3-trade tail *at the time*, not in hindsight.

### 4.2 Engineering that is still in use
- `experiments/_core/` — costs, bootstrap, parameterized fork builder; **56 unit tests green** (31 core + 20 dashboard + 5 execution-bot), verified on the audit date.
- **Cost table** — measured spreads for 13 instruments (majors, crosses, gold, US30/US100); slippage slot reserved (0.0) and flagged; one source of truth consumed by every backtest, label, and the dashboard.
- **Data acquisition** — downloader hardened (retry, indices group, credentials fallback); 3 crosses + US30 + US100 acquired and validated; MT5 alignment verified to the minute.
- **Reporting retrofit (P0.2)** — dashboard Stage-2 tag metrics and the FX backtest report now net-of-cost with CIs.
- **Execution diagnostics (§6.1)** — order-bot now logs slippage/latency/spread-at-fill per execution; the measurement is instrumented and ready for fills.
- **Scheduler fix (2026-09-22)** — `run_daily_scheduler.py` day-rollover bug fixed (had skipped whole days); demo pipelines resume correctly.
- **Risk control** — `max_daily_loss` 200 → 100 (2% of $5k demo).

### 4.3 Records
- `ml-signal-service/experiments/EXP-2026-05…-13` — each with manifest, RUN_LOG, README, `reports/*.json`: the complete evidence chain, reproducible from the READMEs.
- `ROADMAP-2026-Q4-RESEARCH.md`, `ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md`, `GOLD-ENGINE-EVIDENCE-PLAN.md` — the living decision trail.
- `ROADMAP-2026-Q4-SYNTHESIS.md` (this document).

---

## 5. The most important methodological finding of the quarter

**A trustworthy null beats a false positive.** Three times this quarter the naive
gate said GO and the audit said no: US30's roc_auc 0.66 (skill without precision),
gold's 1×ATR/3R +$8.7k (three trades, one week), and XAUUSD event +4.9 bp (2025
only). Each was caught by the same cheap reflex: *remove the top trades, split by
year, compare to the unconditional baseline, and demand the CI survive*. That
reflex is now codified and reusable — it is the quarter's real invention.

---

## 6. Recommended close-out

1. **Close the research line** with the ledger and map intact. Do not fund another
   mechanical variant of these families; the evidence map says they fail for
   specific reasons, and those reasons are not going to change.
2. **Keep the demo paper systems running** (ML+LLM FX, gold rules) as operational
   monitoring — they cost nothing and now resume correctly after the scheduler
   fix — but treat them as monitoring, not as a research bet.
3. **If the team ever resumes research**, the entry conditions should be a
   *genuinely new* mechanism or data source not in §3's map (not a new pair,
   geometry, window, or exit twist), with the same pre-registration discipline.
4. **Preserve the methodology as the deliverable** when reporting Q4: the
   infrastructure, the pre-registered pipeline, and the honest no-edge map are
   the durable output. The market did not cooperate; the process did.

---

*This synthesis supersedes nothing — it summarizes. Every number in §2.1–§2.4
traces to a `reports/*.json`/RUN_LOG on disk, re-read for this document on
2026-09-22.*