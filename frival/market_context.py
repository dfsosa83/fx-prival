#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Market-context snapshot builder for the trade log.

Attaches to trade_log.csv a reproducible record of the market state at the
moment each signal was emitted, so a past decision can be reconstructed
exactly instead of recalled.

Two artefacts are produced per signal:

    context/<log_id>.json   full snapshot — quote, account, ATRs, levels,
                            last 20 M5 and 10 M15 bars, spread, swap
    context/<log_id>.md     human-readable summary of the same

This module is READ-ONLY against MT5. It never places, modifies or cancels an
order, and it never calls the frival signal pipeline.

Usage:
    python market_context.py capture --id T003
    python market_context.py capture --all
    python market_context.py show   --id T003
    python market_context.py audit
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "trade_log.csv"
CTX_DIR = HERE / "context"
from mt5_path import resolve_terminal_path

TERMINAL_PATH = resolve_terminal_path(HERE)

SERVER_UTC_OFFSET_H = 3
LOCAL_UTC_OFFSET_H = -5

M5_BARS = 20
M15_BARS = 10

TF_ATTR = {"M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15",
           "M30": "TIMEFRAME_M30", "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4",
           "D1": "TIMEFRAME_D1"}


def _mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[ERROR] MetaTrader5 package missing. Use anaconda3 python.")
        sys.exit(1)
    if not mt5.initialize(path=TERMINAL_PATH):
        print(f"[ERROR] mt5.initialize failed: {mt5.last_error()}")
        sys.exit(1)
    return mt5


