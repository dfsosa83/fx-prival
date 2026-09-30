"""
Noise-feature voting feature selection.

Mirrors the legacy methodology exactly: inject random noise features
alongside real features, train three models (Random Forest, LightGBM,
Logistic Regression), and keep only real features that consistently
beat the noise benchmark.

The purpose is to prevent overfitting to noise by requiring that any
retained feature demonstrates importance above the noise floor across
multiple model families.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def generate_noise_features(n_rows: int, n_features: int = 9, seed: int = 42) -> pd.DataFrame:
    """
    Generate random noise features with no predictive value.

    Args:
        n_rows: Number of rows.
        n_features: Number of noise features (default 9).
        seed: Random seed for reproducibility.

    Returns:
        DataFrame of noise features.
    """
    rng = np.random.RandomState(seed)
    noise = {}
    for i in range(n_features):
        noise[f"noise_{i}"] = rng.randn(n_rows)
    return pd.DataFrame(noise)


def select_features_by_noise_voting(
    X: pd.DataFrame,
    y: pd.Series,
    voting_percentile: float = 20.0,
    min_strategy_support: int = 1,
    seed: int = 42,
    verbose: bool = True,
    task: str = "regression",
) -> Tuple[List[str], pd.DataFrame]:
    """
    Select features that beat the noise benchmark across 3 model families.

    Supports both classification (binary labels, legacy methodology) and
    regression (continuous targets, e.g. volatility forecasting).

    Algorithm (mirrors legacy methodology):
        1. Augment X with noise features.
        2. Train Random Forest, LightGBM, Logistic/Linear Regression.
        3. Collect importances (tree importance / |coef|).
        4. Compute weighted average importance.
        5. Define 5 selection strategies against the noise floor.
        6. Keep features supported by at least `min_strategy_support` strategies.

    Args:
        X: Feature matrix (train set only).
        y: Labels — binary for classification, continuous for regression.
        voting_percentile: Percentile threshold for each model's vote.
        min_strategy_support: Minimum number of strategies supporting a feature.
        seed: Random seed.
        verbose: Print selection summary.
        task: 'classification' or 'regression'.

    Returns:
        Tuple of (selected_features, importance_report DataFrame).
    """
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.preprocessing import StandardScaler

    try:
        import lightgbm as lgb
        _HAS_LGBM = True
    except ImportError:
        _HAS_LGBM = False

    n = len(X)
    noise_df = generate_noise_features(n, seed=seed)
    X_noise = X.copy().reset_index(drop=True)
    X_noise = pd.concat([X_noise, noise_df], axis=1)
    y_s = y.reset_index(drop=True)

    # ── Train three models ────────────────────────────────────────────────
    if task == "classification":
        rf = RandomForestClassifier(
            n_estimators=200, max_depth=12, min_samples_split=10,
            min_samples_leaf=5, max_features="sqrt", class_weight="balanced",
            random_state=seed, n_jobs=-1,
        )
        logreg = LogisticRegression(C=1.0, max_iter=2000, class_weight="balanced", random_state=seed)
    else:
        rf = RandomForestRegressor(
            n_estimators=200, max_depth=12, min_samples_split=10,
            min_samples_leaf=5, max_features="sqrt", random_state=seed, n_jobs=-1,
        )
        logreg = LinearRegression()
    rf.fit(X_noise.fillna(0), y_s)

    if _HAS_LGBM:
        if task == "classification":
            lgbm = lgb.LGBMClassifier(
                n_estimators=300, max_depth=12, learning_rate=0.05,
                num_leaves=80, min_child_samples=20, subsample=0.8,
                colsample_bytree=0.8, class_weight="balanced",
                random_state=seed, verbose=-1,
            )
        else:
            lgbm = lgb.LGBMRegressor(
                n_estimators=300, max_depth=12, learning_rate=0.05,
                num_leaves=80, min_child_samples=20, subsample=0.8,
                colsample_bytree=0.8, random_state=seed, verbose=-1,
            )
        lgbm.fit(X_noise.fillna(0), y_s)
    else:
        lgbm = None

    X_scaled = StandardScaler().fit_transform(X_noise.fillna(X_noise.median()).fillna(0))
    logreg.fit(X_scaled, y_s)

    # ── Collect importances ────────────────────────────────────────────────
    rf_imp = rf.feature_importances_
    lgbm_imp = lgbm.feature_importances_ if lgbm is not None else np.zeros(len(rf_imp))
    if task == "classification":
        logreg_imp = np.abs(logreg.coef_).ravel()
    else:
        logreg_imp = np.abs(logreg.coef_).ravel()

    imp_df = pd.DataFrame({
        "feature": X_noise.columns,
        "rf_imp": rf_imp,
        "lgbm_imp": lgbm_imp,
        "logreg_imp": logreg_imp,
    })
    imp_df["is_noise"] = imp_df["feature"].str.startswith("noise_")

    # Weighted average — trees more reliable, linear gets lower weight
    if lgbm is not None:
        imp_df["avg_imp"] = 0.3 * rf_imp + 0.6 * lgbm_imp + 0.1 * logreg_imp
    else:
        imp_df["avg_imp"] = 0.7 * rf_imp + 0.3 * logreg_imp
    imp_df = imp_df.sort_values("avg_imp", ascending=False).reset_index(drop=True)

    # ── Voting ─────────────────────────────────────────────────────────────
    rf_thr = np.percentile(rf_imp, voting_percentile)
    lgbm_thr = np.percentile(lgbm_imp, voting_percentile)
    logreg_thr = np.percentile(logreg_imp, voting_percentile)

    imp_df["rf_vote"] = (imp_df["rf_imp"] >= rf_thr).astype(int)
    imp_df["lgbm_vote"] = (imp_df["lgbm_imp"] >= lgbm_thr).astype(int)
    imp_df["logreg_vote"] = (imp_df["logreg_imp"] >= logreg_thr).astype(int)
    imp_df["total_votes"] = imp_df[["rf_vote", "lgbm_vote", "logreg_vote"]].sum(axis=1)

    # ── Noise benchmark ────────────────────────────────────────────────────
    noise_df_imp = imp_df[imp_df["is_noise"]]
    real_df = imp_df[~imp_df["is_noise"]]

    if len(noise_df_imp) == 0:
        return list(X.columns), imp_df

    noise_mean = noise_df_imp["avg_imp"].mean()
    noise_std = noise_df_imp["avg_imp"].std()
    noise_p70 = np.percentile(noise_df_imp["avg_imp"], 70)
    noise_votes_max = noise_df_imp["total_votes"].max()
    best_noise_rank = noise_df_imp.index.min()

    # ── Five strategies ────────────────────────────────────────────────────
    strategies = {
        "better_than_best_noise": set(
            real_df[real_df.index < best_noise_rank]["feature"]
        ),
        "above_noise_p70": set(
            real_df[real_df["avg_imp"] > noise_p70]["feature"]
        ),
        "more_votes_than_noise": set(
            real_df[real_df["total_votes"] > noise_votes_max]["feature"]
        ),
        "statistical_threshold": set(
            real_df[real_df["avg_imp"] > noise_mean + 0.5 * noise_std]["feature"]
        ),
        "vote_and_above_mean": set(
            real_df[(real_df["total_votes"] >= 1) & (real_df["avg_imp"] > noise_mean)]["feature"]
        ),
    }

    # ── Consensus ──────────────────────────────────────────────────────────
    support = {}
    for feats in strategies.values():
        for f in feats:
            support[f] = support.get(f, 0) + 1

    selected_features = sorted(
        [f for f, s in support.items() if s >= min_strategy_support],
        key=lambda f: imp_df.loc[imp_df["feature"] == f, "avg_imp"].iloc[0],
        reverse=True,
    )
    # Safety: never let noise through
    selected_features = [f for f in selected_features if not f.startswith("noise_")]

    if verbose:
        print(f"Real features tested : {len(X.columns)}")
        print(f"Selected             : {len(selected_features)}")
        print(f"Noise mean importance: {noise_mean:.5f}")
        print(f"Noise p70 importance : {noise_p70:.5f}")

    return selected_features, imp_df