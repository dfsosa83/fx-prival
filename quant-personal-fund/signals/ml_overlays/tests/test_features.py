"""Unit tests for signals.ml_overlays.features module."""
import numpy as np
import pandas as pd
import pytest

from signals.ml_overlays.features import compute_all_features, compute_daily_features


@pytest.fixture
def market_data():
    """Synthetic price and return data."""
    rng = np.random.RandomState(11)
    dates = pd.date_range("2020-01-01", periods=800, freq="B")
    # Vol regime switch: first 400 days low vol, last 400 days high vol
    vol = np.concatenate([
        np.full(400, 0.005),
        np.full(400, 0.015),
    ])
    rets = pd.DataFrame({
        "A": rng.randn(800) * vol,
        "B": rng.randn(800) * 0.01,
    }, index=dates)
    prices = 100 * np.exp(rets.cumsum())
    return prices, rets


class TestComputeDailyFeatures:
    def test_output_shape(self, market_data):
        """Features cover the warmup period only."""
        prices, rets = market_data
        feat = compute_daily_features(prices, rets, "A")
        assert len(feat) > 0
        assert len(feat) <= len(prices)

    def test_no_nan(self, market_data):
        """All features are non-NaN after warmup drop."""
        prices, rets = market_data
        feat = compute_daily_features(prices, rets, "A")
        assert feat.notna().all().all()

    def test_expected_feature_groups(self, market_data):
        """Key feature families are present."""
        prices, rets = market_data
        feat = compute_daily_features(prices, rets, "A")
        cols = feat.columns.tolist()
        assert "ret_1d" in cols
        assert "realized_vol_30" in cols
        assert "rsi_14" in cols
        assert "close_vs_ema_50" in cols
        assert any(c.startswith("vol_ratio") for c in cols)

    def test_vol_regime_detected(self, market_data):
        """Realized vol features reflect the regime switch."""
        prices, rets = market_data
        feat = compute_daily_features(prices, rets, "A")
        late_vol = feat["realized_vol_30"].iloc[-100:].mean()
        early_vol = feat["realized_vol_30"].iloc[100:200].mean()
        assert late_vol > early_vol * 1.5

    def test_compute_all(self, market_data):
        """compute_all_features returns dict of DataFrames."""
        prices, rets = market_data
        result = compute_all_features(prices, rets, ["A", "B"])
        assert set(result.keys()) == {"A", "B"}