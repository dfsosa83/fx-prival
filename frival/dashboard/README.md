# Frival Book Dashboard — Stage 1: Portfolio Visibility (read-only)

A web dashboard that shows the **book**, not just the trades: every engine's
state, open positions, combined PnL, and — the key insight — **per-currency
factor exposure**, so you see "the book is net LONG the dollar" instead of
"4 positions open."

Read-only by construction: the backend only ever *queries* MT5 (positions /
account / deals) and *reads* engine journals/state. It places no orders and
writes nothing to engine state.

## Quick start (recommended — local, no Docker needed)

The backend is the brain; it runs with the same conda python already used by
the engines:

```powershell
cd frival/dashboard
# terminal 1 — backend on :8000
C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe -m uvicorn --app-dir backend main:app --host 0.0.0.0 --port 8000

# terminal 2 — data verification (read-only smoke test)
C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe -c "import sys; sys.path.insert(0, 'backend'); import portfolio; print(portfolio.build_book()['exposure'])"
```

Then open <http://localhost:8000/api/book> in a browser, or build the frontend
and serve it:

```powershell
cd frival/dashboard/frontend
npm install
npm run build
# serve dist/ however you like during dev (or use `npm start` for vite dev with proxy)
```

Quickest local UI: `npm start` (vite dev server on :3000, proxies /api -> :8000).

## Public URL (your proven pattern)

```powershell
cd frival/dashboard
# optional access token — first line of defense since the tunnel is public
$env:DASHBOARD_TOKEN = "change-me"

# 1. Start the backend (local mode above) OR docker compose up -d
docker compose up -d frontend     # serves built FE + static via nginx :80

# 2. Tunnel as in your bond project
.\cloudflared.exe tunnel --no-autoupdate --url http://localhost:80
```

## Docker note (honest)

`docker compose up -d full` builds the FE via nginx and the BE container, but
**the backend's MT5 terminal lives on the Windows HOST**, and the MetaTrader5
Python API reaches it through host IPC. Running that from inside a container
(host networking) works only if the terminal data folder and the credentials
are reachable and the same-MT5-instance path resolves. Recommendation:

- **Primary:** run the FastAPI backend locally (conda python, proven above);
  use Docker only for `frontend` (nginx :80) if you want the single-port
  packaging. Point nginx's `/api` at `http://host.docker.internal:8000` if
  you split it that way.
- The compose file as written assumes host networking for the BE and is a
  starting point, not a battle-tested MT5-in-container deployment. We do not
  pretend otherwise.

## Endpoints

| Endpoint | What it returns |
|---|---|
| `/api/book` | Full book snapshot: MT5 account+positions, exposure lens, gold state, PnL, health |
| `/api/exposure` | Per-currency + gross/net exposure only |
| `/api/gold` | Gold engine state + today's journal + PnL |
| `/api/gold/journal?days=N&limit=M` | Raw gold decision journal |
| `/api/fx/signals` | Recent FX scheduler signals |
| `/api/health/engines` | Engine liveness from state-file freshness |

## Tests

```powershell
cd frival/dashboard
C:\Users\david\anaconda3\Library\envs\deaf_agent\python.exe -m unittest tests.test_portfolio
```

Tests pin the exposure-lens ground truth: SELL EURUSD = short EUR/long USD;
SELL USDCAD = short USD (USD is base); four SELL USD-pairs net to +0.04 USD
(they partially hedge). Sign semantics are proven, not assumed.