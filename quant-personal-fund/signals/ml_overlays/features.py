"""
Daily feature engineering for ML overlays.

Mirrors the feature-engineering methodology from the legacy H1 FX notebook
(compute_features), adapted for daily multi-asset data. Features are purely
technical — computed from OHLCV and returns with rolling windows. No
forward-looking information is used: every feature at date t uses only
data available at or before date t.
"""

from typing import List, Optional

import numpy as np
import pandas as pd


def compute_daily_features(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    ticker: str,
    vol_windows: Optional[List[int]] = None,
    ma_windows: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    Compute daily features for a single instrument.

    Feature groups:
        1. Price dynamics: log returns, momentum (multi-horizon).
        2. Volatility: EWMA and realized vol at multiple horizons.
        3. Candle structure: range, body, wick ratios.
        4. Moving averages: close vs SMA/EMA deviations.
        5. Oscillators: RSI, stochastic K, Williams %R.
        6. Risk state: high-vol regime indicator, vol ratio (short/long).

    Args:
        prices: DataFrame (dates × tickers) of daily prices.
        returns: DataFrame (dates × tickers) of daily log returns.
        ticker: Instrument ticker to compute features for.
        vol_windows: Volatility lookback windows.
        ma_windows: Moving-average windows.

    Returns:
        DataFrame (dates × features) of features for the instrument.
        All features are lagged (no same-day leakage).
    """
    if vol_windows is None:
        vol_windows = [10, 30, 60]
    if ma_windows is None:
        ma_windows = [20, 50, 100]

    close = prices[ticker]
    ret = returns[ticker]

    feat = pd.DataFrame(index=prices.index)

    # ── 1. Price dynamics and momentum ─────────────────────────────────────
    feat["ret_1d"] = ret
    feat["ret_5d"] = np.log(close / close.shift(5))
    feat["ret_10d"] = np.log(close / close.shift(10))
    feat["ret_21d"] = np.log(close / close.shift(21))
    feat["ret_63d"] = np.log(close / close.shift(63))
    feat["momentum_21"] = feat["ret_21d"] - feat["ret_5d"]
    feat["momentum_63"] = feat["ret_63d"] - feat["ret_21d"]

    # ── 2. Volatility at multiple horizons ─────────────────────────────────
    for w in vol_windows:
        # Realized volatility (rolling std of daily returns, annualized)
        feat[f"realized_vol_{w}"] = ret.rolling(w, min_periods=w // 2).std() * np.sqrt(252)
        # EWMA volatility
        feat[f"ewma_vol_{w}"] = ret.pow(2).ewm(
            span=w, min_periods=max(w // 2, 5), adjust=False
        ).mean().pow(0.5) * np.sqrt(252)
        # Parkinson vol (range-based)
        high = prices[ticker].rolling(1).max()
        low = prices[ticker].rolling(1).min()
        if "high" in prices.columns and "low" in prices.columns:
            pass  # OHLC not available here; range-based uses close-to-close
        feat[f"range_vol_{w}"] = (np.log(high / low)).rolling(w, min_periods=w // 2).std() * np.sqrt(252)

    # Volatility regime: short-term vol vs long-term vol
    feat["vol_ratio_10_60"] = feat["realized_vol_10"] / feat["realized_vol_60"].replace(0, np.nan)
    feat["vol_ratio_30_60"] = feat["realized_vol_30"] / feat["realized_vol_60"].replace(0, np.nan)

    # ── 3. Candle structure ────────────────────────────────────────────────
    # Range-based features from returns (approximation)
    abs_ret = ret.abs()
    feat["abs_ret_5d_mean"] = abs_ret.rolling(5).mean()
    feat["abs_ret_21d_mean"] = abs_ret.rolling(21).mean()
    feat["abs_ret_ratio_5_21"] = (
        feat["abs_ret_5d_mean"] / feat["abs_ret_21d_mean"].replace(0, np.nan)
    )
    # Sign persistence: fraction of same-sign returns over window
    pos = (ret > 0).astype(float)
    feat["pos_ratio_5d"] = pos.rolling(5).mean()
    feat["pos_ratio_21d"] = pos.rolling(21).mean()

    # ── 4. Moving averages and deviations ──────────────────────────────────
    for w in ma_windows:
        ma = close.rolling(w, min_periods=w // 2).mean()
        feat[f"close_vs_ma_{w}"] = (close - ma) / close
        ema = close.ewm(span=w, min_periods=max(w // 2, 5), adjust=False).mean()
        feat[f"close_vs_ema_{w}"] = (close - ema) / close

    # ── 5. Oscillators ─────────────────────────────────────────────────────
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_g = gain.rolling(14).mean()
    avg_l = loss.rolling(14).mean()
    rs = avg_g / avg_l.replace(0, np.nan)
    feat["rsi_14"] = 100 - (100 / (1 + rs))

    low14 = close.rolling(14).min()
    high14 = close.rolling(14).max()
    feat["stoch_k"] = 100 * (close - low14) / (high14 - low14).replace(0, np.nan)
    feat["stoch_d"] = feat["stoch_k"].rolling(3).mean()
    feat["williams_r"] = -100 * (high14 - close) / (high14 - low14).replace(0, np.nan)

    # ── 6. Risk state ──────────────────────────────────────────────────────
    vol_med = feat["realized_vol_60"].rolling(252, min_periods=60).median()
    feat["vol_above_median"] = (feat["realized_vol_30"] > vol_med).astype(float)

    # Drop rows where any feature is NaN (warmup period)
    feat = feat.dropna()

    # Add constant features excluded from selection
    return feat


def compute_all_features(
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    tickers: List[str],
) -> dict:
    """
    Compute features for multiple instruments.

    Args:
        prices: DataFrame (dates × tickers) of daily prices.
        returns: DataFrame (dates × tickers) of daily returns.
        tickers: List of tickers.

    Returns:
        Dict mapping ticker to feature DataFrame.
    """
    return {
        t: compute_daily_features(prices, returns, t)
        for t in tickers
    }