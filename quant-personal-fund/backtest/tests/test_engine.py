"""Unit tests for backtest.engine module."""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from backtest.engine import run_backtest


@pytest.fixture
def minimal_configs():
    """Create temp config files and data for engine tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)

        # Universe
        universe = {
            "universe": {
                "fx": [
                    {"ticker": "FXA", "base_currency": "A", "quote_currency": "B",
                     "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                     "yahoo_ticker": "FXA_T", "is_active": True},
                ]
            }
        }
        universe_path = base / "universe.yaml"
        with open(universe_path, "w") as f:
            yaml.dump(universe, f)

        # Cost model
        costs = {
            "defaults": {"slippage_pips_fx": 0.0},
            "instruments": {
                "FXA": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
            },
        }
        cost_path = base / "cost_model.yaml"
        with open(cost_path, "w") as f:
            yaml.dump(costs, f)

        # Data
        data_dir = base / "data"
        data_dir.mkdir()
        dates = pd.date_range("2026-01-05", periods=20, freq="B")
        prices = np.exp(np.cumsum(np.random.RandomState(1).randn(20) * 0.005))
        df = pd.DataFrame({
            "date": dates,
            "open": prices * 0.999, "high": prices * 1.01,
            "low": prices * 0.99, "close": prices,
            "adj_close": prices, "volume": [100] * 20,
        })
        df.to_parquet(data_dir / "FXA_T_daily.parquet")

        # Weights
        weights = pd.DataFrame(
            {"FXA": [1.0] * 20},
            index=dates,
        )

        yield {
            "universe_path": str(universe_path),
            "cost_path": str(cost_path),
            "data_dir": str(data_dir),
            "weights": weights,
        }


class TestRunBacktest:
    def test_runs_with_minimal_config(self, minimal_configs):
        """Pipeline runs with minimal valid config."""
        result, metrics, metadata = run_backtest(
            universe_config_path=minimal_configs["universe_path"],
            cost_model_path=minimal_configs["cost_path"],
            data_dir=minimal_configs["data_dir"],
            weights=minimal_configs["weights"],
        )
        assert result is not None
        assert "sharpe_ratio" in metrics
        assert metadata is not None

    def test_weight_mismatch_raises(self, minimal_configs):
        """Unknown ticker in weights raises ValueError."""
        bad_weights = pd.DataFrame(
            {"UNKNOWN": [0.5]},
            index=minimal_configs["weights"].index[:1],
        )
        with pytest.raises(ValueError, match="not in returns panel"):
            run_backtest(
                universe_config_path=minimal_configs["universe_path"],
                cost_model_path=minimal_configs["cost_path"],
                data_dir=minimal_configs["data_dir"],
                weights=bad_weights,
            )

    def test_lag_parameter(self, minimal_configs):
        """Different lag values produce position shifts (output shapes identical)."""
        weights = minimal_configs["weights"]
        r1, _, _ = run_backtest(
            universe_config_path=minimal_configs["universe_path"],
            cost_model_path=minimal_configs["cost_path"],
            data_dir=minimal_configs["data_dir"],
            weights=weights, lag=0,
        )
        r2, _, _ = run_backtest(
            universe_config_path=minimal_configs["universe_path"],
            cost_model_path=minimal_configs["cost_path"],
            data_dir=minimal_configs["data_dir"],
            weights=weights, lag=1,
        )
        # Both should produce valid outputs with same shape
        assert len(r1.nav) == len(r2.nav)
        # Positions should differ by offset: lag=1 shifts positions forward
        assert (r1.positions.iloc[:, 0].fillna(0).values !=
                r2.positions.iloc[:, 0].fillna(0).values).any()

    def test_output_dir_created(self, minimal_configs):
        """Output directory is populated when specified."""
        with tempfile.TemporaryDirectory() as out_dir:
            _, _, _ = run_backtest(
                universe_config_path=minimal_configs["universe_path"],
                cost_model_path=minimal_configs["cost_path"],
                data_dir=minimal_configs["data_dir"],
                weights=minimal_configs["weights"],
                output_dir=out_dir,
            )
            assert Path(out_dir).exists()
            files = list(Path(out_dir).glob("*"))
            assert len(files) >= 4  # nav, returns, positions, costs, etc.