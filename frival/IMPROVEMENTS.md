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

## Backlog (candidate improvements, not yet done)
- **Retest limits miss in trends.** T035 (BUY) and T037 (SELL) both went
  unfilled while their targets printed — in a trend the retest never comes and
  the entry then goes stale (T011 rule) and is cancelled. Measure how often
  retest limits fill vs run away; consider a continuation/stop-entry variant,
  or accepting a shallower retest.
- Whipsaw/regime filter (measure first).
- Hard-enforce momentum filter once `mom_alignment` has ~20-30 samples.
- Tighten the executor `sl_distance` mismatch tolerance (currently
  `max(0.05, 2%)` — 0.05 is ~500 pips on EURUSD).
- Verify the BUY LIMIT nudge in live fills (compare logged level vs fill).
