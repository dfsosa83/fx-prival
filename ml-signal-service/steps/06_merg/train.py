"""
MERG v1 — Final training & serialization.
Top-20 features, original split (train pre-2023, val 2023, test 2024-2026).
Outputs: MERG_v1_reaction.joblib + MERG_v1_direction.joblib + feature list.
"""

import numpy as np
import pandas as pd
import joblib
import json
import warnings
from pathlib import Path
from datetime import datetime, timezone
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import precision_recall_curve, auc, roc_auc_score, brier_score_loss
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

warnings.filterwarnings("ignore")
np.random.seed(42)

# -- Paths --
DATA_CSV = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\ml-signal-service\data\raw\macro\ExportedData.csv")
MODELS_DIR = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\ml-signal-service\models_bin")
FEATURES_DIR = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\ml-signal-service\data\features")
MODELS_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_DIR.mkdir(parents=True, exist_ok=True)

# -- Split --
TRAIN_END = "2022-12-31"
VAL_START, VAL_END = "2023-01-01", "2023-12-31"
TEST_START, TEST_END = "2024-01-01", "2026-07-31"

# -- Hyperparameters --
OUTER_FOLDS, INNER_FOLDS = 4, 4
CALIB_CV, RECENCY_DECAY = 3, 0.15
MIN_VAL_SIGNALS = 30
VOTING_PERCENTILE = 40
MIN_STRATEGY_SUPPORT = 1

# =============================================================================
# 1. Load & preprocess
# =============================================================================

print("Loading data...")
df = pd.read_csv(DATA_CSV, dtype={"event": str, "time": str})
df["time_utc"] = pd.to_datetime(df["time"], format="%Y.%m.%d %H:%M", utc=True)
df = df.sort_values("time_utc").reset_index(drop=True)

# Feature engineering
feature_cols = [c for c in df.columns if c.startswith(("tWick", "body", "bWick"))]
for i in range(1, 16):
    tw, bd, bw = f"tWick{i}", f"body{i}", f"bWick{i}"
    total_range = df[tw] + df[bd].abs() + df[bw] + 1e-9
    df[f"range_{i}"] = total_range
    df[f"body_ratio_{i}"] = df[bd].abs() / total_range
    df[f"wick_asym_{i}"] = (df[tw] - df[bw]) / total_range
    df[f"body_sign_{i}"] = np.sign(df[bd])
df["cum_body_1_3"] = df[[f"body{i}" for i in range(1, 4)]].sum(axis=1)
df["cum_body_1_5"] = df[[f"body{i}" for i in range(1, 6)]].sum(axis=1)
df["cum_body_1_15"] = df[[f"body{i}" for i in range(1, 16)]].sum(axis=1)
df["body_sign_agree_1_5"] = df[[f"body_sign_{i}" for i in range(1, 6)]].sum(axis=1).abs() / 5
df["max_wick_asym_1_5"] = df[[f"wick_asym_{i}" for i in range(1, 6)]].abs().max(axis=1)

derived_cols = [c for c in df.columns if c.startswith(("range_", "body_ratio_", "wick_asym_", "body_sign_", "cum_body_", "body_sign_agree_", "max_wick_asym_"))]
all_feature_cols = feature_cols + derived_cols
print(f"Features: {len(all_feature_cols)} ({len(feature_cols)} base + {len(derived_cols)} derived)")

# Labels
df["y_reaction"] = (df["targetSimple"] != "N").astype(int)
df["y_direction"] = np.where(df["targetSimple"] == "U", 1, np.where(df["targetSimple"] == "D", 0, np.nan))

# Split
mask_train = df["time_utc"] <= TRAIN_END
mask_val = (df["time_utc"] >= VAL_START) & (df["time_utc"] <= VAL_END)
mask_test = (df["time_utc"] >= TEST_START) & (df["time_utc"] <= TEST_END)
df_train, df_val, df_test = df[mask_train].copy(), df[mask_val].copy(), df[mask_test].copy()
print(f"Split: train={len(df_train)}  val={len(df_val)}  test={len(df_test)}")

