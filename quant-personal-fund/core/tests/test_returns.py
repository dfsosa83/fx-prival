"""Unit tests for core.returns module."""
import numpy as np
import pandas as pd
import pytest

from core.returns import (
    align_returns,
    cumulative_returns,
    excess_returns,
    log_returns,
    returns_from_dataframe,
    simple_returns,
)


class TestSimpleReturns:
    """Tests for simple_returns."""

    def test_basic(self):
        """Simple returns are computed correctly."""
        prices = pd.Series([100.0, 102.0, 101.0, 105.0], name="close")
        result = simple_returns(prices)

        assert len(result) == 4
        assert np.isnan(result.iloc[0])
        assert result.iloc[1] == pytest.approx(0.02)  # (102-100)/100
        assert result.iloc[2] == pytest.approx(-0.0098039, rel=1e-4)  # (101-102)/102
        assert result.iloc[3] == pytest.approx(0.0396039, rel=1e-4)  # (105-101)/101

    def test_short_series(self):
        """Returns NaN when series is too short."""
        prices = pd.Series([100.0])
        result = simple_returns(prices)
        assert np.isnan(result.iloc[0])

    def test_multi_period(self):
        """Multi-period returns with periods=2."""
        prices = pd.Series([100.0, 102.0, 105.0])
        result = simple_returns(prices, periods=2)
        assert np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])
        assert result.iloc[2] == pytest.approx(0.05)  # (105-100)/100


class TestLogReturns:
    """Tests for log_returns."""

    def test_basic(self):
        """Log returns are computed correctly."""
        prices = pd.Series([100.0, 102.0, 101.0])
        result = log_returns(prices)

        assert np.isnan(result.iloc[0])
        assert result.iloc[1] == pytest.approx(np.log(102.0 / 100.0))
        assert result.iloc[2] == pytest.approx(np.log(101.0 / 102.0))

    def test_log_vs_simple_approx(self):
        """Log and simple returns are close for small moves."""
        prices = pd.Series([100.0, 100.5, 101.0, 99.8])
        simple = simple_returns(prices)
        logs = log_returns(prices)

        for i in range(1, len(prices)):
            if not np.isnan(simple.iloc[i]):
                # For small returns, log ≈ simple
                assert abs(logs.iloc[i] - simple.iloc[i]) < 0.001

    def test_zero_price(self):
        """Zero price produces NaN return, not inf."""
        prices = pd.Series([0.0, 100.0])
        result = log_returns(prices)
        assert np.isnan(result.iloc[0])
        assert np.isnan(result.iloc[1])  # log(100/0) is -inf → NaN

    def test_negative_price(self):
        """Negative price produces NaN return."""
        prices = pd.Series([-1.0, 100.0])
        result = log_returns(prices)
        assert np.isnan(result.iloc[1])


class TestExcessReturns:
    """Tests for excess_returns."""

    def test_constant_risk_free_rate(self):
        """Excess returns subtract constant annual risk-free rate."""
        returns = pd.Series([0.001, 0.002, -0.001])
        rf_annual = 0.03  # 3%
        rf_daily = rf_annual / 252

        result = excess_returns(returns, annual_rf=rf_annual)
        assert result.iloc[0] == pytest.approx(0.001 - rf_daily)
        assert result.iloc[1] == pytest.approx(0.002 - rf_daily)

    def test_series_risk_free_rate(self):
        """Excess returns with time-varying risk-free rate."""
        returns = pd.Series([0.001, 0.002], index=[0, 1])
        rf_series = pd.Series([0.0001, 0.0002], index=[0, 1])

        result = excess_returns(returns, risk_free_rate=rf_series)
        assert result.iloc[0] == pytest.approx(0.001 - 0.0001)
        assert result.iloc[1] == pytest.approx(0.002 - 0.0002)

    def test_zero_risk_free(self):
        """Excess returns equal raw returns with zero risk-free rate."""
        returns = pd.Series([0.001, 0.002, -0.001])
        result = excess_returns(returns, annual_rf=0.0)
        pd.testing.assert_series_equal(result, returns, check_names=False)


class TestReturnsFromDataframe:
    """Tests for returns_from_dataframe."""

    def test_prefers_adj_close(self):
        """Uses adj_close when available."""
        df = pd.DataFrame({
            "adj_close": [100.0, 102.0, 101.0],
            "close": [99.0, 101.0, 100.0],
        })
        result = returns_from_dataframe(df, method="log")
        # Should use adj_close
        expected = log_returns(pd.Series([100.0, 102.0, 101.0]))
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_falls_back_to_close(self):
        """Falls back to close when adj_close is missing."""
        df = pd.DataFrame({
            "close": [99.0, 101.0, 100.0],
        })
        result = returns_from_dataframe(df, method="simple")
        expected = simple_returns(pd.Series([99.0, 101.0, 100.0]))
        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_missing_columns_raises(self):
        """Raises ValueError when no price columns exist."""
        df = pd.DataFrame({"open": [100.0], "high": [102.0]})
        with pytest.raises(ValueError, match="Neither"):
            returns_from_dataframe(df)


class TestAlignReturns:
    """Tests for align_returns."""

    def test_inner_join(self):
        """Inner join keeps only common dates."""
        r1 = pd.Series([0.01, 0.02], index=pd.date_range("2026-01-01", periods=2))
        r2 = pd.Series([0.03, 0.04], index=pd.date_range("2026-01-02", periods=2))
        result = align_returns({"A": r1, "B": r2}, method="inner")
        assert len(result) == 1  # Only 2026-01-02 is common

    def test_outer_join(self):
        """Outer join keeps all dates."""
        r1 = pd.Series([0.01], index=pd.date_range("2026-01-01", periods=1))
        r2 = pd.Series([0.03], index=pd.date_range("2026-01-03", periods=1))
        result = align_returns({"A": r1, "B": r2}, method="outer")
        assert len(result) == 2


class TestCumulativeReturns:
    """Tests for cumulative_returns."""

    def test_flat_returns(self):
        """Zero returns give zero cumulative return."""
        returns = pd.Series([0.0, 0.0, 0.0])
        result = cumulative_returns(returns)
        assert (result == 0.0).all()

    def test_positive_returns(self):
        """Cumulative return compounds correctly."""
        returns = pd.Series([0.01, 0.02])
        result = cumulative_returns(returns)
        # (1+0.01)*(1+0.02) - 1 = 0.0302
        assert result.iloc[1] == pytest.approx(0.0302)

    def test_nan_handling(self):
        """NaN returns are treated as zero in cumulative computation."""
        returns = pd.Series([np.nan, 0.01, np.nan, 0.02])
        result = cumulative_returns(returns)
        assert result.iloc[3] == pytest.approx(0.0302)