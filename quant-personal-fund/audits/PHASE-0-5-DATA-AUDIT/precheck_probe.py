#!/usr/bin/env python
"""Phase 0.5 — SAFETY PRE-CHECK probe (read-only MT5).

STRICTLY read-only: initialize -> account_info -> positions_get ->
orders_get_all. Does NOT call login(), does not change account/settings,
does not place/modify/cancel any order.

If initialize does not yield a usable session (e.g. terminal not logged in),
STOP and report — do not call login() (would re-login the active session).
"""
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, ".")
OUT = Path("quant-personal-fund/audits/PHASE-0-5-DATA-AUDIT")
CREDS = Path("frival/execution_bot/config/credentials.env")

load_dotenv(CREDS)
login = os.getenv("MT5_LOGIN", "")
server = os.getenv("MT5_SERVER", "")
path = os.getenv("MT5_TERMINAL_PATH") or r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

import MetaTrader5 as mt5

result = {"stage": "precheck", "ok": False, "errors": [], "account": None,
          "positions": None, "orders": None, "login_called": False}

if not mt5.initialize(path=path):
    result["errors"].append(f"initialize failed: {mt5.last_error()}")
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0)

# Read-only account info (no login() call — inherit active terminal session)
info = mt5.account_info()
if info is None:
    # Terminal may not be logged in; must NOT call login (would re-login).
    result["errors"].append(
        f"account_info returned None (terminal session not usable without login). "
        f"last_error={mt5.last_error()}. STOPPING: login() would disturb the active session."
    )
    mt5.shutdown()
    print(json.dumps(result, indent=2, default=str))
    sys.exit(0)

result["account"] = {
    "login": getattr(info, "login", None),
    "server": getattr(info, "server", None),
    "currency": getattr(info, "currency", None),
    "balance": getattr(info, "balance", None),
    "equity": getattr(info, "equity", None),
    "margin": getattr(info, "margin", None),
}
result["ok"] = True

# Read-only positions
positions = mt5.positions_get()
result["positions"] = ([] if positions is None else
                       [{"ticket": p.ticket, "symbol": p.symbol, "type": p.type,
                         "volume": p.volume, "price_open": p.price_open}
                        for p in positions])

# Read-only orders (pending)
orders = mt5.orders_get()
result["orders"] = ([] if orders is None else
                    [{"ticket": o.ticket, "symbol": o.symbol, "type": o.type,
                      "volume": o.volume, "price": o.price} for o in orders])

mt5.shutdown()

# Persist to audit dir
out_json = OUT / "precheck_result.json"
out_json.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")

print(json.dumps(result, indent=2, default=str))