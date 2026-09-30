"""Unit tests for data.pipelines.dataset module."""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from core.instruments import InstrumentMaster
from data.pipelines.dataset import DatasetMetadata, load_and_validate, register_dataset


@pytest.fixture
def instrument_master():
    """Minimal 2-asset instrument master."""
    config = {
        "universe": {
            "fx": [
                {"ticker": "T1", "base_currency": "A", "quote_currency": "B",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "T1_TEST", "is_active": True},
                {"ticker": "T2", "base_currency": "B", "quote_currency": "C",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "T2_TEST", "is_active": True},
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


@pytest.fixture
def data_dir():
    """Create temp dir with valid OHLCV parquet files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dates = pd.date_range("2026-01-05", periods=10, freq="B")
        for ticker in ["T1_TEST", "T2_TEST"]:
            df = pd.DataFrame({
                "date": dates,
                "open": np.random.uniform(1.0, 2.0, 10),
                "high": np.random.uniform(1.5, 2.5, 10),
                "low": np.random.uniform(0.5, 1.5, 10),
                "close": np.random.uniform(1.0, 2.0, 10),
                "adj_close": np.random.uniform(1.0, 2.0, 10),
                "volume": np.random.randint(100, 1000, 10),
            })
            # Ensure OHL consistency
            df["high"] = df[["open", "high", "close"]].max(axis=1)
            df["low"] = df[["open", "low", "close"]].min(axis=1)
            df.to_parquet(Path(tmpdir) / f"{ticker}_daily.parquet")
        yield tmpdir


class TestLoadAndValidate:
    def test_loads_valid_data(self, data_dir, instrument_master):
        """Loads and validates clean data."""
        prices_df, metadata = load_and_validate(
            data_dir=data_dir,
            instrument_master=instrument_master,
        )
        assert isinstance(prices_df, pd.DataFrame)
        assert len(prices_df.columns) == 2
        assert "T1" in prices_df.columns
        assert "T2" in prices_df.columns
        assert isinstance(metadata, DatasetMetadata)
        assert metadata.validation_errors == 0

    def test_metadata_has_required_fields(self, data_dir, instrument_master):
        """Metadata includes all required provenance fields."""
        _, metadata = load_and_validate(
            data_dir=data_dir,
            instrument_master=instrument_master,
        )
        assert metadata.dataset_id.startswith("universe_daily_")
        assert len(metadata.instruments) == 2
        assert metadata.date_range_start is not None
        assert metadata.date_range_end is not None
        assert metadata.inputs_hash is not None

    def test_missing_file_warning(self, data_dir, instrument_master):
        """Missing data file logs warning but does not crash."""
        # Deactivate T2 to avoid needing its file
        instrument_master.instruments["T2"]["is_active"] = False
        instrument_master._refresh_active()

        prices_df, metadata = load_and_validate(
            data_dir=data_dir,
            instrument_master=instrument_master,
        )
        assert "T1" in prices_df.columns
        assert "T2" not in prices_df.columns


class TestRegisterDataset:
    def test_writes_json(self, data_dir, instrument_master):
        """Register writes valid JSON metadata."""
        _, metadata = load_and_validate(
            data_dir=data_dir,
            instrument_master=instrument_master,
        )
        with tempfile.TemporaryDirectory() as out_dir:
            path = register_dataset(metadata, out_dir)
            assert Path(path).exists()
            import json
            with open(path) as f:
                data = json.load(f)
            assert data["dataset_id"] == metadata.dataset_id
            assert data["validation_errors"] == 0

    def test_no_active_instruments_raises(self, instrument_master):
        """Empty universe raises ValueError."""
        instrument_master.instruments["T1"]["is_active"] = False
        instrument_master.instruments["T2"]["is_active"] = False
        instrument_master._refresh_active()
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="No active"):
                load_and_validate(data_dir=tmpdir, instrument_master=instrument_master)