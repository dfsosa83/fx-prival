```
ACTIVE MONITOR — Frival desk. AUTONOMOUS EXECUTION ENABLED.
[MACHINE 2 — PRIMARY since 2026-10-05. The old desktop monitor is stopped.]

The operator authorised autonomous trading on 2026-10-02: "put the trades,
no fear." Read this whole brief before acting. It is self-contained; you have
no prior context.

python   = C:\Users\sosap\anaconda3\envs\frival\python.exe
terminal = auto-resolved by frival/mt5_path.py (this machine:
           C:\Program Files\FP Markets MT5 Terminal\terminal64.exe)
workdir  = C:\Users\sosap\Documents\fx-prival\frival

Read frival/SETUP_NEW_MACHINE.md and frival/DAILY_ROUTINE.md before your first
cycle. Key facts already verified on this machine: account 81486396
FPMarketsSC-Live, MT5 SDK 5.0.4874. Equity is LIVE — read it from
`order_executor.py status`; never trust a number printed in a doc.

=== STEP 1 — READ ===
XAUUSD, EURUSD, USDJPY: M5(15), M15(8), H1(6), tick + spread + tick age.
Triple clock: local UTC-5 / server UTC+3 (server = local + 8h).

DATA QUALITY GATES (block if any fails):
  - Daily close/rollover window 00:00-01:00 SERVER -> no new entries (open
    positions are held through it; SL/TP stay live at the broker). OPERATIONS.md
    §3 is authoritative; an older draft said 23:00-00:30 and was an hour off.
  - Tick age > 5 min -> stale quote, no trade
  - Spread > 50% of clean ATR(M5) -> no trade
  - Clean ATR(M5) < 1.0 -> frozen data, no trade
  - Last M15 range > 2.0x clean ATR(M5) -> thin book spike, no trade
  - Price in a structural VOID (no level within 15 points either side) -> no trade
Clean ATR: exclude bars where high==low OR tick_volume < 30% of median.

INSTRUMENTATION (measurement only, places no orders): every cycle run
  python quality_gate.py log          (script: frival/quality_gate.py)
appends per-symbol spread%/ATR, M15-range/ATR, tick age and which gate blocked
(ROLLOVER/STALE/SPREAD/FROZEN/THIN/PASS) to data/quality_gates.csv. `python
quality_gate.py stats` prints the block-rate. Purpose: over days, tell "FX had
no setups" apart from "FX was blocked by the spread gate" before deciding on any
bounded FX exploration quota. Structural-void / no-level stays an agent call.
Day-1 result (2026-10-13): FX was blocked MORE by THIN than SPREAD (spread ~18-21%)
and still found no setups -> FX is setup-starved, not spread-capped; do NOT loosen
gates on this evidence.

=== STEP 2 — GEOMETRY (this is the gate that matters) ===
A setup is EXECUTABLE when all four hold:
  1. SL sits beyond a real swing high/low, FVG or order block
  2. SL distance is 1.0x to 4.0x clean ATR(M5)
  3. R:R >= 1.9 to the target you are going to use
  4. Risk <= 5% of equity

If 1.9 is reached at TP2/TP3 but not TP1, USE TP2/TP3 as the order's TP and
say so in the first sentence. Do not discard the setup for that.

Multipliers (verified from the broker contract, not assumed):
  XAUUSD 100 per 1.00 move per lot; EURUSD 100,000; USDJPY ~632.
Never hardcode these — frival/log_trade.py has _money_per_price_unit_per_lot().

Max 1 net position. Pending orders count as exposure. CORRELATION, verified
against order_executor.py source — do not use the old brief's version, it was
backwards:
  USD_STRONG_PAIRS = EURUSD, USDCHF, AUDUSD, NZDUSD, XAUUSD   (SELL = USD strong)
  USD_WEAK_PAIRS   = USDJPY                                  (SELL = USD weak)
So: XAUUSD BUY and USDJPY SELL are both USD-weak. XAUUSD SELL and USDJPY BUY
are both USD-strong. Two bets on the same dollar is one position, not two.

=== STEP 3 — EXECUTE (this is the point) ===
  1) python log_trade.py signal --id T0NN --symbol X --side BUY/SELL \
       --order-type LIMIT/STOP/MARKET --volume V --entry E --sl S --tp1 T \
       [--tp2 T2] --trigger "..." --bias "..." --notes "..."
  2) python market_context.py capture --id T0NN
  3) python order_executor.py place --id T0NN [--market]
  4) Each cycle: python order_executor.py manage
The executor enforces risk, position count, R:R and ATR bounds. NEVER use
--force on place. If it blocks, fix the levels and re-emit.
If price is already at the entry level, use --market and say so.

=== STEP 4 — COUNTERFACTUAL ===
Log every REJECTED setup for data, not as a substitute for execution:
  python counterfactual.py consider --id C0NN --symbol X --side BUY/SELL \
    --order-type LIMIT --volume V --entry E --sl S --tp1 T \
    --trigger "..." --reject-reason REASON --notes "..."
  python counterfactual.py sweep
Check for ID collisions first: `python counterfactual.py stats` and look at
the csv. Duplicate C0NN ids crashed the sweep once.

Measured at N=47 resolved (mean +0.41R, t-stat +1.52 — POSITIVE but short of the
t>2 significance bar, and INFLATED by no-fill artifacts; see CAVEAT below). By
reject reason, and these supersede the old brief:
  LEVEL_ALREADY_TESTED    n=17  +0.40R  <- best filter; do NOT block on it
  CORRELATION             n= 2  +0.50R
  NONE_TAKEN              n= 6  +0.42R
  MOMENTUM_AGAINST        n= 1  +3.14R  <- one more data point against a hard veto
  MARGIN_UNIT_BLOCK       n= 1  +2.07R  <- C043, blocked by the old F-03 bug
  STALE_ENTRY             n= 3  +2.60R  <- ARTIFACT (entry never filled)
  NO_STRUCTURAL_TARGET    n= 5  -0.43R  <- keep this filter, never relax it
  R_R_BELOW_2_TO_TP1      n=11  -0.27R  <- the 1.9R floor is justified
The filter destroying the most R is NO_STRUCTURAL_TARGET. That is where any
tuning should start, not the 1.9R floor.
CAVEAT (F-10): the engine ASSUMES every limit fills. STALE_ENTRY / cancelled
rows therefore read as fake TP wins. Before crediting any R to a counterfactual,
verify the entry was actually tagged on the chart.

=== STEP 5 — CIRCUIT BREAKER ===
MAX_CONSECUTIVE_LOSSES = 4 (order_executor.py:121). The operator set it on
2026-10-06 (was disabled at 999); commit e62838c. It IS active: after 4 straight
losses it pauses NEW entries until a win or a new session day, and it RESETS at
the server-day boundary (server 00:00 = local 16:00). Do not change it without
the operator. (OPERATIONS.md §7 is the authoritative table.)

=== STEP 6 — POSITION MANAGEMENT ===
Bracket every entry with SL and TP. Move SL to breakeven at 50% of the
distance to TP1 — the guardrail does this itself on close, not on wick.
STANDING AUTHORISATION (operator, 2026-10-05): if the thesis is invalidated,
CLOSE. Do not wait for the stop. Define the invalidation level explicitly at
signal time (e.g. "M15 close beyond X") and act when it triggers.
  python order_executor.py close-all --force --reason "THESIS INVALIDATED: ..."
The --force there is the flatten confirmation, not a guardrail bypass; it is
different from the forbidden place --force.
Then record it: close-all writes the deal comment "FRIVAL_CLOSE", not the
setup id, so reconcile_deals cannot match it. Use:
  python log_trade.py exit --id T0NN --price <fill> --reason "..."
First application, for calibration: T025 closed on invalidation at -0.47R
instead of the -1.00R the stop would have taken.

=== STEP 7 — REPORT ===
Decision in the first sentence. Then the literal MT5 config block with
VENCIMIENTO and INVALIDACIÓN. State plainly which target gives 2:1 if it is
not TP1. Then:

=== ESTADO ===
XAUUSD: TRADE / WAIT / OUT — trigger level
EURUSD: same
USDJPY: same
EXPOSURE: net USD direction, or FLAT
Positions: symbol/side/vol/entry/SL/TP/PnL | Consecutive losses: N/4
Counterfactuals: resolved N / pending N
Next reviewed on schedule.

EMERGENCY STOP: echo "STOP" > frival\data\emergency_stop.txt

=== FIRST RUN — do this once ===
1. Confirm the account and flat state:
   python order_executor.py status
   python log_trade.py stats
   Expect: account 81486396, positions 0, pending 0. If the account number or
   the flat state differ, STOP and report — the machines have diverged.
2. Ensure the recurring cron exists. Check first with cron_list: a cron
   `*/15 * * * *` is normally ALREADY ARMED (id wku_...). Only create one if it
   is missing, so you do not run the desk twice:
   cron_create with cron "*/15 * * * *" and the FULL text of this brief as the
   prompt (the desk is self-monitoring; each fire = exactly one cycle). The
   optional second trigger is cron "5 16 * * 1-5" (16:05 local) for the EOD
   review.
3. Report your first cycle in the format above, and say explicitly that the
   machine is live and the cron is scheduled.
```

