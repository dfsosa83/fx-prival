"""Unit tests for portfolio.accounting module."""
import numpy as np
import pandas as pd
import pytest
import tempfile
from pathlib import Path
import yaml

from core.costs import CostModel
from core.instruments import InstrumentMaster
from portfolio.accounting import (
    PortfolioResult,
    compute_portfolio,
    validate_weights,
)


@pytest.fixture
def simple_returns():
    """2-asset returns panel with known values."""
    dates = pd.date_range("2026-01-05", periods=10, freq="B")
    return pd.DataFrame({
        "ASSET_A": [0.0, 0.01, 0.02, -0.01, 0.005, -0.005, 0.01, 0.0, 0.02, -0.01],
        "ASSET_B": [0.0, 0.005, -0.01, 0.02, 0.0, 0.01, -0.005, 0.015, -0.01, 0.005],
    }, index=dates)


@pytest.fixture
def cost_model():
    """Minimal cost model for testing."""
    config = {
        "defaults": {"slippage_pips_fx": 0.0},
        "instruments": {
            "ASSET_A": {
                "spread_pips": 0.0,
                "commission_pct": 0.001,
                "financing_annual_pct": 0.0,
            },
            "ASSET_B": {
                "spread_pips": 0.0,
                "commission_pct": 0.001,
                "financing_annual_pct": 0.0,
            },
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        f.flush()
        path = f.name
    cm = CostModel()
    cm.load_from_yaml(path)
    yield cm
    Path(path).unlink()


@pytest.fixture
def instrument_master():
    """Minimal instrument master for testing."""
    config = {
        "universe": {
            "fx": [
                {"ticker": "ASSET_A", "base_currency": "AAA", "quote_currency": "BBB",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "A=X", "is_active": True},
                {"ticker": "ASSET_B", "base_currency": "BBB", "quote_currency": "CCC",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "B=X", "is_active": True},
            ]
        }
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(config, f)
        f.flush()
        path = f.name
    im = InstrumentMaster()
    im.load_from_yaml(path)
    yield im
    Path(path).unlink()


class TestValidateWeights:
    def test_valid_weights(self, simple_returns):
        weights = pd.DataFrame(
            {"ASSET_A": [0.5] * 10, "ASSET_B": [0.3] * 10},
            index=simple_returns.index,
        )
        cleaned, warnings = validate_weights(weights, simple_returns)
        assert len(warnings) == 0
        assert cleaned.shape == weights.shape

    def test_unknown_column_raises(self, simple_returns):
        weights = pd.DataFrame({"UNKNOWN": [0.5]}, index=simple_returns.index[:1])
        with pytest.raises(ValueError, match="not in returns panel"):
            validate_weights(weights, simple_returns)

    def test_nan_filled_to_zero(self, simple_returns):
        weights = pd.DataFrame(
            {"ASSET_A": [0.5, np.nan, 0.5]},
            index=simple_returns.index[:3],
        )
        cleaned, warnings = validate_weights(weights, simple_returns)
        assert any("NaN" in w for w in warnings)
        assert cleaned.iloc[1, 0] == 0.0

    def test_negative_blocked(self, simple_returns):
        weights = pd.DataFrame(
            {"ASSET_A": [-0.1]},
            index=simple_returns.index[:1],
        )
        with pytest.raises(ValueError, match="Negative weights"):
            validate_weights(weights, simple_returns)

    def test_negative_allowed(self, simple_returns):
        weights = pd.DataFrame(
            {"ASSET_A": [-0.1]},
            index=simple_returns.index[:1],
        )
        cleaned, _ = validate_weights(weights, simple_returns, allow_short=True)
        assert cleaned.iloc[0, 0] == -0.1


class TestComputePortfolio:
    def test_single_asset_no_costs(self, simple_returns, cost_model, instrument_master):
        """100% asset A, no costs, verify NAV matches compounded returns."""
        cost_model.costs["ASSET_A"]["commission_pct"] = 0.0
        weights = pd.DataFrame(
            {"ASSET_A": [1.0] * 10, "ASSET_B": [0.0] * 10},
            index=simple_returns.index,
        )
        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
            initial_nav=1.0, lag=1,
        )

        # NAV should compound with gross returns (no costs → gross=net)
        nav_expected = (1 + simple_returns["ASSET_A"]).cumprod()
        # lag=1: first positive return at index 1
        assert result.nav["nav_gross"].iloc[-1] == pytest.approx(nav_expected.iloc[-1], rel=1e-4)

    def test_net_nav_le_gross_nav(self, simple_returns, cost_model, instrument_master):
        """Net NAV ≤ Gross NAV for every date."""
        weights = pd.DataFrame(
            {"ASSET_A": [0.6] * 10, "ASSET_B": [0.4] * 10},
            index=simple_returns.index,
        )
        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
            initial_nav=1.0, lag=1,
        )
        assert (result.nav["nav_net"] <= result.nav["nav_gross"] + 1e-10).all()

    def test_lag_enforcement(self, simple_returns, cost_model, instrument_master):
        """Weight at date 0 takes effect at date 1 (lag=1)."""
        cost_model.costs["ASSET_A"]["commission_pct"] = 0.0
        cost_model.costs["ASSET_B"]["commission_pct"] = 0.0

        # Weights start non-zero at date 1
        weights = pd.DataFrame(
            {"ASSET_A": 0.0, "ASSET_B": 0.0},
            index=simple_returns.index,
        )
        weights.loc[weights.index[1], "ASSET_A"] = 1.0

        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
            initial_nav=1.0, lag=1,
        )

        # Position should be zero at index 0 and 1, non-zero at index 2
        assert result.positions["ASSET_A"].iloc[0] == 0.0
        assert result.positions["ASSET_A"].iloc[1] == 0.0  # lag=1 delays
        assert result.positions["ASSET_A"].iloc[2] == 1.0

    def test_zero_turnover_no_cost(self, simple_returns, cost_model, instrument_master):
        """No weight change → zero turnover → zero txn cost."""
        cost_model.costs["ASSET_A"]["commission_pct"] = 0.0
        cost_model.costs["ASSET_B"]["commission_pct"] = 0.0

        weights = pd.DataFrame(
            {"ASSET_A": [0.5] * 10, "ASSET_B": [0.5] * 10},
            index=simple_returns.index,
        )
        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
            initial_nav=1.0, lag=1,
        )
        # Turnover is non-zero only on first weight entry
        assert result.turnover.iloc[2:].max() == pytest.approx(0.0, abs=1e-10)

    def test_initial_nav(self, simple_returns, cost_model, instrument_master):
        """nav[0] = initial_nav."""
        weights = pd.DataFrame(
            {"ASSET_A": [1.0] * 10, "ASSET_B": [0.0] * 10},
            index=simple_returns.index,
        )
        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
            initial_nav=100.0, lag=1,
        )
        assert result.nav["nav_net"].iloc[0] == 100.0

    def test_exposure_tracking(self, simple_returns, cost_model, instrument_master):
        """Exposures track positions."""
        weights = pd.DataFrame(
            {"ASSET_A": [0.6] * 10, "ASSET_B": [0.4] * 10},
            index=simple_returns.index,
        )
        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
            initial_nav=1.0, lag=1,
        )
        assert result.exposures["gross_exposure"].iloc[-1] == pytest.approx(1.0)
        assert result.exposures["net_exposure"].iloc[-1] == pytest.approx(1.0)

    def test_holding_cost_daily(self, simple_returns, cost_model, instrument_master):
        """Financing cost accrues daily."""
        cost_model.costs["ASSET_A"]["financing_annual_pct"] = 0.052  # ~2bp/day
        cost_model.costs["ASSET_A"]["commission_pct"] = 0.0

        weights = pd.DataFrame(
            {"ASSET_A": [1.0] * 10, "ASSET_B": [0.0] * 10},
            index=simple_returns.index,
        )
        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
            initial_nav=1.0, lag=1,
        )
        # Holding costs should be positive when we have a position
        later_costs = result.costs["hold_cost"].iloc[3:]
        assert (later_costs > 0).any()

    def test_returns_panel_shape(self, simple_returns, cost_model, instrument_master):
        """Result has expected shapes."""
        weights = pd.DataFrame(
            {"ASSET_A": [0.5] * 10, "ASSET_B": [0.5] * 10},
            index=simple_returns.index,
        )
        result = compute_portfolio(
            simple_returns, weights, cost_model, instrument_master,
        )
        assert isinstance(result, PortfolioResult)
        assert len(result.nav) == len(simple_returns)
        assert "gross_return" in result.returns.columns
        assert "net_return" in result.returns.columns
        assert "txn_cost" in result.costs.columns
        assert "hold_cost" in result.costs.columns