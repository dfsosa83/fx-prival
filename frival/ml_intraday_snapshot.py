#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""XAUUSD intraday snapshot writer — Frival manual-desk data pipeline.

Purpose
-------
The canonical ML downloader (ml-signal-service/steps/01_download/mt5_downloader.py)
writes only M1/M5/H1/D1 and is driven by the frival live scheduler, whose pair
list does NOT include XAUUSD. As a result ml-signal-service/data/raw/mt5/H1/
XAUUSD_H1.csv was stale (last bar 2026-09-30 14:00) while the desk was trading
XAUUSD intraday.

This module is DELIBERATELY DECOUPLED from that pipeline:

  * It writes only to ml-signal-service/data/raw/intraday/<TF>/<SYMBOL>_<TF>.csv
    — a NEW directory that no training pipeline reads.
  * It never calls run_live(), never emits signals, never touches
    output/signals/*.jsonl, and never places an order.
  * It never modifies mt5_downloader.py, settings.yaml, pairs.yaml or the
    scheduler's PAIRS list.

Manual execution is the operating model (fx-manual-trades.md §11.1). Adding
XAUUSD to the frival scheduler would generate executable signals for a symbol
the operator executes by hand. This writer avoids that entirely.

MT5 access is the validated path-only attach: the terminal must already be
running and logged in; credentials are never passed to the SDK.

Usage
-----
    python ml_intraday_snapshot.py --once
    python ml_intraday_snapshot.py --watch --interval 60
    python ml_intraday_snapshot.py --once --tf M5 --tf M15
    python ml_intraday_snapshot.py --status
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # fx-prival/
RAW_MT5 = ROOT / "ml-signal-service" / "data" / "raw"
INTRADAY = RAW_MT5 / "intraday"
from mt5_path import resolve_terminal_path

TERMINAL_PATH = resolve_terminal_path(HERE)

SERVER_UTC_OFFSET_H = 3
# Operator local time is UTC-5 (Panama). The SERVER clock reads UTC+3, so
# local = server - 8h. Applied to UTC the same value is UTC - 5h.
LOCAL_UTC_OFFSET_H = -5

CANONICAL_COLS = ["datetime", "open", "high", "low", "close", "volume", "spread"]

TF_MAP = {
    "M1": "TIMEFRAME_M1",
    "M5": "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H4": "TIMEFRAME_H4",
    "D1": "TIMEFRAME_D1",
}

DEFAULT_SYMBOLS = ["XAUUSD"]
DEFAULT_TFS = ["M5", "M15", "M30", "H1", "H4"]

BAR_SECONDS = {
    "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
    "H1": 3600, "H4": 14400, "D1": 86400,
}


def _mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[ERROR] MetaTrader5 package missing. Use C:\\Users\\david\\anaconda3\\python.exe")
        sys.exit(1)
    if not mt5.initialize(path=TERMINAL_PATH):
        print(f"[ERROR] mt5.initialize(path=...) failed: {mt5.last_error()}")
        print("        The terminal must be RUNNING and LOGGED IN.")
        sys.exit(1)
    return mt5


def now_clocks() -> dict:
    utc = dt.datetime.utcnow()
    return {
        "local": (utc + dt.timedelta(hours=LOCAL_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S"),
        "server": (utc + dt.timedelta(hours=SERVER_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S"),
    }


def out_path(symbol: str, tf: str) -> Path:
    d = INTRADAY / tf
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{symbol}_{tf}.csv"


def bars_to_frame(mt5, symbol: str, tf_name: str, count: int = 5000):
    import pandas as pd
    tf = getattr(mt5, TF_MAP[tf_name])
    raw = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if raw is None or len(raw) == 0:
        return None
    df = pd.DataFrame(raw)
    # MT5 bar epoch is BROKER SERVER time. Normalize to UTC so the CSV is
    # comparable with the canonical ml-signal-service H1 files.
    df["datetime"] = (
        pd.to_datetime(df["time"], unit="s") - pd.Timedelta(hours=SERVER_UTC_OFFSET_H)
    ).dt.strftime("%Y-%m-%d %H:%M:%S")
    for c in CANONICAL_COLS:
        if c not in df.columns:
            df[c] = None
    return df[CANONICAL_COLS]


def write(df, symbol: str, tf_name: str) -> tuple:
    p = out_path(symbol, tf_name)
    existed = p.exists() and p.stat().st_size > 0
    df.to_csv(p, index=False, mode="w", header=True)
    return p, len(df), existed


def snapshot(symbols, tfs) -> None:
    mt5 = _mt5()
    try:
        acct = mt5.account_info()
        clocks = now_clocks()
        print(f"[ACCT] {acct.login} {acct.server} bal={acct.balance} "
              f"lev={acct.leverage} pos={mt5.positions_total()}")
        print(f"[TIME] server={clocks['server']}  local={clocks['local']}")
        tick = mt5.symbol_info_tick("XAUUSD")
        info = mt5.symbol_info("XAUUSD")
        if tick and info:
            print(f"[QUOTE] bid={tick.bid} ask={tick.ask} spread={info.spread} "
                  f"contract={info.trade_contract_size} tickval={info.trade_tick_value}")
            print(f"[SWAP]  long={info.swap_long} short={info.swap_short} mode={info.swap_mode}")
        print()
        for tf_name in tfs:
            for sym in symbols:
                df = bars_to_frame(mt5, sym, tf_name)
                if df is None:
                    print(f"[WARN] no bars {sym} {tf_name}")
                    continue
                p, n, existed = write(df, sym, tf_name)
                tag = "updated" if existed else "created"
                last = df["datetime"].iloc[-1]
                print(f"[OK] {sym} {tf_name:3s} {tag:8s} rows={n:5d} last={last} -> {p.name}")
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def status() -> None:
    if not INTRADAY.exists():
        print(f"[INFO] {INTRADAY} does not exist yet")
        return
    import pandas as pd
    print(f"{'file':28s} {'rows':>7s}  {'last bar (UTC)':21s} {'stale_min':>10s}")
    now = dt.datetime.utcnow()
    for tf in sorted(INTRADAY.iterdir()):
        if not tf.is_dir():
            continue
        for f in sorted(tf.glob("*.csv")):
            try:
                d = pd.read_csv(f, usecols=["datetime"])
                last = pd.to_datetime(d["datetime"].iloc[-1])
                age = (now - last).total_seconds() / 60
                print(f"{f.name:28s} {len(d):7d}  {last.strftime('%Y-%m-%d %H:%M:%S'):21s} {age:10.1f}")
            except Exception as e:
                print(f"{f.name:28s}  ERROR {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="single pass, then exit")
    ap.add_argument("--watch", action="store_true", help="continuous loop")
    ap.add_argument("--interval", type=int, default=60, help="seconds between passes (--watch)")
    ap.add_argument("--status", action="store_true", help="report freshness of existing CSVs")
    ap.add_argument("--symbol", action="append", dest="symbols")
    ap.add_argument("--tf", action="append", dest="tfs", choices=list(TF_MAP))
    a = ap.parse_args()

    symbols = a.symbols or DEFAULT_SYMBOLS
    tfs = a.tfs or DEFAULT_TFS

    if a.status:
        status()
        return
    if a.watch:
        print(f"[WATCH] every {a.interval}s — Ctrl+C to stop")
        try:
            while True:
                snapshot(symbols, tfs)
                print("---")
                time.sleep(a.interval)
        except KeyboardInterrupt:
            print("\n[STOP]")
    else:
        snapshot(symbols, tfs)


if __name__ == "__main__":
    main()