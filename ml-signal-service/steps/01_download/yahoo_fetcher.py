"""
Yahoo Finance Inference Fetcher
================================
Fetches the latest N bars for each configured pair / timeframe using Yahoo Finance.
Used at model INFERENCE time — not for training.

Canonical output schema (same as mt5_downloader.py):
    datetime (UTC, "YYYY-MM-DD HH:MM:SS"), open, high, low, close, volume

Output:
    data/raw/yahoo/{TF}/{SYMBOL}_{TF}_latest.csv
    e.g.  data/raw/yahoo/H1/EURUSD_H1_latest.csv
    (overwritten on each run — inference always needs the freshest window)

Staleness check:
    If the last bar is older than the configured limit, a WARNING is printed
    but the file is still written — the caller (inference pipeline) decides
    whether to proceed or abort.

Usage:
    python steps/01_download/yahoo_fetcher.py              # all pairs + all timeframes
    python steps/01_download/yahoo_fetcher.py --pair EURUSD
    python steps/01_download/yahoo_fetcher.py --pair EURUSD --tf H1
"""

import argparse
import warnings
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

# suppress yfinance FutureWarnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ── project root & config ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PAIRS = ROOT / "config" / "pairs.yaml"
CONFIG_SETTINGS = ROOT / "config" / "settings.yaml"

# ── canonical output columns ───────────────────────────────────────────────────
CANONICAL_COLS = ["datetime", "open", "high", "low", "close", "volume"]

# ── Yahoo Finance fetch periods ────────────────────────────────────────────────
# Must cover the lookback_bars in pairs.yaml PLUS a safety buffer.
# Yahoo H1 cap: ~730 days. Yahoo D1: no practical limit.
FETCH_PERIOD = {
    "H1": "60d",    # ~60 days × 24h = 1440 bars — well above 300 lookback
    "D1": "2y",     # ~500 trading days — well above 300 lookback
}

YAHOO_INTERVAL = {
    "H1": "1h",
    "D1": "1d",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def load_configs():
    with open(CONFIG_PAIRS) as f:
        pairs_cfg = yaml.safe_load(f)
    with open(CONFIG_SETTINGS) as f:
        settings = yaml.safe_load(f)
    return pairs_cfg, settings


def check_staleness(df: pd.DataFrame, tf_name: str, pairs_cfg: dict) -> bool:
    """
    Returns True if the data is fresh enough.
    Prints a warning (but does NOT raise) if the last bar is too old.
    """
    if df.empty:
        print("[WARN]  Staleness check: DataFrame is empty.")
        return False

    last_dt = pd.to_datetime(df["datetime"].iloc[-1], utc=True)
    age_min = (datetime.now(timezone.utc) - last_dt.to_pydatetime()).total_seconds() / 60

    limit_key = f"max_staleness_minutes_{tf_name.lower()}"
    limit = pairs_cfg["inference"].get(limit_key, 90)

    if age_min > limit:
        print(f"[WARN]  Last bar is {age_min:.0f} min old (limit: {limit} min) — data may be stale")
        return False
    return True


def normalize_yahoo_df(raw: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """
    Convert a raw yfinance DataFrame to the canonical schema.
    yfinance uses 'Datetime' for sub-daily intervals, 'Date' for daily.
    """
    df = raw.reset_index()

    dt_col = "Datetime" if "Datetime" in df.columns else "Date"
    df = df.rename(columns={
        dt_col:   "datetime",
        "Open":   "open",
        "High":   "high",
        "Low":    "low",
        "Close":  "close",
        "Volume": "volume",
    })

    df["datetime"] = (
        pd.to_datetime(df["datetime"], utc=True)
        .dt.strftime("%Y-%m-%d %H:%M:%S")
    )

    df = df[CANONICAL_COLS].dropna(subset=["close"])
    return df.tail(lookback).reset_index(drop=True)


def get_output_path(settings: dict, tf_name: str, symbol: str) -> Path:
    base = ROOT / settings["paths"]["raw_yahoo"] / tf_name
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{symbol}_{tf_name}_latest.csv"


def fetch_pair(
    symbol: str,
    yahoo_symbol: str,
    tf_name: str,
    settings: dict,
    pairs_cfg: dict,
) -> pd.DataFrame:
    """
    Fetch and normalize the latest bars for one pair/timeframe.
    Returns an empty DataFrame on failure.
    """
    period = FETCH_PERIOD.get(tf_name, "60d")
    interval = YAHOO_INTERVAL.get(tf_name, "1h")
    lookback = pairs_cfg["inference"]["lookback_bars"]

    print(f"[FETCH] {symbol} {tf_name} ({yahoo_symbol})  period={period}  interval={interval} ...", end=" ")

    try:
        ticker = yf.Ticker(yahoo_symbol)
        raw = ticker.history(period=period, interval=interval, auto_adjust=True)
    except Exception as exc:
        print(f"\n[ERROR] yfinance request failed: {exc}")
        return pd.DataFrame()

    if raw is None or raw.empty:
        print(f"\n[WARN]  No data returned for {yahoo_symbol}")
        return pd.DataFrame()

    df = normalize_yahoo_df(raw, lookback)
    check_staleness(df, tf_name, pairs_cfg)

    print(f"{len(df)} bars  (last: {df['datetime'].iloc[-1]})")
    return df


# ── main ──────────────────────────────────────────────────────────────────────

def run(pair_filter: str = None, tf_filter: str = None):
    pairs_cfg, settings = load_configs()

    all_pairs = (
        pairs_cfg["pairs"].get("majors", [])
        + pairs_cfg["pairs"].get("minors", [])
        + pairs_cfg["pairs"].get("commodities", [])
    )
    timeframes = [tf["name"] for tf in pairs_cfg["timeframes"]]

    for pair in all_pairs:
        symbol = pair["symbol"]
        yahoo_symbol = pair.get("yahoo")

        if not yahoo_symbol:
            print(f"[SKIP]  {symbol}: no Yahoo symbol in config")
            continue
        if pair_filter and symbol != pair_filter.upper():
            continue

        for tf in timeframes:
            if tf_filter and tf != tf_filter.upper():
                continue

            df = fetch_pair(symbol, yahoo_symbol, tf, settings, pairs_cfg)

            if not df.empty:
                out_path = get_output_path(settings, tf, symbol)
                df.to_csv(out_path, index=False)
                print(f"[OK]    Saved → {out_path.relative_to(ROOT)}")
            else:
                print(f"[FAIL]  {symbol} {tf}: nothing saved")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch latest bars from Yahoo Finance")
    parser.add_argument("--pair", type=str, help="Single pair, e.g. EURUSD")
    parser.add_argument("--tf",   type=str, help="Timeframe: H1 or D1")
    args = parser.parse_args()
    run(pair_filter=args.pair, tf_filter=args.tf)
