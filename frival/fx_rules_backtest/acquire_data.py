# -*- coding: utf-8 -*-
"""EXP-2026-04 — FX rule-engine backtest: data acquisition (Deliverable 1).

READ-ONLY. Fetches M15 + M30 closed bars for the 4 study pairs from the
running FPMarkets MT5 terminal, caches them as CSV fixtures, and returns
DataFrames compatible with gold_rules bias/levels/engine modules
(columns: datetime, open, high, low, close, volume).

Design contract: EXP-2026-04-RULEENGINE-FX-BACKTEST.md §2.
  - G1 enforcement: only CLOSED bars are kept (server-clock age filter),
    identical to the live gold engine fix.
  - One-time read-only fetch; no orders, no writes to the account.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)

TERMINAL_PATH = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

# Study pairs (operator-approved 2026-09-17). USDJPY history is capped at its
# ML-kill date (2026-07-30); the acquisition returns what the broker serves.
PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "USDCAD"]

# Fetch generous history so the backtest can slice warm-up + window freely.
# ~150 days of M15 (≈14,400 bars) + warm-up margin.
FETCH_DAYS = 150

TIMEFRAME_PERIOD_SEC = {"M15": 15 * 60, "M30": 30 * 60}


def _init_mt5():
    import MetaTrader5 as mt5
    if not mt5.initialize(path=TERMINAL_PATH):
        raise ConnectionError(f"MT5 initialize() failed: {mt5.last_error()}")
    return mt5


def fetch_pair(mt5, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
    """Fetch per-timeframe closed bars for one pair, G1-filtered."""
    tf_map = {"M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30}
    utc_now = datetime.utcnow()
    from_time = utc_now - timedelta(days=days)
    rates = mt5.copy_rates_range(symbol, tf_map[timeframe], from_time, utc_now)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"MT5 returned no {symbol} {timeframe}: {mt5.last_error()}")
    df = pd.DataFrame(rates)
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    df.drop(columns=["time", "spread", "real_volume"], inplace=True, errors="ignore")
    df.rename(columns={"tick_volume": "volume"}, inplace=True)

    # G1: only closed bars survive (server clock age >= period).
    try:
        t = mt5.symbol_info_tick(symbol)
        server_now = t.time if t is not None else None
    except Exception:
        server_now = None
    if server_now is not None:
        closed = df["datetime"].astype("int64") // 10**9 <= (
            server_now - TIMEFRAME_PERIOD_SEC[timeframe]
        )
        df = df[closed]
    else:
        df = df.iloc[:-1]  # conservative fallback: drop newest row

    df = df[["datetime", "open", "high", "low", "close", "volume"]]
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def acquire_all(days: int = FETCH_DAYS) -> None:
    """Fetch M15+M30 for all study pairs and cache as CSV."""
    mt5 = _init_mt5()
    try:
        for symbol in PAIRS:
            for tf in ("M15", "M30"):
                df = fetch_pair(mt5, symbol, tf, days)
                out = DATA / f"{symbol}_{tf}.csv"
                df.to_csv(out, index=False)
                print(f"[acquire] {symbol:<7} {tf:<4} {len(df):>6,} bars "
                      f"({df['datetime'].iloc[0]:%Y-%m-%d} -> "
                      f"{df['datetime'].iloc[-1]:%Y-%m-%d %H:%M}) -> {out.name}")
    finally:
        mt5.shutdown()


def load_pair(symbol: str, timeframe: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{symbol}_{timeframe}.csv", parse_dates=["datetime"])


if __name__ == "__main__":
    acquire_all(days=FETCH_DAYS)