# -*- coding: utf-8 -*-
"""Book Dashboard — FastAPI backend (read-only).

Endpoints expose the portfolio "book lens" computed by portfolio.py.
STRICTLY READ-ONLY: no order endpoints, no position modification, no writes
to engine state. Optional access-token guard via env DASHBOARD_TOKEN.

Run locally (no Docker):
    uvicorn main:app --host 0.0.0.0 --port 8000
Or via docker-compose (nginx proxies :80 -> :8000).
"""
from __future__ import annotations

import os
from typing import Dict, List

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import portfolio

app = FastAPI(title="Frival Book Dashboard", version="0.1.0")

# CORS: allow the frontend origin(s). In production through nginx the FE and BE
# share an origin, so this is permissive-but-same-origin safe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "")


def _guard(x_token: str) -> None:
    """If a token is configured, require it (env DASHBOARD_TOKEN)."""
    if DASHBOARD_TOKEN and x_token != DASHBOARD_TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/api/health")
def health() -> Dict:
    return {"ok": True, "ts": portfolio.datetime.utcnow().isoformat() + "Z"}


@app.get("/api/book")
def book(x_token: str = Header(default="")) -> Dict:
    _guard(x_token)
    try:
        return portfolio.build_book()
    except Exception as e:  # never 500 the whole dashboard on a data hiccup
        return {"error": str(e), "partial": True}


@app.get("/api/exposure")
def exposure(x_token: str = Header(default="")) -> Dict:
    _guard(x_token)
    mt5 = portfolio.get_mt5_snapshot()
    expo = portfolio.compute_exposure(mt5.get("positions", []))
    return {"exposure": expo, "mt5_available": mt5.get("available", False)}


@app.get("/api/gold")
def gold(x_token: str = Header(default="")) -> Dict:
    _guard(x_token)
    state = portfolio.read_gold_state()
    journal = portfolio.read_gold_journal(days=1)
    today_pnl = portfolio.compute_gold_today_pnl()
    return {
        "state": state,
        "journal_last": journal[:40],
        "today_pnl": today_pnl,
        "count_today": len(journal),
    }


@app.get("/api/gold/journal")
def gold_journal(days: int = Query(default=1, ge=1, le=7),
                 limit: int = Query(default=100, ge=1, le=1000),
                 x_token: str = Header(default="")) -> Dict:
    _guard(x_token)
    rows = portfolio.read_gold_journal(days=days)
    return {"count": len(rows), "rows": rows[:limit]}


@app.get("/api/fx/signals")
def fx_signals(x_token: str = Header(default="")) -> Dict:
    _guard(x_token)
    return {"signals": portfolio.read_fx_signals(days=2)}


@app.get("/api/health/engines")
def engines_health(x_token: str = Header(default="")) -> Dict:
    _guard(x_token)
    return portfolio.engine_health()