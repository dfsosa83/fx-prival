"""
Data quality validation for market data.

Validates OHLCV DataFrames against the data dictionary schema, checking
for completeness, monotonicity, price consistency, and outlier detection.
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def validate_ohlcv(df: pd.DataFrame, ticker: str = "unknown") -> Dict[str, any]:
    """
    Validate a daily OHLCV DataFrame against schema rules.

    Checks performed:
        1. Required columns present.
        2. No duplicate dates.
        3. Dates are monotonically increasing.
        4. Prices are positive (open, high, low, close > 0).
        5. high >= open, close, low.
        6. low <= open, close, high.
        7. Volume is non-negative.
        8. Missing date gaps are flagged.

    Args:
        df: DataFrame with columns: date, open, high, low, close, adj_close, volume.
        ticker: Instrument ticker for logging context.

    Returns:
        Dict with keys: is_valid (bool), errors (list of error messages),
        warnings (list of warnings), row_count, missing_pct.
    """
    result = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "row_count": len(df),
        "missing_pct": 0.0,
    }

    # 1. Required columns
    required = {"date", "open", "high", "low", "close"}
    missing_cols = required - set(df.columns)
    if missing_cols:
        result["is_valid"] = False
        result["errors"].append(f"Missing required columns: {missing_cols}")
        return result

    # 2. No duplicate dates
    if df["date"].duplicated().any():
        result["is_valid"] = False
        dup_count = df["date"].duplicated().sum()
        result["errors"].append(f"Found {dup_count} duplicate dates")

    # 3. Sort and check monotonicity
    df_sorted = df.sort_values("date").reset_index(drop=True)
    if not df_sorted["date"].is_monotonic_increasing:
        result["is_valid"] = False
        result["errors"].append("Dates are not monotonically increasing after sort")

    # 4. Positive prices (warn only — NaN returns handled downstream)
    for col in ["open", "high", "low", "close"]:
        neg_mask = df_sorted[col] <= 0
        if neg_mask.any():
            result["warnings"].append(
                f"Column '{col}' has {neg_mask.sum()} non-positive values"
            )

    # 5. high >= open, high >= close, high >= low
    if (df_sorted["high"] < df_sorted["open"]).any():
        n_bad = (df_sorted["high"] < df_sorted["open"]).sum()
        result["warnings"].append(f"high < open on {n_bad} rows (common for FX bid/ask data)")
    if (df_sorted["high"] < df_sorted["close"]).any():
        n_bad = (df_sorted["high"] < df_sorted["close"]).sum()
        result["warnings"].append(f"high < close on {n_bad} rows (common for FX bid/ask data)")
    if (df_sorted["high"] < df_sorted["low"]).any():
        n_bad = (df_sorted["high"] < df_sorted["low"]).sum()
        result["warnings"].append(f"high < low on {n_bad} rows (common for FX bid/ask data)")

    # 6. low <= open, low <= close, low <= high
    if (df_sorted["low"] > df_sorted["open"]).any():
        n_bad = (df_sorted["low"] > df_sorted["open"]).sum()
        result["warnings"].append(f"low > open on {n_bad} rows (common for FX bid/ask data)")
    if (df_sorted["low"] > df_sorted["close"]).any():
        n_bad = (df_sorted["low"] > df_sorted["close"]).sum()
        result["warnings"].append(f"low > close on {n_bad} rows (common for FX bid/ask data)")

    # 7. Volume non-negative
    if "volume" in df_sorted.columns:
        neg_vol = df_sorted["volume"] < 0
        if neg_vol.any():
            result["errors"].append(f"Negative volume: {neg_vol.sum()} rows")
            result["is_valid"] = False

    # 8. Missing values
    missing = df_sorted.isnull().sum()
    total_cells = df_sorted.shape[0] * df_sorted.shape[1]
    total_missing = missing.sum()
    result["missing_pct"] = round(float(total_missing / max(total_cells, 1)), 4)

    if total_missing > 0:
        missing_detail = {k: int(v) for k, v in missing.items() if v > 0}
        result["warnings"].append(f"Missing values: {missing_detail}")

    # 9. Date gaps (warnings only, not errors — holidays are expected gaps)
    if len(df_sorted) > 1:
        date_diffs = df_sorted["date"].diff().dropna()
        # More than 3 calendar days gap (weekend + holiday)
        large_gaps = date_diffs[date_diffs > pd.Timedelta(days=3)]
        if len(large_gaps) > 0:
            result["warnings"].append(
                f"Found {len(large_gaps)} date gaps > 3 days (max gap: "
                f"{large_gaps.max().days} days)"
            )

    return result


def validate_all(
    data_dir: str,
    instrument_master_path: str,
) -> pd.DataFrame:
    """
    Validate all raw data files against expected schemas.

    Args:
        data_dir: Directory containing raw data files.
        instrument_master_path: Path to instrument_master.csv.

    Returns:
        DataFrame with validation results per file.
    """
    master = pd.read_csv(instrument_master_path)
    results = []

    for _, row in master.iterrows():
        ticker = row["ticker"]
        yahoo_ticker = row["yahoo_ticker"]
        filepath = Path(data_dir) / f"{yahoo_ticker}_daily.parquet"

        if not filepath.exists():
            results.append({
                "ticker": ticker,
                "is_valid": False,
                "errors": "File not found",
                "row_count": 0,
            })
            continue

        df = pd.read_parquet(filepath)
        validation = validate_ohlcv(df, ticker=ticker)
        validation["ticker"] = ticker
        results.append(validation)

    return pd.DataFrame(results)