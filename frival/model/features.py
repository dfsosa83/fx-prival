"""
Feature computation for EURUSD H1 SELL signals.

Extracted from eurusd_sell_improved.ipynb Cell 12.
Pure function: takes raw H1 OHLCV, returns feature DataFrame.
"""

from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd


# ── Label parameters (mirrors notebook Cell 4) ───────────────────────────────
ATR_PERIOD   = 14
ATR_TP_MULT  = 1.5
ATR_SL_MULT  = 1.0
FORWARD_BARS = 6

# ── Chronological split boundaries ───────────────────────────────────────────
TRAIN_START = "2020-06-30 00:00:00"
TRAIN_END   = "2025-06-30 23:00:00"
VAL_START   = "2025-07-01 00:00:00"
VAL_END     = "2025-12-31 23:00:00"
TEST_START  = "2026-01-01 00:00:00"

# ── EURUSD SELL (22 features with calendar — v2, threshold 0.326) ────────────
MODEL_FEATURES = [
    "deviation_sum_24h",
    "adx_14",
    "rolling_std_50",
    "hours_since_last_high",
    "d1_rsi",
    "obv",
    "atr_regime",
    "high_events_next_24h",
    "close_vs_ema200",
    "d1_close_vs_ema20",
    "rolling_std_10",
    "minus_di",
    "rsi_lag_5",
    "macd_sig",
    "plus_di",
    "atr_lag_5",
    "volume_ratio",
    "macd_hist",
    "volume_lag_5",
    "bb_width",
    "close_vs_day_open",
    "rsi_lag_3",
]

# ── GBPUSD SELL (19 features from noise-injection voting) ────────────────────
GBPUSD_SELL_FEATURES = [
    "adx_14",
    "rolling_std_50",
    "d1_rsi",
    "atr_regime",
    "d1_close_vs_ema20",
    "obv",
    "close_vs_ema200",
    "rolling_std_10",
    "minus_di",
    "plus_di",
    "atr_lag_5",
    "volume_lag_5",
    "close_vs_day_open",
    "macd_sig",
    "volume_ratio",
    "macd_hist",
    "rsi_lag_5",
    "bb_width",
    "upper_wick",
]

# ── USDCHF BUY (24 features from noise-injection voting) ───────────────────────
USDCHF_BUY_FEATURES = [
    "rolling_std_50",
    "obv",
    "adx_14",
    "d1_rsi",
    "close_vs_ema200",
    "atr_regime",
    "d1_close_vs_ema20",
    "minus_di",
    "close_vs_day_open",
    "rolling_std_10",
    "plus_di",
    "volume_ratio",
    "atr_lag_5",
    "volume_lag_5",
    "macd_sig",
    "rsi_lag_5",
    "volume_lag_1",
    "macd_hist",
    "bb_width",
    "volume_lag_3",
    "lower_wick",
    "d1_ema50",
    "upper_wick",
    "macd_hist_slope",
]


def get_features_for_pair(pair: str, direction: str = "SELL") -> list:
    """Return the model feature list for a given pair."""
    pair_upper = pair.upper()
    if pair_upper == "EURUSD":
        return MODEL_FEATURES
    elif pair_upper == "GBPUSD":
        return GBPUSD_SELL_FEATURES
    elif pair_upper == "USDCHF":
        return USDCHF_BUY_FEATURES
    elif pair_upper == "USDJPY":
        # TODO: Replace with actual features after noise-injection voting completes
        raise NotImplementedError(
            "USDJPY features not yet generated. Run usdjpy_sell_improved.ipynb "
            "first, then update get_features_for_pair() with the selected features."
        )
    else:
        raise ValueError(f"Unknown pair: {pair}. Supported: EURUSD, GBPUSD, USDCHF, USDJPY")


