"""
Performance and risk metrics for portfolio evaluation.

All metrics accept NAV or return series and produce scalar values
or decompositions. Designed for daily-frequency data. Annualization
assumes 252 trading days per year.
"""

from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd


def annualized_return(nav: pd.Series, periods_per_year: int = 252) -> float:
    """
    Annualized compound return from a NAV series.

    r_annual = (NAV_end / NAV_start)^(periods_per_year / n) - 1

    Args:
        nav: NAV series (first value is initial NAV).
        periods_per_year: Trading days per year.

    Returns:
        Annualized return as a decimal.
    """
    nav_clean = nav.dropna()
    if len(nav_clean) < 2:
        return 0.0
    total_return = nav_clean.iloc[-1] / nav_clean.iloc[0]
    n = len(nav_clean) - 1
    if n <= 0:
        return 0.0
    return float(total_return ** (periods_per_year / n) - 1.0)


def annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized volatility from daily returns."""
    return float(returns.std() * np.sqrt(periods_per_year))


def sharpe_ratio(
    returns: pd.Series,
    rf_annual: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Annualized Sharpe ratio.

    Sharpe = (mean_return - rf_daily) / std_return * sqrt(periods)

    Args:
        returns: Series of daily returns.
        rf_annual: Annual risk-free rate (decimal).
        periods_per_year: Trading days per year.

    Returns:
        Annualized Sharpe ratio. Returns 0.0 if std is zero.
    """
    rets = returns.dropna()
    if len(rets) < 2:
        return 0.0

    rf_daily = rf_annual / periods_per_year
    excess = rets - rf_daily
    std = excess.std()
    if std == 0.0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: pd.Series,
    rf_annual: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Annualized Sortino ratio (uses downside deviation only).

    Sortino = (mean_return - rf_daily) / downside_deviation * sqrt(periods)

    Args:
        returns: Series of daily returns.
        rf_annual: Annual risk-free rate.
        periods_per_year: Trading days per year.

    Returns:
        Annualized Sortino ratio.
    """
    rets = returns.dropna()
    if len(rets) < 2:
        return 0.0

    rf_daily = rf_annual / periods_per_year
    excess = rets - rf_daily
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float("inf") if excess.mean() > 0 else 0.0

    downside_std = downside.std()
    if downside_std == 0.0:
        return 0.0
    return float(excess.mean() / downside_std * np.sqrt(periods_per_year))


def max_drawdown(nav: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
    """
    Maximum drawdown from a NAV series.

    Drawdown = (NAV - running_peak) / running_peak
    Max drawdown is the most negative value.

    Args:
        nav: NAV series.

    Returns:
        Tuple of (max_drawdown, peak_date, trough_date).
        max_drawdown is negative (e.g., -0.15 for 15% drawdown).
    """
    nav_clean = nav.dropna()
    if len(nav_clean) < 2:
        return (0.0, nav_clean.index[0], nav_clean.index[0])

    running_peak = nav_clean.cummax()
    drawdown = (nav_clean - running_peak) / running_peak
    min_idx = drawdown.idxmin()
    max_dd = drawdown[min_idx]

    # Find the peak date (most recent peak before the trough)
    peak_idx = running_peak[:min_idx].idxmax()

    return (float(max_dd), peak_idx, min_idx)


def drawdown_series(nav: pd.Series) -> pd.Series:
    """
    Running drawdown from the most recent peak.

    Args:
        nav: NAV series.

    Returns:
        Series of drawdown values (0.0 at peaks, negative in drawdowns).
    """
    nav_clean = nav.dropna()
    running_peak = nav_clean.cummax()
    return (nav_clean - running_peak) / running_peak


def calmar_ratio(
    returns: pd.Series,
    nav: pd.Series,
    periods_per_year: int = 252,
) -> float:
    """
    Calmar ratio: annualized return / absolute max drawdown.

    Args:
        returns: Series of daily returns.
        nav: NAV series.
        periods_per_year: Trading days per year.

    Returns:
        Calmar ratio. Positive = return exceeds max drawdown.
    """
    ann_ret = annualized_return(nav, periods_per_year)
    max_dd, _, _ = max_drawdown(nav)
    if max_dd == 0.0:
        return float("inf") if ann_ret > 0 else 0.0
    return ann_ret / abs(max_dd)


def var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Historical Value-at-Risk at a given confidence level.

    VaR at 95% = 5th percentile of returns (most negative daily return
    that is not in the worst 5%).

    Args:
        returns: Series of daily returns.
        confidence: Confidence level (0.95 = 95% VaR).

    Returns:
        VaR as a decimal (negative value). e.g., -0.02 = 2% daily VaR.
    """
    rets = returns.dropna()
    if len(rets) < 10:
        return 0.0
    return float(np.percentile(rets, 100.0 * (1.0 - confidence)))


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Expected Shortfall (CVaR) — average return in the worst (1-confidence) tail.

    Args:
        returns: Series of daily returns.
        confidence: Confidence level.

    Returns:
        Expected shortfall (negative). e.g., -0.03 = average loss of 3% in tail.
    """
    rets = returns.dropna()
    if len(rets) < 10:
        return 0.0

    var = var_historical(rets, confidence)
    tail = rets[rets <= var]
    if len(tail) == 0:
        return var
    return float(tail.mean())


def cost_to_gross_pnl(total_cost: float, total_gross_pnl: float) -> float:
    """
    Cost-to-gross-PnL ratio. Diagnostic for cost dominance.

    A ratio > 1.0 means costs exceed gross PnL — the strategy is
    dominated by transaction costs.

    Args:
        total_cost: Total costs in NAV units.
        total_gross_pnl: Total gross PnL in NAV units.

    Returns:
        Ratio. 0.0 if gross PnL is zero.
    """
    if abs(total_gross_pnl) < 1e-15:
        return float("inf") if total_cost > 0 else 0.0
    return total_cost / abs(total_gross_pnl)


def performance_summary(
    result,  # PortfolioResult from portfolio.accounting
    rf_annual: float = 0.0,
) -> Dict[str, Any]:
    """
    Produce a complete performance metrics dict from a PortfolioResult.

    Args:
        result: PortfolioResult with nav, returns, costs, turnover.
        rf_annual: Annual risk-free rate (decimal).

    Returns:
        Dict of metric names to values.
    """
    nav = result.nav["nav_net"]
    net_returns = result.returns["net_return"]
    gross_returns = result.returns["gross_return"]

    max_dd_val, peak_date, trough_date = max_drawdown(nav)

    total_txn_cost = result.costs["txn_cost"].sum()
    total_hold_cost = result.costs["hold_cost"].sum()
    total_cost = total_txn_cost + total_hold_cost
    total_gross_pnl = gross_returns.sum()

    return {
        # Returns
        "annualized_return": annualized_return(nav),
        "annualized_volatility": annualized_volatility(net_returns),
        "cumulative_return": float(nav.iloc[-1] / nav.iloc[0] - 1.0),
        # Risk-adjusted
        "sharpe_ratio": sharpe_ratio(net_returns, rf_annual),
        "sortino_ratio": sortino_ratio(net_returns, rf_annual),
        "calmar_ratio": calmar_ratio(net_returns, nav),
        # Drawdown
        "max_drawdown": max_dd_val,
        "max_drawdown_peak": str(peak_date.date()),
        "max_drawdown_trough": str(trough_date.date()),
        # Tail risk
        "var_95_daily": var_historical(net_returns, 0.95),
        "expected_shortfall_95": expected_shortfall(net_returns, 0.95),
        # Costs
        "total_txn_cost": float(total_txn_cost),
        "total_hold_cost": float(total_hold_cost),
        "total_cost": float(total_cost),
        "cost_to_gross_pnl": cost_to_gross_pnl(total_cost, total_gross_pnl),
        # Turnover
        "mean_daily_turnover": float(result.turnover.mean()),
        "annualized_turnover": float(result.turnover.sum()),
        # Sample
        "n_days": len(nav.dropna()),
        "start_date": str(nav.dropna().index[0].date()),
        "end_date": str(nav.dropna().index[-1].date()),
    }


# ── Supplementary moving-block bootstrap (EXP-2026-04A) ────────────────────
# These CIs are SUPPLEMENTARY decision evidence only. They are NOT primary
# gates. Maximum drawdown is never bootstrap-gated (Amendment A2).

def moving_block_ci_mean_diff(
    series_a: pd.Series,
    series_b: pd.Series,
    block_length: int = 10,
    n_resamples: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Dict[str, float]:
    """
    Supplementary: moving-block bootstrap CI for mean(a) - mean(b).

    Returns dict with point, ci_lower, ci_upper, block_length, n_resamples.
    """
    common = series_a.dropna().index.intersection(series_b.dropna().index)
    a = series_a.loc[common].values
    b = series_b.loc[common].values
    n = len(common)
    if n == 0 or block_length > n:
        raise ValueError("Insufficient aligned data for block bootstrap")

    rng = np.random.RandomState(seed)
    n_blocks = int(np.ceil(n / block_length))
    n_possible = n - block_length + 1

    diffs = a - b
    point = float(diffs.mean())
    boot = np.empty(n_resamples)
    for i in range(n_resamples):
        starts = rng.randint(0, n_possible, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        boot[i] = diffs[idx].mean()

    alpha = (1.0 - ci) / 2.0
    return {
        "point_estimate": point,
        "ci_lower": float(np.percentile(boot, 100.0 * alpha)),
        "ci_upper": float(np.percentile(boot, 100.0 * (1.0 - alpha))),
        "ci_level": ci,
        "block_length": block_length,
        "n_resamples": n_resamples,
    }


def moving_block_ci_sharpe_diff(
    returns_a: pd.Series,
    returns_b: pd.Series,
    rf_annual: float = 0.0,
    block_length: int = 10,
    n_resamples: int = 1000,
    ci: float = 0.95,
    seed: int = 42,
) -> Dict[str, float]:
    """
    Supplementary: moving-block bootstrap CI for Sharpe(a) - Sharpe(b).

    Resamples paired blocks and computes the Sharpe difference per resample.
    """
    common = returns_a.dropna().index.intersection(returns_b.dropna().index)
    a = returns_a.loc[common].values
    b = returns_b.loc[common].values
    n = len(common)
    if n == 0 or block_length > n:
        raise ValueError("Insufficient aligned data for block bootstrap")

    rng = np.random.RandomState(seed)
    n_blocks = int(np.ceil(n / block_length))
    n_possible = n - block_length + 1
    rf_daily = rf_annual / 252.0

    def sharpe_of(x: np.ndarray) -> float:
        if x.std(ddof=1) <= 0:
            return 0.0
        return float((x - rf_daily).mean() / x.std(ddof=1) * np.sqrt(252.0))

    point = sharpe_of(a) - sharpe_of(b)
    boot = np.empty(n_resamples)
    for i in range(n_resamples):
        starts = rng.randint(0, n_possible, size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        boot[i] = sharpe_of(a[idx]) - sharpe_of(b[idx])

    alpha = (1.0 - ci) / 2.0
    return {
        "point_estimate": point,
        "ci_lower": float(np.percentile(boot, 100.0 * alpha)),
        "ci_upper": float(np.percentile(boot, 100.0 * (1.0 - alpha))),
        "ci_level": ci,
        "block_length": block_length,
        "n_resamples": n_resamples,
    }


def drawdown_episodes(
    nav: pd.Series,
    min_depth: float = 0.02,
) -> list:
    """
    Report observed maximum drawdown, duration, and major drawdown episodes.

    An episode runs from a running peak until the NAV recovers above that peak.

    Args:
        nav: NAV series.
        min_depth: Minimum episode depth (fraction) to include.

    Returns:
        List of dicts: {start, trough, end, depth, duration_days, recovered}.
        Includes the maximum drawdown episode regardless of min_depth.
    """
    nav_clean = nav.dropna()
    if len(nav_clean) < 2:
        return []

    running_peak = nav_clean.cummax()
    drawdown = (nav_clean - running_peak) / running_peak

    episodes = []
    peak_idx = nav_clean.index[0]
    peak_val = nav_clean.iloc[0]
    trough_idx = None
    trough_val = peak_val

    for idx in nav_clean.index:
        val = nav_clean.loc[idx]
        if val >= peak_val:
            # Close any open episode
            if trough_idx is not None:
                depth = (trough_val - peak_val) / peak_val
                episodes.append({
                    "start": str(peak_idx.date()),
                    "trough": str(trough_idx.date()),
                    "end": str(idx.date()),
                    "depth": float(depth),
                    "duration_days": int((idx - peak_idx).days),
                    "recovered": True,
                })
            peak_idx, peak_val = idx, val
            trough_idx, trough_val = None, val
        else:
            if val < trough_val or trough_idx is None:
                trough_idx, trough_val = idx, val

    # Open episode at the end
    if trough_idx is not None and trough_val < peak_val:
        depth = (trough_val - peak_val) / peak_val
        episodes.append({
            "start": str(peak_idx.date()),
            "trough": str(trough_idx.date()),
            "end": None,
            "depth": float(depth),
            "duration_days": int((trough_idx - peak_idx).days),
            "recovered": False,
        })

    # Filter by min_depth but always keep the deepest
    if episodes:
        deepest = max(episodes, key=lambda e: abs(e["depth"]))
        episodes = [e for e in episodes if abs(e["depth"]) >= min_depth or e is deepest]

    return episodes