# =============================================================================
# 2. Noise-injection feature selection
# =============================================================================

print("\nFeature selection (noise-injection voting)...")
X_train_raw = df_train[all_feature_cols].values.astype(np.float32)
y_train_fs = df_train["y_reaction"].values
n_samples, n_features = X_train_raw.shape

# Inject synthetic noise
rng = np.random.RandomState(42)
noise = np.column_stack([
    rng.normal(0, 1, n_samples),
    rng.uniform(-1, 1, n_samples),
    rng.poisson(1, n_samples).astype(float),
    np.cumsum(rng.normal(0, 0.1, n_samples)),
    np.sin(np.linspace(0, 10 * np.pi, n_samples)),
    np.sin(np.linspace(0, 20 * np.pi, n_samples)),
    rng.exponential(1, n_samples),
    rng.chisquare(3, n_samples).astype(float),
    rng.beta(0.5, 0.5, n_samples),
])
X_with_noise = np.column_stack([X_train_raw, noise])

rf = RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
lgbm = LGBMClassifier(n_estimators=500, random_state=42, verbose=-1)
lr = LogisticRegression(max_iter=5000, random_state=42)
rf.fit(X_with_noise, y_train_fs)
lgbm.fit(X_with_noise, y_train_fs)
lr.fit(X_with_noise, y_train_fs)

rf_imp = rf.feature_importances_
lgbm_imp = lgbm.feature_importances_
lr_coef = np.abs(lr.coef_[0])
lr_imp = lr_coef / (lr_coef.sum() + 1e-9)
avg_imp = 0.3 * rf_imp + 0.6 * lgbm_imp + 0.1 * lr_imp

noise_mask = np.array([n.startswith("NOISE_") for n in list(all_feature_cols) + [f"NOISE_{i}" for i in range(1, 10)]])
real_imp = avg_imp[~noise_mask]
noise_imp = avg_imp[noise_mask]

# Rank by importance
ranked = sorted(zip(all_feature_cols, real_imp), key=lambda x: -x[1])
top20 = [f for f, _ in ranked[:20]]
print(f"Selected top-20 features:")

# Save feature list
with open(FEATURES_DIR / "merg_v1_features_top20.txt", "w") as f:
    for i, (feat, imp) in enumerate(ranked[:20], 1):
        f.write(f"{feat}\n")
        if i <= 15:
            print(f"  {i:2d}. {feat:<25s} imp={imp:.4f}")

print(f"\nNoise max importance: {noise_imp.max():.6f}")
print(f"Features beating noise: {(real_imp > noise_imp.max()).sum()}")

# =============================================================================
# 3. Train Stage 1 — Reaction detector
# =============================================================================

print("\n=== Stage 1 — Reaction Detector ===")

X_train = df_train[top20].values.astype(np.float32)
y_train_s1 = df_train["y_reaction"].values
X_val = df_val[top20].values.astype(np.float32)
y_val_s1 = df_val["y_reaction"].values
X_test = df_test[top20].values.astype(np.float32)
y_test_s1 = df_test["y_reaction"].values

# Recency weights
years_ago = (df_train["time_utc"].max() - df_train["time_utc"]).dt.days / 365.25
sample_w = np.exp(-RECENCY_DECAY * years_ago).values
sample_w = sample_w / sample_w.sum() * len(sample_w)

models = {
    "LogReg": LogisticRegression(max_iter=5000, random_state=42),
    "RandomForest": RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
    "XGBoost": XGBClassifier(scale_pos_weight=len(y_train_s1)/max(y_train_s1.sum(), 1), random_state=42, verbosity=0),
    "LightGBM": LGBMClassifier(class_weight="balanced", random_state=42, verbose=-1),
}

