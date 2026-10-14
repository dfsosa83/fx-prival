# Frival Desk — Master Operations Manual

Single source of truth for running the autonomous Frival execution desk.
Last updated 2026-10-14. English; the desk brief and historical handoffs are in
Spanish.

> If you are a new agent: read this file top-to-bottom, then read
> `ACTIVE MONITOR — Frival desk.md` (the live cron brief) and `AGENTS.md`
> (binding rules). Everything else is reference.

---

## 0. TL;DR (read this first)

- **What:** autonomous execution on MT5 account `81486396` (FP Markets live),
  symbols XAUUSD, EURUSD, USDJPY. The agent evaluates structure, emits a signal,
  and `order_executor.py` enforces the guardrails in code.
- **Where:** work from `frival/` with
  `C:\Users\sosap\anaconda3\envs\frival\python.exe`.
- **Cadence:** a cron `*/15 * * * *` resumes this Kilo session every 15 minutes
  with a fixed prompt (the brief). Each fire = exactly one cycle (STEPS 1-7).
- **Hard rules:** `order_executor.py` is the ONLY component authorised to place,
  modify or close orders. **Never** `place --force`. **Never** run
  `reconcile_deals.py apply` (it is read-only; `apply` mislabels rows).
- **Safe state:** flat (0 positions, 0 pending) is the safe state to leave it in.
- **If anything is ambiguous:** stop and report in the `=== ESTADO ===` format
  rather than improvising.

---

## 1. What the desk is

A semi-systematic discretionary desk. Each cycle the agent:

1. reads live market structure for the three symbols;
2. applies data-quality + geometry gates;
3. if a setup clears **all four gates**, emits a signal and places an order;
4. runs `manage` (break-even / partial);
5. reports `=== ESTADO ===`.

The "system" is the agent's structure reading plus the executor's hard
guardrails. There is no black-box model in this desk (an unrelated ML pipeline
lives in `frival/DAILY_ROUTINE.md` and is NOT this desk).

---

## 2. How it runs continuously

- **Cron:** `*/15 * * * *`. The prompt is the content of
  `ACTIVE MONITOR — Frival desk.md`; each fire runs one cycle.
- **Dependencies for "always operating":**
  - the Kilo app/session must stay **open** (the cron is session-scoped; if the
    app is closed, cycles stop);
  - the **MT5 terminal** must stay running and logged into `81486396`.
- **Pause/resume semantics:** if the PC sleeps or the app closes, missed cron
  fires are **not** replayed one-for-one; on resume, queued fires can drain in a
  burst (you will see several cycles fire with the market clock barely moving).
- **While away:** leave the desk flat. With no positions there is nothing at
  risk and no automation is required overnight.

---

## 3. Clocks and market hours (operator-confirmed)

- **Local = UTC-5. Broker server = UTC+3.** (Everything in the executor and log
  is server-clock unless labelled `_local`.)
- Daily close **16:00 local = 00:00 server**; reopen **17:00 local = 01:00
  server**. Friday closes 16:00 local and does not reopen; Sunday reopens 18:00
  local.
- Around the daily close/rollover: gold has a break, spreads blow out, ticks go
  stale. The desk must not open new positions then (data-quality gate).
- **Correction of record:** an older brief stated a "23:00-00:30 server" rollover
  window; that was off by an hour. The confirmed hours above are authoritative.
- After a weekend/thin period the first M15 can gap — verify ATR before emitting.

---

## 4. The cycle (STEPS 1-7)

1. **Read** XAUUSD/EURUSD/USDJPY: M5 / M15 / H1, current tick, spread, clean
   ATR(M5), server clock. Read-only helpers are **in the repo**: `frival/frival_read.py`
   (full structure + gate inputs) and `frival/frival_bars.py` (OHLC bars). Both run
   from anywhere (`python frival_read.py`). This supersedes the old `%TEMP%` copies.
