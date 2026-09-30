"""Unit tests for data.pipelines.validate module."""
import pandas as pd
import pytest

from data.pipelines.validate import validate_ohlcv


class TestValidateOHLCV:
    """Tests for validate_ohlcv."""

    @pytest.fixture
    def valid_df(self):
        """Create a valid OHLCV DataFrame."""
        return pd.DataFrame({
            "date": pd.date_range("2026-01-05", periods=5, freq="B"),
            "open": [100.0, 101.0, 102.0, 101.5, 103.0],
            "high": [102.0, 103.0, 104.0, 103.0, 105.0],
            "low": [99.0, 100.0, 101.0, 100.5, 102.0],
            "close": [101.0, 102.0, 101.5, 103.0, 104.0],
            "adj_close": [101.0, 102.0, 101.5, 103.0, 104.0],
            "volume": [1000, 1200, 900, 1100, 1300],
        })

    def test_valid_data_passes(self, valid_df):
        """Valid data produces is_valid=True with no errors."""
        result = validate_ohlcv(valid_df, ticker="TEST")
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_missing_columns(self):
        """Missing required columns produce errors."""
        df = pd.DataFrame({"date": [], "open": []})
        result = validate_ohlcv(df)
        assert result["is_valid"] is False
        assert any("Missing required columns" in e for e in result["errors"])

    def test_duplicate_dates(self, valid_df):
        """Duplicate dates produce errors."""
        df = pd.concat([valid_df, valid_df.iloc[[0]]])
        result = validate_ohlcv(df)
        assert result["is_valid"] is False
        assert any("duplicate dates" in e.lower() for e in result["errors"])

    def test_negative_prices(self, valid_df):
        """Negative prices produce warnings."""
        df = valid_df.copy()
        df.loc[0, "close"] = -1.0
        result = validate_ohlcv(df)
        assert any("non-positive" in w for w in result["warnings"])

    def test_high_less_than_low(self, valid_df):
        """high < low produces warnings (common for FX bid/ask data)."""
        df = valid_df.copy()
        df.loc[0, "high"] = 98.0  # Below low=99.0
        result = validate_ohlcv(df)
        assert any("high < low" in w for w in result["warnings"])

    def test_missing_values_warning(self, valid_df):
        """Missing values produce warnings, not errors."""
        df = valid_df.copy()
        df.loc[0, "adj_close"] = None
        result = validate_ohlcv(df)
        assert result["is_valid"] is True  # adj_close is optional
        assert any("Missing values" in w for w in result["warnings"])

    def test_row_count(self, valid_df):
        """row_count matches DataFrame length."""
        result = validate_ohlcv(valid_df)
        assert result["row_count"] == 5

    def test_missing_pct(self, valid_df):
        """missing_pct is computed correctly."""
        result = validate_ohlcv(valid_df)
        assert result["missing_pct"] == 0.0

        df = valid_df.copy()
        df.loc[0, "volume"] = None
        result = validate_ohlcv(df)
        assert result["missing_pct"] > 0.0