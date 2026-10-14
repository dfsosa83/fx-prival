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
| `OPERATIONS.md` | **Start here** — master manual (cycle, sizing, risk, commands) |
| `ACTIVE MONITOR — Frival desk.md` | The live 15-minute cron brief (STEPS 1-7) |
| `AGENTS.md` | Binding agent rules (auto-loaded) |
| `frival/` | The live trading desk — executor, logs, counterfactuals |
| `frival/SETUP_NEW_MACHINE.md` | Bring up a fresh laptop |
| `frival/DAILY_ROUTINE.md` | Legacy session procedure (NOT the autonomous desk) |
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

Machine paths auto-resolve (`frival/mt5_path.py`); a fresh laptop follows
`frival/SETUP_NEW_MACHINE.md`.

## Reading order (for a new agent)

1. `OPERATIONS.md` — master manual (authoritative).
2. `ACTIVE MONITOR — Frival desk.md` — the live cycle brief (STEPS 1-7).
3. `AGENTS.md` — binding agent rules.
Then `frival/SETUP_NEW_MACHINE.md` (machine notes) and `frival/IMPROVEMENTS.md`
(running changelog / lessons).

## Running continuously (the cron)

The desk is driven by a Kilo cron that resumes the session every 15 minutes with
the full brief as the prompt; each fire = exactly one cycle. It is
**session-scoped** — if the Kilo app closes, cycles stop. To bring the desk up on
a new session: read the brief, then `cron_list` and, only if no `*/15 * * * *`
task exists, create one whose prompt is the entire brief (the brief's
"FIRST RUN" section spells this out). An optional `5 16 * * 1-5` cron triggers
the daily review.

## State of the research

Trades are logged in `frival/trade_log.csv`; every setup considered but not taken
is in `frival/counterfactuals.csv` with a reject reason and a resolution.

The honest summary, as of 2026-10-14: 51 rows, 29 closed, **12/29 (41.4%) win
rate, +$149.82, +4.42R**, avg +0.15R, best +3.34R (T046), worst −1.28R (T043).
Equity ~$744 (from a $604 trough at the 2026-10-02 close). The edge is small and
not yet statistically significant at this sample size.

Counterfactuals at N=47 resolved read **+0.41R mean, t-stat +1.52** — positive
but short of significance, and inflated by no-fill artifacts (F-10). By reject
reason, `LEVEL_ALREADY_TESTED` +0.40R (do NOT block), `NO_STRUCTURAL_TARGET`
−0.43R (keep this filter, never relax), `R_R_BELOW_2_TO_TP1` −0.27R (the 1.9R
floor is justified). Tuning starts at `NO_STRUCTURAL_TARGET`, not the geometry
gates.

An external audit (`auditorias/`, 2026-10-11) is **pending operator approval** —
its worktrees must not be merged or acted on. See OPERATIONS.md §17.

`project_last_state.md` and `PROJECT-CONTEXT.md` are the research handoff
documents; both predate the autonomous-trading phase and are kept for that
history.
