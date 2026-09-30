#!/usr/bin/env python
"""PHASE-1A read-only probe — EXP-2026-05-INVALIDATION-REVERSAL.

Authorized scope (data-free audit):
  - Read-only MT5 access on the active demo terminal. NO login() call.
  - Retrieve symbol metadata, current tick, and a diagnostic M15 bar sample
    for XAUUSD, EURUSD, GBPUSD (spread-unit, timezone, rollover, calendar,
    contract facts).
  - Capture account/session state BEFORE and AFTER; verify no change.
  - NO strategy, NO backtest, NO orders, NO settings changes, NO frival writes.

Outputs (written under this script's directory):
  RAW_METADATA_SNAPSHOT.json   — symbol_info / symbol_info_tick / account
  bars_sample.csv              — diagnostic M15 OHLC + spread (last ~5 days)
  session_state.json           — before/after account + position + order state
"""
import json
import os
import sys
import time as _time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
import MetaTrader5 as mt5
from dotenv import load_dotenv

OUT = Path(__file__).resolve().parent
load_dotenv(Path("frival/execution_bot/config/credentials.env"))
TERMINAL = os.getenv("MT5_TERMINAL_PATH") or r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD"]
TF_M15 = mt5.TIMEFRAME_M15


def account_state(mt5):
    info = mt5.account_info()
    pos = mt5.positions_get()
    ords = mt5.orders_get()
    return {
        "login": info.login if info else None,
        "server": info.server if info else None,
        "currency": info.currency if info else None,
        "balance": info.balance if info else None,
        "equity": info.equity if info else None,
        "n_positions": len(pos) if pos is not None else None,
        "n_orders": len(ords) if ords is not None else None,
        "utc_now": datetime.now(timezone.utc).isoformat(),
    }


def symbol_info_dict(si):
    if si is None:
        return {}
    fields = [
        "name", "type", "path", "currency", "additional_symbols", "precision",
        "margin_initial", "margin_maintenance", "company_flags", "display_mode",
        "properties", "bid", "ask", "tick_size", "digits", "point",
        "volume_min", "volume_max", "volume_step", "session_deals",
        "position_deals", "spread", "spread_float", "expiration_mode",
        "expiration_time", "options_mode",
    ]
    return {f: getattr(si, f, None) for f in fields}


def symbol_tick_dict(st):
    if st is None:
        return {}
    fields = ["bid", "ask", "last", "volume", "time", "flags"]
    return {f: getattr(st, f, None) for f in fields}


# ── initialize (no login — inherit active terminal session) ───────────────
if not mt5.initialize(path=TERMINAL):
    print(json.dumps({"fatal": f"initialize failed: {mt5.last_error()}"}))
    sys.exit(1)

before = account_state(mt5)

snapshot = {"probe": "PHASE-1A-DATA-SEMANTICS", "created_utc": before["utc_now"],
            "login_called": False, "symbols": {}, "terminal": str(TERMINAL)}

bars_all = {}
errors = []

try:
    for sym in SYMBOLS:
        si = mt5.symbol_info(sym)
        st = mt5.symbol_info_tick(sym)
        snapshot["symbols"][sym] = {
            "symbol_info": symbol_info_dict(si),
            "symbol_info_tick": symbol_tick_dict(st),
            "last_error_after_metadata": str(mt5.last_error()),
        }

        # Diagnostic M15 sample: last 5 days
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=5)
        rates = mt5.copy_rates_range(sym, TF_M15, start, now)
        if rates is None or len(rates) == 0:
            errors.append({sym: f"copy_rates_range empty: {mt5.last_error()}"})
            continue
        df = pd.DataFrame(rates)
        df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
        bars_all[sym] = df
        snapshot["symbols"][sym]["bars_sample"] = {
            "rows": int(len(df)),
            "first_time_utc": str(df["time_utc"].min()),
            "last_time_utc": str(df["time_utc"].max()),
            "columns": [c for c in df.columns],
        }
        # tick snapshot for spread comparison (live bid/ask)
        snapshot["symbols"][sym]["live_spread_from_tick"] = (
            None if st is None else float(st.ask - st.bid)
        )
        # most recent bar spread field
        last_bar = df.iloc[-1]
        snapshot["symbols"][sym]["last_bar_spread_field"] = float(last_bar["spread"])
        snapshot["symbols"][sym]["last_bar_point"] = float(si.point) if si else None
        snapshot["symbols"][sym]["spread_points_times_point"] = (
            float(last_bar["spread"]) * float(si.point) if si else None
        )

finally:
    after = account_state(mt5)
    snapshot["session_before"] = before
    snapshot["session_after"] = after
    snapshot["session_unchanged"] = {
        k: before.get(k) == after.get(k)
        for k in ["login", "server", "balance", "equity", "n_positions", "n_orders"]
    }
    snapshot["errors"] = errors
    (OUT / "RAW_METADATA_SNAPSHOT.json").write_text(
        json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
    (OUT / "session_state.json").write_text(
        json.dumps({"before": before, "after": after}, indent=2, default=str),
        encoding="utf-8")

    for sym, df in bars_all.items():
        df.to_csv(OUT / f"bars_{sym}.csv", index=False)

    mt5.shutdown()

print(json.dumps({
    "login_called": False,
    "session_unchanged": snapshot["session_unchanged"],
    "bars": {s: len(d) for s, d in bars_all.items()},
    "errors": errors,
}, indent=2, default=str))