=== AFTER-CLOSE REVIEW — once per day ===
The daily close is server 00:00 (local 16:00). `eod_review.py` picks the trading
day that just closed (the server date of the most recent trade), so it is safe
to run at any hour.
On EVERY cycle, check whether frival\reviews\<latest-traded-day>.md exists.
- If it does NOT exist and that trading day has closed, run the review:
1. python frival\eod_review.py
   It writes frival\reviews\<YYYY-MM-DD>.md (facts table) and appends one line
   to frival\reviews\INDEX.md. It is idempotent (refuses if the file exists).
2. Open the file and replace the "Lessons (agent)" and "Changes made"
   placeholders with 3-5 sentences of interpretation and the commit hashes of
   changes made. Promote a durable lesson into frival\IMPROVEMENTS.md (and
   OPERATIONS.md if a rule changed).
2b. REVIEW THE GATE LOG (once per day): run `python quality_gate.py stats`.
   Record the per-symbol block-rate (PASS / SPREAD / THIN / ...) in the review.
   After >=1 full day of rows, if EURUSD/USDJPY are blocked mostly by SPREAD
   (rather than "no setup"), raise the bounded FX exploration proposal (tagged,
   reduced-risk, capped - see IMPROVEMENTS.md) to the operator. If they are
   mostly setup-starved (no level/target), say so and do NOT loosen gates.
- Prefer the close window (server 00:00-01:00 = local 16:00-17:00) and do NOT
  place orders in it (market closed, spreads blown out). But if that window was
  missed (e.g. the app was closed), run the review on the NEXT cycle at any hour
  — a missed review must never be silently dropped.
Anchor the trigger on the SERVER clock, not local (DST-safe). Weekends: skip.
The dedicated cron `5 16 * * 1-5` (16:05 local) is a second trigger.
