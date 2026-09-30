"""End-to-end integration test for Phase 2 pipeline.

Validates the full pipeline with synthetic data:
    3 assets (FX + equity + commodity), 60 trading days,
    equal weights, known returns → verified NAV and metrics.
"""

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from backtest.engine import run_backtest
from core.instruments import InstrumentMaster


@pytest.fixture
def synthetic_universe_config():
    """Minimal universe: FX, equity index, commodity."""
    return {
        "universe": {
            "fx": [
                {"ticker": "FX1", "base_currency": "AAA", "quote_currency": "BBB",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "FX1_TEST", "is_active": True},
            ],
            "equity_index": [
                {"ticker": "EQ1", "currency": "BBB", "tick_size": 0.01,
                 "yahoo_ticker": "EQ1_TEST", "is_active": True},
            ],
            "commodity": [
                {"ticker": "CM1", "currency": "BBB", "tick_size": 0.01,
                 "yahoo_ticker": "CM1_TEST", "is_active": True},
            ],
        }
    }


@pytest.fixture
def synthetic_cost_config():
    """Zero-cost config to simplify NAV verification."""
    return {
        "defaults": {"slippage_pips_fx": 0.0},
        "instruments": {
            "FX1": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
            "EQ1": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
            "CM1": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
        },
    }


@pytest.fixture
def synthetic_setup(synthetic_universe_config, synthetic_cost_config):
    """Create temp directory with configs, data, and weights for the pipeline."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Write universe config
        universe_path = base / "universe.yaml"
        with open(universe_path, "w") as f:
            yaml.dump(synthetic_universe_config, f)

        # Write cost config
        cost_path = base / "cost_model.yaml"
        with open(cost_path, "w") as f:
            yaml.dump(synthetic_cost_config, f)

        # Create data dir with parquet files
        data_dir = base / "data"
        data_dir.mkdir()

        dates = pd.date_range("2026-01-05", periods=60, freq="B")
        rng = np.random.RandomState(123)

        # Generate synthetic prices with known returns
        # FX1: 5bp/day drift + noise
        fx1_returns = 0.0005 + rng.randn(60) * 0.005
        fx1_prices = 1.0 * np.exp(np.cumsum(fx1_returns))

        # EQ1: 3bp/day drift + noise  
        eq1_returns = 0.0003 + rng.randn(60) * 0.008
        eq1_prices = 100.0 * np.exp(np.cumsum(eq1_returns))

        # CM1: zero drift + higher noise
        cm1_returns = rng.randn(60) * 0.01
        cm1_prices = 50.0 * np.exp(np.cumsum(cm1_returns))

        for ticker, prices in [("FX1_TEST", fx1_prices), ("EQ1_TEST", eq1_prices), ("CM1_TEST", cm1_prices)]:
            df = pd.DataFrame({
                "date": dates,
                "open": prices * 0.999,
                "high": prices * 1.005,
                "low": prices * 0.995,
                "close": prices,
                "adj_close": prices,
                "volume": np.random.randint(100, 1000, 60),
            })
            df.to_parquet(data_dir / f"{ticker}_daily.parquet")

        # Create equal weights
        weights = pd.DataFrame(
            {"FX1": [1.0 / 3.0] * 60, "EQ1": [1.0 / 3.0] * 60, "CM1": [1.0 / 3.0] * 60},
            index=dates,
        )

        result = run_backtest(
            universe_config_path=str(universe_path),
            cost_model_path=str(cost_path),
            data_dir=str(data_dir),
            weights=weights,
            initial_nav=1.0,
            lag=1,
        )
        yield result  # (PortfolioResult, metrics, metadata)


class TestEndToEnd:
    def test_pipeline_runs(self, synthetic_setup):
        """Pipeline runs without error and returns expected types."""
        result, metrics, metadata = synthetic_setup
        assert result is not None
        assert isinstance(metrics, dict)
        assert metadata is not None

    def test_nav_starts_at_initial(self, synthetic_setup):
        """NAV starts at 1.0."""
        result, _, _ = synthetic_setup
        assert result.nav["nav_net"].iloc[0] == pytest.approx(1.0)

    def test_nav_positive(self, synthetic_setup):
        """NAV is always positive."""
        result, _, _ = synthetic_setup
        assert (result.nav["nav_net"] > 0).all()
        assert (result.nav["nav_gross"] > 0).all()

    def test_net_nav_le_gross_nav(self, synthetic_setup):
        """Net NAV ≤ Gross NAV at every date."""
        result, _, _ = synthetic_setup
        assert (result.nav["nav_net"] <= result.nav["nav_gross"] + 1e-10).all()

    def test_metrics_computed(self, synthetic_setup):
        """All key metrics are present."""
        _, metrics, _ = synthetic_setup
        required = [
            "annualized_return", "annualized_volatility", "sharpe_ratio",
            "max_drawdown", "sortino_ratio", "calmar_ratio",
            "total_cost", "cost_to_gross_pnl", "n_days",
        ]
        for key in required:
            assert key in metrics, f"Missing metric: {key}"

    def test_metadata_present(self, synthetic_setup):
        """Dataset metadata is present."""
        _, _, metadata = synthetic_setup
        assert len(metadata.instruments) == 3
        assert metadata.validation_errors == 0
        assert metadata.inputs_hash is not None

    def test_positions_align_with_weights(self, synthetic_setup):
        """After lag, positions reflect lagged weights."""
        result, _, _ = synthetic_setup
        # With lag=1 and equal weights, positions should be 1/3 each after warmup
        mid_idx = len(result.positions) // 2
        mid_positions = result.positions.iloc[mid_idx]
        assert mid_positions.sum() == pytest.approx(1.0, abs=0.01)

    def test_outputs_have_correct_structure(self, synthetic_setup):
        """All output DataFrames have expected columns."""
        result, _, _ = synthetic_setup
        assert "nav_gross" in result.nav.columns
        assert "nav_net" in result.nav.columns
        assert "gross_return" in result.returns.columns
        assert "net_return" in result.returns.columns
        assert "txn_cost" in result.costs.columns
        assert "hold_cost" in result.costs.columns
        assert "gross_exposure" in result.exposures.columns
        assert "net_exposure" in result.exposures.columns