2. **Data-quality gates** (any fail => WAIT):
   - spread < 50% of ATR(M5);
   - tick fresh (server-clock);
   - not in the daily close/rollover window;
   - last completed M15 range < 2x ATR(M5) (thin-book guard).
3. **Geometry gates** (all four must hold to be EXECUTABLE):
   - SL beyond a real swing high/low, FVG or order block;
   - SL distance 1.0x-4.0x ATR(M5);
   - R:R >= 1.9 to the order's TP (if 1.9 is only reached at TP2/TP3, use that as
     the order TP and say so);
   - risk <= 5% of live equity.
4. **If executable:** `log_trade.py signal` -> `market_context.py capture` ->
   `order_executor.py place`. If the price is already at the level, `place --market`.
5. **If not:** WAIT, and log the rejected setup as a counterfactual.
6. **Manage:** run `order_executor.py manage` every cycle (BE, partial, stale).
7. **Report:** `=== ESTADO ===` block with the MT5 config section
   (VENCIMIENTO / INVALIDACIÓN).

---

## 5. Entry technique

- Structure-first: **breakout-retest** and **retest-of-broken-level**
  continuations. Entry is a resting LIMIT at the level (nudged by the spread —
  see §13); do not chase.
- **Targets are real levels**: prior H1/M15 swing highs/lows or measured moves.
  No level => no trade.
- **Momentum alignment** is recorded on every signal (`mom_alignment` =
  ALIGNED/AGAINST) but is **advisory, not a veto**, until ~20-30 samples are
  measured. Evidence: C040 was vetoed on AGAINST and would have made +3.1R.
- If price runs without a retest and the entry goes stale (would need a full
  reversal to fill), **cancel** it (the "T011 rule").

---

## 6. Position sizing — MANDATORY

Never use fixed lots. Size from the risk budget, per symbol:

    volume = (equity * RISK_PCT/100) / (sl_distance * money_per_price_unit)

- `money_per_price_unit` = USD value of a 1.00 PRICE move per 1.00 lot, from the
  broker (`symbol_info.trade_tick_value / trade_tick_size`) or
  `log_trade._money_per_price_unit_per_lot(symbol)`. **Never hardcode.**
  Live: **XAUUSD 100, EURUSD 100000, USDJPY ~632.**
- `RISK_PCT` = 5.0 (`MAX_RISK_PCT_PER_TRADE`). Round **down** to the 0.01 lot
  step; state the realised `risk_pct`.
- Use the helper: `log_trade.py size --symbol X --entry E --sl S`, or pass
  `--risk-pct 5` to `log_trade.py signal` instead of `--volume`.

At ~$700 equity and SL = 1.5xATR(M5), 5% risk is roughly:

| symbol | correct vol | risk at the 0.01 min lot |
|---|---|---|
| XAUUSD | ~0.045 | ~$7 (1.0%) |
| EURUSD | ~0.5-0.6 | ~$0.06 (0.01%) |
| USDJPY | ~0.6-0.7 | ~$0.5 (0.07%) |

**The recurring error is tiny FX lots.** USDJPY at 0.01-0.02 lots risks < $1 —
30-50x undersized (T017 0.01 = -$0.61; T025 0.02 = -$0.71). Derive it from the
formula; never reuse a gold lot count on an FX pair.

---

## 7. Risk controls (all enforced in code)

`order_executor.py` constants (verify live with `order_executor.py status`):

