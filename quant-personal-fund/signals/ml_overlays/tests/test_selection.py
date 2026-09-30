"""Unit tests for signals.ml_overlays.selection module."""
import numpy as np
import pandas as pd
import pytest

from signals.ml_overlays.selection import generate_noise_features, select_features_by_noise_voting


class TestGenerateNoiseFeatures:
    def test_shape(self):
        """Noise features have expected shape."""
        noise = generate_noise_features(100, n_features=5)
        assert noise.shape == (100, 5)

    def test_reproducible(self):
        """Same seed → same noise."""
        n1 = generate_noise_features(100, seed=42)
        n2 = generate_noise_features(100, seed=42)
        pd.testing.assert_frame_equal(n1, n2)


class TestSelectFeaturesByNoiseVoting:
    def test_strong_features_selected(self):
        """Features with real signal are selected over noise."""
        rng = np.random.RandomState(42)
        n = 1000
        # Create a strong signal feature
        X = pd.DataFrame({
            "strong_signal": rng.randn(n),
            "weak_signal": rng.randn(n),
            "pure_noise_feat": rng.randn(n),
        })
        # Label strongly depends on strong_signal
        y = pd.Series((X["strong_signal"] + 0.1 * rng.randn(n)) > 0).astype(int)

        selected, imp_df = select_features_by_noise_voting(
            X, y, min_strategy_support=1, seed=42, verbose=False
        )
        assert "strong_signal" in selected
        assert not any(f.startswith("noise_") for f in selected)

    def test_noise_not_selected(self):
        """Pure noise features never pass."""
        rng = np.random.RandomState(7)
        n = 800
        X = pd.DataFrame({"f": rng.randn(n)})
        y = pd.Series(rng.binomial(1, 0.5, n))  # Pure noise label
        selected, imp_df = select_features_by_noise_voting(
            X, y, min_strategy_support=1, seed=42, verbose=False
        )
        assert not any(f.startswith("noise_") for f in selected)

    def test_importance_report(self):
        """Importance report contains required columns."""
        rng = np.random.RandomState(99)
        n = 600
        X = pd.DataFrame({"f1": rng.randn(n), "f2": rng.randn(n)})
        y = pd.Series((X["f1"] > 0).astype(int))
        selected, imp_df = select_features_by_noise_voting(X, y, verbose=False)
        for col in ["feature", "avg_imp", "rf_vote", "lgbm_vote", "logreg_vote", "total_votes", "is_noise"]:
            assert col in imp_df.columns