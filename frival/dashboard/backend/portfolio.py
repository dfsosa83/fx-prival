# -*- coding: utf-8 -*-
"""Book Dashboard — portfolio computation layer (read-only).

Implements the "book lens": instead of viewing each engine's trades in
isolation (pair-level risk), this computes BOOK-level metrics:

  - Positions & gross/net exposure across ALL open positions
  - PER-CURRENCY FACTOR EXPOSURE: maps every FX pair/XAUUSD position to its
    implicit currency legs, so the user sees "this book is +3.2 units USD"
    instead of "4 positions open" (the four-shorts-are-one-USD-bet insight).
  - Combined daily PnL across gold engine + FX/ML pipeline + MT5 day PnL.
  - Engine health / process status.

STRICTLY READ-ONLY:
  - MT5 access is limited to positions/account/deals queries (no orders,
    no position modification), with the same transient-error tolerance used
    in the gold engine (never crashes on a momentary IPC blip).
  - Dashboard NEVER holds MT5 open connections; each call connect->query->
    shutdown (the proven pre-flight pattern).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# ── Paths (resolved relative to this file) ───────────────────────────────────────
HERE = Path(__file__).resolve().parent
FRIVAL = HERE.parent.parent              # frival/
GOLD_RULES_DIR = FRIVAL / "gold_rules"
GOLD_STATE = GOLD_RULES_DIR / "state" / "engine_state.json"
GOLD_JOURNAL_DIR = GOLD_RULES_DIR / "journal"
GOLD_CREDS = GOLD_RULES_DIR / "config" / "credentials.env"
FX_OUTPUT_DIR = FRIVAL / "output"
FX_SIGNALS_DIR = FX_OUTPUT_DIR / "signals"

TERMINAL_PATH = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

# ── Instrument -> currency legs (factor exposure lens) ───────────────────────────
# Each pair is described by its STRUCTURE: base currency = +1 (longing base when
# BUY), quote currency = -1 (shorting quote when BUY). Position sign then decides
# the actual legs:
#   BUY  EURUSD -> LONG EUR (+v), SHORT USD (-v)
#   SELL EURUSD -> SHORT EUR (-v), LONG USD (+v)
#   SELL USDCAD -> SHORT USD, LONG CAD  (USD is the BASE in this pair)
# The correct formula is: exposure[leg] += position_sign * vol * leg_multiplier.
CURRENCY_LEGS: Dict[str, Dict[str, float]] = {
    "EURUSD": {"EUR": +1.0, "USD": -1.0},
    "GBPUSD": {"GBP": +1.0, "USD": -1.0},
    "USDCHF": {"USD": +1.0, "CHF": -1.0},
    "USDCAD": {"USD": +1.0, "CAD": -1.0},
    "AUDUSD": {"AUD": +1.0, "USD": -1.0},
    "USDJPY": {"USD": +1.0, "JPY": -1.0},
    "XAUUSD": {"XAU": +1.0, "USD": -1.0},   # gold quoted in USD; buy gold = long XAU, short USD
}

# engines/comment tags the dashboard attributes PnL to
GOLD_COMMENTS = ("GOLD_RULES_v1", "GOLD_RULES_C")


def load_env(path: Path) -> Dict[str, str]:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def _safe_mt5(fn, default=None):
    """Run an MT5 read with transient-error tolerance (returns default on byte)."""
    try:
        return fn()
    except Exception:
        return default


def get_mt5_snapshot() -> Dict[str, Any]:
    """One-shot read-only MT5 snapshot: account + all positions + today's deals.

    Never writes; opens and closes the connection per call (pre-flight pattern).
    Returns a dict ready for JSON serialization.
    """
    import MetaTrader5 as mt5

    result = {
        "available": False,
        "account": None,
        "positions": [],
        "today_deals_pnl": 0.0,
        "error": None,
        "ts": datetime.utcnow().isoformat() + "Z",
    }

    if not _safe_mt5(lambda: mt5.initialize(path=TERMINAL_PATH)):
        result["error"] = str(mt5.last_error())
        return result

    try:
        account = mt5.account_info()
        if account is not None:
            result["available"] = True
            result["account"] = {
                "login": account.login,
                "server": account.server,
                "balance": account.balance,
                "equity": account.equity,
                "margin_free": account.margin_free,
                "leverage": account.leverage,
                "currency": account.currency,
            }

        positions = mt5.positions_get()
        if positions is None:
            positions = []

        pos_rows = []
        for p in positions:
            pos_rows.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "comment": p.comment or "",
                "magic": p.magic,
            })
        result["positions"] = pos_rows

        # realized PnL today (all symbols; dashboard is display-only)
        start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
        deals = _safe_mt5(lambda: mt5.history_deals_get(start, datetime.utcnow()), [])
        if deals:
            result["today_deals_pnl"] = sum(d.profit for d in deals)
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    return result


def compute_exposure(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute gross/net exposure and per-currency factor exposure.

    Exposure units are expressed in the instrument's notional (1 lot-ish unit).
    For the factor lens: each position contributes its currency legs weighted
    by volume, e.g. short 0.08 EURUSD => {EUR: -0.08, USD: +0.08}.
    """
    gross = 0.0
    net_by_symbol: Dict[str, float] = {}
    # currency factor ledger
    currency_exposure: Dict[str, float] = {}
    per_currency_positions: Dict[str, List[Dict]] = {}

    for pos in positions:
        sym = pos["symbol"]
        vol = float(pos["volume"])
        sign = +1.0 if pos["type"] == "BUY" else -1.0
        gross += vol

        leg = CURRENCY_LEGS.get(sym)
        if leg:
            for cur, direction in leg.items():
                exposure = sign * vol * direction
                currency_exposure[cur] = currency_exposure.get(cur, 0.0) + exposure
                per_currency_positions.setdefault(cur, []).append({
                    "symbol": sym,
                    "ticket": pos["ticket"],
                    "type": pos["type"],
                    "volume": vol,
                    "profit": pos.get("profit", 0.0),
                    "side": "LONG" if direction * sign > 0 else "SHORT",
                })

        net_by_symbol[sym] = net_by_symbol.get(sym, 0.0) + sign * vol

    # Interpret: USD exposure is the factor that links all USD-pairs
    usd_exposure = currency_exposure.get("USD", 0.0)

    return {
        "gross_exposure": round(gross, 4),
        "net_exposure_symbols": {k: round(v, 4) for k, v in net_by_symbol.items()},
        "currency_exposure": {k: round(v, 4) for k, v in sorted(currency_exposure.items())},
        "usd_exposure_units": round(usd_exposure, 4),
        "per_currency_positions": per_currency_positions,
    }


