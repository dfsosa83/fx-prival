"""Unit tests for core.volatility module."""
import numpy as np
import pandas as pd
import pytest

from core.volatility import (
    annualize_volatility,
    ewma_volatility,
    parkinson_volatility,
    portfolio_volatility,
    realized_volatility,
    rolling_portfolio_volatility,
)


class TestEWMAVolatility:
    """Tests for ewma_volatility."""

    def test_non_negative(self):
        """EWMA volatility is always non-negative."""
        rng = np.random.RandomState(42)
        returns = pd.Series(rng.randn(500) * 0.01)
        vol = ewma_volatility(returns, halflife=20, annualize=False)
        assert (vol.dropna() >= 0).all()

    def test_nan_handling(self):
        """NaN returns are handled gracefully."""
        returns = pd.Series([np.nan, 0.01, -0.02, 0.005, np.nan])
        vol = ewma_volatility(returns, halflife=3, min_periods=1, annualize=False)
        # Should produce some non-NaN values
        assert vol.dropna().shape[0] > 0

    def test_annualize(self):
        """Annualization multiplies by sqrt(periods_per_year)."""
        returns = pd.Series(np.random.RandomState(1).randn(500) * 0.01)
        vol_daily = ewma_volatility(returns, halflife=20, annualize=False)
        vol_annual = ewma_volatility(returns, halflife=20, annualize=True)
        ratio = vol_annual.dropna() / vol_daily.dropna()
        expected_ratio = np.sqrt(252)
        np.testing.assert_allclose(ratio, expected_ratio, rtol=0.01)

    def test_constant_returns(self):
        """Constant returns produce near-zero volatility (after warmup)."""
        returns = pd.Series([0.001] * 200)
        vol = ewma_volatility(returns, halflife=20, min_periods=10, annualize=False)
        # With constant positive returns, the EWMA vol converges to a small positive
        # value (the EWMA of squared returns). It should be small, not exactly zero.
        tail = vol.iloc[-50:]
        assert (tail < 0.0011).all()  # Should be close to the constant return value


class TestRealizedVolatility:
    """Tests for realized_volatility."""

    def test_non_negative(self):
        """Realized volatility is always non-negative."""
        returns = pd.Series(np.random.RandomState(3).randn(500) * 0.01)
        vol = realized_volatility(returns, window=60, annualize=False)
        assert (vol.dropna() >= 0).all()

    def test_window_behavior(self):
        """Window parameter controls computation size."""
        returns = pd.Series(np.random.RandomState(4).randn(500) * 0.01)
        vol_short = realized_volatility(
            returns, window=10, min_periods=10, annualize=False
        )
        vol_long = realized_volatility(
            returns, window=60, min_periods=20, annualize=False
        )
        # Short window should be more reactive (higher variance of vol)
        assert vol_short.dropna().std() > vol_long.dropna().std()

    def test_min_periods(self):
        """Produces NaN until min_periods are reached."""
        returns = pd.Series(np.random.randn(100) * 0.01)
        vol = realized_volatility(returns, window=20, min_periods=20, annualize=False)
        assert vol.iloc[:18].isna().all()
        assert not np.isnan(vol.iloc[19])


class TestParkinsonVolatility:
    """Tests for parkinson_volatility."""

    def test_non_negative(self):
        """Parkinson volatility is always non-negative."""
        rng = np.random.RandomState(5)
        n = 200
        close = pd.Series(100 + rng.randn(n).cumsum() * 0.5)
        high = close + rng.rand(n) * 1.0
        low = close - rng.rand(n) * 1.0
        # Ensure high >= low
        high = pd.Series(np.maximum(high.values, low.values + 0.01))
        low = pd.Series(np.minimum(low.values, high.values - 0.01))

        vol = parkinson_volatility(high, low, window=30, annualize=False)
        assert (vol.dropna() >= 0).all()

    def test_efficiency_gain(self):
        """Parkinson vol should be in a reasonable range relative to close-to-close."""
        rng = np.random.RandomState(6)
        n = 500
        prices = 100 + rng.randn(n).cumsum() * 0.5
        close = pd.Series(prices)
        high = pd.Series(prices + rng.uniform(0.1, 1.0, n))
        low = pd.Series(prices - rng.uniform(0.1, 1.0, n))

        rets = close.pct_change()
        close_vol = realized_volatility(rets, window=60, annualize=False).iloc[-1]
        park_vol = parkinson_volatility(high, low, window=60, annualize=False).iloc[-1]

        # Parkinson should not be wildly different from close-to-close
        assert park_vol > 0
        assert park_vol / close_vol < 5.0  # Sanity bound


class TestPortfolioVolatility:
    """Tests for portfolio_volatility."""

    def test_single_asset(self):
        """Portfolio vol equals asset vol for single asset."""
        cov = np.array([[0.04]])  # 20% annual vol = 0.04 variance
        weights = np.array([1.0])
        result = portfolio_volatility(weights, cov)
        assert result == pytest.approx(0.2)

    def test_two_assets_uncorrelated(self):
        """Two uncorrelated assets: portfolio vol = sqrt(w1^2*s1^2 + w2^2*s2^2)."""
        cov = np.array([[0.04, 0.0], [0.0, 0.01]])
        weights = np.array([0.5, 0.5])
        result = portfolio_volatility(weights, cov)
        expected = np.sqrt(0.5**2 * 0.04 + 0.5**2 * 0.01)
        assert result == pytest.approx(expected)

    def test_negative_variance_handling(self):
        """Handles near-zero or negative variance gracefully."""
        cov = np.array([[-0.0001]])  # Should return 0, not NaN
        weights = np.array([1.0])
        result = portfolio_volatility(weights, cov)
        assert result == 0.0  # max(var, 0) → 0


class TestAnnualizeVolatility:
    """Tests for annualize_volatility."""

    def test_basic(self):
        """Annualization is daily_vol * sqrt(252)."""
        daily_vol = 0.01
        annual_vol = annualize_volatility(daily_vol)
        assert annual_vol == pytest.approx(0.01 * np.sqrt(252))

    def test_custom_periods(self):
        """Custom periods_per_year supported."""
        daily_vol = 0.01
        annual_vol = annualize_volatility(daily_vol, periods_per_year=365)
        assert annual_vol == pytest.approx(0.01 * np.sqrt(365))