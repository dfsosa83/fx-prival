"""
Ensemble model loading and inference for EURUSD H1 SELL signals.

Loads the trained VotingClassifier bundle and produces calibrated probability
predictions. Pure functions — no side effects beyond model loading.
"""

import warnings
from pathlib import Path
from typing import Dict, Any, Optional

import joblib
import numpy as np
import pandas as pd


# ── Model paths ──────────────────────────────────────────────────────────────
MODELS_DIR = (
    Path(__file__).resolve().parents[2]
    / "ml-signal-service" / "models_bin"
)
MODEL_FILE = "EURUSD_H1_sell_Ensemble.joblib"


def load_model(model_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the trained ensemble bundle from disk.

    Parameters
    ----------
    model_path : str, optional
        Path to .joblib file. Defaults to MODELS_DIR / MODEL_FILE.

    Returns
    -------
    dict with keys: model, features, threshold, atr_tp_mult, atr_sl_mult, forward_bars
    """
    path = model_path or str(MODELS_DIR / MODEL_FILE)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bundle = joblib.load(path)

    # Validate required keys
    required = ["model", "features", "threshold"]
    missing = [k for k in required if k not in bundle]
    if missing:
        raise KeyError(
            f"Bundle at {path} missing required keys: {missing}. "
            f"Found: {list(bundle.keys())}"
        )

    return bundle


def predict(
    bundle: Dict[str, Any],
    df_features: pd.DataFrame,
    *,
    threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Run ensemble inference on a feature DataFrame.

    Parameters
    ----------
    bundle : dict
        Loaded model bundle from load_model().
    df_features : pd.DataFrame
        Feature matrix with exactly the 20 model features in the correct order.
        Can be a single row or multiple rows.
    threshold : float, optional
        Override the bundle threshold. Defaults to bundle threshold.

    Returns
    -------
    dict with keys:
        probability      : float — calibrated soft-vote mean (class1 = SELL)
        threshold        : float — operating threshold
        signal_fired     : bool  — probability >= threshold
        individual_probs : dict  — per-estimator class1 probabilities
        features_used    : list  — feature names used
        n_samples        : int   — number of rows evaluated
    """
    model = bundle["model"]
    expected_features = bundle["features"]
    threshold = threshold if threshold is not None else bundle["threshold"]

    # Validate features
    missing = [f for f in expected_features if f not in df_features.columns]
    if missing:
        raise KeyError(
            f"Feature DataFrame missing {len(missing)} required columns: {missing[:5]}..."
        )

    X = df_features[expected_features]

    # Ensemble soft-vote probability (keep as DataFrame for feature name compatibility)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        proba = model.predict_proba(X)
    class1_proba = float(proba[0, 1]) if len(X) == 1 else proba[:, 1]

    # Per-estimator probabilities
    individual = {}
    for name, est in model.named_estimators_.items():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ip = est.predict_proba(X)
        individual[name] = float(ip[0, 1]) if len(X) == 1 else ip[:, 1].tolist()

    # Single-row result
    if len(X) == 1:
        result = {
            "probability": float(class1_proba),
            "threshold": float(threshold),
            "signal_fired": bool(float(class1_proba) >= threshold),
            "individual_probs": individual,
            "features_used": expected_features,
            "n_samples": 1,
        }
    else:
        # Multi-row: return array of probabilities
        result = {
            "probability": class1_proba.tolist(),
            "threshold": float(threshold),
            "signal_fired": (class1_proba >= threshold).tolist(),
            "individual_probs": individual,
            "features_used": expected_features,
            "n_samples": len(X),
        }

    return result