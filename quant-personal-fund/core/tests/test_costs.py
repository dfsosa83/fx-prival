"""Unit tests for core.costs module."""
import tempfile
from pathlib import Path

import pytest
import yaml

from core.costs import CostModel


@pytest.fixture
def sample_cost_yaml():
    """Create a sample cost model config."""
    return {
        "defaults": {
            "slippage_pips_fx": 0.5,
            "slippage_equity_pct": 0.0005,
            "session_multiplier": 1.0,
        },
        "instruments": {
            "EURUSD": {
                "spread_pips": 1.8,
                "spread_source": "Test measurement",
                "commission_per_lot": 0.0,
                "swap_long_points": 0.0,
                "swap_short_points": 0.0,
            },
            "SPX": {
                "spread_pips": 0.0,
                "commission_pct": 0.0005,
                "financing_annual_pct": 0.05,
            },
        },
    }


@pytest.fixture
def cost_yaml_path(sample_cost_yaml):
    """Write sample cost config to temp file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(sample_cost_yaml, f)
        f.flush()
        path = f.name
    yield path
    Path(path).unlink()


@pytest.fixture
def cost_model(cost_yaml_path):
    """Return a CostModel loaded with test data."""
    model = CostModel()
    model.load_from_yaml(cost_yaml_path)
    return model


class TestCostModel:
    """Tests for CostModel."""

    def test_load_from_yaml(self, cost_model):
        """Loads cost data from YAML config."""
        assert len(cost_model.costs) == 2
        assert "EURUSD" in cost_model
        assert "SPX" in cost_model

    def test_get_returns_cost_record(self, cost_model):
        """get() returns the cost dict for a ticker."""
        eur_record = cost_model.get("EURUSD")
        assert eur_record["spread_pips"] == 1.8

    def test_get_missing_raises(self, cost_model):
        """KeyError for unknown ticker."""
        with pytest.raises(KeyError):
            cost_model.get("NONEXISTENT")

    def test_spread_pips(self, cost_model):
        """Returns spread in pips for FX instruments."""
        assert cost_model.spread_pips("EURUSD") == 1.8
        assert cost_model.spread_pips("SPX") == 0.0

    def test_round_trip_cost_pct_fx(self, cost_model):
        """Round-trip cost for FX includes spread + 2*slippage."""
        cost = cost_model.round_trip_cost_pct("EURUSD", notional=100000.0)
        # Spread 1.8 pips + 2 * 0.5 slippage = 2.8 pips
        # 2.8 * 0.0001 ≈ 0.00028 fraction
        assert cost > 0
        assert cost < 0.01  # Should be a small fraction

    def test_round_trip_cost_pct_equity(self, cost_model):
        """Round-trip cost for equity uses commission percentage."""
        cost = cost_model.round_trip_cost_pct("SPX")
        # 2 * 0.0005 commission + daily financing
        assert cost > 0

    def test_round_trip_cost_missing_notional_raises(self, cost_model):
        """FX instruments require notional for cost calculation."""
        with pytest.raises(ValueError, match="Notional required"):
            cost_model.round_trip_cost_pct("EURUSD")

    def test_all_tickers(self, cost_model):
        """Returns all tickers with cost data."""
        tickers = cost_model.all_tickers()
        assert "EURUSD" in tickers
        assert "SPX" in tickers

    def test_cost_per_trade_positive(self, cost_model):
        """Cost per trade is always positive."""
        cost = cost_model.cost_per_trade("EURUSD", notional=100000.0, holding_days=1)
        assert cost > 0

    def test_cost_always_reduces_returns(self, cost_model):
        """
        Costs are always positive (they reduce returns).
        This is a critical property — negative cost would be a sign error.
        """
        for ticker in cost_model.all_tickers():
            rec = cost_model.get(ticker)
            # Spread should be non-negative
            spread = rec.get("spread_pips", 0.0)
            assert spread >= 0, f"Negative spread for {ticker}"
            
            # Commission should be non-negative
            commission = rec.get("commission_pct", 0.0) or rec.get("commission_per_lot", 0.0)
            assert commission >= 0, f"Negative commission for {ticker}"

    def test_repr(self, cost_model):
        """__repr__ is informative."""
        rep = repr(cost_model)
        assert "CostModel" in rep

    def test_load_missing_file_raises(self):
        """FileNotFoundError for missing config."""
        model = CostModel()
        with pytest.raises(FileNotFoundError):
            model.load_from_yaml("/nonexistent/cost_model.yaml")