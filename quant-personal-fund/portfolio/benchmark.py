"""
Benchmark A (buy-and-hold) and Benchmark B (monthly-rebalanced, PRIMARY)
for the EXP-2026-04A active universe.

Both are USD-denominated equal-weight benchmarks on the 15-instrument
active universe, built on portfolio.accounting_v2.
"""

from typing import List, Optional, Tuple

import pandas as pd

from core.costs import CostModel
from portfolio.accounting_v2 import (
    PortfolioResultV2,
    compute_buy_and_hold,
    compute_monthly_rebalanced,
)


def equal_weights_for(tickers: List[str]) -> pd.Series:
    """Equal weights 1/N for the given tickers."""
    n = len(tickers)
    if n == 0:
        raise ValueError("Cannot build equal weights for an empty universe")
    return pd.Series(1.0 / n, index=tickers)


def build_benchmarks(
    returns_usd: pd.DataFrame,
    cost_model: CostModel,
    active_tickers: List[str],
    initial_nav: float = 1.0,
    rebalance_freq: str = "M",
) -> Tuple[PortfolioResultV2, PortfolioResultV2]:
    """
    Build Benchmark A and Benchmark B.

    Args:
        returns_usd: DataFrame (dates x tickers) of USD log returns.
        cost_model: CostModel (one-way cost API).
        active_tickers: Active universe tickers.
        initial_nav: Starting NAV.
        rebalance_freq: 'M' for Benchmark B (month-end).

    Returns:
        (benchmark_A, benchmark_B). Benchmark B is PRIMARY.
    """
    tickers = [t for t in active_tickers if t in returns_usd.columns]
    weights = equal_weights_for(tickers)

    benchmark_a = compute_buy_and_hold(returns_usd[tickers], cost_model, weights, initial_nav)
    benchmark_b = compute_monthly_rebalanced(
        returns_usd[tickers], cost_model, weights, initial_nav, cash_weight_value=0.0
    )
    return benchmark_a, benchmark_b