def compute_features(data: pd.DataFrame, pair: Optional[str] = None) -> pd.DataFrame:
    """
    Compute all technical features from raw H1 OHLCV data.

    Parameters
    ----------
    data : pd.DataFrame
        Columns: datetime, open, high, low, close, volume.
        Rows sorted chronologically (oldest first).
    pair : str, optional
        Trading pair (EURUSD, GBPUSD, etc.). If provided, economic calendar
        features are merged after technical feature computation.

    Returns
    -------
    pd.DataFrame
        Original columns + all feature columns (+ calendar features if pair given).
        Rows with NaN (warm-up for rolling windows) are dropped.
    """
    df = data.copy()

    # ── 1. Time features ──────────────────────────────────────────────────
    df["hour"]        = df["datetime"].dt.hour
    df["day_of_week"] = df["datetime"].dt.dayofweek
    df["month"]       = df["datetime"].dt.month

    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"]  = np.sin(2 * np.pi * df["day_of_week"] / 5)
    df["dow_cos"]  = np.cos(2 * np.pi * df["day_of_week"] / 5)

    _h = df["hour"]
    df["session_asian"]   = ((_h >= 0)  & (_h < 7)).astype(int)
    df["session_london"]  = ((_h >= 7)  & (_h < 16)).astype(int)
    df["session_ny"]      = ((_h >= 13) & (_h < 22)).astype(int)
    df["session_overlap"] = ((_h >= 13) & (_h < 17)).astype(int)

    # ── 2. Candle structure ───────────────────────────────────────────────
    df["body_size"]   = abs(df["close"] - df["open"])
    df["price_range"] = df["high"] - df["low"]
    df["upper_wick"]  = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"]  = df[["open", "close"]].min(axis=1) - df["low"]
    df["body_ratio"]  = df["body_size"] / df["price_range"].replace(0, np.nan)

    # ── 3. Moving averages ────────────────────────────────────────────────
    for w in [10, 20, 50]:
        df[f"sma_{w}"] = df["close"].rolling(w).mean()

    for s in [10, 20, 50, 100, 200]:
        df[f"ema_{s}"] = df["close"].ewm(span=s, adjust=False).mean()

    df["close_vs_ema50"]  = (df["close"] - df["ema_50"])  / df["close"]
    df["close_vs_ema200"] = (df["close"] - df["ema_200"]) / df["close"]

    # ── 4. Momentum oscillators ───────────────────────────────────────────
    delta   = df["close"].diff()
    gain    = delta.clip(lower=0)
    loss    = (-delta).clip(lower=0)
    avg_g   = gain.rolling(14).mean()
    avg_l   = loss.rolling(14).mean()
    rs      = avg_g / avg_l.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    low14   = df["low"].rolling(14).min()
    high14  = df["high"].rolling(14).max()
    df["stoch_k"]    = 100 * (df["close"] - low14) / (high14 - low14).replace(0, np.nan)
    df["stoch_d"]    = df["stoch_k"].rolling(3).mean()
    df["williams_r"] = -100 * (high14 - df["close"]) / (high14 - low14).replace(0, np.nan)

    ema12              = df["close"].ewm(span=12, adjust=False).mean()
    ema26              = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]         = ema12 - ema26
    df["macd_sig"]     = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]    = df["macd"] - df["macd_sig"]
    df["macd_hist_slope"] = df["macd_hist"].diff()

    # ── 5. Volatility ─────────────────────────────────────────────────────
    high_low   = df["high"] - df["low"]
    high_pc    = (df["high"] - df["close"].shift()).abs()
    low_pc     = (df["low"]  - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
    df["atr_14"] = true_range.rolling(ATR_PERIOD).mean()

    df["atr_regime"] = df["atr_14"] / df["atr_14"].rolling(50).mean()

    bb_mid          = df["close"].rolling(20).mean()
    bb_std          = df["close"].rolling(20).std()
    df["bb_upper"]  = bb_mid + 2 * bb_std
    df["bb_lower"]  = bb_mid - 2 * bb_std
    df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / bb_mid
    df["bb_pct"]    = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)

    for w in [10, 20, 50]:
        df[f"rolling_std_{w}"] = df["close"].rolling(w).std()

    # ── 6. Trend strength ─────────────────────────────────────────────────
    plus_dm  = df["high"].diff().clip(lower=0)
    minus_dm = (-df["low"].diff()).clip(lower=0)
    plus_dm  = plus_dm.where(plus_dm > minus_dm, 0)
    minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
    atr_adx  = true_range.rolling(14).mean()
    plus_di  = 100 * (plus_dm.rolling(14).mean()  / atr_adx.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr_adx.replace(0, np.nan))
    dx       = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    df["adx_14"]   = dx.rolling(14).mean()
    df["plus_di"]  = plus_di
    df["minus_di"] = minus_di

    tp = (df["high"] + df["low"] + df["close"]) / 3
    df["cci_20"]     = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).std())
    df["roc_10"]     = df["close"].pct_change(10) * 100
    df["momentum_10"] = df["close"] - df["close"].shift(10)

    # ── 7. Volume ─────────────────────────────────────────────────────────
    df["obv"]          = (np.sign(df["close"].diff()) * df["volume"]).fillna(0).cumsum()
    vol_ma20           = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / vol_ma20.replace(0, np.nan)

    # ── 8. Lagged features ────────────────────────────────────────────────
    for lag in [1, 2, 3, 5]:
        df[f"close_lag_{lag}"]  = df["close"].shift(lag)
        df[f"rsi_lag_{lag}"]    = df["rsi_14"].shift(lag)
        df[f"atr_lag_{lag}"]    = df["atr_14"].shift(lag)
        df[f"volume_lag_{lag}"] = df["volume"].shift(lag)

    # ── 9. Price-change returns ───────────────────────────────────────────
    for p in [1, 5, 10]:
        df[f"return_{p}b"] = df["close"].pct_change(p)

    # ── 10. D1 context (resampled from H1, no leakage) ────────────────────
    _d1 = (
        df.set_index("datetime")[["open", "high", "low", "close", "volume"]]
        .resample("1D")
        .agg({"open": "first", "high": "max", "low": "min",
              "close": "last", "volume": "sum"})
        .dropna()
    )
    _d1["d1_ema20"]  = _d1["close"].ewm(span=20, adjust=False).mean()
    _d1["d1_ema50"]  = _d1["close"].ewm(span=50, adjust=False).mean()
    _d1["d1_trend"]  = (_d1["d1_ema20"] > _d1["d1_ema50"]).astype(int)
    _dd = _d1["close"].diff()
    _d1["d1_rsi"]    = 100 - 100 / (
        1 + _dd.clip(lower=0).rolling(14).mean()
          / (-_dd).clip(lower=0).rolling(14).mean().replace(0, np.nan)
    )
    _d1["d1_close_vs_ema20"] = (_d1["close"] - _d1["d1_ema20"]) / _d1["close"]

    _d1_cols    = ["d1_ema20", "d1_ema50", "d1_trend", "d1_rsi", "d1_close_vs_ema20"]
    _d1_shifted = (
        _d1[_d1_cols]
        .shift(1)
        .reset_index()
        .rename(columns={"datetime": "_d1_date"})
    )

    # ── 11. Intraday context ──────────────────────────────────────────────
    df["_date"]   = df["datetime"].dt.normalize()
    _day_open     = df.groupby("_date")["open"].first().rename("_day_open")
    df            = df.join(_day_open, on="_date")
    df["close_vs_day_open"] = (df["close"] - df["_day_open"]) / df["_day_open"]

    df = df.merge(_d1_shifted, left_on="_date", right_on="_d1_date", how="left")
    df.drop(columns=["_date", "_d1_date", "_day_open"], inplace=True)

    # ── Drop NaN rows ─────────────────────────────────────────────────────
    n_before = len(df)
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)
    n_dropped = n_before - len(df)
    print(f"Rows dropped (NaN warm-up): {n_dropped:,}  |  Rows remaining: {len(df):,}")

    # ── Calendar features (optional — no lookahead) ─────────────────────────
    if pair:
        try:
            from data.calendar import compute_calendar_features
            cal_feats = compute_calendar_features(df["datetime"], pair)
            df = df.merge(
                pd.concat([df[["datetime"]], cal_feats.reset_index(drop=True)], axis=1),
                on="datetime", how="left",
            )
            new_cols = [c for c in cal_feats.columns if c not in df.columns]
            for c in new_cols:
                df[c] = cal_feats[c].values
            print(f"Calendar features merged: {list(cal_feats.columns)}")
        except Exception as e:
            print(f"Calendar features skipped: {e}")

    return df


def extract_model_features(df_features: pd.DataFrame, features: Optional[list] = None) -> pd.DataFrame:
    """
    Extract only the model features in the correct order.

    Parameters
    ----------
    df_features : pd.DataFrame
        Full feature DataFrame from compute_features().
    features : list, optional
        Feature list to extract. Defaults to MODEL_FEATURES (EURUSD).
    """
    feats = features if features is not None else MODEL_FEATURES
    missing = [f for f in feats if f not in df_features.columns]
    if missing:
        raise KeyError(f"Missing required features: {missing}")
    return df_features[feats].copy()