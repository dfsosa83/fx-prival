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
FPMarketsSC-Live, equity ~655.39, MT5 SDK 5.0.4874, kill switch 8/8.

=== STEP 1 — READ ===
XAUUSD, EURUSD, USDJPY: M5(15), M15(8), H1(6), tick + spread + tick age.
Triple clock: local UTC-5 / server UTC+3 (server = local + 8h).

DATA QUALITY GATES (block if any fails):
  - Rollover window 23:00-00:30 server -> no new entries (open positions are
    held through it; SL/TP stay live at the broker)
  - Tick age > 5 min -> stale quote, no trade
  - Spread > 50% of clean ATR(M5) -> no trade
  - Clean ATR(M5) < 1.0 -> frozen data, no trade
  - Last M15 range > 2.0x clean ATR(M5) -> thin book spike, no trade
  - Price in a structural VOID (no level within 15 points either side) -> no trade
Clean ATR: exclude bars where high==low OR tick_volume < 30% of median.

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

Measured at N=36 (mean -0.074R, t-stat -0.25 — mildly negative, not
significant). By reject reason, and these supersede the old brief:
  LEVEL_ALREADY_TESTED    n=15  +0.38R  <- best filter; do NOT block on it
  CORRELATION             n= 2  +0.50R
  NONE_TAKEN              n= 5  +0.05R
  R_R_BELOW_2_TO_TP1      n= 9  -0.35R  <- was +0.04 "neutral"; no longer
  NO_STRUCTURAL_TARGET    n= 4  -0.95R  <- keep this filter, never relax it
The filter destroying the most R is NO_STRUCTURAL_TARGET. That is where any
tuning should start, not the 1.9R floor.

=== STEP 5 — CIRCUIT BREAKER ===
MAX_CONSECUTIVE_LOSSES is set to 999: the operator disabled it on 2026-10-02.
It will not halt the day. Do not "fix" this without the operator.

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
Positions: symbol/side/vol/entry/SL/TP/PnL | Consecutive losses: N/3
Counterfactuals: resolved N / pending N
Next reviewed on schedule.

EMERGENCY STOP: echo "STOP" > frival\data\emergency_stop.txt

=== FIRST RUN — do this once ===
1. Confirm the account and flat state:
   python order_executor.py status
   python log_trade.py stats
   Expect: account 81486396, equity ~655.39, positions 0, pending 0,
   closed=12, total PnL $61.18, total R 1.92, win rate 5/12.
   If any of those differ, STOP and report — the machines have diverged.
2. Create a recurring cron that sends you this exact prompt every 15 minutes,
   so the desk monitors itself. Use cron_create with cron "*/15 * * * *".
3. Report your first cycle in the format above, and say explicitly that the
   machine is live and the cron is scheduled.
```