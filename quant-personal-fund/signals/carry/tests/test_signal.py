"""Unit tests for signals.carry.signal module."""
import numpy as np
import pandas as pd
import pytest

from signals.carry.signal import compute_carry_signal, normalize_carry_scores


@pytest.fixture
def fx_prices():
    """Synthetic FX spot data with a cheap then expensive cycle."""
    rng = np.random.RandomState(7)
    dates = pd.date_range("2020-01-01", periods=600, freq="B")
    # Pair 1: starts cheap (below MA) then appreciates
    p1 = 1.0 * np.exp(np.cumsum(rng.randn(600) * 0.003))
    # Pair 2: starts expensive then depreciates
    p2 = 1.0 * np.exp(np.cumsum(rng.randn(600) * 0.003))
    return pd.DataFrame({"PAIR1": p1, "PAIR2": p2}, index=dates)


class TestComputeCarrySignal:
    def test_output_shape(self, fx_prices):
        """Output shape matches input."""
        result = compute_carry_signal(fx_prices)
        assert result.shape == fx_prices.shape

    def test_values_in_range(self, fx_prices):
        """Carry scores are bounded."""
        result = compute_carry_signal(fx_prices)
        vals = result.values
        assert np.abs(vals).max() <= 1.0 + 1e-10

    def test_cheap_currency_gets_positive(self, fx_prices):
        """A pair trading below its MA should have positive carry."""
        # Force pair1 to drop 20% then hold
        rng = np.random.RandomState(1)
        dates = pd.date_range("2020-01-01", periods=400, freq="B")
        p = pd.Series(1.0, index=dates)
        p.iloc[100:150] = 0.8  # Drop to 0.80
        p.iloc[150:] = 0.8  # Stay
        prices = pd.DataFrame({"PAIR": p}, index=dates)
        result = compute_carry_signal(prices)
        # After the drop, spot stays below MA → positive carry
        tail = result["PAIR"].iloc[200:].mean()
        assert tail > 0, f"Expected positive carry for cheap currency, got {tail:.4f}"


class TestNormalizeCarryScores:
    def test_bounds(self, fx_prices):
        """Normalized scores are in [-1, 1] (or [0, 1] long-only)."""
        raw = compute_carry_signal(fx_prices)
        norm = normalize_carry_scores(raw, long_only=True)
        assert (norm >= 0).all().all()
        assert (norm <= 1.0).all().all()

    def test_long_short_allows_negative(self, fx_prices):
        """Long/short mode allows negative scores."""
        raw = compute_carry_signal(fx_prices)
        norm = normalize_carry_scores(raw, long_only=False)
        assert (norm >= -1.0).all().all()
        assert (norm <= 1.0).all().all()