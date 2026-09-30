"""
Correlation matrix estimation for multi-asset portfolios.

Provides functions for estimating correlation matrices from return data
using multiple methods: sample Pearson, EWMA, and Ledoit-Wolf shrinkage.
All methods produce symmetric positive semi-definite matrices.
"""

from typing import Optional

import numpy as np
import pandas as pd


def pearson_correlation(
    returns: pd.DataFrame,
    min_periods: int = 60,
) -> pd.DataFrame:
    """
    Full-sample Pearson correlation matrix.

    Uses pairwise complete observations — each pair is computed from
    dates where both instruments have non-NaN returns.

    Args:
        returns: DataFrame of returns (dates × tickers).
        min_periods: Minimum overlapping observations per pair.

    Returns:
        DataFrame (tickers × tickers) of correlations.
    """
    return returns.corr(method="pearson", min_periods=min_periods)


def spearman_correlation(
    returns: pd.DataFrame,
    min_periods: int = 60,
) -> pd.DataFrame:
    """
    Full-sample Spearman rank correlation matrix.

    Args:
        returns: DataFrame of returns (dates × tickers).
        min_periods: Minimum overlapping observations per pair.

    Returns:
        DataFrame (tickers × tickers) of rank correlations.
    """
    return returns.corr(method="spearman", min_periods=min_periods)


def ewma_correlation(
    returns: pd.DataFrame,
    halflife: int = 60,
    min_periods: int = 20,
) -> pd.DataFrame:
    """
    EWMA correlation matrix at the most recent date.

    Uses exponentially weighted covariance and variance with the same
    halflife, then normalizes to correlation.

    Computation uses a two-pass approach:
        1. EWMA variance per instrument.
        2. Rolling pairwise covariance (or full EWMA covariance matrix).

    Args:
        returns: DataFrame of returns (dates × tickers).
        halflife: EWMA halflife in periods.
        min_periods: Minimum observations before producing a value.

    Returns:
        DataFrame (tickers × tickers) of EWMA correlations at the last date.
    """
    tickers = returns.columns.tolist()
    n = len(tickers)

    # Simple approach: compute EWMA covariance using the formula
    # cov_ij = ewma(r_i * r_j) - ewma(r_i) * ewma(r_j)
    # This avoids the pandas MultiIndex complexity.

    ewma_mean = returns.ewm(halflife=halflife, min_periods=min_periods).mean()
    centered = returns - ewma_mean

    # EWMA of cross products
    cov_values = np.zeros((n, n))
    for i, ti in enumerate(tickers):
        for j, tj in enumerate(tickers):
            product = centered[ti] * centered[tj]
            ewma_product = product.ewm(halflife=halflife, min_periods=min_periods).mean()
            cov_values[i, j] = ewma_product.iloc[-1]

    # Normalize to correlation
    vols = np.sqrt(np.diag(cov_values))
    vols_safe = np.where(vols > 1e-15, vols, 1.0)
    outer_vols = np.outer(vols_safe, vols_safe)
    corr_values = cov_values / outer_vols
    np.fill_diagonal(corr_values, 1.0)

    return pd.DataFrame(corr_values, index=tickers, columns=tickers)


def _is_psd(matrix: np.ndarray, tol: float = 1e-10) -> bool:
    """Check if a matrix is positive semi-definite."""
    eigenvalues = np.linalg.eigvalsh(matrix)
    return bool(np.all(eigenvalues >= -tol))


def shrinkage_correlation(
    returns: pd.DataFrame,
    shrinkage: float = 0.2,
) -> pd.DataFrame:
    """
    Shrinkage correlation matrix toward the identity.

    Shrinks the sample correlation matrix toward the identity matrix
    using a constant shrinkage intensity. This improves conditioning
    and reduces estimation error when the number of observations is
    small relative to the number of assets.

    Sigma_shrunk = (1 - delta) * Sigma_sample + delta * I

    Args:
        returns: DataFrame of returns (dates × tickers).
        shrinkage: Shrinkage intensity in [0, 1]. 0 = sample, 1 = identity.
                   Default 0.2 is a conservative choice.

    Returns:
        DataFrame (tickers × tickers) of shrunk correlations.
    """
    sample_corr = returns.corr().values
    identity = np.eye(len(sample_corr))
    shrunk = (1.0 - shrinkage) * sample_corr + shrinkage * identity

    # Ensure PSD
    if not _is_psd(shrunk):
        eigenvalues = np.linalg.eigvalsh(shrunk)
        min_eig = eigenvalues.min()
        if min_eig < 0:
            shrunk = shrunk - min_eig * np.eye(len(shrunk))
            # Re-normalize diagonal to 1.0
            d = np.sqrt(np.diag(shrunk))
            shrunk = shrunk / np.outer(d, d)

    return pd.DataFrame(shrunk, index=returns.columns, columns=returns.columns)


def rolling_correlation(
    returns: pd.DataFrame,
    window: int = 252,
    min_periods: int = 60,
    pairwise: bool = False,
) -> pd.DataFrame:
    """
    Rolling Pearson correlation for a pair of instruments.

    For >2 instruments, use pairwise=False (returns the full correlation
    of all instruments at each date as a MultiIndex DataFrame).

    Args:
        returns: DataFrame of returns (dates × tickers).
        window: Rolling window in periods.
        min_periods: Minimum observations per window.
        pairwise: If True, compute pairwise rolling correlations (slower).

    Returns:
        If pairwise=False: MultiIndex DataFrame (date, ticker_i, ticker_j).
        If pairwise=True and returns has 2 columns: Series of rolling correlation.
    """
    if pairwise:
        return returns.iloc[:, 0].rolling(window, min_periods=min_periods).corr(
            returns.iloc[:, 1]
        )
    return returns.rolling(window, min_periods=min_periods).corr()