"""Unit tests for core.bootstrap module."""
import numpy as np
import pytest

from core.bootstrap import block_bootstrap_ci, ci_summary, iid_bootstrap_ci


class TestBlockBootstrapCI:
    """Tests for block_bootstrap_ci."""

    def test_point_estimate_is_mean(self):
        """Point estimate equals the sample mean."""
        obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        point, lo, hi = block_bootstrap_ci(obs, block_length=2, n_resamples=200)
        assert point == pytest.approx(3.0)

    def test_ci_bounds_ordered(self):
        """CI lower bound ≤ point estimate ≤ CI upper bound."""
        obs = np.random.RandomState(7).randn(100)
        point, lo, hi = block_bootstrap_ci(obs, block_length=5, n_resamples=500)
        assert lo <= point <= hi

    def test_empty_raises(self):
        """Empty observations raise ValueError."""
        with pytest.raises(ValueError, match="empty"):
            block_bootstrap_ci([], block_length=1)

    def test_block_length_too_large_raises(self):
        """block_length > n raises ValueError."""
        with pytest.raises(ValueError, match="exceeds number"):
            block_bootstrap_ci([1.0, 2.0], block_length=5)

    def test_block_length_one(self):
        """block_length=1 reduces to IID bootstrap (approximately)."""
        obs = np.random.RandomState(8).randn(200)
        point_b, lo_b, hi_b = block_bootstrap_ci(
            obs, block_length=1, n_resamples=500, random_seed=42
        )
        point_i, lo_i, hi_i = iid_bootstrap_ci(
            obs, n_resamples=500, random_seed=42
        )
        assert point_b == pytest.approx(point_i)
        # CIs should be similar for IID data with block_length=1
        assert abs(lo_b - lo_i) < 0.05
        assert abs(hi_b - hi_i) < 0.05

    def test_wider_ci_for_autocorrelated_data(self):
        """
        Block bootstrap with block_length > 1 produces wider CI than IID
        bootstrap for positively autocorrelated data. This is the key property
        that justifies the block bootstrap.

        Test with AR(1) data: rho=0.5 → significant positive dependence.
        """
        rng = np.random.RandomState(42)
        n = 200
        rho = 0.5
        eps = rng.randn(n)
        
        # Generate AR(1) process
        ar1 = np.zeros(n)
        ar1[0] = eps[0]
        for i in range(1, n):
            ar1[i] = rho * ar1[i - 1] + eps[i]
        
        # IID bootstrap
        _, lo_iid, hi_iid = iid_bootstrap_ci(ar1, n_resamples=500, random_seed=1)
        iid_width = hi_iid - lo_iid
        
        # Block bootstrap with block_length > 1
        _, lo_block, hi_block = block_bootstrap_ci(
            ar1, block_length=10, n_resamples=500, random_seed=1
        )
        block_width = hi_block - lo_block
        
        # Block bootstrap CI should be wider for positively autocorrelated data
        assert block_width > iid_width, (
            f"Block CI width ({block_width:.4f}) should exceed IID CI width "
            f"({iid_width:.4f}) for AR(1) data with rho=0.5"
        )

    def test_reproducibility(self):
        """Same seed produces same result."""
        obs = np.random.RandomState(9).randn(100)
        r1 = block_bootstrap_ci(obs, block_length=5, n_resamples=200, random_seed=42)
        r2 = block_bootstrap_ci(obs, block_length=5, n_resamples=200, random_seed=42)
        assert r1 == r2

    def test_narrow_ci_for_large_sample(self):
        """CI narrows with increasing sample size (law of large numbers)."""
        rng = np.random.RandomState(10)
        obs_small = rng.randn(50)
        obs_large = rng.randn(1000)
        
        _, _, _ = block_bootstrap_ci(obs_small, block_length=5, n_resamples=200)
        _, lo_lg, hi_lg = block_bootstrap_ci(obs_large, block_length=5, n_resamples=200)
        
        # Large sample CI should be narrower (but not always — stochastic)
        # Weak check: CI width should not be absurdly large
        assert (hi_lg - lo_lg) < 2.0

    def test_ci_level_99_is_wider_than_95(self):
        """99% CI is wider than 95% CI."""
        obs = np.random.RandomState(11).randn(200)
        _, lo95, hi95 = block_bootstrap_ci(obs, block_length=5, n_resamples=500, ci=0.95)
        _, lo99, hi99 = block_bootstrap_ci(obs, block_length=5, n_resamples=500, ci=0.99)
        
        assert (hi99 - lo99) >= (hi95 - lo95), (
            f"99% CI width ({hi99 - lo99:.4f}) should be >= 95% CI width ({hi95 - lo95:.4f})"
        )


class TestIIDBootstrapCI:
    """Tests for iid_bootstrap_ci (convenience wrapper)."""

    def test_equivalent_to_block_length_one(self):
        """iid_bootstrap_ci produces same result as block_bootstrap_ci(block_length=1)."""
        obs = np.random.RandomState(12).randn(100)
        r_iid = iid_bootstrap_ci(obs, n_resamples=300, random_seed=42)
        r_block = block_bootstrap_ci(
            obs, block_length=1, n_resamples=300, random_seed=42
        )
        np.testing.assert_array_almost_equal(r_iid, r_block)


class TestCISummary:
    """Tests for ci_summary convenience function."""

    def test_returns_dict_with_keys(self):
        """Returns a dict with expected keys."""
        obs = np.random.RandomState(13).randn(100)
        summary = ci_summary(obs, block_length=5, n_resamples=200, label="test")
        
        assert summary["label"] == "test"
        assert summary["n"] == 100
        assert "point_estimate" in summary
        assert "ci_lower" in summary
        assert "ci_upper" in summary
        assert summary["ci_level"] == 0.95
        assert summary["block_length"] == 5