| Control | Value | Constant |
|---|---|---|
| Risk per trade | 5.0% | `MAX_RISK_PCT_PER_TRADE` |
| Aggregate risk (all open) | 12.0% | `MAX_RISK_PCT_TOTAL` |
| Max positions | 3 | `MAX_POSITIONS` |
| Same-USD-thesis cap | 2 | `MAX_SAME_THESIS` |
| Min R:R to TP | 1.9 | `MIN_RR` |
| SL vs ATR(M5) | 1.0x - 4.0x | `MIN_ATR_MULTIPLE`, `MAX_SL_DISTANCE_PCT_OF_ATR` |
| Min margin level after | 100% | `MIN_MARGIN_LEVEL` |
| Break-even at | +50% to TP1 | `BE_FRACTION` |
| Partial close at | +50% to TP2 | `PARTIAL_AT_FRACTION`, `PARTIAL_CLOSE_FRACTION` |
| Consecutive-loss pause | **4** | `MAX_CONSECUTIVE_LOSSES` |
| Daily-loss halt | **10%** | `MAX_DAILY_LOSS_PCT` |
| Hard equity floor | **18%** | `MAX_RISK_PCT_TOTAL_LOSS_CAP` |
| Edge-stop spacing (advisory) | >= 20 pips | `MIN_EXTREME_STOP_SPACING_PIPS` |
| Limit entry spread nudge | on | `NUDGE_LIMIT_ENTRY_BY_SPREAD` |

- The consecutive-loss counter and `daily_realised` are recomputed from the trade
  log every cycle (`refresh_state_from_log`). Before 2026-10-06 they were read but
  never written — the breaker silently did nothing. Fixed.
- **The consecutive-loss breaker resets at the server-day boundary** (server 00:00
  = local 16:00): it counts only trades closed in the current server day, newest
  first, stopping at the first win. Before 2026-10-12 it scanned the whole ledger
  and only a win cleared it (a full halt could never self-heal; audit F-09). Fixed.
- Margin for the guardrail comes from `mt5.order_calc_margin()` (currency-aware),
  **not** a hand-rolled notional. The old `vol*contract_size*entry` treated a
  JPY-quoted pair's price as USD (USDJPY 1.00 lot -> ~$31,638 instead of ~$200),
  hard-capping USDJPY at ~0.02 lots. Fixed 2026-10-12 (audit F-03).
- **Kill switch:** write `STOP` to `frival/data/emergency_stop.txt` (constant
  `KILL_SWITCH`) to block all new entries. `close-all` still works (never block
  closing).
- The consecutive/daily/floor numbers are the operator's policy; the mechanics
  are code.

---

## 8. Execution commands (full flow)

    # 1. log the signal BEFORE placing
    python log_trade.py signal --id T0NN --symbol XAUUSD --side SELL \
      --order-type LIMIT --volume 0.02 --entry 4143.50 --sl 4147.54 \
      --tp1 4132.20 --trigger "..." --bias "..." --notes "..."
    # or auto-size:  ... --risk-pct 5   (instead of --volume)

    # 2. reproducible market snapshot
    python market_context.py capture --id T0NN

    # 3. place (executor blocks if any guardrail fails). NEVER --force.
    python order_executor.py place --id T0NN
    # if price is already at the level:  place --id T0NN --market

    # 4. manage every cycle (BE, partial, stale)
    python order_executor.py manage

    # 5. cancel a pending order (via broker, never by editing the CSV)
    python order_executor.py cancel --id T0NN

    # 6. log a rejected setup (dataset)
    python counterfactual.py consider --id C0NN --symbol X --side BUY \
      --order-type LIMIT --volume V --entry E --sl S --tp1 T \
      --trigger "..." --reject-reason LEVEL_ALREADY_TESTED

    # 7. metrics
    python counterfactual.py stats
    python log_trade.py stats
    python order_executor.py status

    # emergency flatten (always allowed)
    python order_executor.py close-all --force --reason "reason"

---

## 9. Components (what each file does)

In `frival/`:

- `order_executor.py` — the ONLY order authority. `status`, `place`, `manage`,
  `cancel`, `close-all`. Holds the guardrails, STATE, and audit.
- `log_trade.py` — trade-log CLI. `signal`, `exit`, `fill`, `stats`, `size`,
  plus `_money_per_price_unit_per_lot`, true-fill resolution, momentum logging.
- `market_context.py` — reproducible per-signal snapshot (quote, account, ATR on
  5 timeframes, bars) -> `context/T0NN.{json,md}`.
