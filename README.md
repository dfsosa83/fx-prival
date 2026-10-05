# fx-prival

Autonomous, auditable FX trading desk for **XAUUSD, EURUSD and USDJPY** on
FP Markets (account `81486396`, FPMarketsSC-Live).

Every order goes through a guarded executor. Every signal is written to a
versioned log. Every rejected setup is recorded as a counterfactual so the
system's own blind spots are measurable rather than assumed.

---

## Layout

| Path | What it is |
|---|---|
| `frival/` | The live trading desk — executor, logs, counterfactuals |
| `frival/SETUP_NEW_MACHINE.md` | **Start here** to bring up a fresh laptop |
| `frival/DAILY_ROUTINE.md` | Session procedure and operator rules |
| `frival/requirements.txt` | Pinned Python deps for the trading path |
| `ml-signal-service/` | Model training and inference for the FX pipeline |
| `gold_rules/` | Gold-specific rule engine and research tests |
| `quant-personal-fund/` | Personal-fund mandate research |
| `fx_rules_backtest/` | Rule backtests and per-symbol ledgers |
| `DeafAgent/` | Accessibility tooling (unrelated to trading) |

The repo is public. The account number and P&L history are in it by operator
decision; credentials are excluded via `.gitignore` and never committed.

## The trading path

`order_executor.py` is the **only** component authorised to place, modify or
close orders. It enforces, on every order:

- max 5% of equity per trade, 12% aggregate
- max 3 positions, max 2 sharing one USD thesis
- R:R ≥ 1.9 to the target actually used
- SL between 1.0× and 4.0× clean ATR(M5)
- margin level ≥ 100% after the trade
- SL on the correct side of entry

An emergency-stop file blocks all order placement. It is gitignored so a fresh
clone can never inherit an armed switch.

`reconcile_deals.py` is read-only and reconciles the log against broker history
— it is how a corrupted log is rebuilt.

## Quick start

```bash
git clone https://github.com/dfsosa83/fx-prival.git
cd fx-prival/frival
pip install -r requirements.txt

python order_executor.py status      # account + guardrail state
python test_kill_switch.py           # 8/8 must pass before live trading
```

Full procedure, including the three hardcoded paths that must change per
machine, is in [`frival/SETUP_NEW_MACHINE.md`](frival/SETUP_NEW_MACHINE.md).

## State of the research

Trades are logged in `frival/trade_log.csv`; every setup considered but not taken
is in `frival/counterfactuals.csv` with a reject reason and a resolution.

The honest summary, as of 2026-10-05: 11 closed trades, +$61.89, +2.39R, 45.5%
win rate. That number is the sum of 11 trades since T004 — the most recent two
(T022, T023) lost $67.38 combined and took equity from $723.48 to $656.10.

Counterfactuals at N=36 read **−0.074R mean, t-stat −0.25** — mildly negative,
not significant. The reject reason that destroys the most R is
`NO_STRUCTURAL_TARGET` (−0.95R, n=4), not the 1.9R floor. Anyone tuning this
system should start there.

`project_last_state.md` and `PROJECT-CONTEXT.md` are the research handoff
documents; both predate the autonomous-trading phase and are kept for that
history.
