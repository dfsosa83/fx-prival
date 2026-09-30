"""Unit tests for signals.value.signal module."""
import numpy as np
import pandas as pd
import pytest

from signals.value.signal import compute_value_signal


class TestComputeValueSignal:
    def test_output_shape(self):
        """Output shape matches input."""
        dates = pd.date_range("2020-01-01", periods=1000, freq="B")
        p = pd.Series(1.0 + np.random.RandomState(3).randn(1000) * 0.05, index=dates)
        prices = pd.DataFrame({"PAIR": p})
        result = compute_value_signal(prices)
        assert result.shape == prices.shape

    def test_bounds(self):
        """Value scores are clipped to [-1, 1]."""
        dates = pd.date_range("2020-01-01", periods=1000, freq="B")
        p = pd.Series(1.0 + np.random.RandomState(3).randn(1000) * 0.05, index=dates)
        prices = pd.DataFrame({"PAIR": p})
        result = compute_value_signal(prices)
        assert (result.abs() <= 1.0).all().all()

    def test_undervalued_positive(self):
        """A currency trading well below its long-run mean → positive value."""
        dates = pd.date_range("2018-01-01", periods=1500, freq="B")
        p = pd.Series(1.0, index=dates)
        p.iloc[:1000] = 1.0
        p.iloc[1000:] = 0.7  # Sharp depreciation → undervalued
        prices = pd.DataFrame({"PAIR": p})
        result = compute_value_signal(prices)
        tail = result["PAIR"].iloc[1100:]
        assert tail.mean() > 0, f"Expected positive value for undervalued currency, got {tail.mean():.4f}"

    def test_z_threshold_filters_noise(self):
        """Weak deviations below threshold produce zero signal."""
        dates = pd.date_range("2018-01-01", periods=1000, freq="B")
        rng = np.random.RandomState(9)
        p = pd.Series(1.0 + rng.randn(1000) * 0.01, index=dates)  # Low noise
        prices = pd.DataFrame({"PAIR": p})
        result = compute_value_signal(prices, z_threshold=2.0)
        # With tiny noise, few values exceed 2-sigma
        active = int((result.abs() > 0).sum().sum())
        assert active < 100