outer_cv = TimeSeriesSplit(n_splits=OUTER_FOLDS)
pr_s1 = {}
for name, model in models.items():
    scores = []
    for tr, te in outer_cv.split(X_train):
        model.fit(X_train[tr], y_train_s1[tr], sample_weight=sample_w[tr] if len(tr) < len(sample_w) else sample_w[:len(tr)])
        proba = model.predict_proba(X_train[te])[:, 1]
        prec, rec, _ = precision_recall_curve(y_train_s1[te], proba)
        scores.append(auc(rec, prec))
    pr_s1[name] = np.mean(scores)
    print(f"  {name:<15s} CV PR-AUC: {pr_s1[name]:.4f}")

# Soft-vote ensemble
estimators = [(n, CalibratedClassifierCV(m, method="isotonic", cv=CALIB_CV)) for n, m in models.items()]
ensemble_s1 = VotingClassifier(estimators=estimators, voting="soft")
ensemble_s1.fit(X_train, y_train_s1, sample_weight=sample_w)

# Threshold on validation
proba_val = ensemble_s1.predict_proba(X_val)[:, 1]
prec_v, rec_v, thresh_v = precision_recall_curve(y_val_s1, proba_val)
best_t1, best_s1 = 0.5, -np.inf
for i, t in enumerate(thresh_v):
    n = (proba_val >= t).sum()
    if n < MIN_VAL_SIGNALS or i >= len(prec_v):
        continue
    score = prec_v[i] * np.log(n + 1)
    if score > best_s1:
        best_s1, best_t1 = score, t
print(f"  Threshold: {best_t1:.4f}")
print(f"  Val signals: {(proba_val >= best_t1).sum()}/{len(proba_val)}")

# Test
proba_test = ensemble_s1.predict_proba(X_test)[:, 1]
roc_1 = roc_auc_score(y_test_s1, proba_test)
prec_1, rec_1, _ = precision_recall_curve(y_test_s1, proba_test)
prauc_1 = auc(rec_1, prec_1)
brier_1 = brier_score_loss(y_test_s1, proba_test)
print(f"  Test  ROC-AUC={roc_1:.4f}  PR-AUC={prauc_1:.4f}  Brier={brier_1:.4f}")

# =============================================================================
# 4. Train Stage 2 — Direction classifier
# =============================================================================

print("\n=== Stage 2 — Direction Classifier ===")

mask_r_tr = df_train["y_reaction"] == 1
mask_r_val = df_val["y_reaction"] == 1
mask_r_test = df_test["y_reaction"] == 1

X_train2 = df_train.loc[mask_r_tr, top20].values.astype(np.float32)
y_train_s2 = df_train.loc[mask_r_tr, "y_direction"].values
X_val2 = df_val.loc[mask_r_val, top20].values.astype(np.float32)
y_val_s2 = df_val.loc[mask_r_val, "y_direction"].values
X_test2 = df_test.loc[mask_r_test, top20].values.astype(np.float32)
y_test_s2 = df_test.loc[mask_r_test, "y_direction"].values

dates_tr2 = df_train.loc[mask_r_tr, "time_utc"]
years_ago2 = (dates_tr2.max() - dates_tr2).dt.days / 365.25
sample_w2 = np.exp(-RECENCY_DECAY * years_ago2).values
sample_w2 = sample_w2 / sample_w2.sum() * len(sample_w2)

pr_s2 = {}
for name, model in models.items():
    if len(X_train2) < 10:
        continue
    scores = []
    for tr, te in outer_cv.split(X_train2):
        model.fit(X_train2[tr], y_train_s2[tr], sample_weight=sample_w2[tr])
        proba = model.predict_proba(X_train2[te])[:, 1]
        prec, rec, _ = precision_recall_curve(y_train_s2[te], proba)
        scores.append(auc(rec, prec))
    pr_s2[name] = np.mean(scores)
    print(f"  {name:<15s} CV PR-AUC: {pr_s2[name]:.4f}")

estimators2 = [(n, CalibratedClassifierCV(m, method="isotonic", cv=CALIB_CV)) for n, m in models.items()]
ensemble_s2 = VotingClassifier(estimators=estimators2, voting="soft")
ensemble_s2.fit(X_train2, y_train_s2, sample_weight=sample_w2)

