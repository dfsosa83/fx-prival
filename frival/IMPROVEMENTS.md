# Frival desk — system improvements log

Running record of changes to the desk and the lessons that drove them. Each
entry: date, what changed, why, and the evidence. The desk operator authorised
autonomous improvement on 2026-10-06 ("do it, do not wait for my
authorization; the system should learn every time").

## 2026-10-06

### Fixes (commits 7837988, e62838c)
- **PnL from true fill.** `log_trade.py exit` resolves the broker's opening
  deal (`FRIVAL_<id>`) when `fill_price` is empty. Evidence: T028 booked
  -1.04 from the signal entry 4142.75; the broker filled 4142.46 (-0.75).
- **Upsert by id.** `signal` now updates the row for an existing `log_id`
  instead of appending a duplicate; `_load` collapses historical duplicates.
  Evidence: T032 was blocked because `place` read a stale first row after a
  re-emit appended a second.
- **Precision.** `sl_distance`, `be_trigger_price`, `atr_*_at_signal` now 5dp;
  `.2f` zeroed EURUSD stops (T013/T016 logged 0.00) and EURUSD ATR.
- **Intrabar BE/partial.** `order_executor.manage` moves BE and partial
  triggers on intrabar M5 extremes since the position opened, not the poll
  tick. Evidence: T030 pierced 4116.76 past its 4119.36 BE trigger and
  reverted before the next cycle, so full stop risk stayed on a +0.9R trade.

### Rule: risk-based sizing (AGENTS.md)
- `volume = (equity * RISK_PCT) / (sl_distance * money_per_price_unit)`, per
  symbol, never a fixed lot. New `log_trade.py size` helper and
  `signal --risk-pct`. Evidence: USDJPY at 0.01-0.02 lots risked <$1
  (T017 -0.61, T025 -0.71) vs ~0.6-0.7 lots needed for 5%.

### Rule: momentum alignment (AGENTS.md)
- Do not enter against the immediately-preceding H1 candle body. Logged as
  `mom_alignment` on every signal so the filter can be MEASURED before it is
  hard-enforced in the executor. Evidence: T032 bought into a rejection bar.
- Decision 2026-10-06: NOT hard-enforced yet — a strict rule would also have
  blocked winners (T020 +2.60R, T021 +2.08R). Measure first.

### Fix: working loss circuit breaker (commit e62838c)
- `refresh_state_from_log()` recomputes `consecutive_losses` and
  `daily_realised` from the trade log every cycle. Before this, those STATE
  keys were READ but never WRITTEN, so the consecutive-loss breaker and the
  daily-loss halt always passed and `MAX_RISK_PCT_TOTAL_LOSS_CAP` was never
  checked — the desk had NO working loss circuit breaker.
- Values: pause new entries at **4** consecutive losses (operator),
  daily-loss halt **10%**, hard equity floor **18%** (operator, was 25%).

### Lessons from the 2026-10-06 session
- The 4170-down-to-4150 whipsaw stopped four XAUUSD retests (T029, T032-T034)
  while the two ~2R winners (T030/T031) came from cleaner breakouts/retests
  with real structural targets.
- Retest entries repeatedly **missed by the spread** (T034 filled only after a
  deeper dip; T035 missed three times then went stale and was cancelled per
  the T011 rule). Consider whether the desk should widen limit entries by the
  spread or use a small buffer.
- Open idea: a whipsaw/regime filter (skip retests when the last 3 H1 bars
  alternate with ranges > 1.5x ATR). Measure before enforcing.

### Fix: BUY LIMIT spread nudge (order_executor.py)
- Quotes/bars are BID, so a BUY LIMIT placed exactly on a bid level only fills
  after the bid trades ~spread below it. Evidence: T035 BUY LIMIT 4166.50, bid
  low 4166.6, ask never reached 4166.50 -> unfilled, then price ran to 4184 and
  the +2.73R target hit without us. `cmd_place` now places a BUY LIMIT at
  `level + spread` (guarded to stay below the ask) so a touch of the intended
  level fills. SELL LIMITs are unaffected (they fill on the bid, which matches
  how levels are read). Toggle: `NUDGE_BUY_LIMIT_BY_SPREAD`; nudges are audited
  as `LIMIT_ENTRY_NUDGE`.

## 2026-10-07

### Fix: SELL LIMIT spread nudge (mirror of the BUY nudge)
- A SELL LIMIT fills when the BID reaches it, so one placed exactly on a bid
  level can miss by the spread. T039 proved it: bid high 4137.46 vs the 4137.50
  entry — a 0.04 miss — and the target (4123.18) then nearly printed without us.
  `cmd_place` now nudges a SELL LIMIT down by the spread (guarded above the
  bid), symmetric to the BUY nudge. Constant renamed
  `NUDGE_BUY_LIMIT_BY_SPREAD` -> `NUDGE_LIMIT_ENTRY_BY_SPREAD` (both sides).

### Rule change: momentum filter back to ADVISORY (not a veto)
- I over-enforced the momentum filter: cancelled T036 on 2026-10-07 because
  `mom_alignment=AGAINST`. That setup (logged as C040) resolved **TP_ONLY, MFE
  22.8** — it would have hit its target for ~+3.1R. Vetoing every entry against
  the prior H1 body is too blunt. AGENTS.md now says: record and scrutinise the
  flag, do NOT cancel an otherwise valid setup solely because it is AGAINST,
  until ~20-30 samples are measured. Lesson: measure before enforcing.

### Fix: EOD review targeted the wrong day at the close
- The daily close is server 00:00, so a review run in the 00:00-01:00 window
  (the dedicated cron fires 16:05 local = server 00:05) had a wall-clock server
  date of the NEXT day. `eod_review.py` would have written a near-empty review
  for the new day instead of the one that just closed. Default day is now taken
  from the most recent trade's `logged_at_server` (the trading day that just
  ended), falling back to the server date only if the log is empty.

