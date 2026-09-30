"""Unit tests for core.instruments module."""
import os
import tempfile
from pathlib import Path

import pytest
import yaml

from core.instruments import InstrumentMaster


@pytest.fixture
def sample_universe_yaml():
    """Create a temporary universe.yaml for testing."""
    data = {
        "universe": {
            "fx": [
                {
                    "ticker": "EURUSD",
                    "base_currency": "EUR",
                    "quote_currency": "USD",
                    "pip_value": 0.0001,
                    "lot_size": 100000,
                    "tick_size": 0.00001,
                    "yahoo_ticker": "EURUSD=X",
                    "is_active": True,
                },
                {
                    "ticker": "USDJPY",
                    "base_currency": "USD",
                    "quote_currency": "JPY",
                    "pip_value": 0.01,
                    "lot_size": 100000,
                    "tick_size": 0.001,
                    "yahoo_ticker": "USDJPY=X",
                    "is_active": True,
                },
            ],
            "equity_index": [
                {
                    "ticker": "SPX",
                    "asset_name": "S&P 500",
                    "currency": "USD",
                    "tick_size": 0.01,
                    "yahoo_ticker": "^GSPC",
                    "is_active": True,
                },
            ],
            "commodity": [
                {
                    "ticker": "XAUUSD",
                    "asset_name": "Gold",
                    "currency": "USD",
                    "tick_size": 0.01,
                    "yahoo_ticker": "GC=F",
                    "is_active": False,
                },
            ],
        }
    }
    return data


@pytest.fixture
def sample_yaml_path(sample_universe_yaml):
    """Write the sample universe to a temp file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        yaml.dump(sample_universe_yaml, f)
        f.flush()
        path = f.name
    yield path
    Path(path).unlink()


class TestInstrumentMaster:
    """Tests for InstrumentMaster."""

    def test_load_from_yaml(self, sample_yaml_path):
        """Loads instruments from YAML config."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        assert len(master) == 4
        assert "EURUSD" in master
        assert "SPX" in master

    def test_active_tickers(self, sample_yaml_path):
        """Only active instruments are returned by tickers()."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        active = master.tickers(active_only=True)
        assert "EURUSD" in active
        assert "USDJPY" in active
        assert "SPX" in active
        assert "XAUUSD" not in active  # is_active = False

    def test_all_tickers_includes_inactive(self, sample_yaml_path):
        """tickers(active_only=False) returns all instruments."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        all_tickers = master.tickers(active_only=False)
        assert len(all_tickers) == 4
        assert "XAUUSD" in all_tickers

    def test_by_asset_class(self, sample_yaml_path):
        """Filters instruments by asset class."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        fx = master.by_asset_class("fx")
        assert set(fx) == {"EURUSD", "USDJPY"}

        equity = master.by_asset_class("equity_index")
        assert equity == ["SPX"]

    def test_by_base_currency(self, sample_yaml_path):
        """Filters FX instruments by base currency."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        eur_instruments = master.by_base_currency("EUR")
        assert eur_instruments == ["EURUSD"]

    def test_yahoo_ticker(self, sample_yaml_path):
        """Returns correct Yahoo Finance ticker."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        assert master.yahoo_ticker("EURUSD") == "EURUSD=X"
        assert master.yahoo_ticker("SPX") == "^GSPC"

    def test_get_missing_raises(self, sample_yaml_path):
        """KeyError for unknown ticker."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        with pytest.raises(KeyError):
            master.get("NONEXISTENT")

    def test_is_active(self, sample_yaml_path):
        """Correctly reports active status."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        assert master.is_active("EURUSD") is True
        assert master.is_active("XAUUSD") is False

    def test_to_dataframe(self, sample_yaml_path):
        """Exports to DataFrame with ticker as index."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        df = master.to_dataframe(active_only=True)
        assert len(df) == 3
        assert df.index.name == "ticker"
        assert "EURUSD" in df.index

    def test_missing_required_fields_raises(self):
        """Missing required fields raise ValueError."""
        data = {
            "universe": {
                "fx": [
                    {
                        "ticker": "BADPAIR",
                        # Missing base_currency, quote_currency, pip_value, lot_size
                        "yahoo_ticker": "BAD=X",
                        "is_active": True,
                    }
                ]
            }
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            f.flush()
            path = f.name

        try:
            master = InstrumentMaster()
            with pytest.raises(ValueError, match="missing required fields"):
                master.load_from_yaml(path)
        finally:
            Path(path).unlink()

    def test_pip_value(self, sample_yaml_path):
        """Returns correct pip_value."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        assert master.pip_value("EURUSD") == 0.0001
        assert master.pip_value("USDJPY") == 0.01

    def test_repr(self, sample_yaml_path):
        """__repr__ returns informative string."""
        master = InstrumentMaster()
        master.load_from_yaml(sample_yaml_path)
        rep = repr(master)
        assert "InstrumentMaster" in rep
        assert "total=4" in rep

    def test_consecutive_loads_accumulate(self):
        """Loading two YAML files merges instruments."""
        data1 = {
            "universe": {
                "fx": [
                    {
                        "ticker": "EURUSD",
                        "base_currency": "EUR",
                        "quote_currency": "USD",
                        "pip_value": 0.0001,
                        "lot_size": 100000,
                        "tick_size": 0.00001,
                        "yahoo_ticker": "EURUSD=X",
                        "is_active": True,
                    }
                ]
            }
        }
        data2 = {
            "universe": {
                "fx": [
                    {
                        "ticker": "GBPUSD",
                        "base_currency": "GBP",
                        "quote_currency": "USD",
                        "pip_value": 0.0001,
                        "lot_size": 100000,
                        "tick_size": 0.00001,
                        "yahoo_ticker": "GBPUSD=X",
                        "is_active": True,
                    }
                ]
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f1:
            yaml.dump(data1, f1)
            f1.flush()
            p1 = f1.name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f2:
            yaml.dump(data2, f2)
            f2.flush()
            p2 = f2.name

        try:
            master = InstrumentMaster()
            master.load_from_yaml(p1)
            master.load_from_yaml(p2)
            assert len(master) == 2
            assert "EURUSD" in master
            assert "GBPUSD" in master
        finally:
            Path(p1).unlink()
            Path(p2).unlink()