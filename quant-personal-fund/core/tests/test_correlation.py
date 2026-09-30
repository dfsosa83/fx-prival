"""Unit tests for core.correlation module."""
import numpy as np
import pandas as pd
import pytest

from core.correlation import (
    ewma_correlation,
    pearson_correlation,
    rolling_correlation,
    shrinkage_correlation,
    spearman_correlation,
)


@pytest.fixture
def uncorrelated_returns():
    """Two independent return series."""
    rng = np.random.RandomState(42)
    n = 500
    return pd.DataFrame({
        "A": rng.randn(n) * 0.01,
        "B": rng.randn(n) * 0.01,
    })


@pytest.fixture
def correlated_returns():
    """Two correlated return series."""
    rng = np.random.RandomState(43)
    n = 500
    x = rng.randn(n) * 0.01
    y = 0.7 * x + 0.3 * rng.randn(n) * 0.01
    return pd.DataFrame({"A": x, "B": y})


@pytest.fixture
def multi_asset_returns():
    """5-asset return panel."""
    rng = np.random.RandomState(44)
    n = 300
    return pd.DataFrame(
        {f"ASSET_{i}": rng.randn(n) * 0.01 for i in range(5)},
        index=pd.date_range("2020-01-01", periods=n, freq="B"),
    )


class TestPearsonCorrelation:
    def test_identity(self):
        """Correlation of an asset with itself is 1.0."""
        returns = pd.DataFrame({"A": np.random.randn(100) * 0.01})
        corr = pearson_correlation(returns)
        assert corr.loc["A", "A"] == pytest.approx(1.0)

    def test_perfect_negative(self):
        """Negated series: correlation = -1.0."""
        rng = np.random.RandomState(1)
        x = rng.randn(100)
        returns = pd.DataFrame({"A": x, "B": -x})
        corr = pearson_correlation(returns)
        assert corr.loc["A", "B"] == pytest.approx(-1.0)

    def test_uncorrelated(self, uncorrelated_returns):
        """Independent series have near-zero correlation."""
        corr = pearson_correlation(uncorrelated_returns)
        assert abs(corr.loc["A", "B"]) < 0.15

    def test_correlated_detected(self, correlated_returns):
        """Correlation is detected for dependent series."""
        corr = pearson_correlation(correlated_returns)
        assert corr.loc["A", "B"] > 0.5

    def test_symmetric(self, multi_asset_returns):
        """Correlation matrix is symmetric."""
        corr = pearson_correlation(multi_asset_returns)
        np.testing.assert_array_almost_equal(corr.values, corr.values.T)

    def test_diagonal_is_one(self, multi_asset_returns):
        """Diagonal entries are 1.0."""
        corr = pearson_correlation(multi_asset_returns)
        for i in range(5):
            assert corr.iloc[i, i] == pytest.approx(1.0)


class TestSpearmanCorrelation:
    def test_monotonic(self):
        """Spearman detects monotonic (nonlinear) relationship."""
        rng = np.random.RandomState(2)
        x = rng.randn(200)
        y = np.sign(x) * np.abs(x) ** 0.5  # Non-linear but monotonic
        returns = pd.DataFrame({"A": x, "B": y})
        corr = spearman_correlation(returns)
        assert abs(corr.loc["A", "B"]) > 0.7


class TestEWMACorrelation:
    def test_produces_valid_matrix(self, multi_asset_returns):
        """EWMA produces a valid correlation matrix."""
        corr = ewma_correlation(multi_asset_returns)
        assert corr.shape == (5, 5)
        for i in range(5):
            assert corr.iloc[i, i] == pytest.approx(1.0)

    def test_symmetric(self, multi_asset_returns):
        """EWMA correlation matrix is symmetric."""
        corr = ewma_correlation(multi_asset_returns)
        np.testing.assert_array_almost_equal(corr.values, corr.values.T)


class TestShrinkageCorrelation:
    def test_identity_with_full_shrinkage(self, multi_asset_returns):
        """shrinkage=1.0 produces identity matrix."""
        corr = shrinkage_correlation(multi_asset_returns, shrinkage=1.0)
        np.testing.assert_array_almost_equal(corr.values, np.eye(5))

    def test_sample_with_zero_shrinkage(self, multi_asset_returns):
        """shrinkage=0.0 matches Pearson."""
        shrunk = shrinkage_correlation(multi_asset_returns, shrinkage=0.0)
        pearson = pearson_correlation(multi_asset_returns)
        np.testing.assert_array_almost_equal(shrunk.values, pearson.values)

    def test_shrinkage_reduces_extremes(self, multi_asset_returns):
        """Shrinkage pulls extreme correlations toward zero."""
        pearson = pearson_correlation(multi_asset_returns)
        shrunk = shrinkage_correlation(multi_asset_returns, shrinkage=0.3)
        off_diag_pearson = pearson.values[~np.eye(5, dtype=bool)]
        off_diag_shrunk = shrunk.values[~np.eye(5, dtype=bool)]
        assert off_diag_shrunk.std() < off_diag_pearson.std()


class TestRollingCorrelation:
    def test_pairwise(self, correlated_returns):
        """Rolling correlation for a pair produces a series."""
        corr = rolling_correlation(correlated_returns, window=60, pairwise=True)
        assert isinstance(corr, pd.Series)
        assert len(corr.dropna()) > 0

    def test_full_matrix(self, multi_asset_returns):
        """Rolling full matrix produces MultiIndex DataFrame."""
        corr = rolling_correlation(multi_asset_returns, window=60)
        assert isinstance(corr, pd.DataFrame)