### Fix: exit PnL ignored partial closes
- `log_trade.py exit` computed PnL as `(exit-entry) x full volume`, ignoring
  partial closes. T041 booked **+78.75** when the broker actually paid **+38.47**
  (0.03 of 0.05 had already closed early at +6.81; only 0.02 reached the TP).
  New `_resolve_realised_from_broker()` sums every deal sharing the entry
  deal's `position_id` (partials + final); `exit` now prefers that broker total
  and falls back to the estimate only when history is unavailable. Verified:
  T040 -> 12.66, T041 -> 38.47 (both match the broker).

### Fix: save_log schema crash truncated the ledger (be_executed)
- The partial-close path sets `be_executed` on a row. `order_executor.save_log`
  took fieldnames from `rows[0]` and raised "dict contains fields not in
  fieldnames" — AND it had opened the CSV with mode `"w"`, so trade_log.csv was
  truncated mid-write and T040's row was lost (its partial had already executed
  at the broker). This only surfaced because the earlier tolerance fix made
  `manage` actually run on gold positions for the first time.
- Fix: `save_log` now writes the ordered union of all row keys (with
  `extrasaction="ignore"` as a safety), and `be_executed` is a real column in
  `log_trade.COLUMNS`. T040 was reconstructed from `context/T040.json` and
  reconciled from broker deals (partial +12.96, BE remainder -0.30, net +12.66).
- Lesson: a writer must be schema-tolerant, and should write-then-rename so a
  mid-write failure cannot destroy the file.

### Fix: manage skipped every gold position (BE/partial never ran)
- `cmd_manage` mapped a live position to its log row with a fixed entry
  tolerance of 0.005. A gold order fills at the bid/ask, so the fill differs
  from the signal entry by ~the spread (T038: signal 4149.00, fill 4149.04).
  0.04 > 0.005, so T038 was marked CLOSED in memory and skipped by the
  management loop — BE and partial never ran on ANY gold position. Tolerance
  is now symbol-aware (`max(0.005, 0.25 * ATR(M5))`).
- The new intrabar line used `mt5.copy_rates_from_pos(...) or []`, which raises
  "truth value of an array with more than one element is ambiguous". Fixed with
  an explicit None check.
- Evidence: T038 reached +2R (price 4141.33, BE level 4144.52) and manage did
  nothing; after the fix manage moved the SL to break-even 4149.04.
- Note: `cmd_manage` still does not persist its in-memory stale-row retires
  (no save_log call). Low impact today but worth aligning.

## 2026-10-08

### Lesson: a violent gold whipsaw defeats retests BOTH ways
- Gold spent the day in a ~4105-4140 range punctuated by spikes. Two full-risk
  losses: **T042** (short filled 4117.75, stopped at 4123.02) and **T043**
  (short filled 4115.98, stopped at 4121.11) — both filled on the intended
  retest and then the tape reversed straight through the stop.
