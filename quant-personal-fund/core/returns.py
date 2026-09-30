"""
Return computation for multi-asset instruments.

Provides functions for computing simple, log, and excess returns from
daily OHLCV data, with date alignment across multiple instruments.

All functions operate on pandas DataFrames and are designed to be
used with the instrument master and data pipeline.
"""

from typing import Optional

import numpy as np
import pandas as pd


def simple_returns(prices: pd.Series, periods: int = 1) -> pd.Series:
    """
    Compute simple percentage returns.

    r_t = (p_t / p_{t-periods}) - 1

    Args:
        prices: Series of prices indexed by date. Prefer adjusted close.
        periods: Number of periods to shift (default 1 for daily returns).

    Returns:
        Series of simple returns. First `periods` entries are NaN.
    """
    if len(prices) < periods + 1:
        return pd.Series(np.nan, index=prices.index, name=f"simple_ret_{periods}d")

    returns = prices.pct_change(periods=periods)
    returns.name = f"simple_ret_{periods}d" if returns.name is None else returns.name
    return returns


def log_returns(prices: pd.Series, periods: int = 1) -> pd.Series:
    """
    Compute log (continuously compounded) returns.

    r_t = ln(p_t / p_{t-periods})

    Args:
        prices: Series of prices indexed by date. Prefer adjusted close.
        periods: Number of periods to shift (default 1 for daily returns).

    Returns:
        Series of log returns. First `periods` entries are NaN.
        All values are finite unless prices contain zero or negative values.
    """
    if len(prices) < periods + 1:
        return pd.Series(np.nan, index=prices.index, name=f"log_ret_{periods}d")

    shifted = prices.shift(periods)
    valid_mask = (prices > 0) & (shifted > 0)
    result = pd.Series(np.nan, index=prices.index, name=f"log_ret_{periods}d")
    result[valid_mask] = np.log(
        prices[valid_mask].values / shifted[valid_mask].values
    )
    return result


def excess_returns(
    returns: pd.Series,
    risk_free_rate: Optional[pd.Series] = None,
    annual_rf: float = 0.0,
    periods_per_year: int = 252,
) -> pd.Series:
    """
    Compute excess returns over the risk-free rate.

    Args:
        returns: Series of log or simple returns.
        risk_free_rate: Series of matching risk-free rates (e.g., daily).
                        Takes precedence over annual_rf if provided.
        annual_rf: Annual risk-free rate (decimal, e.g. 0.03 for 3%).
                   Used only if risk_free_rate is None.
        periods_per_year: Number of trading periods per year (252 for daily).

    Returns:
        Series of excess returns.
    """
    if risk_free_rate is not None:
        rf_daily = risk_free_rate.reindex(returns.index)
        return returns - rf_daily

    rf_daily = annual_rf / periods_per_year
    return returns - rf_daily


def returns_from_dataframe(
    df: pd.DataFrame,
    price_col: str = "adj_close",
    fallback_col: str = "close",
    method: str = "log",
) -> pd.Series:
    """
    Compute returns from a standard OHLCV DataFrame.

    Prefers adjusted close, falls back to unadjusted close.

    Args:
        df: DataFrame with OHLCV columns indexed by date.
        price_col: Preferred price column (default 'adj_close').
        fallback_col: Fallback price column if preferred is unavailable.
        method: 'simple' or 'log' returns.

    Returns:
        Series of daily returns.
    """
    if price_col in df.columns and df[price_col].notna().any():
        prices = df[price_col]
    elif fallback_col in df.columns:
        prices = df[fallback_col]
    else:
        raise ValueError(
            f"Neither '{price_col}' nor '{fallback_col}' found in DataFrame columns: "
            f"{list(df.columns)}"
        )

    if method == "log":
        return log_returns(prices)
    else:
        return simple_returns(prices)


def align_returns(
    returns_dict: dict,
    method: str = "inner",
) -> pd.DataFrame:
    """
    Align return series from multiple instruments to a common date index.

    Args:
        returns_dict: Dict mapping ticker to return Series.
        method: Join method — 'inner' (intersection), 'outer' (union).

    Returns:
        DataFrame with tickers as columns, dates as index.
    """
    df = pd.DataFrame(returns_dict)
    if method == "inner":
        return df.dropna()
    return df


def cumulative_returns(returns: pd.Series) -> pd.Series:
    """
    Compute cumulative returns from a return series.

    Uses simple compounding: cumret_t = prod(1 + r_i) - 1

    Args:
        returns: Series of simple or log returns. If log returns, they are
                 converted to simple returns internally for compounding.

    Returns:
        Series of cumulative returns starting from 0.
    """
    return (1 + returns.fillna(0)).cumprod() - 1


def yield_to_price(
    yields: pd.Series,
    maturity_years: float = 10.0,
) -> pd.Series:
    """
    Convert a yield series to log returns using a constant-maturity
    zero-coupon bond price proxy.

    For a bond with yield Y_t and constant maturity T:
        P_t = 1 / (1 + Y_t)^T
        r_t = T * ln((1 + Y_{t-1}) / (1 + Y_t))

    This is a simple and transparent proxy for bond returns that captures
    the direction and approximate magnitude of price moves from yield changes.
    It ignores roll-down, convexity, and coupon income.

    Args:
        yields: Series of yields in decimal form (e.g., 0.045 for 4.5%).
                If values are > 1.0, they are assumed to be in percent and
                divided by 100.0 automatically.
        maturity_years: Constant time to maturity in years (default 10).

    Returns:
        Series of daily log returns. First entry is NaN.

    Raises:
        ValueError: If yields contain negative values after conversion.
    """
    # Auto-detect percent vs decimal: if median > 1.0, assume percent
    y_test = yields.dropna()
    if len(y_test) == 0:
        return pd.Series(np.nan, index=yields.index, name=f"bond_ret_{maturity_years}y")

    if y_test.median() > 1.0:
        yields = yields / 100.0

    if (yields.dropna() < 0).any():
        raise ValueError("Yields contain negative values after conversion. Check input series.")

    prices = 1.0 / (1.0 + yields.clip(lower=0.0)) ** maturity_years
    return log_returns(prices)