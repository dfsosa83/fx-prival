# -*- coding: utf-8 -*-
"""Data harness for gold_rules unit tests.

Fetches XAUUSD M30 + H1 bars from the running FPMarkets MT5 terminal
(READ-ONLY; no orders), caches them as CSV fixtures for offline re-runs,
and returns them as DataFrames compatible with bias.py / levels.py
(columns: datetime, open, high, low, close, volume).

Usage:
    python -m tests.fetch_data   (from frival/gold_rules/)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
FIXTURES.mkdir(exist_ok=True)

M30_FILE = FIXTURES / "XAUUSD_M30.csv"
H1_FILE = FIXTURES / "XAUUSD_H1.csv"
M15_FILE = FIXTURES / "XAUUSD_M15.csv"

TERMINAL_PATH = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"


def _init_mt5():
    import MetaTrader5 as mt5

    if not mt5.initialize(path=TERMINAL_PATH):
        raise ConnectionError(f"MT5 initialize() failed: {mt5.last_error()}")
    return mt5


def fetch_and_cache(days: int = 30) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch M15 + M30 + H1 for the last `days` days; cache; return (m15, m30, h1)."""
    from datetime import datetime as _datetime

    utc_now = _datetime.utcnow()
    from_time = utc_now - timedelta(days=days)

    mt5 = _init_mt5()

    frames = {}
    for tf, mt5_tf, out_file in (
        ("M15", mt5.TIMEFRAME_M15, M15_FILE),
        ("M30", mt5.TIMEFRAME_M30, M30_FILE),
        ("H1", mt5.TIMEFRAME_H1, H1_FILE),
    ):
        rates = mt5.copy_rates_range("XAUUSD", mt5_tf, from_time, utc_now)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"MT5 returned no XAUUSD {tf} data: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["datetime"] = pd.to_datetime(df["time"], unit="s")
        df.drop(columns=["time", "spread", "real_volume"], inplace=True, errors="ignore")
        df.rename(columns={"tick_volume": "volume"}, inplace=True)
        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        df.sort_values("datetime", inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.to_csv(out_file, index=False)
        frames[tf] = df
        print(f"[fetch] cached {len(df):,} XAUUSD {tf} bars -> {out_file.name}")

    mt5.shutdown()
    return frames["M15"], frames["M30"], frames["H1"]


def load_m15() -> pd.DataFrame:
    return pd.read_csv(M15_FILE, parse_dates=["datetime"])


def load_m30() -> pd.DataFrame:
    return pd.read_csv(M30_FILE, parse_dates=["datetime"])


def load_h1() -> pd.DataFrame:
    return pd.read_csv(H1_FILE, parse_dates=["datetime"])


def ensure_fixtures(days: int = 30):
    """Use cached fixtures if present, otherwise fetch from MT5."""
    if M15_FILE.exists() and M30_FILE.exists() and H1_FILE.exists():
        return load_m15(), load_m30(), load_h1()
    return fetch_and_cache(days=days)


if __name__ == "__main__":
    m15, m30, h1 = fetch_and_cache(days=30)
    print(f"[fetch] M15 last bar: {m15['datetime'].iloc[-1]}  close={m15['close'].iloc[-1]}")
    print(f"[fetch] M30 last bar: {m30['datetime'].iloc[-1]}  close={m30['close'].iloc[-1]}")
    print(f"[fetch] H1  last bar: {h1['datetime'].iloc[-1]}  close={h1['close'].iloc[-1]}")