- Simultaneously, several setups were RIGHT on direction but the retest never
  came, so they expired unfilled (**T035, T037, T039**). So in this regime it
  fails whether you get filled or not: the *regime*, not the setup, is the
  problem. The desk's job is to recognise it and stand aside.
- Implication: the retest-limit style needs a **regime filter**, not a better
  level. Candidate (already in the backlog): skip new entries when the last ~3
  H1 bars alternate direction with ranges > 1.5x ATR (whipsaw). MEASURE this
  against the ledger before enforcing — same discipline as the momentum filter.
- Day result: 2 trades, both −1R range shorts; net −2.33R for the day, session
  still +$39.82. The discipline saved more than the setups earned.

## 2026-10-11

### Measurement: whipsaw regime recorded (no behaviour change) — P1
- `log_trade.py signal` and `counterfactual.py consider` now stamp `regime`
  (WHIPSAW / ALTERNATING / TREND) and `regime_detail` (the three per-bar
  range/ATR(H1) ratios) on every signal, from the last 3 completed H1 bars.
  WHIPSAW = directions strictly alternate AND each range > 1.5x ATR(H1).
- WHY: the losing cluster (T029, T033, T034, T042, T043) is all range-whipsaw,
  and the 2026-10-08 lesson called for a regime filter — but only after
  MEASUREMENT (the discipline that twice stopped the momentum filter being
  over-enforced). `log_trade.py stats` and `counterfactual.py stats` now print
  meanR **by regime**, so the filter can be decided on data. It does NOT gate
  entries.
- First live reads: XAUUSD TREND (rH1atr 0.87/0.74/0.31); USDJPY ALTERNATING
  (0.61/0.66/1.61). New rows carry the flag; pre-existing rows read NA.

### Guard: undersized-lot warning — P3
- `log_trade.py signal` warns and stamps `[UNDERSIZED risk_pct=x.xx]` into
  `notes` when realised risk < 1% of equity; `log_trade.py size` warns too.
  Catches the desk's most repeated error — a manually passed tiny FX lot
  (T017 0.01 = -$0.61, T025 0.02 = -$0.71) — at log time. Non-blocking.
  Verified: USDJPY manual 0.01 lot -> "UNDERSIZED risk_pct=0.18".

### Hardening: write-then-rename on every evidence writer — P4
- `order_executor.save_log`, `log_trade._save` and `counterfactual._save` now
  compose the new file beside the target and `os.replace` it, so a mid-write
  failure can no longer truncate `trade_log.csv` / `counterfactuals.csv` (T040's
  row was lost this way on 2026-10-07). Closes the §14 backlog item for all
  three writers. Verified reversibly.
- NOTE: the 2026-10-11 external audit (`auditorias/`) flags further P0-P4 issues
  (F-01 `close-all` account scope, F-04 `place` idempotency, F-06 stale rows,
  F-03 notional/margin unit) as **pending operator approval** — not acted on here.

### Hardening: symbol-aware sl_distance mismatch tolerance
- `guardrail_report` cross-checks the logged `sl_distance` against
  `|entry - SL|` with `max(0.05, sl_dist*0.02)`. On EURUSD 0.05 is ~500 pips,
  so a grossly wrong `sl_distance` passed for FX (the 2026-10-02 bug that let a
  10.70 column validate a 6.51 stop was gold; FX was still wide open). It is now
  `max(tick_size * 5, sl_dist * 0.01)`: a few broker ticks absolute, 1% relative.
  Verified: a matching EURUSD `sl_distance` does not abort; a +0.01 (100-pip)
  mismatch aborts.

### Hardening: manage persists stale-row retires — P4
- `cmd_manage` mutated stale OPEN/ORDER_PLACED retires in memory but only
  called `save_log` when a BE/partial fired, so it re-retired the same rows
  every cycle. It now persists whenever it retires a row.

### Safe P0/P1 robustness (operator-approved scope, 2026-10-11)
- **`guardrail_report` response shape** — the symbol/tick-unavailable early
  return was `{"ok": False, "reason": ...}` with no `failed` key, so
  `cmd_place` raised `KeyError('failed')` (fail-closed but unaudited). It now
  returns the same shape as the normal path. (audit remediation P2-02.)
- **Atomic `save_state`** — write-then-rename like the ledgers, so a mid-write
  failure cannot corrupt `executor_state.json`.
- **`log_trade._save` writes the union of keys** — previously only the fixed
  `COLUMNS`, so a field written by another tool could be silently dropped on
  the next log_trade save. Now mirrors `order_executor.save_log`. (P1-01.)
