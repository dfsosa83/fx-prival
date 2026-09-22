#!/usr/bin/env python
"""Fetch XAUUSD M5 path + verify time alignment against real trades.

Critical: MT5 statement times and bar times can differ by the broker's server
offset. If they don't align, the replay would be silently wrong. We verify by
checking that a trade's entry price lies within the M5 bar's [low, high] at the
statement timestamp, testing candidate offsets.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
CREDS = ROOT.parent / "frival" / "execution_bot" / "config" / "credentials.env"
LEDGER = DATA / "gold_manual_trades.csv"
M5_OUT = DATA / "xauusd_m5.csv"


def fetch_m5() -> pd.DataFrame:
    import MetaTrader5 as mt5
    load_dotenv(CREDS)
    path = os.getenv("MT5_PATH") or r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"
    if not mt5.initialize(path=path):
        raise SystemExit(f"MT5 init failed: {mt5.last_error()}")
    if not mt5.login(int(os.getenv("MT5_LOGIN", "0")), os.getenv("MT5_PASSWORD", ""), os.getenv("MT5_SERVER", "")):
        raise SystemExit(f"MT5 login failed: {mt5.last_error()}")

    start = datetime(2026, 8, 25, tzinfo=timezone.utc)
    end = datetime(2026, 9, 19, tzinfo=timezone.utc)
    tf = getattr(mt5, "TIMEFRAME_M5")
    rates = mt5.copy_rates_range("XAUUSD", tf, start, end)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        raise SystemExit("no M5 data returned")
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df[["time", "open", "high", "low", "close"]].sort_values("time").reset_index(drop=True)
    df.to_csv(M5_OUT, index=False)
    print(f"fetched {len(df)} M5 bars  {df['time'].min()} -> {df['time'].max()} -> {M5_OUT}")
    return df


def main() -> None:
    df = fetch_m5() if not M5_OUT.exists() else pd.read_csv(M5_OUT, parse_dates=["time"])
    if not M5_OUT.exists():
        df.to_csv(M5_OUT, index=False)

    trades = pd.read_csv(LEDGER, parse_dates=["open_time"])
    gold = trades[(trades["symbol"] == "XAUUSD") & trades["sl"].notna() & trades["entry"].notna()].copy()
    print(f"\ngold trades with SL+entry: {len(gold)}")

    # alignment test: does entry price sit inside the M5 bar at the stated time?
    print("\nalignment check (fraction of trades whose entry is inside the bar's H/L):")
    for offset_h in (0, 1, 2, 3, -2):
        hits = 0
        for _, t in gold.head(40).iterrows():
            ts = t["open_time"] - pd.Timedelta(hours=offset_h)
            row = df[df["time"] == ts]
            if len(row) and (row.iloc[0]["low"] <= t["entry"] <= row.iloc[0]["high"]):
                hits += 1
        print(f"  offset {offset_h:+d}h: {hits}/40 in-bar")


if __name__ == "__main__":
    main()