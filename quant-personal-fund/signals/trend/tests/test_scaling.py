"""Unit tests for signals.trend.scaling module."""
import numpy as np
import pandas as pd
import pytest

from signals.trend.scaling import compute_vol_scaled_positions


@pytest.fixture
def sample_data():
    """3-asset data with different volatilities."""
    rng = np.random.RandomState(55)
    dates = pd.date_range("2022-01-01", periods=300, freq="B")
    returns = pd.DataFrame({
        "LOW_VOL": rng.randn(300) * 0.005,
        "MID_VOL": rng.randn(300) * 0.01,
        "HIGH_VOL": rng.randn(300) * 0.02,
    }, index=dates)
    # Different signal strengths to differentiate weights
    scores = pd.DataFrame({
        "LOW_VOL": 1.0,
        "MID_VOL": 0.5,
        "HIGH_VOL": 0.2,
    }, index=dates)
    return scores, returns


class TestComputeVolScaledPositions:
    def test_weights_sum_to_one(self, sample_data):
        """Normalized weights sum to <= 1.0 (caps may reduce total allocation)."""
        scores, returns = sample_data
        weights = compute_vol_scaled_positions(scores, returns, max_position=1.0)
        tail = weights.iloc[-100:]
        row_sums = tail.abs().sum(axis=1)
        active_rows = row_sums[row_sums > 0]
        if len(active_rows) > 0:
            np.testing.assert_allclose(active_rows, 1.0, rtol=0.01)

    def test_low_vol_gets_higher_weight(self, sample_data):
        """Inverse-vol scaling gives more weight to low-vol instruments."""
        scores, returns = sample_data
        weights = compute_vol_scaled_positions(scores, returns)
        tail = weights.iloc[-100:]
        avg_weights = tail.mean()
        assert avg_weights["LOW_VOL"] > avg_weights["HIGH_VOL"]

    def test_long_only(self, sample_data):
        """Long-only mode produces only non-negative weights."""
        scores, returns = sample_data
        # Set some negative scores
        scores["HIGH_VOL"] = -1.0
        weights = compute_vol_scaled_positions(scores, returns, long_only=True)
        assert (weights["HIGH_VOL"].iloc[-100:] == 0.0).all()

    def test_max_position_cap(self, sample_data):
        """Max position per instrument is enforced (after normalization)."""
        scores, returns = sample_data
        weights = compute_vol_scaled_positions(scores, returns, max_position=0.15)
        tail = weights.iloc[-100:]
        assert (tail.abs().max().max() <= 0.15 + 1e-10)

    def test_all_zero_signals(self, sample_data):
        """All-zero signals produce all-zero weights."""
        scores, returns = sample_data
        scores[:] = 0.0
        weights = compute_vol_scaled_positions(scores, returns)
        assert (weights == 0.0).all().all()

    def test_no_division_by_zero(self, sample_data):
        """Zero volatility doesn't crash — produces zero weight."""
        scores, returns = sample_data
        returns["ZERO_VOL"] = 0.0
        scores["ZERO_VOL"] = 1.0
        weights = compute_vol_scaled_positions(scores, returns)
        tail = weights.iloc[-100:]
        assert (tail["ZERO_VOL"] == 0.0).all()