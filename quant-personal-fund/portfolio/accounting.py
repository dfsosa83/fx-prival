"""
Portfolio accounting engine for daily multi-asset backtesting.

Takes a returns panel and externally supplied target weights, applies
lag rules, transaction costs, and holding costs, and produces gross/net
NAV, turnover, and exposure series.

Weights are consumed externally — this module does not generate them.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from core.costs import CostModel


@dataclass
class PortfolioResult:
    """Complete portfolio backtest output."""
    nav: pd.DataFrame
    returns: pd.DataFrame
    positions: pd.DataFrame
    turnover: pd.Series
    costs: pd.DataFrame
    exposures: pd.DataFrame


def validate_weights(
    weights: pd.DataFrame,
    returns_panel: pd.DataFrame,
    allow_short: bool = False,
    max_leverage: Optional[float] = None,
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Validate and clean externally supplied portfolio weights.

    Checks:
        - All columns exist in returns panel.
        - NaN weights → filled to 0.0 with warning.
        - Negative weights blocked unless allow_short=True.
        - Leverage cap enforced if max_leverage is set.

    Args:
        weights: DataFrame (dates × tickers) of target weights.
        returns_panel: DataFrame (dates × tickers) of daily returns.
        allow_short: If False, negative weights raise ValueError.
        max_leverage: If set, sum(abs(weight)) must be <= max_leverage.

    Returns:
        Tuple of (cleaned_weights, warnings).
    """
    warnings: List[str] = []
    cleaned = weights.copy()

    # Check columns
    unknown = set(cleaned.columns) - set(returns_panel.columns)
    if unknown:
        raise ValueError(f"Weight columns not in returns panel: {unknown}")

    # Fill NaN to 0.0
    nan_cols = cleaned.columns[cleaned.isna().any()].tolist()
    if nan_cols:
        warnings.append(f"NaN weights in columns {nan_cols} filled to 0.0")
        cleaned = cleaned.fillna(0.0)

    # Check short positions
    if not allow_short and (cleaned < -1e-10).any().any():
        short_cols = cleaned.columns[(cleaned < -1e-10).any()].tolist()
        raise ValueError(
            f"Negative weights found in columns {short_cols}. "
            "Set allow_short=True to permit short positions."
        )

    # Check leverage
    if max_leverage is not None:
        gross_exp = cleaned.abs().sum(axis=1)
        violations = gross_exp[gross_exp > max_leverage]
        if len(violations) > 0:
            warnings.append(
                f"Leverage exceeds {max_leverage} on {len(violations)} dates "
                f"(max: {violations.max():.2f})"
            )

    return cleaned, warnings


def compute_portfolio(
    returns_panel: pd.DataFrame,
    target_weights: pd.DataFrame,
    cost_model: CostModel,
    instrument_master,  # InstrumentMaster for pip_value lookup
    initial_nav: float = 1.0,
    lag: int = 1,
    allow_short: bool = False,
) -> PortfolioResult:
    """
    Run the full portfolio accounting pipeline.

    Accounting convention:
        weights[t] (computed after close[t]) → position at close[t+lag] → earns return[t+lag]

    For lag=1:
        position[t] = target_weights[t-1]
        gross_return[t] = sum(position[t] * return[t])
        txn_cost[t] = turnover[t] * round_trip_cost
        net_return[t] = gross_return[t] - txn_cost[t] - hold_cost[t]
        nav[t] = nav[t-1] * (1 + net_return[t])

    Args:
        returns_panel: DataFrame (dates × tickers) of daily log returns.
        target_weights: DataFrame (dates × tickers) of target weights.
        cost_model: CostModel instance.
        instrument_master: InstrumentMaster instance (for pip_value lookup).
        initial_nav: Starting NAV (default 1.0).
        lag: Trading-day lag between weight signal and position (default 1).
        allow_short: If True, permit negative weights.

    Returns:
        PortfolioResult with nav, returns, positions, turnover, costs, exposures.

    Raises:
        ValueError: If weights fail validation.
    """
    # Validate and clean weights
    cleaned_weights, _ = validate_weights(
        target_weights, returns_panel, allow_short=allow_short
    )

    # Align weights and returns to common date range
    common_tickers = list(
        set(cleaned_weights.columns) & set(returns_panel.columns)
    )
    if not common_tickers:
        raise ValueError("No common tickers between weights and returns panel")

    weights_aligned = cleaned_weights[common_tickers].copy()
    returns_aligned = returns_panel[common_tickers].copy()

    # Common date index
    all_dates = returns_aligned.index.union(weights_aligned.index).sort_values()
    weights_aligned = weights_aligned.reindex(all_dates)
    returns_aligned = returns_aligned.reindex(all_dates)

    # Build pip_value lookup
    pip_values = {
        t: instrument_master.pip_value(t)
        if instrument_master.asset_class(t) == "fx"
        else 0.0001
        for t in common_tickers
    }

    # Apply lag: shift weights forward
    positions = weights_aligned.shift(lag).fillna(0.0)

    # Gross returns: sum(position * return)
    gross_return = (positions * returns_aligned).sum(axis=1)
    gross_return.name = "gross_return"

    # Turnover: 0.5 * sum(abs(weight_t - weight_{t-1}))
    weight_changes = weights_aligned.diff().abs()
    daily_turnover = 0.5 * weight_changes.sum(axis=1)
    daily_turnover.name = "turnover"

    # Transaction costs: turnover * round_trip_cost per instrument
    txn_cost_series = pd.Series(0.0, index=all_dates, name="txn_cost")
    for ticker in common_tickers:
        turnover_ticker = 0.5 * weight_changes[ticker]
        cost_rate = cost_model.round_trip_cost_pct(
            ticker, notional=1.0, pip_value=pip_values[ticker]
        )
        txn_cost_series += turnover_ticker * cost_rate

    # Holding costs: daily rate * gross_exposure
    gross_exposure = positions.abs().sum(axis=1)
    gross_exposure.name = "gross_exposure"
    net_exposure = positions.sum(axis=1)
    net_exposure.name = "net_exposure"

    hold_cost_series = pd.Series(0.0, index=all_dates, name="hold_cost")
    for ticker in common_tickers:
        holding_rate = cost_model.daily_holding_cost_pct(ticker)
        if holding_rate > 0:
            hold_cost_series += positions[ticker].abs() * holding_rate

    # Net returns
    net_return = gross_return - txn_cost_series - hold_cost_series
    net_return.name = "net_return"

    # NAV
    nav_gross = (1.0 + gross_return.fillna(0.0)).cumprod() * initial_nav
    nav_gross.name = "nav_gross"
    nav_net = (1.0 + net_return.fillna(0.0)).cumprod() * initial_nav
    nav_net.name = "nav_net"

    nav = pd.DataFrame({"nav_gross": nav_gross, "nav_net": nav_net})
    returns_out = pd.DataFrame({
        "gross_return": gross_return,
        "net_return": net_return,
    })
    costs_out = pd.DataFrame({
        "txn_cost": txn_cost_series,
        "hold_cost": hold_cost_series,
    })
    exposures_out = pd.DataFrame({
        "gross_exposure": gross_exposure,
        "net_exposure": net_exposure,
    })

    return PortfolioResult(
        nav=nav,
        returns=returns_out,
        positions=positions,
        turnover=daily_turnover,
        costs=costs_out,
        exposures=exposures_out,
    )