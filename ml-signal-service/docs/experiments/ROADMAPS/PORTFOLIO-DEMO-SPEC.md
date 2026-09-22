# Frival — Verified-Components Demo Portfolio (spec + pre-registration)

**Date:** 2026-09-22
**Status:** SPEC (not yet running) — prerequisite back-end PnL fix required (§3).
**Origin:** engagement with the conclusion that no single edge exists — test
whether a **portfolio of verified ingredients** can still be net-positive in demo.

## 0. Honest premise (read before everything)

No component below has standalone edge — each was falsified alone across
EXP-2026-05…14. This portfolio is **NOT a claim of edge.** It is a *feasibility*
test of the only remaining construction: **assemble non-zero verified effects such
that they partially offset, pay costs rarely, and together net positive in a real
demo.** Prior: low-to-moderate. If the combined demo book is net-negative after
the PnL fix, close it with the evidence — that is also a result.

## 1. Why this is not "shipping a losing strategy"

The single-hypothesis tests each tried to use ONE edge to pay EVERY cost. A
portfolio can behave differently because it can:

- **Pay cost rarely** — only trade a small, high-conviction subset (the exact
  failure mode was cost, so the antidote is trade less).
- **Offset** — combine gold (safe-haven) with USD-directions so a USD-driven move
  doesn't hit everything at once (portfolio-level noise reduction).
- **Use the veto** — the only genuine skill found (US30 roc_auc 0.69) is better at
  saying "don't trade" than "trade this"; deploy it as a *filter*, not a signal.

## 2. Portfolio rules (each ingredient is a verified effect)

| Rule | Verified effect it uses | Verification |
|---|---|---|
| **R1 — Trade rarely.** Only take the top ~10% of each instrument's fired-signal
  distribution (highest-conviction), and only in CALM regime. | US30 ranking skill
  (EXP-08/09) + B1's "expansion is worse" (EXP-14) | roc_auc 0.66-0.69; CALM EV ≥ VOL EV everywhere |
| **R2 — No event windows.** Block entries in ±1h around HIGH/MED macro events. | FX surprise is priced-in / adverse within the hour (EXP-13) | all 5 FX 1h cells ≤ 0 |
| **R3 — Cost-aware asymmetric exits.** Wider TP / modest SL (≈1×ATR), break-even
  trail; never the tight operator-style SL (its median 8 pts is below noise). | P0.2
  cost model; EXP-10/11 (operators' SLs too tight) | cost 1.2-1.6 pips vs 12-20 pt TP |
| **R4 — Small, proportional sizing + no pyramid.** Daily cap exists. | risk-control change | `max_daily_loss: 100` (<2% of $5k) |
| **R5 — Long/short asymmetry cap.** Max 2 concurrent positions, at most one per
  instrument. | concurrency gate already in the engine | settings.yaml |

**Crucially: R1-R3 do not fight the evidence.** Each is a *risk/timing* rule, not a
new claim of edge. The book is expected to trade **a handful of times a week**, not
every signal — that is the point (pay costs rarely).

## 3. PREREQUISITE — the PnL fix (this is the real block today)

The current demo harness **does not record virtual PnL**:
- FX execution bot demo orders → `ticket=0`, `pnl 0` (observed on GBPUSD 2026-09-21).
- Gold engine demo entries → self-close in ~1 min with `pnl 0` (G7).

Without real virtual PnL, "run it in demo" measures nothing. So Step 1 of the
spec is a **back-end fix** (same root cause as the audit gap G7, extended to the FX
bot):

- [x] **DONE 2026-09-22** — FX `order_bot.py` demo path: on `ticket=0`/None
      (demo simulation), open a **virtual position** (`demo_ledger.py`), resolve
      SL/TP against live ticks on subsequent signal checks, compute realized R + $
      from price action, append to `execution_bot/data/demo_trades_ledger.jsonl`.
- [x] **DONE 2026-09-22** — Gold `run_gold_rules.py` demo/dry path: `positions_open()`
      now returns the **simulated** slot count in demo (fixes the `open_positions==0`
      instant-self-close bug, G7); on SL/TP/INVALIDATE/CLOSE decisions, `_realize_trade`
      computes realized USD (volume × contract) + R into the SAME shared ledger.
- [x] **DONE 2026-09-22** — Both write the shared per-trade ledger (`symbol, ts,
      entry, sl, tp, exit, exit_reason, realized_usd, R`) — the §6.1 fields.
- [x] **DONE 2026-09-22** — Unit tests assert a non-zero virtual PnL is recorded on
      a simulated trade (10 new tests: `execution_bot/tests/test_demo_ledger.py`,
      `gold_rules/tests/test_demo_pnl.py`). Full relevant suite: **97 passed**.

**Result:** paper trading now produces evidence — a demo order resolves to a
realized R + $ per trade, not `ticket=0, pnl=0`. The paper book (FX + gold) is a
single ledger and is navigable / reportable (§4).

## 4. Evaluation protocol (pre-registered)

- **Facilities:** paper (demo) only; account 7409623 (A1). No live orders ever in
  this spec.
- **Window:** ≥ 4 consecutive weeks after the PnL fix, continuous.
- **Per-trade + daily metrics:** realized $, R, win%, net EV, PF, max DD,
  daily-cap breaches, event-window blocks, cost paid per trade.
- **Stop rules (evaluate continuously, pre-registered):**
  - **GO** → 30+ trades with net EV > 0 and CI_lo > −0.05 → build stage-2 (ML
    allocation) as a NEW experiment.
  - **HOLD** → net EV ≈ 0 or < 30 trades → extend window once (pre-registered).
  - **STOP** → net EV ≤ −0.05 with CI_hi < 0, OR any day hits the daily cap, OR 2
    consecutive losing weeks → kill the demo leg, record the verdict.
- **Honesty rule:** the demo results are the verdict — no mid-window parameter
  changes; any change restarts the window.

## 5. What would make the portfolio net-positive (the arithmetic we're testing)

- If we trade **≤ 5×/week** instead of 20×/day, cost paid per month drops ~30×.
- If the CALM filter keeps the book out of the expansion regimes (VOL ≈ −9 bp vs
  CALM ≈ −3.5 bp), that's ≈ +6 bp/trade of improvement vs trading everything.
- If event windows avoid adverse hours (EXP-13 FX 1h ≈ −1 bp), +1 bp/trade.
- Sum: a handful of −3 bp trades avoided + costs avoided ≈ the margin we need.
  Whether it crosses zero is exactly the feasibility question the demo answers.

## 6. Non-goals

No ML selection in the demo (R1 uses the existing model's probability, not new
training); no new instruments; no deviation-quantile or lookback search; no
live-money ever in this spec; no claim of edge.

---

*This spec does not approve money at risk. It approves a ≥4-week paper feasibility
test — with a hard stop — after the prerequisite PnL fix lands.*