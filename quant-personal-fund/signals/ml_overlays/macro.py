"""
Macro-economic features from FRED for ML overlays.

Aligns FRED macro series to the daily market panel with strict
look-ahead safety:

    Daily series (DGS3MO, DGS10, T10Y3M, VIXCLS):
        Observed at close of date t. Lagged by 1 day before use —
        a feature at date t uses macro data known at close of t-1.

    Monthly series (CPIAUCSL, UNRATE):
        Reference period is the calendar month, but the release occurs
        ~2-3 weeks into the FOLLOWING month. We shift the observation
        forward by `publication_lag_days` (default 45) before
        forward-filling, guaranteeing the feature is knowable at the
        date it is used.

No macro feature ever uses information that would not have been
available at the feature date.
"""

from pathlib import Path
from typing import Dict, Optional

import pandas as pd


# Series classification: daily (no publication lag beyond 1 day) vs monthly
DAILY_SERIES = {"DGS3MO", "DGS10", "T10Y3M", "VIXCLS"}
MONTHLY_SERIES = {"CPIAUCSL", "UNRATE"}

# Human-readable names
SERIES_NAMES = {
    "DGS3MO": "us_3m_yield",
    "DGS10": "us_10y_yield",
    "T10Y3M": "us_10y3m_spread",
    "VIXCLS": "vix_close",
    "CPIAUCSL": "cpi",
    "UNRATE": "unemployment",
}


def load_fred_series(
    data_dir: str,
    series_ids: Optional[list] = None,
) -> Dict[str, pd.Series]:
    """
    Load FRED series from CSV files into date-indexed Series.

    Args:
        data_dir: Directory containing {SERIES_ID}.csv files.
        series_ids: List of series IDs to load. Default: all six.

    Returns:
        Dict mapping series ID to pd.Series (date → value).
    """
    if series_ids is None:
        series_ids = list(DAILY_SERIES | MONTHLY_SERIES)

    result = {}
    for sid in series_ids:
        path = Path(data_dir) / f"{sid}.csv"
        if not path.exists():
            continue
        df = pd.read_csv(path, parse_dates=["date"])
        df = df.dropna()
        series = df.set_index("date")["value"].astype(float)
        series = series[~series.index.duplicated(keep="last")]
        result[sid] = series
    return result


def align_macro_features(
    daily_index: pd.DatetimeIndex,
    series_dict: Dict[str, pd.Series],
    publication_lag_days: int = 45,
) -> pd.DataFrame:
    """
    Align macro series to a daily index with look-ahead safety.

    Daily series: reindex to daily index, shift by 1 day (close of t-1),
                 then forward-fill.
    Monthly series: shift observations forward by `publication_lag_days`,
                 reindex to daily, forward-fill.

    Args:
        daily_index: Target daily DatetimeIndex (e.g., the market panel index).
        series_dict: Dict from load_fred_series().
        publication_lag_days: Buffer for monthly series publication lag.

    Returns:
        DataFrame (daily_index × macro_feature_names) with no look-ahead.
    """
    features = pd.DataFrame(index=daily_index)

    for sid, series in series_dict.items():
        col = SERIES_NAMES.get(sid, sid)

        if sid in DAILY_SERIES:
            # Close of date t is usable for features at date t+1
            lagged = series.shift(1)
            aligned = lagged.reindex(daily_index).ffill()
        elif sid in MONTHLY_SERIES:
            # Shift by publication lag to guarantee knowability
            shifted = series.shift(1)  # observation month is known next month
            shifted.index = shifted.index + pd.Timedelta(days=publication_lag_days)
            aligned = shifted.reindex(daily_index).ffill()
        else:
            continue

        # Keep only dates on/before the last available macro observation
        last_known = series.index[-1] if len(series) > 0 else daily_index[0]
        features[col] = aligned

    return features


def macro_feature_deltas(
    macro_features: pd.DataFrame,
    windows: Optional[list] = None,
) -> pd.DataFrame:
    """
    Add delta/momentum features for macro series.

    The level of a macro series is persistent and non-stationary.
    Changes (deltas) over short windows carry regime information
    (e.g., rising unemployment, steepening curve).

    Args:
        macro_features: DataFrame from align_macro_features().
        windows: Change windows in days.

    Returns:
        DataFrame with original levels + delta features.
    """
    if windows is None:
        windows = [21, 63]

    result = macro_features.copy()
    for col in macro_features.columns:
        for w in windows:
            result[f"{col}_delta_{w}d"] = macro_features[col].diff(w)
    return result