- `counterfactual.py` — logs considered-but-rejected setups and resolves them
  against price. `consider`, `sweep`, `stats`.
- `reconcile_deals.py` — matches the log against broker deals. **Read-only;
  never run `apply`** without understanding it (it mislabels OPEN).
- `quality_gate.py` — per-cycle data-quality instrumentation. `log` appends each
  symbol's spread%/ATR, M15-range/ATR, tick age and blocking gate to
  `data/quality_gates.csv`; `stats` prints the block-rate. Measurement only, no
  orders. Run `log` every cycle (see the brief).
- `eod_review.py` — daily review generator (facts only). See §16.
- `ml_intraday_snapshot.py` — writes XAUUSD M5..H4 bars to CSV (unrelated ML).
- `mt5_path.py` — resolves the MT5 terminal path.
- `main.py`, `signal_gate.py`, `live_logger.py`, etc. — the older ML pipeline.

Data files: see §10.

---

## 10. Logs and data (locations + meaning)

All under `frival/`:

- `trade_log.csv` — the ledger. One row per trade; 40+ columns incl.
  `log_id, symbol, side, volume, entry_price, stop_loss, tp1, sl_distance,
  risk_usd, risk_pct_equity, mom_alignment, regime, regime_detail, be_executed,
  status, fill_price, exit_price, pnl_usd, r_multiple, mfe_usd, mae_usd, notes`.
  Status values: PENDING_FILL / ORDER_PLACED / OPEN / CLOSED / SKIPPED.
- `counterfactuals.csv` — rejected setups + their resolution (TP/SL/expired).
- `execution_audit.jsonl` — every executor action with the guardrail verdicts.
- `executor_state.json` — session date, session-start equity, consecutive_losses,
  daily_realised (rebuilt each cycle).
- `context/T0NN.json` + `T0NN.md` — exact market at each signal.
- `IMPROVEMENTS.md` — running changelog of system changes + lessons + backlog.
- `data/emergency_stop.txt` — kill switch (only if armed).

Docs (repo root / frival):
- `ACTIVE MONITOR — Frival desk.md` (root) — the live cron brief (STEPS 1-7).
- `AGENTS.md` (root) — binding agent rules (auto-loaded).
- `OPERATIONS.md` (root, this file) — the master manual.
- `frival/SETUP_NEW_MACHINE.md` — machine/setup notes.
- `continua-operando.md` (root) — **historical** session handoff (2026-10-02);
  keep for context, but this file supersedes it.

---

## 11. Ledger and performance (as of 2026-10-14)

- Account `81486396 FPMarketsSC-Live`; equity **~$744** (from a $604 trough at the
  2026-10-02 close — **+~23%**).
- `log_trade.py stats`: 51 rows, 29 closed, **win rate 12/29 (41.4%)**, total
  **+$149.82**, total **+4.42R**, avg R +0.15, best +3.34 (T046), worst -1.28 (T043).
- Shape: winners ~2R, losers ~-1R; the R:R engine carries a sub-50% hit rate.
- Counterfactuals: 47 resolved / 0 pending; mean +0.41R (t +1.52) — that headline
  mean is INFLATED by no-fill artifacts (F-10); read it by reject reason, not
  overall.
- Recent: T046 +3.34R and T047 -1.02R (2026-10-12); T051 +0.33R (2026-10-14). On
  2026-10-14 a broad USD squeeze crashed gold −$70 in 30 min; the thin-book gate
  kept the desk flat through it. The losing cluster (T029, T032-T034, T042/T043)
  was retests inside a whipsaw range.

---

## 12. Rules that are not up for debate

1. **The log is a record, not a control.** To cancel/modify, act at the broker
   (`order_executor.py`), never by editing the CSV.
2. **`sl_distance` is in PRICE UNITS**, and the executor cross-checks it against
   `|entry - SL|` (aborts on mismatch).
