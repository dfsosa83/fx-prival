# Frival — Daily Routine

**Account:** Live 81486396 | Standard | $1,000 | 1:500
**Pairs:** EURUSD (0.333) | GBPUSD (0.381) | USDCHF (0.365) | USDCAD (0.341) — all SELL
**Lot size:** 0.08 (EURUSD/GBPUSD/USDCAD) | 0.04 (USDCHF)
**Execution mode:** LIVE (orders placed in MT5)
**Schedule:** 8:01, 9:01, 10:01, 11:01 AM Panama (UTC-5)
**MERG:** ON in shadow mode (log-only) — built into the Step 2 command. See Step 3b for hard-block activation.

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
MERG_ENABLED=true MERG_SHADOW_ONLY=true \
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe -u -c \
  "import sys; sys.path.insert(0, '.'); from main import run_live, execute_pending; run_live(borderline=True, pair='EURUSD'); run_live(borderline=True, pair='GBPUSD'); run_live(borderline=True, pair='USDCHF'); run_live(borderline=True, pair='USDCAD'); execute_pending()"
```

This generates signals for all 4 pairs (MERG veto in shadow/log-only mode), then auto-executes any FIRED orders through MT5.
Wait 90–120 seconds for completion.

---

## Step 3 — Three-Tier Probability System

| Tier | Range | Rule | EURUSD | GBPUSD | USDCHF | USDCAD |
|---|---|---|---|---|---|---|---|
| **Standard** | p >= th | Single agent confirm OK | p >= 0.306 | p >= 0.367 | p >= 0.365 | p >= 0.341 |
| **Borderline** | 0.20 <= p < th | Both agents must CONFIRM | 0.20-0.306 | 0.20-0.367 | 0.20-0.365 | 0.20-0.341 |
| **Blocked** | p < 0.20 | No evaluation | p < 0.20 | p < 0.20 | p < 0.20 | p < 0.20 |

---

## Step 3b — MERG Event-Risk Gate

MERG is a silent safety gate that activates only when a HIGH-impact economic event (CPI, FOMC, NFP, etc.) is scheduled within 60 minutes of a signal firing.

**Default state:** ON in **shadow mode** (log-only) — already set by the Step 2 command. The pipeline runs normally, but any MERG veto is written to the log *without* blocking the trade.

**To switch to live-hard-block mode (after 5+ days of clean shadow validation):**
```bash
# In the Step 2 command, change MERG_SHADOW_ONLY to false:
MERG_ENABLED=true MERG_SHADOW_ONLY=false \
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe -u -c \
  "import sys; sys.path.insert(0, '.'); from main import run_live, execute_pending; run_live(borderline=True, pair='EURUSD'); run_live(borderline=True, pair='GBPUSD'); run_live(borderline=True, pair='USDCHF'); run_live(borderline=True, pair='USDCAD'); execute_pending()"
```

**What happens when MERG is ON:**
1. After the normal gates pass, MERG checks the calendar
2. If a HIGH event is in the next 60 min → fetches the last 5 M1 bars → runs the Stage-1 reaction model
3. If MERG predicts a reaction with `P(reaction) >= 0.60` → veto (shadow: log only; hard-block: signal killed before agents)
4. Otherwise → PASS (agents run normally)

> MERG is **direction-agnostic** — it blocks on reaction confidence alone (volatility is coming),
> not on predicted direction. Direction was tested and found to be unpredictable.

**MERG decision log:** `frival/output/merg_shadow.log` — one JSON line per activation.
Check with: `tail -n 5 frival/output/merg_shadow.log`

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
