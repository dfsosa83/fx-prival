# Frival — Daily Routine

**Account:** Live 81486396 | Standard | $1,021 | 1:500
**Pairs:** EURUSD SELL (th=0.333) | GBPUSD SELL (th=0.381) | USDCHF SELL (th=0.365)
**Lot size:** 0.08 (EURUSD/GBPUSD) | 0.04 (USDCHF — experimental)
**Schedule:** 8:01, 9:01, 10:01, 11:01 AM Panama (UTC-5)
**MERG:** OFF by default (MERG_ENABLED=false). See Step 3b for activation.

---

## Step 1 — Start MT5 (once per morning)

Open MetaTrader 5, use:
```
Login: 81486396 | Server: FPMarketsSC-Live
```

EURUSD AND GBPUSD must be visible in Market Watch.

---

## Step 2 — Run all pairs + auto-execute at each hour (:01)

Open Git Bash in `frival/` directory:

```bash
cd "/c/Users/david/OneDrive/Documents/fx-prival/frival"
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe -u -c \
  "import sys; sys.path.insert(0, '.'); from main import run_live, execute_pending; run_live(borderline=True, pair='EURUSD'); run_live(borderline=True, pair='GBPUSD'); run_live(borderline=True, pair='USDCHF'); execute_pending()"
```

This generates signals for all 3 pairs, then auto-executes any FIRED orders through MT5.
Wait 90–120 seconds for completion.

---

## Step 3 — Three-Tier Probability System

| Tier | Range | Rule | EURUSD | GBPUSD |
|---|---|---|---|---|
| **Standard** | p >= th | Single agent confirm OK | p >= 0.306 | p >= 0.367 |
| **Borderline** | 0.20 <= p < th | Both agents must CONFIRM | 0.20-0.306 | 0.20-0.367 |
| **Blocked** | p < 0.20 | No evaluation | p < 0.20 | p < 0.20 |

---

## Step 3b — MERG Event-Risk Gate (OPTIONAL — only when enabled)

MERG is a silent safety gate that activates only when a HIGH-impact economic event (CPI, FOMC, NFP, etc.) is scheduled within 60 minutes of a signal firing.

**Default state:** OFF. The pipeline runs exactly as before — no MERG interference.

**To activate MERG in shadow mode (log-only, no blocking):**
```bash
export MERG_ENABLED=true
export MERG_SHADOW_ONLY=true
# Then run Step 2 as normal
```

**To activate MERG in live-hard-block mode (after 5+ days of shadow validation):**
```bash
export MERG_ENABLED=true
export MERG_SHADOW_ONLY=false
# Then run Step 2 as normal
```

**What happens when MERG is ON:**
1. After the normal gates pass, MERG checks the calendar
2. If a HIGH event is in the next 60 min → fetches last 15 M1 bars → runs model
3. If MERG predicts price will move against our direction → BLOCK (signal killed before agents)
4. If MERG predicts aligned direction or no reaction → PASS (agents run normally)

**MERG decision log:** `frival/output/merg_shadow.log` — one JSON line per activation.
Check with: `cat frival/output/merg_shadow.log | python -m json.tool`

**Expected activations:** ~2-4 times per month across all 3 pairs (only when signal + HIGH event coincide).

### Auto-execution

If `execute_pending()` finds any FIRED signals, it places the order automatically:

```
[OrderBot] EXECUTING: EURUSD SELL 0.08 lots
  Entry: 1.15722  SL: 1.15809  TP: 1.15592
[OrderBot] Order placed — ticket: XXXX
```

If BLOCKED or SHELVED: nothing to do. Wait for next hour.

---
## Step 4 — Execution bot as background service (optional)

If you want the execution bot to run continuously between hours (picks up signals instantly):
```bash
cd /c/Users/david/OneDrive/Documents/fx-prival/frival/execution_bot
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe run.py
```

Leave this terminal open. The signal pipeline in Step 2 will still work — the bot just picks up signals as they land.

---

## Rules

1. Max 1 trade per pair at a time. Never pyramid.
2. Entry zone: 2 pips around bar close. Skip if price moves outside before entry.
3. Expiry: 6 hours from signal. No entry after expiry.
4. Do not chase a signal — if you miss the zone, skip it.
5. Borderline = lower conviction. Expect lower precision.
6. Logs: `output/signals/`, `output/logs/`, `output/reports/`.

---

## Per-Pair Config

| | EURUSD | GBPUSD | USDCHF |
|---|---|---|---|
| Direction | SELL | SELL | SELL |
| Model threshold | 0.333 | 0.381 | 0.365 |
| Spread | ~0.8 pips | ~1.2 pips | ~0.8 pips |
| Agent B context | ECB vs Fed | BoE vs Fed | SNB vs Fed |
| Typical ATR(14) | ~0.0006 | ~0.0010 | ~0.0005 |
| ROC-AUC | 0.674 | 0.673 | 0.608 |
| Test precision | 0.411 | 0.436 | 0.435 |
| Lot size | 0.08 | 0.08 | 0.04 |
| Status | Core | Core | Experimental |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| MT5 connection error | Start MT5 terminal first |
| Pair data not found | Add pair to Market Watch in MT5 |
| No output after 60s | Agent B searching — wait longer |
| `GBPUSD_H1.csv` missing | Run: `python -c "from data import fetch_ohlcv; fetch_ohlcv('GBPUSD','H1',source='mt5')"` |
