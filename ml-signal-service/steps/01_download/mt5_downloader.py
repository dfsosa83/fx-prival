"""
MT5 Historical Data Downloader
================================
Downloads OHLCV bars for all configured pairs and timeframes from MetaTrader 5.
Incremental: if a CSV already exists, only fetches bars added since the last record.

Canonical output schema (same as yahoo_fetcher.py):
    datetime (UTC, "YYYY-MM-DD HH:MM:SS"), open, high, low, close, volume

Output:
    data/raw/mt5/{TF}/{SYMBOL}_{TF}.csv
    e.g.  data/raw/mt5/H1/EURUSD_H1.csv

Usage:
    python steps/01_download/mt5_downloader.py              # all pairs + all timeframes
    python steps/01_download/mt5_downloader.py --pair EURUSD
    python steps/01_download/mt5_downloader.py --pair EURUSD --tf H1

Note: requires MetaTrader 5 terminal running on Windows and a valid .env file.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd
import pytz
import yaml
from dotenv import load_dotenv

# ── project root & config ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PAIRS = ROOT / "config" / "pairs.yaml"
CONFIG_SETTINGS = ROOT / "config" / "settings.yaml"
ENV_FILE = ROOT / ".env"

# ── canonical output columns ───────────────────────────────────────────────────
CANONICAL_COLS = ["datetime", "open", "high", "low", "close", "volume"]

# ── MT5 timeframe constants (resolved at runtime to avoid import-time MT5 init) ─
MT5_TF_MAP = {
    "M1": "TIMEFRAME_M1",
    "M5": "TIMEFRAME_M5",
    "H1": "TIMEFRAME_H1",
    "D1": "TIMEFRAME_D1",
}

# ── how much to advance after the last bar per timeframe ──────────────────────
TF_INCREMENT = {
    "H1": timedelta(hours=1),
    "D1": timedelta(days=1),
    "M5": timedelta(minutes=5),
    "M1": timedelta(minutes=1),
}

UTC = pytz.UTC


# ── helpers ───────────────────────────────────────────────────────────────────

def load_configs():
    with open(CONFIG_PAIRS) as f:
        pairs_cfg = yaml.safe_load(f)
    with open(CONFIG_SETTINGS) as f:
        settings = yaml.safe_load(f)
    return pairs_cfg, settings


def connect_mt5(settings: dict) -> bool:
    load_dotenv(ENV_FILE)
    mt5_path = os.getenv("MT5_PATH") or settings["mt5"]["terminal_path_default"]
    login = int(os.getenv("MT5_LOGIN", "0"))
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")

    if not mt5.initialize(path=mt5_path):
        print(f"[ERROR] MT5 initialize() failed: {mt5.last_error()}")
        return False

    if not mt5.login(login, password, server):
        print(f"[ERROR] MT5 login() failed: {mt5.last_error()}")
        mt5.shutdown()
        return False

    info = mt5.account_info()
    print(f"[MT5]   Connected → server={info.server}  account={info.login}  balance={info.balance}")
    return True


def get_output_path(settings: dict, tf_name: str, symbol: str) -> Path:
    base = ROOT / settings["paths"]["raw_mt5"] / tf_name
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{symbol}_{tf_name}.csv"


def get_from_date(csv_path: Path, start_date: str, tf_name: str) -> datetime:
    """
    If CSV already exists: resume from last bar + one bar increment.
    Otherwise: start from the configured history start date.
    """
    if csv_path.exists() and csv_path.stat().st_size > 0:
        df = pd.read_csv(csv_path, usecols=["datetime"])
        if not df.empty:
            last_dt = pd.to_datetime(df["datetime"].iloc[-1], utc=True)
            return last_dt.to_pydatetime() + TF_INCREMENT.get(tf_name, timedelta(hours=1))

    return datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UTC)


def download_pair(symbol: str, tf_name: str, settings: dict, start_date: str):
    mt5_tf_attr = MT5_TF_MAP.get(tf_name)
    if mt5_tf_attr is None:
        print(f"[SKIP]  {symbol} {tf_name}: unknown timeframe")
        return

    mt5_tf = getattr(mt5, mt5_tf_attr)
    csv_path = get_output_path(settings, tf_name, symbol)
    from_dt = get_from_date(csv_path, start_date, tf_name)
    to_dt = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)

    if from_dt >= to_dt:
        print(f"[SKIP]  {symbol} {tf_name}: already up to date ({csv_path.name})")
        return

    print(f"[FETCH] {symbol} {tf_name}: {from_dt.date()} → {to_dt.date()} ...", end=" ")
    rates = mt5.copy_rates_range(symbol, mt5_tf, from_dt, to_dt)

    if rates is None or len(rates) == 0:
        print(f"\n[WARN]  {symbol} {tf_name}: MT5 returned no data — check symbol name and broker availability")
        return

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.rename(columns={"time": "datetime", "tick_volume": "volume"})
    df = df[CANONICAL_COLS].copy()
    df["datetime"] = df["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    file_exists = csv_path.exists() and csv_path.stat().st_size > 0
    df.to_csv(csv_path, mode="a", header=not file_exists, index=False)
    print(f"{len(df)} bars → {csv_path.name}")


# ── main ──────────────────────────────────────────────────────────────────────

def run(pair_filter: str = None, tf_filter: str = None):
    pairs_cfg, settings = load_configs()

    if not connect_mt5(settings):
        sys.exit(1)

    try:
        start_date = pairs_cfg["history"]["start_date"]
        all_pairs = (
            pairs_cfg["pairs"].get("majors", [])
            + pairs_cfg["pairs"].get("minors", [])
            + pairs_cfg["pairs"].get("commodities", [])
        )
        timeframes = [tf["name"] for tf in pairs_cfg["timeframes"]]

        for pair in all_pairs:
            symbol = pair["symbol"]
            if pair_filter and symbol != pair_filter.upper():
                continue
            for tf in timeframes:
                if tf_filter and tf != tf_filter.upper():
                    continue
                download_pair(symbol, tf, settings, start_date)

    finally:
        mt5.shutdown()
        print("[MT5]   Disconnected.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download MT5 historical OHLCV data")
    parser.add_argument("--pair", type=str, help="Single pair to download, e.g. EURUSD")
    parser.add_argument("--tf",   type=str, help="Single timeframe: H1 or D1")
    args = parser.parse_args()
    run(pair_filter=args.pair, tf_filter=args.tf)
