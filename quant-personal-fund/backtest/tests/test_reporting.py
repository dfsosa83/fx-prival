"""Unit tests for backtest.reporting module."""
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from core.costs import CostModel
from core.instruments import InstrumentMaster
from portfolio.accounting import compute_portfolio
from backtest.reporting import generate_report
from data.pipelines.dataset import DatasetMetadata
from risk.metrics import performance_summary


@pytest.fixture
def sample_portfolio_result():
    """Generate a PortfolioResult for testing."""
    dates = pd.date_range("2026-01-05", periods=20, freq="B")
    returns = pd.DataFrame({
        "A": np.random.RandomState(1).randn(20) * 0.01,
        "B": np.random.RandomState(2).randn(20) * 0.01,
    }, index=dates)

    cost_config = {
        "defaults": {"slippage_pips_fx": 0.0},
        "instruments": {
            "A": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
            "B": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(cost_config, f)
        f.flush()
        cost_path = f.name

    inst_config = {
        "universe": {
            "fx": [
                {"ticker": "A", "base_currency": "AA", "quote_currency": "BB",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "A=X", "is_active": True},
                {"ticker": "B", "base_currency": "BB", "quote_currency": "CC",
                 "pip_value": 0.0001, "lot_size": 100000, "tick_size": 0.00001,
                 "yahoo_ticker": "B=X", "is_active": True},
            ]
        }
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(inst_config, f)
        f.flush()
        inst_path = f.name

    cm = CostModel()
    cm.load_from_yaml(cost_path)
    im = InstrumentMaster()
    im.load_from_yaml(inst_path)

    weights = pd.DataFrame(
        {"A": [0.6] * 20, "B": [0.4] * 20},
        index=dates,
    )
    result = compute_portfolio(returns, weights, cm, im)

    # Cleanup
    Path(cost_path).unlink()
    Path(inst_path).unlink()

    return result


@pytest.fixture
def sample_metadata():
    """Sample DatasetMetadata."""
    return DatasetMetadata(
        dataset_id="test_dataset_001",
        instruments=["A", "B"],
        date_range_start="2026-01-05",
        date_range_end="2026-02-02",
        row_counts={"A": 20, "B": 20},
        missing_pct={"A": 0.0, "B": 0.0},
        validation_errors=0,
        total_validation_warnings=0,
        inputs_hash="abc123",
        created_at="2026-09-22T00:00:00",
    )


class TestGenerateReport:
    def test_writes_artifacts(self, sample_portfolio_result, sample_metadata):
        """Report generation creates all expected files."""
        metrics = performance_summary(sample_portfolio_result)
        with tempfile.TemporaryDirectory() as out_dir:
            path = generate_report(
                result=sample_portfolio_result,
                metrics=metrics,
                dataset_meta=sample_metadata,
                output_dir=out_dir,
                experiment_id="EXP-TEST-001",
            )

            assert Path(out_dir, "nav.csv").exists()
            assert Path(out_dir, "returns.csv").exists()
            assert Path(out_dir, "positions.csv").exists()
            assert Path(out_dir, "costs.csv").exists()
            assert Path(out_dir, "turnover.csv").exists()
            assert Path(out_dir, "exposures.csv").exists()
            assert Path(out_dir, "report.json").exists()
            assert Path(out_dir, "summary.md").exists()

    def test_report_json_valid(self, sample_portfolio_result, sample_metadata):
        """report.json is valid JSON with required fields."""
        metrics = performance_summary(sample_portfolio_result)
        with tempfile.TemporaryDirectory() as out_dir:
            generate_report(
                result=sample_portfolio_result,
                metrics=metrics,
                dataset_meta=sample_metadata,
                output_dir=out_dir,
                experiment_id="EXP-TEST-001",
            )
            with open(Path(out_dir, "report.json")) as f:
                report = json.load(f)
            assert "metrics" in report
            assert "dataset" in report
            assert "generated_at" in report
            assert report["experiment_id"] == "EXP-TEST-001"

    def test_summary_contains_metrics(self, sample_portfolio_result, sample_metadata):
        """summary.md includes key metrics."""
        metrics = performance_summary(sample_portfolio_result)
        with tempfile.TemporaryDirectory() as out_dir:
            generate_report(
                result=sample_portfolio_result,
                metrics=metrics,
                dataset_meta=sample_metadata,
                output_dir=out_dir,
                experiment_id="EXP-TEST-001",
            )
            with open(Path(out_dir, "summary.md")) as f:
                content = f.read()
            assert "Sharpe Ratio" in content
            assert "Max Drawdown" in content

    def test_nav_csv_matches_result(self, sample_portfolio_result, sample_metadata):
        """nav.csv contains the same data as result.nav."""
        metrics = performance_summary(sample_portfolio_result)
        with tempfile.TemporaryDirectory() as out_dir:
            generate_report(
                result=sample_portfolio_result,
                metrics=metrics,
                dataset_meta=sample_metadata,
                output_dir=out_dir,
            )
            nav_csv = pd.read_csv(Path(out_dir, "nav.csv"), index_col=0)
            assert len(nav_csv) == len(sample_portfolio_result.nav)
            assert "nav_gross" in nav_csv.columns