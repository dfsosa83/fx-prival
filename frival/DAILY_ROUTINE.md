# Frival — Daily Routine

**Account:** Live 81486396 | Standard | $1,021 | 1:500
**Pair:** EURUSD H1 SELL only
**Lot size:** 0.08 (0.63% risk at 8-pip SL)
**Schedule:** 8:01, 9:01, 10:01, 11:01 AM Panama (UTC-5)

---

## Step 1 — Start MT5 (once per morning)

Open MetaTrader 5, use:

```
Login:    81486396
Server:   FPMarketsSC-Live
Password: u#wWU#64esZjNVn
```

EURUSD must be visible in Market Watch. No other scripts using the terminal.

---

## Step 2 — Run at each hour (:01)

Open Bash terminal in this exact directory:

```bash
cd "/c/Users/david/OneDrive/Documents/fx-prival/frival"
```

Run:

```bash
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe main.py --mode live
```

Wait 30–60 seconds for agent evaluation. Read the output.

---

## Step 3 — Interpret the result

### If signal FIRES:

```
============================================================
  SIGNAL FIRED: EURUSD SELL
  Timestamp:    2026-07-28T17:00:00+00:00
  Entry zone:   1.15352 — 1.15312
  Stop Loss:    1.15406  (7.4 pips)
  Take Profit:  1.15221  (11.1 pips)
  R:R:          1.5
  Expires:      2026-07-28T23:00:00+00:00
  Confidence:   HIGH
  Probability:  0.3109
============================================================
  Agent A: CONFIRM (HIGH)
  Agent B: CONFIRM (MODERATE)
```

**Action:** Place SELL 0.08 lots in MT5:
- Entry: between 1.15352 and 1.15312
- Stop Loss: 1.15406
- Take Profit: 1.15221

If price is outside the entry zone before you place the order → skip.
Signal expires at 23:00 UTC (6:00 PM Panama).

### If signal is BLOCKED:

```
Probability: 0.2920  threshold=0.306
Gate result: BLOCK  (p=0.2920 < 0.306)
```

Nothing to do. Wait for next hour.

### If signal is SHELVED:

```
Signal SHELVED: technical: D1 ADX > 30, strong USD bid — selling adverse
```

The agents disagreed. Nothing to do. Wait for next hour.

---

## Rules

1. **Max 1 trade at a time.** Never pyramid EURUSD H1 signals.
2. **Don't chase.** If price breaks above the entry zone, skip. You're selling into strength — it's worse, not better.
3. **Expiry is real.** No entry after the expiry time. The model's prediction window is closed.
4. **No manual overrides.** The agents already voted. Trust the output.
5. **Log everything.** Every FIRED signal goes to `output/signals/YYYY-MM/YYYY-MM-DD.jsonl`. Weekly review against MT5 history.

---

## Expected behavior

- 3–5 signals per month
- Cooldown prevents signals within 4 hours of last FIRED
- Agent A (technical) will reject ~50% of candidates
- Agent B (fundamental) will veto on macro events, stay neutral otherwise
- Win rate target: 38–43% at 1.5R

---

## Troubleshooting

| Problem | Fix |
|---|---|
| MT5 connection error | Start MT5 terminal first, then re-run |
| No output after 60s | Agent B searching the web — wait longer |
| Python not found | Full path: `/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe` |
| Signal but no time to enter | The zone is tight (2 pips). If >3 mins since the run, check if price still in zone |
