# Frival — Daily Routine

**Account:** Live 81486396 | Standard | $1,021 | 1:500
**Pairs:** EURUSD H1 SELL (th=0.306) | GBPUSD H1 SELL (th=0.367)
**Lot size:** 0.08 each (0.63% risk at 8-pip SL per trade)
**Schedule:** 8:01, 9:01, 10:01, 11:01 AM Panama (UTC-5)

---

## Step 1 — Start MT5 (once per morning)

Open MetaTrader 5, use:
```
Login: 81486396 | Server: FPMarketsSC-Live
```

EURUSD AND GBPUSD must be visible in Market Watch.

---

## Step 2 — Run both pairs at each hour (:01)

Open Git Bash in `frival/` directory:

```bash
cd "/c/Users/david/OneDrive/Documents/fx-prival/frival"
/c/Users/david/anaconda3/Library/envs/deaf_agent/python.exe -u -c \
  "import sys; sys.path.insert(0, '.'); from main import run_live; run_live(borderline=True, pair='EURUSD'); run_live(borderline=True, pair='GBPUSD')"
```

Wait 60–90 seconds for both pairs. Read the output for each.

---

## Step 3 — Three-Tier Probability System

| Tier | Range | Rule | EURUSD | GBPUSD |
|---|---|---|---|---|
| **Standard** | p >= th | Single agent confirm OK | p >= 0.306 | p >= 0.367 |
| **Borderline** | 0.20 <= p < th | Both agents must CONFIRM | 0.20-0.306 | 0.20-0.367 |
| **Blocked** | p < 0.20 | No evaluation | p < 0.20 | p < 0.20 |

---

## Step 4 — Interpret the result

### If signal FIRES:

```
============================================================
  SIGNAL FIRED: EURUSD SELL (or GBPUSD SELL)
  Entry zone:   1.15352 - 1.15312
  Stop Loss:    1.15406  (7.4 pips)
  Take Profit:  1.15221  (11.1 pips)
  R:R:          1.5
  Expires:      2026-07-29T23:00:00
  Confidence:   HIGH
  Probability:  0.3109
============================================================
```

**Action:** Place 0.08 lots SELL using the trade levels shown. Standard=HIGH/MODERATE confidence, Borderline=MODERATE only.

### If BLOCKED or SHELVED:

Nothing to do. Wait for next hour.

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

| | EURUSD | GBPUSD |
|---|---|---|
| Model threshold | 0.306 | 0.367 |
| Spread | ~0.8 pips | ~1.2 pips |
| Agent B context | ECB vs Fed | BoE vs Fed |
| Typical ATR(14) | ~0.0006 | ~0.0010 |
| Signals/month (est) | 4-6 | 3-5 |
| ROC-AUC | 0.674 | 0.685 |
| Test precision (raw) | 0.411 | 0.515 |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| MT5 connection error | Start MT5 terminal first |
| Pair data not found | Add pair to Market Watch in MT5 |
| No output after 60s | Agent B searching — wait longer |
| `GBPUSD_H1.csv` missing | Run: `python -c "from data import fetch_ohlcv; fetch_ohlcv('GBPUSD','H1',source='mt5')"` |
