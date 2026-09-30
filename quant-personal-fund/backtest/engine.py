"""
Backtesting engine for the Phase 2 portfolio-research pipeline.

Orchestrates the full pipeline:
    load data → validate → compute returns → accept weights → apply lag →
    compute portfolio → measure risk → produce report
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

from core.calendar import TradingCalendar
from core.costs import CostModel
from core.instruments import InstrumentMaster
from core.returns import returns_from_dataframe, yield_to_price
from data.pipelines.dataset import DatasetMetadata, load_and_validate
from portfolio.accounting import PortfolioResult, compute_portfolio
from risk.metrics import performance_summary

logger = logging.getLogger(__name__)


def _compute_returns_panel(
    prices_df: pd.DataFrame,
    instrument_master: InstrumentMaster,
) -> pd.DataFrame:
    """
    Compute daily log returns from a prices DataFrame.

    For govt_bond instruments, uses yield-to-price conversion.
    For all others, uses adjusted close / close.

    Args:
        prices_df: DataFrame (dates × tickers) of prices.
        instrument_master: InstrumentMaster instance.

    Returns:
        DataFrame (dates × tickers) of daily log returns.
    """
    returns_dict = {}

    for ticker in prices_df.columns:
        prices = prices_df[ticker].dropna()
        if len(prices) < 2:
            logger.warning(f"Insufficient data for {ticker}, skipping")
            continue

        asset_class = instrument_master.asset_class(ticker)

        if instrument_master.get(ticker).get("data_type") == "yield":
            # Yield series → bond return proxy
            returns_dict[ticker] = yield_to_price(prices, maturity_years=10.0)
        elif asset_class == "govt_bond":
            # Bond ETF: standard price returns
            returns_dict[ticker] = np.log(prices / prices.shift(1))
        else:
            # Standard OHLCV → log returns
            returns_dict[ticker] = np.log(prices / prices.shift(1))

    returns_df = pd.DataFrame(returns_dict).sort_index()
    return returns_df


def run_backtest(
    universe_config_path: str,
    cost_model_path: str,
    data_dir: str,
    weights: pd.DataFrame,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    initial_nav: float = 1.0,
    lag: int = 1,
    allow_short: bool = False,
    output_dir: Optional[str] = None,
) -> Tuple[PortfolioResult, Dict[str, Any], DatasetMetadata]:
    """
    Run the full Phase 2 pipeline.

    1. Load instrument master.
    2. Load cost model.
    3. Load and validate OHLCV data for all active instruments.
    4. Compute daily returns panel.
    5. Load and validate externally supplied weights.
    6. Run portfolio accounting with lag and costs.
    7. Compute risk/performance metrics.
    8. Optionally write experiment artifact to output_dir.

    Args:
        universe_config_path: Path to config/universe.yaml.
        cost_model_path: Path to config/cost_model.yaml.
        data_dir: Directory containing raw parquet files.
        weights: DataFrame (dates × tickers) of target weights.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        initial_nav: Starting NAV (default 1.0).
        lag: Trading-day lag (default 1).
        allow_short: Permit negative weights if True.
        output_dir: If provided, write report artifacts here.

    Returns:
        Tuple of (PortfolioResult, metrics_dict, DatasetMetadata).
    """
    # 1. Load instrument master
    master = InstrumentMaster()
    master.load_from_yaml(universe_config_path)
    logger.info(f"Loaded {len(master)} instruments ({len(master.tickers())} active)")

    # 2. Load cost model
    cost_model = CostModel()
    cost_model.load_from_yaml(cost_model_path)
    logger.info(f"Loaded cost model with {len(cost_model.costs)} instruments")

    # 3. Load and validate data
    prices_df, dataset_meta = load_and_validate(
        data_dir=data_dir,
        instrument_master=master,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info(
        f"Loaded {len(prices_df.columns)} instruments, "
        f"{len(prices_df)} dates: {dataset_meta.date_range_start} to {dataset_meta.date_range_end}"
    )

    # 4. Compute returns panel
    returns_panel = _compute_returns_panel(prices_df, master)
    logger.info(f"Returns panel: {len(returns_panel)} dates × {len(returns_panel.columns)} tickers")

    # 5. Validate that weights cover returns dates
    if start_date:
        returns_panel = returns_panel[returns_panel.index >= pd.Timestamp(start_date)]
    if end_date:
        returns_panel = returns_panel[returns_panel.index <= pd.Timestamp(end_date)]

    # 6. Run portfolio accounting
    result = compute_portfolio(
        returns_panel=returns_panel,
        target_weights=weights,
        cost_model=cost_model,
        instrument_master=master,
        initial_nav=initial_nav,
        lag=lag,
        allow_short=allow_short,
    )

    # 7. Compute metrics
    metrics = performance_summary(result, rf_annual=0.0)

    # 8. Write report
    if output_dir:
        _write_report(result, metrics, dataset_meta, output_dir)

    return result, metrics, dataset_meta


def _write_report(
    result: PortfolioResult,
    metrics: Dict[str, Any],
    dataset_meta: DatasetMetadata,
    output_dir: str,
) -> None:
    """Write reproducible experiment artifacts to output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # NAV and returns
    result.nav.to_csv(out / "nav.csv")
    result.returns.to_csv(out / "returns.csv")
    result.positions.to_csv(out / "positions.csv")
    result.costs.to_csv(out / "costs.csv")

    # Turnover
    result.turnover.to_csv(out / "turnover.csv", header=["turnover"])

    # Exposures
    result.exposures.to_csv(out / "exposures.csv")

    # Metrics and metadata
    report = {
        "metrics": {k: str(v) if isinstance(v, float) and np.isinf(v) else v
                     for k, v in metrics.items()},
        "dataset": {
            "dataset_id": dataset_meta.dataset_id,
            "instruments": dataset_meta.instruments,
            "date_range_start": dataset_meta.date_range_start,
            "date_range_end": dataset_meta.date_range_end,
            "inputs_hash": dataset_meta.inputs_hash,
            "validation_errors": dataset_meta.validation_errors,
        },
        "generated_at": datetime.now().isoformat(),
    }
    with open(out / "report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info(f"Report written to {output_dir}")


# ═══════════════════════════════════════════════════════════════════════════
# EXP-2026-04A PATHWAY — benchmark foundation (additive; run_backtest untouched)
# ═══════════════════════════════════════════════════════════════════════════

def load_usd_returns_panel(
    universe_config_path: str,
    data_dir: str,
) -> pd.DataFrame:
    """
    Load the active universe, compute log returns, and convert to USD.

    Uses core.fx conversion for non-USD assets (SX5E/EUR, NKY/JPY) and
    the EURJPY cross-pair rule. Excluded instruments (US10Y, BUND, JGB)
    are simply absent because they are marked is_active: false.

    Returns:
        DataFrame (dates x tickers) of USD log returns (active universe only).
    """
    from core.fx import convert_cross_eurjpy, convert_local_to_usd

    master = InstrumentMaster()
    master.load_from_yaml(universe_config_path)

    prices_df, _ = load_and_validate(data_dir=data_dir, instrument_master=master)

    local_returns = np.log(prices_df / prices_df.shift(1)).dropna(how="all")

    # FX prices needed for conversion legs (EURUSD, USDJPY)
    fx_needed = {"EURUSD": "EURUSD=X", "USDJPY": "USDJPY=X"}
    fx_prices = {}
    for ticker, yt in fx_needed.items():
        if ticker in prices_df.columns:
            fx_prices[ticker] = prices_df[ticker]
    fx_frame = pd.DataFrame(fx_prices)

    result = local_returns.copy()
    # SX5E (EUR) and NKY (JPY) are the non-USD assets in the active universe
    for ticker, ccy in [("SX5E", "EUR"), ("NKY", "JPY")]:
        if ticker in result.columns:
            result[ticker] = convert_local_to_usd(
                local_returns[ticker], fx_frame, ccy, max_ffill_days=5
            )
    # EURJPY cross-pair conversion
    if "EURJPY" in result.columns and "USDJPY" in fx_frame.columns:
        result["EURJPY"] = convert_cross_eurjpy(
            local_returns["EURJPY"], fx_frame["USDJPY"], max_ffill_days=5
        )

    return result.dropna(how="all")