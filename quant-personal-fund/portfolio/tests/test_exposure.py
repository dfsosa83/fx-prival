"""Unit tests for portfolio.exposure module."""
import numpy as np
import pandas as pd
import pytest
import tempfile
from pathlib import Path
import yaml

from core.instruments import InstrumentMaster
from portfolio.exposure import decompose_currency_exposure, detect_concentration


@pytest.fixture
def instrument_master():
    """Instrument master with FX and non-FX instruments."""
    config = {
        "universe": {
            "fx": [
                {"ticker": "EURUSD", "base_currency": "EUR", "quote_currency": "USD",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "EURUSD=X", "is_active": True},
                {"ticker": "USDJPY", "base_currency": "USD", "quote_currency": "JPY",
                 "pip_value": 0.01, "lot_size": 100000, "tick_size": 0.001,
                 "yahoo_ticker": "USDJPY=X", "is_active": True},
                {"ticker": "GBPUSD", "base_currency": "GBP", "quote_currency": "USD",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "GBPUSD=X", "is_active": True},
                {"ticker": "USDCHF", "base_currency": "USD", "quote_currency": "CHF",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "USDCHF=X", "is_active": True},
            ],
            "equity_index": [
                {"ticker": "SPX", "asset_name": "S&P 500", "currency": "USD",
                 "tick_size": 0.01, "yahoo_ticker": "^GSPC", "is_active": True},
            ],
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


class TestDecomposeCurrencyExposure:
    def test_long_eurusd(self, instrument_master):
        """Long EURUSD = +EUR, -USD."""
        positions = pd.DataFrame(
            {"EURUSD": [1.0]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        result = decompose_currency_exposure(positions, instrument_master)
        assert result.loc["2026-01-05", "EUR"] == pytest.approx(1.0)
        assert result.loc["2026-01-05", "USD"] == pytest.approx(-1.0)

    def test_short_eurusd(self, instrument_master):
        """Short EURUSD (negative weight) = -EUR, +USD."""
        positions = pd.DataFrame(
            {"EURUSD": [-1.0]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        result = decompose_currency_exposure(positions, instrument_master)
        assert result.loc["2026-01-05", "EUR"] == pytest.approx(-1.0)
        assert result.loc["2026-01-05", "USD"] == pytest.approx(1.0)

    def test_long_usdjpy(self, instrument_master):
        """Long USDJPY = +USD, -JPY."""
        positions = pd.DataFrame(
            {"USDJPY": [1.0]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        result = decompose_currency_exposure(positions, instrument_master)
        assert result.loc["2026-01-05", "USD"] == pytest.approx(1.0)
        assert result.loc["2026-01-05", "JPY"] == pytest.approx(-1.0)

    def test_currency_netting(self, instrument_master):
        """Long EURUSD + Long USDJPY → EUR +1, JPY -1, USD 0."""
        positions = pd.DataFrame(
            {"EURUSD": [1.0], "USDJPY": [1.0]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        result = decompose_currency_exposure(positions, instrument_master)
        assert result.loc["2026-01-05", "EUR"] == pytest.approx(1.0)
        assert result.loc["2026-01-05", "JPY"] == pytest.approx(-1.0)
        assert result.loc["2026-01-05", "USD"] == pytest.approx(0.0)

    def test_hidden_concentration(self, instrument_master):
        """Long EURUSD + Long GBPUSD + Short USDCHF → large net short USD."""
        positions = pd.DataFrame(
            {"EURUSD": [1.0], "GBPUSD": [1.0], "USDCHF": [-1.0]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        result = decompose_currency_exposure(positions, instrument_master)
        # EURUSD: +EUR, -USD. GBPUSD: +GBP, -USD. Short USDCHF: -USD, +CHF.
        # Total USD: -1 -1 -1 = -3
        assert result.loc["2026-01-05", "USD"] == pytest.approx(-3.0)

    def test_non_fx_instruments(self, instrument_master):
        """SPX treated as local-currency (USD) exposure."""
        positions = pd.DataFrame(
            {"SPX": [0.5]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        result = decompose_currency_exposure(positions, instrument_master)
        assert result.loc["2026-01-05", "USD"] == pytest.approx(0.5)

    def test_multi_date(self, instrument_master):
        """Exposure decomposition works across multiple dates."""
        dates = pd.date_range("2026-01-05", periods=3)
        positions = pd.DataFrame(
            {"EURUSD": [1.0, 0.5, 0.0]},
            index=dates,
        )
        result = decompose_currency_exposure(positions, instrument_master)
        assert len(result) == 3
        assert result.loc[dates[0], "EUR"] == 1.0
        assert result.loc[dates[1], "EUR"] == 0.5
        assert result.loc[dates[2], "EUR"] == 0.0


class TestDetectConcentration:
    def test_no_concentration(self, instrument_master):
        """No concentration when exposures are moderate."""
        positions = pd.DataFrame(
            {"EURUSD": [0.2], "USDJPY": [0.2], "GBPUSD": [0.2]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        exposures = decompose_currency_exposure(positions, instrument_master)
        result = detect_concentration(exposures, threshold=0.5)
        assert len(result) == 0

    def test_concentration_detected(self, instrument_master):
        """Concentration detected when single currency dominates."""
        positions = pd.DataFrame(
            {"EURUSD": [1.0], "GBPUSD": [1.0]},
            index=pd.date_range("2026-01-05", periods=1),
        )
        exposures = decompose_currency_exposure(positions, instrument_master)
        result = detect_concentration(exposures, threshold=0.5)
        assert len(result) > 0