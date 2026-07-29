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

Open Git Bash, navigate and run:

```bash
cd "/c/Users/david/OneDrive/Documents/fx-prival/frival"
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe -u -c "import sys; sys.path.insert(0, '.'); from main import run_live; run_live(borderline=True)"
```

Wait 30–60 seconds for agent evaluation. Read the output.

The `-u` flag disables output buffering. The `borderline=True` enables the extended range.

---

## Step 3 — Three-Tier Probability System

| Tier | Probability | Trigger | Rule |
|---|---|---|---|
| **Standard** | p ≥ 0.306 | Model confident | Agent A + B vote, single confirm sufficient |
| **Borderline** | 0.20 ≤ p < 0.306 | Model uncertain | **Both** agents must CONFIRM to fire |
| **Blocked** | p < 0.20 | Model opposed | No agent evaluation, no signal |

---

## Step 4 — Interpret the result

### If signal FIRES (standard):

```
Gate result: PASS (standard)
============================================================
  SIGNAL FIRED: EURUSD SELL
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

**Action:** Place SELL 0.08 lots in MT5. See trade levels above.

### If signal FIRES (borderline):

```
Gate result: PASS (borderline)
============================================================
  SIGNAL FIRED: EURUSD SELL
  Confidence:   MODERATE
  Probability:  0.2572
============================================================
  Agent A: CONFIRM (HIGH)
  Agent B: CONFIRM (MODERATE)
```

**Action:** Both agents see opportunity despite weak model. Place same 0.08 lots. Monitor closely — the model is less confident.

### If signal is BLOCKED:

```
Gate result: BLOCK  (p=0.1257 < 0.306)
```

Model sees no edge. Nothing to do.

### If signal is SHELVED:

```
Signal SHELVED: technical: D1 ADX > 30, strong USD bid
```

The agents disagreed or couldn't reach consensus. Nothing to do.

---

## Rules

1. **Max 1 trade at a time.** Never pyramid EURUSD H1 signals.
2. **Don't chase.** If price breaks above the entry zone, skip. Selling into strength = worse, not better.
3. **Expiry is real.** No entry after expiry (6 hours from signal). The model's prediction window is closed.
4. **Borderline = lower conviction.** If a borderline signal fires, expect lower precision (~30–35% vs 38–43% for standard).
5. **No manual overrides.** The agents + model already voted. Trust the output.
6. **Log everything.** Signals → `output/signals/` | Reports → `output/reports/`. Weekly review against MT5 history.

---

## Expected behavior

- 3–5 standard signals + 1–3 borderline signals per month
- Cooldown prevents signals within 4 hours of last FIRED
- Agent A will reject ~50% of candidates
- Agent B will veto on macro events, stay neutral otherwise
- Win rate target: 38–43% (standard), 30–35% (borderline) at 1.5R

---

## Troubleshooting

| Problem | Fix |
|---|---|
| MT5 connection error | Start MT5 terminal first, then re-run |
| No output after 60s | Agent B searching the web — wait longer |
| Python not found | Use full path: `/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe` |
| Signal but no time to enter | Zone is tight (2 pips). If >3 mins since run, check if price still in zone |
| Borderline not running | Check `borderline=True` in the run command |
