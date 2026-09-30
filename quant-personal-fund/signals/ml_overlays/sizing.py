"""
Conditional position sizing overlay.

Uses volatility forecasts to scale portfolio positions. When the model
forecasts elevated forward volatility, positions are reduced. When
forecast volatility is low, positions return to baseline.

This is the "ML for risk, not price direction" role — it never predicts
direction, only scales exposure based on predicted risk.
"""

from typing import Optional

import numpy as np
import pandas as pd


def volatility_scaling_factor(
    vol_forecast: pd.Series,
    vol_baseline: pd.Series,
    min_scale: float = 0.5,
    max_scale: float = 1.0,
    k: float = 1.0,
) -> pd.Series:
    """
    Compute exposure scaling factor from volatility forecast.

    scale[t] = clip(max_scale - k * (forecast[t] / baseline[t] - 1), min_scale, max_scale)

    A forecast equal to baseline → scale 1.0 (no adjustment).
    Forecast 2× baseline → scale 0.5 (halve exposure).
    Forecast below baseline → scale capped at max_scale (no expansion).

    Args:
        vol_forecast: Series of forecast volatility (annualized).
        vol_baseline: Series of baseline volatility (annualized, e.g. realized 60d).
        min_scale: Minimum exposure scale (floor).
        max_scale: Maximum exposure scale (cap).
        k: Sensitivity. Higher k → more aggressive de-risking.

    Returns:
        Series of scaling factors in [min_scale, max_scale].
    """
    baseline_safe = vol_baseline.replace(0, np.nan)
    ratio = vol_forecast / baseline_safe
    scale = max_scale - k * (ratio - 1.0)
    scale = scale.clip(lower=min_scale, upper=max_scale)
    return scale.fillna(max_scale)


def apply_scaling(
    weights: pd.DataFrame,
    scale: pd.Series,
) -> pd.DataFrame:
    """
    Apply an exposure scaling series to portfolio weights.

    Each row of weights is multiplied by the corresponding scale factor.
    The unallocated capital (1 - gross_exposure) absorbs the reduction.

    Args:
        weights: DataFrame (dates × tickers) of baseline weights.
        scale: Series (dates) of scaling factors.

    Returns:
        Scaled weights DataFrame.
    """
    scale_aligned = scale.reindex(weights.index).fillna(1.0)
    return weights.mul(scale_aligned, axis=0)


def create_regime_filter(
    vol_forecast: pd.Series,
    threshold: float = 1.5,
) -> pd.Series:
    """
    Create a binary regime filter: trade normally (1.0) or de-risk (scale < 1.0).

    The regime is "elevated" when forecast vol exceeds `threshold` × baseline.
    Uses the ratio of forecast to a rolling baseline median to avoid
    absolute-level dependence.

    Args:
        vol_forecast: Forecast volatility series.
        threshold: Ratio threshold for elevated regime.

    Returns:
        Series of 1.0 (normal) or de-risk scale (0.5 default).
    """
    baseline = vol_forecast.rolling(252, min_periods=60).median()
    ratio = vol_forecast / baseline.replace(0, np.nan)
    elevated = ratio > threshold
    # Binary: 1.0 normal, 0.5 de-risk
    scale = pd.Series(1.0, index=vol_forecast.index)
    scale[elevated] = 0.5
    return scale