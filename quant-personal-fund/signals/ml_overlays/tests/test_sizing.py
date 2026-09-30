"""Unit tests for signals.ml_overlays.sizing module."""
import numpy as np
import pandas as pd
import pytest

from signals.ml_overlays.sizing import (
    apply_scaling,
    create_regime_filter,
    volatility_scaling_factor,
)


class TestVolatilityScalingFactor:
    def test_baseline_ratio_one(self):
        """Forecast == baseline → scale = 1.0."""
        dates = pd.date_range("2020-01-01", periods=100)
        forecast = pd.Series(0.10, index=dates)
        baseline = pd.Series(0.10, index=dates)
        scale = volatility_scaling_factor(forecast, baseline)
        assert scale.mean() == pytest.approx(1.0)

    def test_double_vol_halves(self):
        """Forecast 2× baseline → scale ≈ 0.5."""
        dates = pd.date_range("2020-01-01", periods=100)
        forecast = pd.Series(0.20, index=dates)
        baseline = pd.Series(0.10, index=dates)
        scale = volatility_scaling_factor(forecast, baseline, k=0.5)
        assert scale.mean() == pytest.approx(0.5)

    def test_bounds(self):
        """Scale stays within [min_scale, max_scale]."""
        dates = pd.date_range("2020-01-01", periods=100)
        forecast = pd.Series(0.50, index=dates)  # 5x baseline
        baseline = pd.Series(0.10, index=dates)
        scale = volatility_scaling_factor(forecast, baseline, min_scale=0.25)
        assert (scale >= 0.25).all()
        assert (scale <= 1.0).all()

    def test_low_vol_no_expansion(self):
        """Below-baseline forecast doesn't exceed max_scale."""
        dates = pd.date_range("2020-01-01", periods=100)
        forecast = pd.Series(0.01, index=dates)
        baseline = pd.Series(0.10, index=dates)
        scale = volatility_scaling_factor(forecast, baseline)
        assert (scale <= 1.0 + 1e-10).all()


class TestApplyScaling:
    def test_scales_weights(self):
        """Weights are scaled row-wise."""
        dates = pd.date_range("2020-01-01", periods=10)
        weights = pd.DataFrame({"A": 0.5, "B": 0.5}, index=dates)
        scale = pd.Series(0.5, index=dates)
        scaled = apply_scaling(weights, scale)
        assert (scaled["A"] == 0.25).all()
        assert (scaled["B"] == 0.25).all()


class TestCreateRegimeFilter:
    def test_normal_regime(self):
        """Below threshold → scale 1.0."""
        dates = pd.date_range("2020-01-01", periods=500, freq="B")
        forecast = pd.Series(0.10, index=dates)
        scale = create_regime_filter(forecast, threshold=1.5)
        assert (scale == 1.0).all()

    def test_elevated_regime(self):
        """High forecast vol → de-risk scale."""
        dates = pd.date_range("2020-01-01", periods=600, freq="B")
        # Low for 300 days, then 3x spike
        forecast = pd.Series(0.10, index=dates)
        forecast.iloc[400:] = 0.30
        scale = create_regime_filter(forecast, threshold=1.5)
        # After the spike, scale should be < 1.0
        assert (scale.iloc[450:] < 1.0).any()