3. **Compute the arithmetic on the grid before emitting**, never by hand.
4. **Never `place --force`.** If the executor blocks, fix the levels and re-emit.
5. **Never run `reconcile_deals.py apply`.** Use `scan`/`audit` only.
6. **`order_executor.py` is the only order authority.**
7. **Log the signal BEFORE placing**, and capture the market context.
8. If a level breaks, re-read the structure; do not assume the next level.

---

## 13. Gotchas and lessons (all found live, all fixed)

- **Fill vs signal entry:** PnL must come from the broker fill, not the signal
  entry. `log_trade.py exit` now resolves the true opening fill (deal comment
  `FRIVAL_<id>`).
- **Upsert by id:** re-emitting a signal updates its row; it no longer appends a
  duplicate (which had blocked an ATR-floor fix on T032).
- **Symbol-aware row matching:** `manage` maps a live position to its log row
  with a `max(0.005, 0.25xATR)` tolerance. A fixed 0.005 retired every gold
  position (gold fills differ from the signal entry by ~the spread), so BE never
  ran.
- **Intrabar BE:** BE/partial trigger on intrabar M5 extremes since the position
  opened, not the poll tick (T030 pierced its BE level and reverted before the
  poll; T038 confirmed the fix).
- **Limit-entry spread nudge:** quotes are bid, so a limit on a level can miss by
  the spread (T035 buy missed; T039 sell missed by 0.04). Both sides are nudged
  by the spread now.
- **Schema-tolerant writers:** the partial path sets `be_executed`; `save_log`
  used to crash mid-write and **truncate the ledger** (T040). It now writes the
  union of all keys, and **every writer is write-then-rename** (temp file +
  `os.replace`), so a mid-write failure cannot truncate `trade_log.csv`,
  `counterfactuals.csv` or `executor_state.json` (2026-10-11/12).
- **`manage` retired live pending orders (F-06):** it matched rows against
  `positions_get()` only, so every resting limit's row was wrongly marked CLOSED
  and the order orphaned (T048, 2026-10-12). It now also checks `orders_get()`.
- **USDJPY could not be sized correctly (F-03):** margin came from
  `vol*contract_size*entry`, treating a JPY-quoted price as USD (USDJPY 1.00 lot
  -> ~$31,638 instead of ~$200), hard-capping USDJPY at ~0.02 lots. It now uses
  `mt5.order_calc_margin()`. Fixed 2026-10-12.
- **The consecutive-loss breaker did not reset daily (F-09):** it scanned the
  whole ledger and only a win cleared it. It now resets at the server-day
  boundary. Fixed 2026-10-12.
- **Counterfactuals assume a fill (F-10):** the resolver credits every limit as
  if tagged, so `STALE_ENTRY` / cancelled rows read as fake TP wins. Verify the
  entry was really tagged before crediting R.
- **Premium data:** during rollover / a flash move (2026-10-07 ~15:25 server:
  gold −50 pts; 2026-10-14 ~15:30 server: gold −$70 in 30 min) the desk stands
  aside via the thin-book gate.

---

## 14. Open backlog (see `IMPROVEMENTS.md` for detail)

- Whipsaw/regime filter (skip retests when the last 3 H1 bars alternate with
  ranges > 1.5x ATR) — **now measuring**: a `regime` flag
  (WHIPSAW/ALTERNATING/TREND) + `regime_detail` is recorded on every signal and
  counterfactual since 2026-10-11, and both `stats` commands print meanR by
  regime. Enforce only once the by-regime data justifies it.
- Hard-enforce the momentum filter once `mom_alignment` has ~20-30 samples.
- ~~Tighten the executor `sl_distance` mismatch tolerance~~ **done 2026-10-11**
  (now `max(tick_size*5, sl_dist*1%)`; the old 0.05 floor was ~500 pips on EURUSD).
- ~~Write-then-rename for `trade_log.csv`~~ **done 2026-10-11** (all three writers
  now write to a temp file and `os.replace` it).
