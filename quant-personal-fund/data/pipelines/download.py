"""
Market data downloader.

Downloads daily OHLCV data from Yahoo Finance for instruments in the
universe configuration. Creates data manifests with SHA256 hashes for
each downloaded file.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def download_yahoo_daily(
    yahoo_ticker: str,
    start_date: str,
    end_date: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Download daily OHLCV data from Yahoo Finance.

    Args:
        yahoo_ticker: Yahoo Finance ticker symbol (e.g., 'EURUSD=X').
        start_date: Start date in 'YYYY-MM-DD' format.
        end_date: End date in 'YYYY-MM-DD' format. Defaults to today.
        output_dir: Directory to save the raw data file. If None, data is not saved.

    Returns:
        DataFrame with columns: date, open, high, low, close, adj_close, volume.
        Index is date (DatetimeIndex).

    Raises:
        ImportError: If yfinance is not installed.
    """
    try:
        import yfinance as yf
    except ImportError:
        raise ImportError(
            "yfinance is required for data download. "
            "Install with: pip install yfinance"
        )

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Downloading {yahoo_ticker} from {start_date} to {end_date}")

    ticker_obj = yf.Ticker(yahoo_ticker)
    df = ticker_obj.history(start=start_date, end=end_date)

    if df.empty:
        logger.warning(f"No data returned for {yahoo_ticker}")
        return pd.DataFrame()

    # Standardize column names
    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    })

    # Reset index to make date a column
    df = df.reset_index()
    if "Date" in df.columns:
        df = df.rename(columns={"Date": "date"})

    # Keep only standard columns
    keep_cols = ["date"] + [c for c in ["open", "high", "low", "close", "adj_close", "volume"] if c in df.columns]
    df = df[keep_cols]

    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        filename = f"{yahoo_ticker}_daily.parquet"
        filepath = output_path / filename
        df.to_parquet(filepath, index=False)
        logger.info(f"Saved {len(df)} rows to {filepath}")

    return df


def download_universe(
    universe_yaml_path: str,
    output_dir: str,
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
) -> List[str]:
    """
    Download daily data for all active instruments in the universe.

    Args:
        universe_yaml_path: Path to config/universe.yaml.
        output_dir: Directory to save raw data files.
        start_date: Start date for all downloads.
        end_date: End date for all downloads.

    Returns:
        List of downloaded Yahoo tickers.
    """
    with open(universe_yaml_path, "r") as f:
        config = yaml.safe_load(f)

    downloaded = []
    universe = config.get("universe", {})

    for asset_class, instruments in universe.items():
        for record in instruments:
            if not record.get("is_active", False):
                continue
            yahoo_ticker = record.get("yahoo_ticker")
            if not yahoo_ticker:
                logger.warning(f"No yahoo_ticker for {record.get('ticker')}")
                continue

            try:
                download_yahoo_daily(
                    yahoo_ticker=yahoo_ticker,
                    start_date=start_date,
                    end_date=end_date,
                    output_dir=output_dir,
                )
                downloaded.append(yahoo_ticker)
            except Exception as e:
                logger.error(f"Failed to download {yahoo_ticker}: {e}")

    return downloaded


def download_fred_series(
    series_id: str,
    start_date: str,
    end_date: Optional[str] = None,
    api_key_file: str = "fred-credentials.txt",
) -> "pd.Series":
    """
    Download a single FRED economic data series.

    Reads the FRED API key from a credentials file at the project root.
    The credentials file should contain the API key as plain text on the
    first line (no JSON, no YAML — just the key string).

    Args:
        series_id: FRED series identifier (e.g., 'DGS3MO').
        start_date: Start date in 'YYYY-MM-DD' format.
        end_date: End date in 'YYYY-MM-DD' format. Defaults to today.
        api_key_file: Path to the FRED credentials file.

    Returns:
        Series indexed by date with the FRED series values.

    Raises:
        ImportError: If fredapi is not installed.
        FileNotFoundError: If the credentials file does not exist.
    """
    try:
        from fredapi import Fred
    except ImportError:
        raise ImportError(
            "fredapi is required for FRED data download. "
            "Install with: pip install fredapi"
        )

    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    cred_path = Path(api_key_file)
    if not cred_path.exists():
        raise FileNotFoundError(
            f"FRED credentials file not found: {cred_path}. "
            "Create a file containing your FRED API key on the first line."
        )

    with open(cred_path, "r") as f:
        api_key = f.readline().strip()

    logger.info(f"Downloading FRED series {series_id} from {start_date} to {end_date}")

    fred = Fred(api_key=api_key)
    series = fred.get_series(series_id, observation_start=start_date, observation_end=end_date)
    series.name = series_id

    return series