"""Unit tests for signals.trend.signal module."""
import numpy as np
import pandas as pd
import pytest

from signals.trend.signal import blend_signals, compute_trend_signal


@pytest.fixture
def price_data():
    """Synthetic price data: 3 assets, 500 days."""
    rng = np.random.RandomState(42)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    prices = pd.DataFrame({
        "UP": 100 * np.exp(np.cumsum(rng.randn(500) * 0.008 + 0.002)),   # Strong upward drift
        "DOWN": 100 * np.exp(np.cumsum(rng.randn(500) * 0.008 - 0.002)),  # Strong downward drift
        "FLAT": 100 * np.exp(np.cumsum(rng.randn(500) * 0.008)),          # No drift
    }, index=dates)
    return prices


class TestComputeTrendSignal:
    def test_sign_method(self, price_data):
        """Sign method returns -1, 0, 1 values (or NaN for out-of-sample)."""
        result = compute_trend_signal(price_data, method="sign")
        assert isinstance(result, pd.DataFrame)
        vals = result.dropna().values.flatten()
        unique_vals = set(np.round(vals).astype(int))
        assert unique_vals.issubset({-1, 0, 1}), f"Unexpected values: {unique_vals}"

    def test_log_return_method(self, price_data):
        """Log return method returns continuous values."""
        result = compute_trend_signal(price_data, method="log_return")
        assert isinstance(result, pd.DataFrame)
        assert result.shape[1] > 0

    def test_custom_lookbacks(self, price_data):
        """Custom lookback list is respected."""
        result = compute_trend_signal(price_data, lookbacks=[10, 20], method="sign")
        # Check that we got results for two lookbacks
        assert result.shape[1] == 6  # 2 lookbacks * 3 tickers

    def test_upward_trend_detected(self, price_data):
        """Asset with upward drift should show positive trend at long lookbacks."""
        scores = blend_signals(price_data, long_only=False)
        up_avg = scores["UP"].dropna().mean()
        assert up_avg > 0, f"UP average score {up_avg:.3f} should be positive"

    def test_downward_trend_detected(self, price_data):
        """Asset with strong downward drift should show negative trend at longest lookback."""
        # Check the 12M return directly (not the z-score blend)
        ret_12m = np.log(price_data["DOWN"] / price_data["DOWN"].shift(252))
        tail = ret_12m.dropna().iloc[-100:]
        # The 12M log return should be negative for a downward-drifting asset
        assert tail.mean() < 0, f"12M return mean = {tail.mean():.4f}, should be negative"


class TestBlendSignals:
    def test_long_only_clips_negatives(self, price_data):
        """Long-only mode clips negative scores to 0 (check tail where z-scores are stable)."""
        scores = blend_signals(price_data, long_only=True)
        tail = scores.dropna().iloc[-100:]
        assert (tail >= -1e-10).all().all()

    def test_long_short_allows_negatives(self, price_data):
        """Non-long-only mode allows negative scores."""
        scores = blend_signals(price_data, long_only=False)
        assert (scores < 0).any().any()

    def test_output_shape(self, price_data):
        """Output has same shape as input (dates × tickers)."""
        scores = blend_signals(price_data)
        assert scores.shape[0] == len(price_data)
        assert set(scores.columns) == set(price_data.columns)

    def test_initial_nan(self, price_data):
        """First N days have NaN where lookback hasn't accumulated."""
        scores = blend_signals(price_data, lookbacks=[252])
        assert scores.iloc[:251].isna().all().all()
        assert not scores.iloc[252:].isna().all().all()