def read_gold_state() -> Optional[Dict[str, Any]]:
    if not GOLD_STATE.exists():
        return None
    try:
        return json.loads(GOLD_STATE.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_gold_journal(days: int = 1) -> List[Dict[str, Any]]:
    """Read the last N days of gold engine journal JSONL (newest first)."""
    rows: List[Dict[str, Any]] = []
    if not GOLD_JOURNAL_DIR.exists():
        return rows
    today = datetime.utcnow().date()
    for offset in range(days):
        d = today - timedelta(days=offset)
        f = GOLD_JOURNAL_DIR / f"{d.isoformat()}.jsonl"
        if not f.exists():
            continue
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
        except Exception:
            pass
    # newest first
    rows.sort(key=lambda x: x.get("utc", ""), reverse=True)
    return rows


def compute_gold_today_pnl() -> float:
    """Sum gold-engine realized PnL today (comment-tagged, same as runner)."""
    rows = read_gold_journal(days=1)
    pnl = 0.0
    for r in rows:
        if r.get("action") in ("CLOSE_POSITION", "ORDER_SENT") and r.get("result"):
            res = r.get("result", {})
            pnl += res.get("pnl", 0.0)
    return pnl


def read_fx_signals(days: int = 2) -> List[Dict[str, Any]]:
    """Read recent FX signal JSONLs (scheduler output)."""
    rows: List[Dict[str, Any]] = []
    if not FX_SIGNALS_DIR.exists():
        return rows
    today = datetime.utcnow().date()
    for offset in range(days):
        d = today - timedelta(days=offset)
        month_dir = FX_SIGNALS_DIR / f"{d.year:04d}-{d.month:02d}"
        if not month_dir.exists():
            continue
        for f in month_dir.glob("*.jsonl"):
            try:
                for line in f.read_text(encoding="utf-8").splitlines():
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
            except Exception:
                pass
    rows.sort(key=lambda x: x.get("datetime", x.get("ts", "")), reverse=True)
    return rows[-50:]  # cap


def engine_health() -> Dict[str, Any]:
    """Process-liveness heuristics from timestamps (no psutil dependency)."""
    out = {}
    # gold engine: state file freshness
    if GOLD_STATE.exists():
        mtime = GOLD_STATE.stat().st_mtime
        age_s = time.time() - mtime
        out["gold"] = {
            "alive": bool(age_s < 300),  # <5min since last heartbeat/state write
            "age_seconds": round(age_s, 0),
            "updated_at": datetime.utcfromtimestamp(mtime).isoformat() + "Z",
        }
    else:
        out["gold"] = {"alive": False, "note": "no state file"}
    # fx scheduler: signals dir freshness
    if FX_SIGNALS_DIR.exists():
        try:
            latest = max(f.stat().st_mtime for f in FX_SIGNALS_DIR.rglob("*.jsonl"))
            age_s = time.time() - latest
            out["fx_scheduler"] = {
                "alive": bool(age_s < 1800),  # <30min since a signal was written
                "age_seconds": round(age_s, 0),
                "updated_at": datetime.utcfromtimestamp(latest).isoformat() + "Z",
            }
        except ValueError:
            out["fx_scheduler"] = {"alive": False}
    else:
        out["fx_scheduler"] = {"alive": False, "note": "no signals dir"}

    return out


def build_book() -> Dict[str, Any]:
    """Assemble the full book snapshot presented by the dashboard."""
    mt5 = get_mt5_snapshot()
    exposure = compute_exposure(mt5.get("positions", []))
    state = read_gold_state()
    gold_pnl = compute_gold_today_pnl()

    return {
        "ts": datetime.utcnow().isoformat() + "Z",
        "mt5": mt5,
        "exposure": exposure,
        "gold_state": state,
        "gold_pnl": gold_pnl,
        "health": engine_health(),
        "combined_today_pnl": round(mt5.get("today_deals_pnl", 0.0), 2),
    }