"""
Volatility estimation for multi-asset portfolios.

Provides functions for estimating volatility from return series using
multiple methods: exponentially weighted moving average (EWMA), realized
volatility, and Parkinson (high-low range-based) volatility.
"""

from typing import Optional, Union

import numpy as np
import pandas as pd


def ewma_volatility(
    returns: pd.Series,
    halflife: int = 60,
    annualize: bool = True,
    periods_per_year: int = 252,
    min_periods: int = 20,
) -> pd.Series:
    """
    Exponentially weighted moving average volatility.

    Uses the standard RiskMetrics EWMA estimator:
        sigma^2_t = lambda * sigma^2_{t-1} + (1 - lambda) * r^2_t
    where lambda = exp(-ln(2) / halflife).

    Args:
        returns: Series of daily returns (simple or log).
        halflife: EWMA halflife in periods (default 60 trading days).
        annualize: If True, annualize by sqrt(periods_per_year).
        periods_per_year: Trading periods per year (252 for daily).
        min_periods: Minimum non-NaN observations before producing a value.

    Returns:
        Series of volatility estimates aligned to the returns index.
    """
    variance = returns.pow(2).ewm(
        halflife=halflife,
        min_periods=min_periods,
        adjust=False,
    ).mean()

    volatility = np.sqrt(variance)

    if annualize:
        volatility *= np.sqrt(periods_per_year)

    volatility.name = f"ewma_vol_{halflife}d"
    return volatility


def realized_volatility(
    returns: pd.Series,
    window: int = 60,
    annualize: bool = True,
    periods_per_year: int = 252,
    min_periods: int = 20,
) -> pd.Series:
    """
    Realized (historical) volatility using a rolling window.

    sigma_t = std(r_{t-window+1}, ..., r_t)

    Args:
        returns: Series of daily returns.
        window: Rolling window size in periods.
        annualize: If True, annualize by sqrt(periods_per_year).
        periods_per_year: Trading periods per year.
        min_periods: Minimum observations before producing a value.

    Returns:
        Series of volatility estimates.
    """
    volatility = returns.rolling(
        window=window,
        min_periods=min_periods,
    ).std()

    if annualize:
        volatility *= np.sqrt(periods_per_year)

    volatility.name = f"realized_vol_{window}d"
    return volatility


def parkinson_volatility(
    high: pd.Series,
    low: pd.Series,
    window: int = 60,
    annualize: bool = True,
    periods_per_year: int = 252,
    min_periods: int = 20,
) -> pd.Series:
    """
    Parkinson (high-low range-based) volatility estimator.

    sigma_t = sqrt(1 / (4 * ln(2) * n)) * sqrt(sum(ln(H_i/L_i)^2))

    This estimator is approximately 5x more efficient than close-to-close
    volatility when prices follow a driftless geometric Brownian motion.

    Args:
        high: Series of daily high prices.
        low: Series of daily low prices.
        window: Rolling window in periods.
        annualize: If True, annualize.
        periods_per_year: Trading periods per year.
        min_periods: Minimum observations before producing a value.

    Returns:
        Series of Parkinson volatility estimates.
    """
    # Parkinson scaling factor
    # Var = 1/(4*ln(2)) * E[ln(H/L)^2]
    factor = 1.0 / (4.0 * np.log(2.0))

    log_hl = np.log(high / low)
    parkinson_var = factor * (log_hl ** 2)

    volatility = np.sqrt(
        parkinson_var.rolling(
            window=window,
            min_periods=min_periods,
        ).mean()
    )

    if annualize:
        volatility *= np.sqrt(periods_per_year)

    volatility.name = f"parkinson_vol_{window}d"
    return volatility


def portfolio_volatility(
    weights: Union[np.ndarray, pd.Series],
    covariance: Union[np.ndarray, pd.DataFrame],
) -> float:
    """
    Compute portfolio volatility from weights and covariance matrix.

    sigma_p = sqrt(w' * Sigma * w)

    Args:
        weights: Vector of portfolio weights (aligned to covariance columns).
        covariance: Covariance matrix (N x N).

    Returns:
        Portfolio volatility (same frequency as covariance matrix input).
    """
    if isinstance(weights, pd.Series):
        weights = weights.values
    if isinstance(covariance, pd.DataFrame):
        covariance = covariance.values

    w = np.asarray(weights).flatten()
    sigma = np.asarray(covariance)

    var = w.T @ sigma @ w
    return float(np.sqrt(max(var, 0.0)))


def rolling_portfolio_volatility(
    returns: pd.DataFrame,
    weights: pd.Series,
    window: int = 60,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> pd.Series:
    """
    Compute rolling portfolio volatility from asset returns and fixed weights.

    Args:
        returns: DataFrame of asset returns (dates x tickers).
        weights: Series of fixed weights per ticker.
        window: Rolling window size.

    Returns:
        Series of rolling portfolio volatility.
    """
    # Align returns and weights
    common_tickers = returns.columns.intersection(weights.index)
    w = weights[common_tickers].values
    rets = returns[common_tickers]

    # Portfolio returns: w' @ r_t
    port_returns = rets @ w

    vol = realized_volatility(
        port_returns,
        window=window,
        annualize=annualize,
        periods_per_year=periods_per_year,
    )
    return vol


def annualize_volatility(
    daily_vol: float,
    periods_per_year: int = 252,
) -> float:
    """
    Annualize a daily volatility estimate.

    Args:
        daily_vol: Daily volatility (standard deviation of daily returns).
        periods_per_year: Trading periods per year.

    Returns:
        Annualized volatility.
    """
    return daily_vol * np.sqrt(periods_per_year)