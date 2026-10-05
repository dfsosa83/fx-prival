# Frival — New Machine Setup

Written 2026-10-05. Target: a fresh Windows laptop that will become the primary
trading machine. Budget ~45 minutes.

The repository is the source of truth. Nothing under `data/`, `context/`,
`trade_log.csv` or `counterfactuals.csv` needs to be recreated — clone and the
evidence base comes with it.

---

## 1. Prerequisites

| Requirement | Version used in production | Notes |
|---|---|---|
| Windows | 10 or 11 | The MetaTrader5 Python package is Windows-only |
| FP Markets MT5 Terminal | current build | Must be installed **and** logged into account `81486396` (FPMarketsSC-Live) before any script runs |
| Python | 3.9.21 | Base anaconda. The `deaf_agent` env (3.11.11) also works for order placement but ships pandas 2.2.2 — see note at the end |
| Git | any | — |

Install the terminal first. `mt5.initialize(path=...)` attaches to a running,
already-authenticated terminal; it does not accept credentials in this
codebase. See `project_last_state.md` §12.3 for the failure mode when login is
passed explicitly.

## 2. Clone

```bash
git clone https://github.com/dfsosa83/fx-prival.git
cd fx-prival
```

**The repository is public.** The account number and the full P&L history are
in it by operator decision (2026-10-02) — the evidence base only has value if
it is versioned next to the code that produced it. Credentials are excluded via
`.gitignore`; `frival/config/.env` never left this machine.

## 3. Python environment

```bash
"C:\Users\<you>\anaconda3\python.exe" -m pip install -r frival/requirements.txt
```

MetaTrader5 is **not** reliably on PyPI — install it from
<https://www.mettester.com/python-packages> so the version matches the terminal.
Production ran `MetaTrader5 5.0.4874`.

Verify before anything else:

```bash
python -c "import MetaTrader5, pandas, numpy; print(MetaTrader5.__version__, pandas.__version__, numpy.__version__)"
```

Expect `5.0.4874 2.1.3 1.25.2`.

`scikit-learn` is deliberately **not** in requirements. `main.py` loads
`*.joblib` model bundles that need it, but those binaries are gitignored and the
autonomous trading path (`order_executor`, `log_trade`, `counterfactual`,
`market_context`, `reconcile_deals`) never loads a model. Install it only if you
intend to run `main.py`.

## 4. Machine-specific paths

Three things are hardcoded and must be changed for a new machine. They are all
`TERMINAL_PATH` constants plus the Python path in the launchers.

| File | Line | Constant |
|---|---|---|
| `frival/order_executor.py` | 44 | `TERMINAL_PATH` |
| `frival/log_trade.py` | 35 | `TERMINAL_PATH` |
| `frival/counterfactual.py` | 44 | `TERMINAL_PATH` |
| `frival/market_context.py` | 36 | `TERMINAL_PATH` |
| `frival/ml_intraday_snapshot.py` | 48 | `TERMINAL_PATH` |
| `frival/reconcile_deals.py` | 41 | `TERMINAL_PATH` |
| `frival/test_kill_switch.py` | 43 | inline `mt5.initialize(path=...)` |
| `frival/*.bat` (4 files) | 6 | `set "PYTHON=..."` |

Default value, correct unless MT5 lives elsewhere:

```python
TERMINAL_PATH = r'C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe'
```

**Do not run two MT5 terminals logged into the live account simultaneously**
unless you intend both to trade. `order_executor` places real orders.

## 5. Credentials

Create `frival/config/.env` from the example:

```
MT5_LOGIN=81486396
MT5_PASSWORD=<not in git — supply locally>
MT5_SERVER=FPMarketsSC-Live
MT5_PATH=C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe
OPENROUTER_API_KEY=<local only>
PERPLEXITY_API_KEY=<local only>
```

The order-placement path authenticates through the logged-in terminal, not
through this file. It is required for the analysis submodules.

## 6. Verify before trading

Run in this order. Each must pass before the next.

```bash
cd frival

python order_executor.py status     # account, equity, positions, guardrails
python market_context.py capture --id SMOKE
python counterfactual.py sweep      # resolves matured counterfactuals
python order_executor.py manage     # no-op with no open positions
```

Then the kill switch — **8/8 passing is the gate for live orders**:

```bash
python test_kill_switch.py
```

Confirm nothing is armed on a fresh clone. `frival/data/emergency_stop.txt` is
gitignored precisely so a clone cannot inherit a stop:

```bash
if exist data\emergency_stop.txt (echo KILL SWITCH ARMED — INVESTIGATE) else (echo clear)
```

## 7. Operational invariants

Read `frival/DAILY_ROUTINE.md` before the first session. The rules that matter
most on day one:

- `order_executor.py` is the **only** component authorised to place, modify or
  close orders. `reconcile_deals.py` is read-only.
- Never `--force` on `place`. If a guardrail blocks, fix the levels and re-emit.
- Positions are held to SL/TP, **except** when the thesis is invalidated.
  On 2026-10-05 the operator gave a standing authorisation: *"PUEDES CERRAR,
  siempre hazlo si la tesis se invalida."* If the stated invalidation condition
  triggers (for example an M15 close beyond the level the thesis depends on),
  close the position with `close-all --force --reason "..."` and record the
  broker deal. Do not wait for the stop. `close-all` requires `--force` or an
  armed kill switch; that flag is the flatten confirmation, not a guardrail
  bypass, and is distinct from the forbidden `place --force`.
- `MAX_CONSECUTIVE_LOSSES` is set to 999 — the circuit breaker is **disabled by
  operator instruction** (2026-10-02). It will not stop the day. This is
  deliberate; do not "fix" it without the operator.
- Guardrails in force: `MAX_POSITIONS=3`, `MAX_RISK_PCT_PER_TRADE=5.00`,
  `MAX_RISK_PCT_TOTAL=12.00`, `MAX_SAME_THESIS=2`, `MIN_RR=1.9`,
  `MIN_MARGIN_LEVEL=100.0`, `MAX_POSITIONS` is effectively 1 net position by
  operator practice.

## 8. Trading hours and clocks

Server (UTC+3) is 8 hours ahead of local (UTC−5).

- Daily close 16:00–17:00 local — no new entries.
- Friday close 16:00 local. Sunday reopen 18:00 local.

## 9. Runtime artifacts that regenerate

Not in git, by design. All regenerate on first run:

- `frival/executor_state.json` — session equity anchor, consecutive-loss counter
- `frival/data/cache/` — H1 rate caches
- `frival/data/last_signal.json`
- `frival/output/`

## 10. Open items carried over

Not blockers, but the next laptop inherits them:

- `T024` (USDJPY) sits `PENDING_FILL` with no broker deal — the executor
  blocked it. It should be marked `SKIPPED`; the `fill` subcommand refuses to
  touch a `PENDING_FILL` row by design, so this needs a direct log edit.
- `trade_log.CORRUPT-9rows.csv.bak` is a debug artifact from the 2026-10-04 row-
  loss incident. Untracked, and should stay that way.
- Counterfactual stats at N=36 read **−0.074R mean, t-stat −0.25**. The filter
  destroying the most R is `NO_STRUCTURAL_TARGET` at −0.95R, not the 1.9R
  floor. Any tuning should start there, not with the geometry gates.