def _bars(mt5, symbol: str, tf_name: str, count: int):
    import pandas as pd
    raw = mt5.copy_rates_from_pos(symbol, getattr(mt5, TF_ATTR[tf_name]), 0, count)
    if raw is None or len(raw) == 0:
        return []
    df = pd.DataFrame(raw)
    out = []
    for _, r in df.iterrows():
        out.append({
            "server_time": dt.datetime.utcfromtimestamp(r["time"]).strftime("%Y-%m-%d %H:%M:%S"),
            "utc_time": (dt.datetime.utcfromtimestamp(r["time"])
                         - dt.timedelta(hours=SERVER_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S"),
            "open": round(float(r["open"]), 2),
            "high": round(float(r["high"]), 2),
            "low": round(float(r["low"]), 2),
            "close": round(float(r["close"]), 2),
            "tick_volume": int(r["tick_volume"]),
            "spread": int(r["spread"]),
        })
    return out


def _atr(mt5, symbol: str, tf_name: str, n: int = 80) -> str:
    import pandas as pd
    raw = mt5.copy_rates_from_pos(symbol, getattr(mt5, TF_ATTR[tf_name]), 0, n)
    if raw is None or len(raw) < 15:
        return ""
    df = pd.DataFrame(raw)
    pc = df["close"].shift(1)
    tr = pd.concat([df["high"] - df["low"], (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return f"{tr.tail(14).mean():.2f}"


def _levels(mt5, symbol: str) -> dict:
    """Recent swing extremes used as the desk's structural reference points."""
    import pandas as pd
    out = {}
    for tf_name, n in (("H1", 40), ("M15", 40), ("M5", 40)):
        raw = mt5.copy_rates_from_pos(symbol, getattr(mt5, TF_ATTR[tf_name]), 0, n)
        if raw is None or len(raw) == 0:
            continue
        df = pd.DataFrame(raw)
        out[tf_name] = {
            "window_bars": len(df),
            "high": round(float(df["high"].max()), 2),
            "low": round(float(df["low"].min()), 2),
            "close": round(float(df["close"].iloc[-1]), 2),
        }
    return out


def _log_rows():
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def capture(log_id: str) -> Path:
    rows = _log_rows()
    row = next((r for r in rows if r.get("log_id") == log_id), None)
    if row is None:
        print(f"[ERROR] {log_id} not in {LOG_PATH.name}")
        sys.exit(1)

    symbol = row.get("symbol") or "XAUUSD"
    mt5 = _mt5()
    try:
        acct = mt5.account_info()
        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        utc = dt.datetime.utcnow()
        snap = {
            "log_id": log_id,
            "setup_id": row.get("setup_id", ""),
            "captured_at_local": (utc + dt.timedelta(hours=LOCAL_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S"),
            "captured_at_server": (utc + dt.timedelta(hours=SERVER_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S"),
            "account": {
                "login": acct.login if acct else None,
                "server": acct.server if acct else None,
                "balance": acct.balance if acct else None,
                "equity": acct.equity if acct else None,
                "leverage": acct.leverage if acct else None,
                "open_positions": mt5.positions_total(),
            },
            "quote": {
                "bid": tick.bid if tick else None,
                "ask": tick.ask if tick else None,
                "spread_points": info.spread if info else None,
                "contract_size": info.trade_contract_size if info else None,
                "tick_value": info.trade_tick_value if info else None,
                "swap_long": info.swap_long if info else None,
                "swap_short": info.swap_short if info else None,
            },
            "atr14": {tf: _atr(mt5, symbol, tf) for tf in ("M5", "M15", "M30", "H1", "H4")},
            "levels": _levels(mt5, symbol),
            "bars_m5": _bars(mt5, symbol, "M5", M5_BARS),
            "bars_m15": _bars(mt5, symbol, "M15", M15_BARS),
            "signal": {
                "side": row.get("side", ""),
                "order_type": row.get("order_type", ""),
                "volume": row.get("volume", ""),
                "entry_price": row.get("entry_price", ""),
                "stop_loss": row.get("stop_loss", ""),
                "tp1": row.get("tp1", ""),
                "tp2": row.get("tp2", ""),
                "sl_distance": row.get("sl_distance", ""),
                "expected_rr_tp1": row.get("expected_rr_tp1", ""),
                "expected_rr_tp2": row.get("expected_rr_tp2", ""),
                "risk_usd": row.get("risk_usd", ""),
                "risk_pct_equity": row.get("risk_pct_equity", ""),
                "trigger_condition": row.get("trigger_condition", ""),
                "htf_bias": row.get("htf_bias", ""),
                "be_trigger_price": row.get("be_trigger_price", ""),
                "status": row.get("status", ""),
            },
        }
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    CTX_DIR.mkdir(parents=True, exist_ok=True)
    jp = CTX_DIR / f"{log_id}.json"
    jp.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    (CTX_DIR / f"{log_id}.md").write_text(_render_md(snap), encoding="utf-8")
    print(f"[OK] {log_id} snapshot -> {jp.name} + {log_id}.md")
    return jp


def _render_md(s: dict) -> str:
    sig, q, a = s["signal"], s["quote"], s["account"]
    L = [
        f"# {s['log_id']} — {s['setup_id']}",
        "",
        f"* captured local `{s['captured_at_local']}` / server `{s['captured_at_server']}`",
        f"* account `{a['login']}` {a['server']}  balance `{a['balance']}`  lev `{a['leverage']}`  open pos `{a['open_positions']}`",
        f"* quote bid `{q['bid']}` ask `{q['ask']}` spread `{q['spread_points']}` pts  "
        f"swap L `{q['swap_long']}` S `{q['swap_short']}`",
        "",
        "## Signal",
        "",
        "| field | value |",
        "| :--- | :--- |",
    ]
    for k, v in sig.items():
        L.append(f"| {k} | {v} |")
    L += ["", "## ATR(14)", "", "| tf | atr |", "| :--- | :--- |"]
    for k, v in s["atr14"].items():
        L.append(f"| {k} | {v} |")
    L += ["", "## Levels", "", "| tf | window | high | low | close |", "| :--- | :--- | :--- | :--- | :--- |"]
    for k, v in s["levels"].items():
        L.append(f"| {k} | {v['window_bars']} | {v['high']} | {v['low']} | {v['close']} |")
    L += ["", f"## Last {len(s['bars_m5'])} M5 bars (UTC)", "",
          "| utc | o | h | l | c | vol |", "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for b in s["bars_m5"]:
        L.append(f"| {b['utc_time']} | {b['open']} | {b['high']} | {b['low']} | {b['close']} | {b['tick_volume']} |")
    L += ["", f"## Last {len(s['bars_m15'])} M15 bars (UTC)", "",
          "| utc | o | h | l | c | vol |", "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for b in s["bars_m15"]:
        L.append(f"| {b['utc_time']} | {b['open']} | {b['high']} | {b['low']} | {b['close']} | {b['tick_volume']} |")
    return "\n".join(L) + "\n"


def show(log_id: str) -> None:
    p = CTX_DIR / f"{log_id}.md"
    if not p.exists():
        print(f"[INFO] no snapshot for {log_id}")
        return
    print(p.read_text(encoding="utf-8"))


def audit() -> None:
    rows = _log_rows()
    print(f"{'log_id':7s} {'status':14s} {'side':5s} {'ctx.json':9s} {'ctx.md':7s}  setup")
    for r in rows:
        lid = r.get("log_id", "")
        has_j = (CTX_DIR / f"{lid}.json").exists()
        has_m = (CTX_DIR / f"{lid}.md").exists()
        print(f"{lid:7s} {r.get('status',''):14s} {r.get('side',''):5s} "
              f"{'yes' if has_j else 'NO':9s} {'yes' if has_m else 'NO':7s}  {r.get('setup_id','')}")
    missing = [r.get("log_id") for r in rows if not (CTX_DIR / f"{r.get('log_id')}.json").exists()]
    if missing:
        print(f"\nmissing context for: {', '.join(missing)}")
        print(f"run: python market_context.py capture --id <id>")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--id")
    c.add_argument("--all", action="store_true")
    s = sub.add_parser("show"); s.add_argument("--id", required=True)
    a = sub.add_parser("audit")
    args = ap.parse_args()

    if args.cmd == "capture":
        ids = [r["log_id"] for r in _log_rows()] if args.all else [args.id]
        for lid in ids:
            if lid:
                capture(lid)
    elif args.cmd == "show":
        show(args.id)
    elif args.cmd == "audit":
        audit()


if __name__ == "__main__":
    main()