proba_val2 = ensemble_s2.predict_proba(X_val2)[:, 1]
prec_v2, rec_v2, thresh_v2 = precision_recall_curve(y_val_s2, proba_val2)
best_t2, best_s2 = 0.5, -np.inf
for i, t in enumerate(thresh_v2):
    n = (proba_val2 >= t).sum()
    if n < MIN_VAL_SIGNALS or i >= len(prec_v2):
        continue
    score = prec_v2[i] * np.log(n + 1)
    if score > best_s2:
        best_s2, best_t2 = score, t
print(f"  Threshold: {best_t2:.4f}")

proba_test2 = ensemble_s2.predict_proba(X_test2)[:, 1]
roc_2 = roc_auc_score(y_test_s2, proba_test2)
prec_2, rec_2, _ = precision_recall_curve(y_test_s2, proba_test2)
prauc_2 = auc(rec_2, prec_2)
brier_2 = brier_score_loss(y_test_s2, proba_test2)
print(f"  Test  ROC-AUC={roc_2:.4f}  PR-AUC={prauc_2:.4f}  Brier={brier_2:.4f}")

# =============================================================================
# 5. Serialize
# =============================================================================

print("\nSerializing...")

meta = {
    "split_strategy": "A",
    "train_end": TRAIN_END,
    "test_start": TEST_START,
    "trained_at": datetime.now(timezone.utc).isoformat(),
    "n_features": 20,
    "dataset_version": "ExportedData.csv",
}

bundle_s1 = {
    "model": ensemble_s1,
    "features": top20,
    "threshold": best_t1,
    "roc_auc": float(roc_1),
    "pr_auc": float(prauc_1),
    "brier": float(brier_1),
    **meta,
}
joblib.dump(bundle_s1, MODELS_DIR / "MERG_v1_reaction.joblib")
print(f"  MERG_v1_reaction.joblib  ({len(top20)} features, ROC={roc_1:.4f})")

bundle_s2 = {
    "model": ensemble_s2,
    "features": top20,
    "threshold": best_t2,
    "roc_auc": float(roc_2),
    "pr_auc": float(prauc_2),
    "brier": float(brier_2),
    **meta,
}
joblib.dump(bundle_s2, MODELS_DIR / "MERG_v1_direction.joblib")
print(f"  MERG_v1_direction.joblib  ({len(top20)} features, ROC={roc_2:.4f})")

# Feature importance artifact
imp_json = [{"rank": i, "feature": f, "importance": float(imp)}
            for i, (f, imp) in enumerate(ranked[:20], 1)]
with open(FEATURES_DIR / "merg_v1_feature_importance.json", "w") as f:
    json.dump(imp_json, f, indent=2)
print(f"  merg_v1_feature_importance.json")

# =============================================================================
# 6. Quick combined validation
# =============================================================================

p_rxn = ensemble_s1.predict_proba(X_test)[:, 1]
p_up_arr = np.zeros(len(p_rxn))
p_up_arr[mask_r_test.values] = ensemble_s2.predict_proba(X_test2)[:, 1]
pU = p_rxn * p_up_arr
pD = p_rxn * (1 - p_up_arr)
pN = 1 - p_rxn
pred_cls = np.array(["U", "D", "N"])[np.argmax(np.column_stack([pU, pD, pN]), axis=1)]
actual_cls = df_test["targetSimple"].values
acc = (pred_cls == actual_cls).mean()
maj = (actual_cls == "N").mean()
dir_mask = pred_cls != "N"
dir_acc = (pred_cls[dir_mask] == actual_cls[dir_mask]).mean() if dir_mask.sum() > 0 else 0

print(f"\n  Combined accuracy: {acc:.4f}  (majority baseline: {maj:.4f})")
print(f"  Directional precision: {dir_acc:.4f}  ({dir_mask.sum()} predictions)")

print("\nDone.")