"""
Prepare structured context for agent evaluation from the feature DataFrame.

Extracts D1 context, top features, and current price for a given bar.
"""

from typing import Dict, Any
import pandas as pd


D1_COLUMNS = [
    "d1_rsi",
    "d1_close_vs_ema20",
    "d1_trend",
    "d1_ema20",
    "d1_ema50",
]

ADDITIONAL_CONTEXT = [
    "ema_10", "ema_50", "ema_200",
    "rsi_14", "macd_hist", "macd_hist_slope",
    "adx_14", "plus_di", "minus_di",
    "atr_regime", "atr_14",
    "close_vs_ema50", "close_vs_day_open",
    "rolling_std_10", "rolling_std_50",
]


def build_context(
    df_features_row,
    probability: float,
    threshold: float,
    individual_probs: Dict[str, float],
) -> Dict[str, Any]:
    """
    Build evaluation context for the technical agent from a single feature row.

    Returns dict with:
    - current_price
    - d1_context (dict of D1 feature values)
    - top_features (dict of model input feature values)
    """
    row = df_features_row

    current_price = float(row["close"])

    # D1 context
    d1 = {}
    for col in D1_COLUMNS:
        if col in row.index:
            val = row[col]
            d1[col] = float(val) if pd.notna(val) else 0.0

    # Additional context for agent reasoning
    extra = {}
    for col in ADDITIONAL_CONTEXT:
        if col in row.index:
            val = row[col]
            extra[col] = float(val) if pd.notna(val) else 0.0

    # Merge: top_features = model features with per-model probs for agent awareness
    top_features = {**extra}

    return {
        "current_price": current_price,
        "d1_context": d1,
        "top_features": top_features,
        "probability": probability,
        "threshold": threshold,
        "individual_probs": individual_probs,
    }