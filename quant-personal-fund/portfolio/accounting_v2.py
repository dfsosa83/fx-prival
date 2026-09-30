"""
Economic portfolio accounting engine (v2) — EXP-2026-04A.

Supersedes the accounting semantics of portfolio/accounting.py for
benchmark construction. Key differences:

    1. Tracks ACTUAL economic holdings (drifted weights), target weights,
       and trade weights — not a free-rebalancing target approximation.
    2. Charges the initial allocation transaction cost ONCE.
    3. Financing is charged ONLY via daily holding cost (never inside
       transaction costs) — fixes the confirmed H1 double-charge.
    4. Exposes net_exposure, gross_exposure, explicit cash_weight, and a
       reserved collateral field as SEPARATE concepts.
    5. Implements the approved DAILY NEXT-OBSERVATION / NEXT-RETURN-INTERVAL
       convention (see experiment manifest EXP-2026-04A):
           - target formed at close[D] using info through D
           - effective for return interval r[D+1]
           - transaction costs booked on D+1 for that next-observation position

    Execution-grade timing, bid/ask fills, and intraday session alignment
    are OUT OF SCOPE (research convention only).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from core.costs import CostModel


@dataclass
class PortfolioResultV2:
    """Economic portfolio backtest output (v2)."""

    nav: pd.DataFrame                 # nav_gross, nav_net (dates x 2)
    returns: pd.DataFrame             # gross_return, net_return (dates x 2)
    holdings_w: pd.DataFrame          # dates x tickers (drifted economic weights, start-of-interval)
    target_w: pd.DataFrame            # dates x tickers (target weights)
    trade_w: pd.DataFrame             # dates x tickers (traded weights; nonzero on entry/rebalance)
    turnover: pd.Series               # daily turnover (0.5 * sum|trade_w|)
    costs: pd.DataFrame               # txn_cost, hold_cost (dates x 2)
    exposures: pd.DataFrame           # net_exposure, gross_exposure, cash_weight (dates x 3)
    collateral_margin: Optional[pd.DataFrame] = None  # RESERVED — always None in 04A


# ---------------------------------------------------------------------------
# Exposure / cash helpers
# ---------------------------------------------------------------------------

def _exposures(holdings_w: pd.DataFrame, cash_weight: pd.Series) -> pd.DataFrame:
    """
    Build the exposure frame from holdings and explicit cash weight.

    net_exposure   = sum(holdings_w)          (signed)
    gross_exposure = sum(|holdings_w|)
    cash_weight    = explicit allocation (0 for benchmarks A/B)

    cash_weight is ASSIGNED, never derived as 1 - net. The consistency
    invariant cash_weight + net_exposure == 1 is asserted by callers.
    """
    net = holdings_w.sum(axis=1)
    gross = holdings_w.abs().sum(axis=1)
    return pd.DataFrame({
        "net_exposure": net,
        "gross_exposure": gross,
        "cash_weight": cash_weight.reindex(holdings_w.index).fillna(0.0),
    })


def _daily_hold_cost(
    holdings_w: pd.DataFrame,
    cost_model: CostModel,
) -> pd.Series:
    """Daily holding cost = sum(|holdings_w_i| * daily_holding_rate_i)."""
    hold = pd.Series(0.0, index=holdings_w.index)
    for ticker in holdings_w.columns:
        rate = cost_model.daily_holding_cost_pct(ticker)
        if rate > 0:
            hold = hold + holdings_w[ticker].abs() * rate
    return hold


def _drift_weights(
    holdings_w_prev: pd.Series,
    returns_t: pd.Series,
) -> pd.Series:
    """
    Drift holdings from start-of-interval t to start-of-interval t+1.

    Uses simple compounding from log returns:
        w_i' = w_i * exp(r_i) / sum(w_j * exp(r_j))
    """
    exp_r = np.exp(returns_t.fillna(0.0).clip(lower=-10.0, upper=10.0))
    num = holdings_w_prev * exp_r
    denom = num.sum()
    if denom <= 0:
        return pd.Series(0.0, index=holdings_w_prev.index)
    return num / denom


def _rebalance_dates(dates: pd.DatetimeIndex, freq: str) -> List[pd.Timestamp]:
    """
    Last trading day of each period (month-end by default).

    Same period-end convention as portfolio/builder.py trend_weights.
    """
    period = pd.Series(dates.to_period(freq))
    is_last = period != period.shift(-1)
    return [d for d, flag in zip(dates, is_last) if flag]


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

def compute_economic_benchmark(
    returns_usd: pd.DataFrame,
    cost_model: CostModel,
    initial_weights: pd.Series,
    initial_nav: float = 1.0,
    rebalance_freq: Optional[str] = "M",
    cash_weight_value: float = 0.0,
    entry_direction: str = "entry",
) -> PortfolioResultV2:
    """
    Run the economic accounting engine for benchmark A (rebalance_freq=None)
    or benchmark B (rebalance_freq="M").

    Convention (EXP-2026-04A manifest):
        - At close[D], targets formed using info through D.
        - Target effective for return interval r[D+1].
        - Transaction costs booked on D+1 for that next-observation position.

    Args:
        returns_usd: DataFrame (dates x tickers) of USD log returns.
        cost_model: CostModel with one_way/entry/exit cost API.
        initial_weights: Series (tickers) summing to 1.0 (equal-weight 1/N).
        initial_nav: Starting NAV.
        rebalance_freq: 'M' (month-end) for benchmark B; None for A.
        cash_weight_value: explicit cash allocation (0.0 for A/B).
        entry_direction: 'entry' (research) — symmetric interface reserved.

    Returns:
        PortfolioResultV2.
    """
    tickers = [t for t in returns_usd.columns if t in initial_weights.index]
    returns = returns_usd[tickers].copy()
    n = len(tickers)
    if n == 0:
        raise ValueError("No overlapping tickers between returns and initial_weights")

    dates = returns.index
    n_days = len(dates)

    # Precompute one-way transaction cost per ticker (fraction of notional).
    # Financing EXCLUDED by the one-way API (H1 fix).
    pip_value_map: Dict[str, float] = {}
    one_way_cost: Dict[str, float] = {}
    for t in tickers:
        # pip_value only matters for FX (spread > 0). We use 0.0001 default;
        # the cost table for FX pairs drives the pip conversion.
        one_way_cost[t] = cost_model.one_way_transaction_cost(
            t, notional=1.0, pip_value=pip_value_map.get(t, 0.0001)
        )

    holdings = pd.DataFrame(0.0, index=dates, columns=tickers)
    targets = pd.DataFrame(0.0, index=dates, columns=tickers)
    trades = pd.DataFrame(0.0, index=dates, columns=tickers)
    gross_ret = pd.Series(0.0, index=dates)
    txn_cost = pd.Series(0.0, index=dates)
    turnover_series = pd.Series(0.0, index=dates)

    if rebalance_freq is not None:
        reb_dates = set(_rebalance_dates(dates, rebalance_freq))
    else:
        reb_dates = set()

    # ── Day 0: initial allocation at close[dates[0]] ──────────────────────
    # Target formed at close[0]; effective for r[1]; entry txn booked at day 1.
    target0 = initial_weights.reindex(tickers).fillna(0.0)
    if abs(target0.sum() - 1.0) > 1e-6:
        target0 = target0 / target0.sum()
    targets.iloc[0] = target0.values

    holdings.iloc[0] = target0.values      # start-of-interval 1 weights (effective for r[1])
    trades.iloc[0] = target0.values        # initial allocation trade decided at close[0]

    entry_turnover = 0.5 * target0.abs().sum()
    entry_cost_t0 = sum(
        w * one_way_cost[t] for t, w in zip(tickers, target0.values)
    )

    # ── Iterate days 1..N-1 ────────────────────────────────────────────────
    cash_series = pd.Series(cash_weight_value, index=dates)

    for i in range(1, n_days):
        date = dates[i]
        r_t = returns.iloc[i]              # returns for interval [i-1, i]

        # Market return applied to the position effective for this interval
        gross_ret.iloc[i] = float((holdings.iloc[i - 1] * r_t.fillna(0.0)).sum())

        # Drift holdings from start-of-interval i to start-of-interval i+1
        drifted = _drift_weights(holdings.iloc[i - 1], r_t)

        if date in reb_dates and rebalance_freq is not None:
            # Rebalance decision at close[i]: trade = target - drifted
            target_i = target0.reindex(tickers).fillna(0.0)
            targets.iloc[i] = target_i.values
            trade_i = target_i - drifted
            trades.iloc[i] = trade_i.values
            holdings.iloc[i] = target_i.values   # effective for r[i+1]
            # Turnover and txn cost booked for this trade (next-observation position)
            turnover_series.iloc[i] = 0.5 * trade_i.abs().sum()
            txn_cost.iloc[i] = sum(
                abs(tw) * one_way_cost[t]
                for t, tw in zip(tickers, trade_i.values)
            )
        else:
            # No trade: holdings continue to drift
            targets.iloc[i] = targets.iloc[i - 1].values
            holdings.iloc[i] = drifted.values
            txn_cost.iloc[i] = 0.0

    # ── Book the INITIAL ENTRY cost and turnover at day 1 ──────────────────
    # Entry trade decided at close[0]; cost booked at day 1 per convention.
    txn_cost.iloc[1] = txn_cost.iloc[1] + entry_cost_t0
    turnover_series.iloc[1] = turnover_series.iloc[1] + entry_turnover

    # ── Holding costs: position held during interval i is holdings[i-1] ────
    # hold_cost[i] = daily rate * |holdings[i-1]| (for i >= 1); day 0 = 0.
    hold_cost = pd.Series(0.0, index=dates)
    for i in range(1, n_days):
        hold_cost.iloc[i] = _daily_hold_cost(
            holdings.iloc[[i - 1]], cost_model
        ).iloc[0]

    # ── Build NAV ──────────────────────────────────────────────────────────
    nav_gross = (1.0 + gross_ret.fillna(0.0)).cumprod() * initial_nav
    net_ret = gross_ret - txn_cost - hold_cost
    nav_net = (1.0 + net_ret.fillna(0.0)).cumprod() * initial_nav

    exposures = _exposures(holdings, cash_series)

    return PortfolioResultV2(
        nav=pd.DataFrame({"nav_gross": nav_gross, "nav_net": nav_net}),
        returns=pd.DataFrame({"gross_return": gross_ret, "net_return": net_ret}),
        holdings_w=holdings,
        target_w=targets,
        trade_w=trades,
        turnover=turnover_series,
        costs=pd.DataFrame({"txn_cost": txn_cost, "hold_cost": hold_cost}),
        exposures=exposures,
        collateral_margin=None,
    )


def compute_buy_and_hold(
    returns_usd: pd.DataFrame,
    cost_model: CostModel,
    initial_weights: pd.Series,
    initial_nav: float = 1.0,
    cash_weight_value: float = 0.0,
) -> PortfolioResultV2:
    """Benchmark A: USD buy-and-hold equal-weight after one initial allocation."""
    return compute_economic_benchmark(
        returns_usd, cost_model, initial_weights,
        initial_nav=initial_nav, rebalance_freq=None,
        cash_weight_value=cash_weight_value,
    )


def compute_monthly_rebalanced(
    returns_usd: pd.DataFrame,
    cost_model: CostModel,
    initial_weights: pd.Series,
    initial_nav: float = 1.0,
    cash_weight_value: float = 0.0,
) -> PortfolioResultV2:
    """Benchmark B (PRIMARY): USD monthly-rebalanced equal-weight with drift/trades."""
    return compute_economic_benchmark(
        returns_usd, cost_model, initial_weights,
        initial_nav=initial_nav, rebalance_freq="M",
        cash_weight_value=cash_weight_value,
    )