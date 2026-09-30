"""Tests for supplementary CI + drawdown episodes (EXP-2026-04A)."""
import numpy as np
import pandas as pd
import pytest

from risk.metrics import (
    drawdown_episodes,
    moving_block_ci_mean_diff,
    moving_block_ci_sharpe_diff,
)


class TestMovingBlockCiMeanDiff:
    def test_point_estimate(self):
        """Point estimate equals the mean of differences."""
        a = pd.Series(np.random.RandomState(1).randn(500) * 0.01)
        b = pd.Series(np.random.RandomState(2).randn(500) * 0.01)
        res = moving_block_ci_mean_diff(a, b, block_length=10, n_resamples=200, seed=42)
        assert res["point_estimate"] == pytest.approx((a - b).mean(), abs=1e-10)

    def test_ci_bounds_ordered(self):
        a = pd.Series(np.random.RandomState(1).randn(500) * 0.01)
        b = pd.Series(np.random.RandomState(2).randn(500) * 0.01)
        res = moving_block_ci_mean_diff(a, b, block_length=10, n_resamples=200, seed=42)
        assert res["ci_lower"] <= res["point_estimate"] <= res["ci_upper"]

    def test_reproducible(self):
        a = pd.Series(np.random.RandomState(1).randn(500) * 0.01)
        b = pd.Series(np.random.RandomState(2).randn(500) * 0.01)
        r1 = moving_block_ci_mean_diff(a, b, block_length=10, n_resamples=200, seed=42)
        r2 = moving_block_ci_mean_diff(a, b, block_length=10, n_resamples=200, seed=42)
        assert r1["ci_lower"] == r2["ci_lower"]

    def test_wider_with_longer_block(self):
        """Serial dependence: longer blocks -> wider CI."""
        rng = np.random.RandomState(5)
        n = 1000
        eps = rng.randn(n)
        ar1 = np.zeros(n)
        ar1[0] = eps[0]
        for i in range(1, n):
            ar1[i] = 0.5 * ar1[i - 1] + eps[i]
        a = pd.Series(ar1 * 0.01)
        b = pd.Series(np.zeros(n))
        w1 = moving_block_ci_mean_diff(a, b, block_length=1, n_resamples=200, seed=42)
        w20 = moving_block_ci_mean_diff(a, b, block_length=20, n_resamples=200, seed=42)
        assert (w20["ci_upper"] - w20["ci_lower"]) > (w1["ci_upper"] - w1["ci_lower"])

    def test_insufficient_data_raises(self):
        a = pd.Series([0.01] * 5)
        b = pd.Series([0.01] * 5)
        with pytest.raises(ValueError, match="Insufficient"):
            moving_block_ci_mean_diff(a, b, block_length=10)


class TestMovingBlockCiSharpeDiff:
    def test_point_matches_direct_computation(self):
        rng = np.random.RandomState(7)
        a = pd.Series(rng.randn(500) * 0.01 + 0.0002)
        b = pd.Series(rng.randn(500) * 0.01)
        res = moving_block_ci_sharpe_diff(a, b, block_length=10, n_resamples=200, seed=1)
        sharpe_a = a.mean() / a.std() * np.sqrt(252)
        sharpe_b = b.mean() / b.std() * np.sqrt(252)
        assert res["point_estimate"] == pytest.approx(sharpe_a - sharpe_b, abs=1e-8)


class TestDrawdownEpisodes:
    def test_single_episode_detected(self):
        """A known V-shaped NAV produces one recovered episode."""
        nav = pd.Series(
            [100, 110, 105, 95, 100, 105, 120],
            index=pd.date_range("2024-01-01", periods=7),
        )
        episodes = drawdown_episodes(nav, min_depth=0.01)
        assert len(episodes) >= 1
        deepest = max(episodes, key=lambda e: abs(e["depth"]))
        # peak=110 (day 1), trough=95 (day 3): depth = (95-110)/110
        assert deepest["depth"] == pytest.approx(-15.0 / 110.0, rel=1e-6)
        assert deepest["recovered"] is True

    def test_monotonic_increasing_no_episode(self):
        nav = pd.Series(np.arange(1.0, 11.0), index=pd.date_range("2024-01-01", periods=10))
        episodes = drawdown_episodes(nav, min_depth=0.001)
        assert episodes == []

    def test_open_episode_at_end(self):
        """A terminal drawdown is reported as not recovered."""
        nav = pd.Series(
            [100, 120, 110, 100],
            index=pd.date_range("2024-01-01", periods=4),
        )
        episodes = drawdown_episodes(nav, min_depth=0.01)
        open_eps = [e for e in episodes if not e["recovered"]]
        assert len(open_eps) == 1
        # peak=120 (day1), trough=100 (day3): depth=-20/120
        assert open_eps[0]["depth"] == pytest.approx(-20.0 / 120.0, rel=1e-6)

    def test_always_keeps_deepest(self):
        """Deepest episode included even below min_depth."""
        nav = pd.Series(
            [100, 101, 100.5, 100, 100.5, 99, 100, 101, 102],
            index=pd.date_range("2024-01-01", periods=9),
        )
        episodes = drawdown_episodes(nav, min_depth=0.10)
        assert len(episodes) >= 1  # deepest retained