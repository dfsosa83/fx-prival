"""
Data acquisition for EURUSD H1.

Supports two sources:
- csv : Read from disk (backtest mode)
- mt5 : Fetch from running MetaTrader 5 terminal (live mode)

Cache-first: MT5 data is saved to CSV after fetch so backtests can run offline.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

# ── MT5 import (optional — only needed for live mode) ────────────────────────
try:
    import MetaTrader5 as mt5
    _MT5_AVAILABLE = True
except ImportError:
    _MT5_AVAILABLE = False
    mt5 = None  # type: ignore


# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "ml-signal-service" / "data" / "raw" / "mt5" / "H1"
)
CACHE_DIR = Path(__file__).resolve().parent / "cache"


def _load_env() -> Tuple[str, str, str, str]:
    """Load MT5 credentials from .env file or environment variables."""
    env_file = Path(__file__).resolve().parents[1] / "config" / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip()

    return (
        os.environ.get("MT5_LOGIN", ""),
        os.environ.get("MT5_PASSWORD", ""),
        os.environ.get("MT5_SERVER", ""),
        os.environ.get("MT5_PATH", ""),
    )


def fetch_ohlcv(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    *,
    source: str = "csv",
) -> pd.DataFrame:
    """
    Fetch OHLCV data for a symbol and timeframe.

    Parameters
    ----------
    symbol : str
        Trading symbol (EURUSD, GBPUSD, etc.)
    timeframe : str
        Timeframe string (H1, M1, etc.)
    start_date : str, optional
        Start date YYYY-MM-DD. CSV mode loads everything if omitted.
    end_date : str, optional
        End date YYYY-MM-DD. CSV mode loads everything if omitted.
    source : str
        "csv" — read from disk (backtest)
        "mt5" — fetch from running MT5 terminal (live)

    Returns
    -------
    pd.DataFrame with columns: datetime, open, high, low, close, tick_volume
    """
    if source == "csv":
        return _fetch_csv(symbol, timeframe, start_date, end_date)
    elif source == "mt5":
        return _fetch_mt5(symbol, timeframe, start_date, end_date)
    else:
        raise ValueError(f"Unknown source: {source}. Use 'csv' or 'mt5'.")


def _fetch_csv(
    symbol: str,
    timeframe: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> pd.DataFrame:
    """Read OHLCV data from CSV file."""
    filename = f"{symbol}_{timeframe}.csv"
    filepath = DATA_DIR / filename

    if not filepath.exists():
        raise FileNotFoundError(
            f"Data file not found: {filepath}\n"
            f"Run with source='mt5' first to fetch data, or place CSV manually."
        )

    df = pd.read_csv(filepath, parse_dates=["datetime"])

    if start_date:
        df = df[df["datetime"] >= start_date]
    if end_date:
        end_dt = pd.Timestamp(end_date) + pd.Timedelta(hours=23, minutes=59)
        df = df[df["datetime"] <= end_dt]

    df.reset_index(drop=True, inplace=True)

    # Normalize column name for compatibility
    if "tick_volume" in df.columns and "volume" not in df.columns:
        df.rename(columns={"tick_volume": "volume"}, inplace=True)

    print(f"[csv] Loaded {len(df):,} bars from {filename}")
    return df


def _fetch_mt5(
    symbol: str,
    timeframe: str,
    start_date: Optional[str],
    end_date: Optional[str],
) -> pd.DataFrame:
    """Fetch OHLCV data from MetaTrader 5 terminal."""
    if not _MT5_AVAILABLE:
        raise ImportError(
            "MetaTrader5 package not installed. Install with: pip install MetaTrader5"
        )

    login, password, server, mt5_path = _load_env()

    # ── Initialize MT5 ────────────────────────────────────────────────────
    if mt5_path:
        if not mt5.initialize(path=mt5_path):
            raise ConnectionError(f"MT5 initialize() failed: {mt5.last_error()}")
    else:
        if not mt5.initialize():
            raise ConnectionError(f"MT5 initialize() failed: {mt5.last_error()}")

    print(f"[mt5] Connected to terminal")

    # ── Login if credentials provided ─────────────────────────────────────
    if login and password and server:
        if not mt5.login(int(login), password, server):
            print(f"[mt5] Warning: login failed: {mt5.last_error()}")
        else:
            print(f"[mt5] Logged in to {server} (account {login})")

    # ── Map timeframe string to MT5 constant ──────────────────────────────
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    mt5_tf = tf_map.get(timeframe)
    if mt5_tf is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    # ── Determine date range ──────────────────────────────────────────────
    import pytz
    utc = pytz.timezone("Etc/UTC")

    if start_date:
        from_time = pd.Timestamp(start_date).tz_localize(utc).to_pydatetime()
    else:
        from_time = pd.Timestamp("2019-01-02").tz_localize(utc).to_pydatetime()

    if end_date:
        to_time = pd.Timestamp(end_date).tz_localize(utc).to_pydatetime()
        to_time = to_time.replace(hour=23, minute=59)
    else:
        to_time = datetime.now(utc)

    print(f"[mt5] Fetching {symbol} {timeframe} from {from_time} to {to_time}")

    # ── Fetch from MT5 ────────────────────────────────────────────────────
    rates = mt5.copy_rates_range(symbol, mt5_tf, from_time, to_time)

    if rates is None or len(rates) == 0:
        raise RuntimeError(f"MT5 returned no data for {symbol}. Error: {mt5.last_error()}")

    df = pd.DataFrame(rates)
    df["datetime"] = pd.to_datetime(df["time"], unit="s")
    df.drop(columns=["time", "spread", "real_volume"], inplace=True, errors="ignore")
    df.rename(columns={"tick_volume": "volume"}, inplace=True)

    print(f"[mt5] Fetched {len(df):,} bars")

    # ── Cache to CSV for offline backtesting ──────────────────────────────
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = CACHE_DIR / f"{symbol}_{timeframe}_live_cache.csv"
    df.to_csv(cache_file, index=False)
    print(f"[mt5] Cached to {cache_file.name}")

    mt5.shutdown()
    return df


# Need datetime for end_date default in _fetch_mt5
from datetime import datetime