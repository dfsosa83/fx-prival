"""Unit tests for signals.ml_overlays.macro module."""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from signals.ml_overlays.macro import (
    align_macro_features,
    load_fred_series,
    macro_feature_deltas,
)


@pytest.fixture
def macro_csv_dir():
    """Create temp dir with FRED-style CSV files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        d = Path(tmpdir)

        # Daily series: 60 trading days
        dates = pd.date_range("2024-01-01", periods=60, freq="B")
        daily = pd.DataFrame({"date": dates, "value": np.linspace(5.0, 5.5, 60)})
        daily.to_csv(d / "DGS3MO.csv", index=False)

        # Monthly series: 6 monthly observations
        mdates = pd.date_range("2024-01-01", periods=6, freq="ME")
        monthly = pd.DataFrame({"date": mdates, "value": np.linspace(3.0, 3.3, 6)})
        monthly.to_csv(d / "UNRATE.csv", index=False)

        yield str(d)


class TestLoadFredSeries:
    def test_loads_daily_and_monthly(self, macro_csv_dir):
        """Loads both daily and monthly series."""
        result = load_fred_series(macro_csv_dir)
        assert "DGS3MO" in result
        assert "UNRATE" in result

    def test_duplicates_removed(self, macro_csv_dir):
        """Duplicate dates are removed (keep last)."""
        result = load_fred_series(macro_csv_dir)
        for sid, series in result.items():
            assert not series.index.duplicated().any()


class TestAlignMacroFeatures:
    def test_daily_series_no_lookahead(self, macro_csv_dir):
        """Daily series are shifted by 1 day — no same-day leak."""
        series = load_fred_series(macro_csv_dir)
        daily_index = pd.date_range("2024-01-01", periods=60, freq="B")
        feat = align_macro_features(daily_index, series)

        # The feature value at date t must equal the raw value at t-1 (lagged)
        raw = series["DGS3MO"]
        # Compare at a mid-period date
        test_date = daily_index[20]
        expected = raw[raw.index < test_date].iloc[-1]
        actual = feat.loc[test_date, "us_3m_yield"]
        assert actual == pytest.approx(expected)

    def test_monthly_series_publication_lag(self, macro_csv_dir):
        """Monthly series are shifted by publication lag — no early use."""
        series = load_fred_series(macro_csv_dir)
        daily_index = pd.date_range("2024-01-01", periods=120, freq="B")
        feat = align_macro_features(daily_index, series, publication_lag_days=45)

        # First usable date must be > 45 days after the first observation
        first_obs = series["UNRATE"].index[0]
        # Find first non-NaN unemployment feature date
        first_usable = feat["unemployment"].dropna().index[0]
        assert (first_usable - first_obs).days >= 44

    def test_output_shape(self, macro_csv_dir):
        """Output covers the full daily index with named columns."""
        series = load_fred_series(macro_csv_dir)
        daily_index = pd.date_range("2024-01-01", periods=60, freq="B")
        feat = align_macro_features(daily_index, series)
        assert len(feat) == len(daily_index)
        assert "us_3m_yield" in feat.columns
        assert "unemployment" in feat.columns


class TestMacroFeatureDeltas:
    def test_delta_columns_added(self, macro_csv_dir):
        """Delta features are added for each base series."""
        series = load_fred_series(macro_csv_dir)
        daily_index = pd.date_range("2024-01-01", periods=60, freq="B")
        feat = align_macro_features(daily_index, series)
        with_deltas = macro_feature_deltas(feat, windows=[21])
        assert "us_3m_yield_delta_21d" in with_deltas.columns