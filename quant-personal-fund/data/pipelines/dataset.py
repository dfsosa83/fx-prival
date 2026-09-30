"""
Dataset registry for reproducible data management.

Provides functions to load, validate, align, and register daily OHLCV
data with immutable metadata including SHA256 hashes and validation
results. The dataset metadata serves as the provenance record for
every backtest and experiment.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from core.hashing import hash_file
from data.pipelines.validate import validate_ohlcv

logger = logging.getLogger(__name__)


@dataclass
class DatasetMetadata:
    """Immutable metadata for a loaded and validated dataset."""
    dataset_id: str
    instruments: List[str]
    date_range_start: str
    date_range_end: str
    row_counts: Dict[str, int]
    missing_pct: Dict[str, float]
    validation_errors: int
    total_validation_warnings: int
    inputs_hash: str
    created_at: str


def load_and_validate(
    data_dir: str,
    instrument_master,  # InstrumentMaster instance
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[pd.DataFrame, DatasetMetadata]:
    """
    Load, validate, align, and register a dataset from raw parquet files.

    For each active instrument in the instrument master:
        1. Load raw parquet file.
        2. Validate against OHLCV schema.
        3. Extract adjusted close prices.
        4. Align to a common date index.

    Government bond instruments (govt_bond) are loaded as yield series
    and require conversion to returns via core.returns.yield_to_price.
    This function loads and validates the raw yield data; conversion is
    handled downstream.

    Args:
        data_dir: Directory containing raw parquet files.
        instrument_master: InstrumentMaster instance with active instruments.
        start_date: Optional start date filter.
        end_date: Optional end date filter.

    Returns:
        Tuple of (prices_df, metadata).
        prices_df: DataFrame (dates × tickers) of adjusted close prices.
        metadata: DatasetMetadata with provenance information.

    Raises:
        ValueError: If no instruments have data.
    """
    active_tickers = instrument_master.tickers(active_only=True)
    if not active_tickers:
        raise ValueError("No active instruments in the instrument master")

    prices_dict: Dict[str, pd.Series] = {}
    row_counts: Dict[str, int] = {}
    missing_pct_dict: Dict[str, float] = {}
    total_validation_errors = 0
    total_validation_warnings = 0
    file_hashes: List[str] = []
    loaded_instruments: List[str] = []

    for ticker in active_tickers:
        yahoo_ticker = instrument_master.yahoo_ticker(ticker)
        filepath = Path(data_dir) / f"{yahoo_ticker}_daily.parquet"

        if not filepath.exists():
            logger.warning(f"Data file not found for {ticker}: {filepath}")
            continue

        # Hash the raw file for provenance
        file_hashes.append(hash_file(filepath))

        # Load and validate
        df = pd.read_parquet(filepath)
        validation = validate_ohlcv(df, ticker=ticker)

        row_counts[ticker] = validation["row_count"]
        missing_pct_dict[ticker] = validation["missing_pct"]
        total_validation_errors += len(validation["errors"])
        total_validation_warnings += len(validation["warnings"])

        if not validation["is_valid"]:
            logger.error(
                f"Validation failed for {ticker}: {validation['errors']}"
            )
            continue

        # Extract price series (prefer adjusted close)
        if "adj_close" in df.columns and df["adj_close"].notna().any():
            prices = df.set_index("date")["adj_close"]
        elif "close" in df.columns:
            prices = df.set_index("date")["close"]
        else:
            logger.error(f"No price column found for {ticker}")
            continue

        # Normalize dates: strip timezone, keep date only
        prices.index = pd.to_datetime(prices.index).tz_localize(None).normalize()
        # Drop duplicate dates (keep last)
        prices = prices[~prices.index.duplicated(keep="last")]

        prices.name = ticker
        if start_date is not None:
            prices = prices[prices.index >= pd.Timestamp(start_date)]
        if end_date is not None:
            prices = prices[prices.index <= pd.Timestamp(end_date)]

        if len(prices) > 0:
            prices_dict[ticker] = prices
            loaded_instruments.append(ticker)

    if not prices_dict:
        raise ValueError("No valid instrument data loaded")

    # Align to common date index
    prices_df = pd.DataFrame(prices_dict).sort_index()

    # Compute dataset hash from file hashes
    inputs_hash = hash_file.__self__ if False else ""  # noqa
    import hashlib
    combined = "|".join(sorted(file_hashes))
    inputs_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]

    date_range_start = str(prices_df.index.min().date())
    date_range_end = str(prices_df.index.max().date())

    metadata = DatasetMetadata(
        dataset_id=f"universe_daily_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        instruments=sorted(loaded_instruments),
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        row_counts=row_counts,
        missing_pct=missing_pct_dict,
        validation_errors=total_validation_errors,
        total_validation_warnings=total_validation_warnings,
        inputs_hash=inputs_hash,
        created_at=datetime.now().isoformat(),
    )

    return prices_df, metadata


def register_dataset(metadata: DatasetMetadata, output_path: str) -> str:
    """
    Write dataset metadata to a JSON file.

    Args:
        metadata: DatasetMetadata instance.
        output_path: Directory or file path for the metadata JSON.

    Returns:
        Path to the written metadata file.
    """
    path = Path(output_path)
    if path.is_dir():
        path = path / f"{metadata.dataset_id}_metadata.json"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as f:
        json.dump(asdict(metadata), f, indent=2, default=str)

    logger.info(f"Dataset metadata registered: {path}")
    return str(path)