- The external remediation plan's structural tickets (F-01 `close-all` scope,
  F-04 `place` idempotency/reservation, F-03 notional/margin units, D-01..D-10
  policy) remain **pending operator approval** and were NOT implemented.

## 2026-10-12

### Live observation — over-discretion cost R in a trend (gold)
- During the strong 2026-10-12 Asia uptrend (XAUUSD 4184 → 4217) the desk
  declined two retest-longs; both resolved **TP_ONLY**:
  - **C041** entry 4191.50 TP 4199.47 → **+1.14R** (rejected `R_R_BELOW_2_TO_TP1`;
    correct — it was below the 1.9 gate).
  - **C042** entry 4190.50 TP 4202.01 → **+1.92R** (rejected `NONE_TAKEN` on a
    qualitative "target sits near the 4199 top" judgement — **wrong**: geometry
    passed all four gates, R:R 1.92).
  - **C044** entry 4202.00 TP 4208.56 → **+1.64R** (rejected `NO_STRUCTURAL_TARGET`
    / SL 0.94x ATR under the 1.0 floor).
  - All three were `regime=TREND`; in a one-way trend every retest-long worked,
    so ~4.7R was forgone by the three rejections combined.
- **Lesson (repeat of the momentum-filter pattern):** once a setup passes all
  four gates, do NOT add a qualitative veto such as "target near resistance" or
  "entry needs a pullback / no chase". That is discretion overriding the rule.
  Re-measure before any policy change. The gates are the filter.
- **Regime signal to watch:** `regime=TREND` samples now all resolve TP. This is
  the counterpart to the whipsaw hypothesis — a trend-permissive mode (e.g.
  relax the R:R floor when H1 bars are NOT alternating) may be worth testing
  once the regime column has ~20 TREND/WHIPSAW samples. Not a rule yet.

### Fix: F-03 margin-unit bug (USDJPY was hard-capped at ~0.02 lots)
- `guardrail_report` now takes margin from `mt5.order_calc_margin()` (leverage-
  aware, currency-correct) instead of `notional = vol * contract_size * entry`.
  That formula treated USDJPY's JPY-quoted price as USD: 1.00 lot → ~$31,638
  margin vs the correct ~$200 (158x too high), so **every correctly-sized
  USDJPY order was blocked** and USDJPY was silently capped at ~0.02 lots
  (~0.1% risk) — the documented 30-50x undersizing. It cost the only valid
  USDJPY setup this session (C043, +2.07R, TP_ONLY).
- Verified: USDJPY 0.95 lot now `ok=True`, risk 4.99%, margin level 348%;
  XAUUSD/EURUSD margin values unchanged. Falls back to the old formula only if
  the broker query returns None, and records `margin_source` in the audit.
- NOTE: the 2026-10-02 policy comment that lowered `MIN_MARGIN_LEVEL` 500→100
  cited a "$157,754 USDJPY notional" derived from the same bug; that comment is
  now misleading and should be revisited with the operator.

### Fix: consecutive-loss breaker resets on the new session day (F-09)
- `refresh_state_from_log` now counts the streak only over trades **closed in
  the current server day** (newest-first, stopping at the first win), so the
  breaker resets at the server-day boundary **server 00:00 = local 16:00** —
  matching the documented "or a new session day". Previously it scanned the
  whole ledger and only a win cleared it, so a full halt could never self-heal
  and the code comment was wrong (audit F-09).
- Verified: breaker now reads **1/4** (only T045 closed in server-day
  2026-10-12; T042/T043 were 2026-10-08), down from the stale all-time 3/4.

### Fix: manage no longer retires live pending orders (F-06)
- The stale-row retirement in `cmd_manage` only consulted `positions_get()`, so
  a live resting LIMIT (status `ORDER_PLACED`, which has **no** position until
  filled) was auto-retired every cycle and its row wrongly marked `CLOSED`.
  The 2026-10-12 P4b change ("persist retires") made this stick: **T048** (a
  live XAUUSD SELL limit) was marked CLOSED, which orphaned the order and reset
  the loss-streak breaker (a `pnl=0.0` "closed" row breaks it).
- `manage` now matches `ORDER_PLACED` rows against `orders_get()` by symbol +
  `FRIVAL_<log_id>` and only retires when neither a matching position nor a
  matching pending order exists. Verified: T048 stays `ORDER_PLACED`; breaker
  reads 1/4. (audit F-06 / P1-03, minimal scope.)
