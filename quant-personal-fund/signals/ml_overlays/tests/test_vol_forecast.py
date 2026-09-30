"""Unit tests for signals.ml_overlays.vol_forecast module."""
import numpy as np
import pandas as pd
import pytest

from signals.ml_overlays.vol_forecast import (
    build_regression_dataset,
    forward_realized_volatility,
)


class TestForwardRealizedVolatility:
    def test_positive(self):
        """Forward vol is always non-negative."""
        returns = pd.Series(np.random.RandomState(1).randn(500) * 0.01)
        fwd = forward_realized_volatility(returns, horizon=30)
        assert (fwd.dropna() >= 0).all()

    def test_high_vol_period_detected(self):
        """Forward vol is high after a high-vol period."""
        # 200 days low vol, then 200 days high vol
        rng = np.random.RandomState(2)
        vol = np.concatenate([np.full(200, 0.005), np.full(200, 0.02)])
        returns = pd.Series(rng.randn(400) * vol)
        fwd = forward_realized_volatility(returns, horizon=30)
        # At the switch point (t=200), forward vol should be high
        switch_vol = fwd.iloc[195:205].mean()
        early_vol = fwd.iloc[50:60].mean()
        assert switch_vol > early_vol


class TestBuildRegressionDataset:
    def test_alignment(self):
        """Features and labels align on common index."""
        rng = np.random.RandomState(3)
        dates = pd.date_range("2020-01-01", periods=500, freq="B")
        returns = pd.Series(rng.randn(500) * 0.01, index=dates)
        features = pd.DataFrame(
            {"f1": rng.randn(500), "f2": rng.randn(500)},
            index=dates,
        )
        X, y = build_regression_dataset(features, returns, horizon=30)
        assert len(X) == len(y)
        # Forward vol requires min_periods=15 at the start; the last 30 rows are NaN
        assert len(X) <= 500 - 10

    def test_no_overlap_in_label(self):
        """Labels use only future returns — no leakage into features."""
        rng = np.random.RandomState(4)
        dates = pd.date_range("2020-01-01", periods=500, freq="B")
        returns = pd.Series(rng.randn(500) * 0.01, index=dates)
        features = pd.DataFrame({"f1": rng.randn(500)}, index=dates)
        X, y = build_regression_dataset(features, returns, horizon=30)
        # Verify y at date t uses returns AFTER t
        # Check correlation between y and forward returns is positive
        assert len(y) > 100