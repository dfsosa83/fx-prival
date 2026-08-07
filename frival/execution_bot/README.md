# Frival Order Execution Bot

Automated MT5 order executor for Frival trading signals.

## How It Works

```
Frival (run_live) → output/signals/*.jsonl
                              ↓
                    signal_watcher.py (polls every second)
                              ↓
                    order_bot.py (risk gates + execution)
                              ↓
                    MT5 Terminal (order sent)
```

## Quick Start

```bash
cd frival/execution_bot

# 1. Install dependencies
pip install MetaTrader5 pyyaml python-dotenv pandas numpy

# 2. Configure credentials
cp config/credentials.env.example config/credentials.env
# Edit credentials.env with your MT5 login/password/server

# 3. Review pair config
# Edit config/settings.yaml — EURUSD is live by default.
# GBPUSD and USDCHF are shadow-only (monitor, don't execute).

# 4. Run the bot
python run.py

# Single-pass mode (process pending signals and exit)
python run.py --once
```

## Risk Gates

Every signal passes these checks before execution:

| Gate | What it blocks | How to configure |
|---|---|---|
| Emergency stop | All execution if `emergency_stop.txt` exists | Create/delete `frival/data/emergency_stop.txt` |
| Shadow pairs | No execution for GBPUSD/USDCHF | Set `shadow: false` in settings.yaml |
| Daily loss | Blocks after $50 loss per day | `risk.max_daily_loss` in settings.yaml |
| Duplicate position | Skips if pair already has open position | Automatic |
| Margin check | Skips if insufficient free margin | Automatic |
| Signal expiry | Skips if `expires_at_utc` is in the past | From signal JSON |

## Files

| File | Purpose |
|---|---|
| `run.py` | Entry point — starts watcher + order bot |
| `signal_watcher.py` | Polls JSONL output for new FIRED signals |
| `order_bot.py` | Orchestrator — risk gates + MT5 execution |
| `core/` | MT5 connector, order manager, config (from DeafAgent) |
| `config/settings.yaml` | Trading, risk, and pair configuration |
| `config/credentials.env` | MT5 credentials (gitignored) |
| `data/watcher_state.json` | Tracks last processed signal_id |
| `data/execution_log.jsonl` | Execution audit trail |

## Execution Log

Every signal (executed or rejected) is logged to `data/execution_log.jsonl`:

```json
{
  "timestamp_utc": "2026-08-07T14:05:23",
  "signal_id": "EURUSD_H1_SELL_2026-08-07T14:00:00Z",
  "symbol": "EURUSD",
  "direction": "SELL",
  "status": "EXECUTED",
  "detail": "ticket=12345678",
  "daily_pnl": -12.50
}
```

## Emergency Stop

To halt all order execution immediately:

```bash
echo "STOP" > frival/data/emergency_stop.txt
```

To resume:

```bash
rm frival/data/emergency_stop.txt
```

## Deployment Plan

| Phase | Duration | Action |
|---|---|---|
| 1 — Demo | 2 weeks | Run with `DEMO_MODE=true`, validate 0 errors |
| 2 — Shadow live | 1 week | Enable live-only for EURUSD, 0.01 lots |
| 3 — Full live | Ongoing | EURUSD 0.08 lots, GBPUSD/USDCHF remain shadow |