- ~~Consecutive-loss daily reset~~ **done 2026-10-12** (audit F-09).
- ~~USDJPY margin / notional (F-03)~~ **done 2026-10-12** (`order_calc_margin`).
- ~~`manage` retiring live pending orders (F-06)~~ **done 2026-10-12**.
- **External audit (2026-10-11, `auditorias/`) — PENDING OPERATOR APPROVAL.**
  Two other-agent worktrees (frival-p001-wt, frival-p002-wt) plus a remediation
  plan flag P0-P4 issues not yet acted on. Highest-severity OPEN ones: **F-01**
  (`close-all` has no account/ownership filter — it flattens every position on
  the account) and **F-04** (`place` has no idempotency/reservation before
  `order_send`). (F-03, F-06, F-09 and F-10 are already handled — see §13.) The
  plan itself says "implementation not authorised". See §17.

---

## 15. Resume checklist (after any stop)

1. Confirm the MT5 terminal is running and logged into `81486396`.
2. `python order_executor.py status` — check equity, positions, pending, breaker
   state (`consecutive losses N/4`, `daily realised`, `drawdown`).
3. If the kill switch is armed from a prior session, clear it
   (`frival/data/emergency_stop.txt`) — the monitor does not clear it.
4. `python reconcile_deals.py scan` (and `audit`) — register any closed trades
   whose P&L is not yet in the log. **Do not `apply`.**
5. Re-read fresh structure (levels from the prior session are stale).
6. Continue the cycle (STEPS 1-7) with the config in §7.

---

## 16. End-of-day review (daily close)

Once per day, during the close window, the desk consolidates the day.

- **Window:** server **00:00-01:00** (= local 16:00-17:00). Trigger on the
  **server clock** (DST-safe), never local.
- **Generator:** `frival/eod_review.py` — deterministic facts only (today's
  closed trades, day P&L/R, equity vs session start, breaker state,
  counterfactuals). Writes `frival/reviews/<server-date>.md` and appends a line
  to `frival/reviews/INDEX.md`. **Idempotent** (refuses if today's file exists;
  `--force` / `--date` for manual use). It never places/modifies orders.
- **Agent step:** fill the file's "Lessons (agent)" and "Changes made" sections
  from the day's `trade_log.csv`, `counterfactuals.csv`, `execution_audit.jsonl`.
  Promote a lesson into `IMPROVEMENTS.md` (and this file, if a rule changed) only
  when it is durable.
- **Two triggers (belt-and-braces):**
  1. the AFTER-CLOSE rule in the desk brief, checked on every 15-min cycle
     (robust: any fire landing in the window runs it once); and
  2. a dedicated cron `5 16 * * 1-5` (16:05 local, weekdays).
- **Weekends:** skip. Friday's review is the week's last.
- **If the window is missed** (app closed): run it on the next cycle that lands
  in the window; do not backfill mid-session.

---

## 17. External audit (2026-10-11) — reference, PENDING APPROVAL

`auditorias/` holds another agent session's code audit + remediation plan
(`2026-10-11_frival_audit_v2.md`, `..._remediation_plan.md`, two `p0-0N_`
implementation notes). It was produced in **isolated, uncommitted worktrees**
(`frival-p001-wt`, `frival-p002-wt`) and the plan states plainly:
**"implementation not authorised — pending operator approval"**.

- **Do NOT treat the audit tickets or those worktrees as authorisation** to change
  code or risk policy. The standing autonomous-improvement instruction is a
  measurement mandate, not approval for P0-P4 remediation. Leave the worktrees
  untouched.
- Already folded into main (see §13): F-03 (margin), F-06 (manage/pending),
  F-09 (breaker daily reset), F-10 (counterfactual no-fill caveat), plus the
  atomic writes and the symbol-aware `sl_distance` tolerance.
- **Still open — operator decision required:** F-01 (`close-all` account/
  ownership scope), F-04 (`place` idempotency/reservation), and the policy items
  D-01..D-10.