- **Honest note:** the defect was latent (F-06), but my persistence change made
  it material — the persistence is correct, the row classification was not.
  Lesson: when persisting a previously in-memory mutation, re-check that the
  mutation is correct first.

### Observation — retest LIMITs miss by 1-2 pts (2 samples, watch)
- **T048** (SELL limit 4191.28; the bounce topped 4188.06 in its window) and
  **T049** (SELL limit 4181.28; bounce topped **4180.07**, 1.2 below) both had
  the direction right — gold fell to (or past) the target each time — but the
  resting LIMIT never filled, so both were cancelled stale (C045/C046). The
  limit is nudged −spread (0.22) yet still sits ~1-2 pts beyond the actual
  retest high, so shallow pullbacks miss it.
- **Both resolved `TP_ONLY` (+2.69R / +3.19R) but that is an F-10 no-fill
  artifact** — gold never returned to either entry after placement (it ranged
  4154-4175), so the real cost of the two cancels was ~0R. The counterfactual
  engine credits the full R as if filled; do NOT read these as missed winners
  until F-10 (a fill model) is addressed.
- Candidate fix (NOT applied): place the retest LIMIT **at or just inside** the
  swing/level rather than beyond it, accepting a touch-fill. Measure with the
  STALE_ENTRY counterfactuals first (fill-assumption caveat F-10 applies, so
  verify the entry was actually tagged before crediting any R).

### Measurement: data-quality gate instrumented (FX exploration decision)
- Operator observed that if the gates always block EURUSD/USDJPY, those pairs
  can never be tested (included or discarded) for lack of samples. Agreed plan:
  **instrument first, then decide** on any exploration quota.
- Added `frival/quality_gate.py` (MEASUREMENT ONLY, places no orders): each
  cycle logs per-symbol spread%/ATR, M15-range/ATR, tick age and which gate
  blocked (ROLLOVER/STALE/SPREAD/FROZEN/THIN/PASS), with a `spread_only` flag,
  to `frival/data/quality_gates.csv`. `python quality_gate.py stats` prints the
  block-rate per symbol. Run `log` every cycle alongside the read.
- Purpose: after ~1-2 days, tell "FX had no setups" apart from "FX blocked by
  the spread gate" BEFORE proposing a bounded FX exploration quota. If the
  spread gate is the dominant FX blocker, the next step is a tagged, reduced
  risk exploration entry (passes gates 1-4 but fails only spread) - NOT yet
  implemented, pending the data and operator sign-off.
- Note: counterfactuals are still logged manually when an FX setup fails only
  on spread (a setup is needed first; a bare gate-block alone has no levels).

### Gate-stats, day 1 (2026-10-13, n=33 per symbol)
- XAUUSD: PASS 20 / THIN 12 / ROLLOVER 1 -> **spread-blocked 0%**.
- EURUSD: PASS 13 / SPREAD 7 / THIN 12 / ROLLOVER 1 -> **spread-blocked 21%**.
- USDJPY: PASS 17 / SPREAD 6 / THIN 9 / ROLLOVER 1 -> **spread-blocked 18%**.
- Read: FX is blocked **more by THIN (volatility spike bar) than by SPREAD**, and
  FX *data-quality PASSES* 40-52% of cycles yet produced no entry — i.e. the
  binding constraint is **geometry (no 1.9R level), not the spread gate**. Early
  (1 day, N=33); per the agreed plan, do NOT loosen gates. Re-read when the CSV
  has ~3+ days. If SPREAD stays a minority blocker, the FX exploration quota is
  NOT justified.
- First day of the desk day 2026-10-13 also had **zero fills** (all cycles
  WAIT); no EOD review is generated for a zero-trade day.

## Backlog (candidate improvements, not yet done)
- **Retest limits miss in trends.** T035 (BUY) and T037 (SELL) both went
  unfilled while their targets printed — in a trend the retest never comes and
  the entry then goes stale (T011 rule) and is cancelled. Measure how often
  retest limits fill vs run away; consider a continuation/stop-entry variant,
  or accepting a shallower retest.
- Whipsaw/regime filter — now **measuring** (regime column added 2026-10-11);
  enforce only when the by-regime meanR justifies it.
- Hard-enforce momentum filter once `mom_alignment` has ~20-30 samples.
- Tighten the executor `sl_distance` mismatch tolerance (currently
  `max(0.05, 2%)` — 0.05 is ~500 pips on EURUSD).
- Verify the BUY LIMIT nudge in live fills (compare logged level vs fill).
