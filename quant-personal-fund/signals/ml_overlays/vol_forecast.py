"""
Volatility forecasting model for conditional position sizing.

Mirrors the legacy modeling methodology (noise-voting feature selection,
chronological split, calibration) but targets a risk-management problem:
forecasting forward realized volatility to enable conditional sizing.

The hypothesis: if we can forecast elevated volatility, we can reduce
exposure before the elevated regime, improving the risk-adjusted return
of the portfolio without predicting price direction.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def forward_realized_volatility(
    returns: pd.Series,
    horizon: int = 30,
    annualize: bool = True,
    periods_per_year: int = 252,
) -> pd.Series:
    """
    Compute forward-looking realized volatility.

    vol_fwd[t] = std(returns[t+1 ... t+horizon]) * sqrt(252)

    This is the LABEL for volatility forecasting. It uses only future
    returns (by definition), so it must be shifted when building the
    training set — the features at date t predict the label at date t.

    Args:
        returns: Series of daily returns.
        horizon: Forward window in days.
        annualize: Annualize by sqrt(periods_per_year).
        periods_per_year: Trading days per year.

    Returns:
        Series of forward realized volatility aligned to returns index.
        Last `horizon` entries are NaN.
    """
    # Rolling std of the REVERSED series = forward-looking std
    fwd_vol = returns[::-1].rolling(horizon, min_periods=max(horizon // 2, 10)).std()[::-1]
    if annualize:
        fwd_vol = fwd_vol * np.sqrt(periods_per_year)
    return fwd_vol


def build_regression_dataset(
    features: pd.DataFrame,
    returns: pd.Series,
    horizon: int = 30,
    purge_days: int = 30,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Build a supervised regression dataset for vol forecasting.

    X[t] = features at date t (already lagged — only past info).
    y[t] = forward realized vol computed from returns[t+1 ... t+horizon].

    A purge of `purge_days` between train and test is REQUIRED to prevent
    overlap leakage: the label at train-time t uses returns up to t+horizon,
    which overlaps with test features at dates < t+horizon.

    Args:
        features: Feature DataFrame (dates × features).
        returns: Daily returns Series (for label computation).
        horizon: Forward window for the label.
        purge_days: Minimum gap between train end and test start.

    Returns:
        Tuple of (X, y) aligned on the same index with NaN labels dropped.
    """
    y = forward_realized_volatility(returns, horizon=horizon)

    # Align features and labels, drop rows where label is NaN
    common = features.index.intersection(y.index)
    X = features.loc[common]
    y = y.loc[common]

    valid = y.notna()
    return X[valid], y[valid]


def train_vol_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_type: str = "lgbm",
    seed: int = 42,
) -> Tuple[object, List[str]]:
    """
    Train a volatility forecasting model on pre-selected features.

    Args:
        X_train: Training features (post-selection).
        y_train: Training labels (forward vol).
        model_type: 'lgbm' or 'rf'.
        seed: Random seed.

    Returns:
        Tuple of (fitted_model, selected_features).
    """
    from sklearn.ensemble import RandomForestRegressor
    try:
        import lightgbm as lgb
        _HAS_LGBM = True
    except ImportError:
        _HAS_LGBM = False

    selected_features = X_train.columns.tolist()

    if model_type == "lgbm" and _HAS_LGBM:
        model = lgb.LGBMRegressor(
            n_estimators=400, max_depth=12, learning_rate=0.03,
            num_leaves=60, min_child_samples=20, subsample=0.8,
            colsample_bytree=0.8, random_state=seed, verbose=-1,
        )
    else:
        model = RandomForestRegressor(
            n_estimators=300, max_depth=12, min_samples_split=10,
            min_samples_leaf=5, random_state=seed, n_jobs=-1,
        )

    model.fit(X_train.values, y_train.values)
    return model, selected_features


def forecast_volatility(
    model: object,
    X: pd.DataFrame,
    selected_features: List[str],
) -> pd.Series:
    """
    Generate volatility forecasts from a fitted model.

    Args:
        model: Fitted model (LGBM or RF).
        X: Full feature DataFrame.
        selected_features: Features used by the model.

    Returns:
        Series of volatility forecasts aligned to X.index.
    """
    cols = [c for c in selected_features if c in X.columns]
    if len(cols) != len(selected_features):
        missing = set(selected_features) - set(cols)
        raise ValueError(f"Missing features in X: {missing}")

    preds = model.predict(X[cols].values)
    return pd.Series(preds, index=X.index, name="vol_forecast")