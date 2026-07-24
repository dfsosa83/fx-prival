# %%
# SECTION 2: DEFINE FEATURES AND TARGETS
# ================================================================================
print("\n🎯 DEFINING FEATURES AND TARGETS")
print("-" * 60)

# Define the 6 target bonds
TARGET_BONDS = [
    'PANAMA_3.875_28',
    'PANAMA_9.375_29',
    'PANAMA_6.4_35' ,
    'PANAMA_6.7_36',
    #'PANAMA_4.3_53',
    'PANAMA_6.853_54',
    'PANAMA_3.87_60'
]

# Target columns (6 spreads to predict)
target_columns = [f'{bond}_spread_target' for bond in TARGET_BONDS]

# Load selected features from Vote System
selected_features_df = pd.read_csv('C:/Users/dsosa/Documents/augment-projects/Alpha-Underdog/production_v2/notebooks/selected_features_vote_system.csv')
feature_columns = selected_features_df['Feature'].tolist()

print(f"📊 Features: {len(feature_columns)}")
print(f"🎯 Targets: {len(target_columns)}")
print()
print("Target bonds:")
for i, bond in enumerate(TARGET_BONDS, 1):
    print(f"   {i}. {bond}")

# Verify all columns exist
missing_features = [f for f in feature_columns if f not in train_df.columns]
missing_targets = [t for t in target_columns if t not in train_df.columns]

if missing_features:
    print(f"\n⚠️ Missing features: {missing_features}")
    feature_columns = [f for f in feature_columns if f in train_df.columns]

if missing_targets:
    print(f"\n⚠️ Missing targets: {missing_targets}")
    target_columns = [t for t in target_columns if t in train_df.columns]

print(f"\n✅ Final feature count: {len(feature_columns)}")
print(f"✅ Final target count: {len(target_columns)}")



# %%
# SECTION 3: PREPARE DATASETS FOR NESTED CV
# ================================================================================
print("\n📊 PREPARING DATASETS FOR NESTED CV")
print("-" * 60)

# Combine train and validation for nested CV (test remains held out)
#train_full_df = pd.concat([train_df, valid_df], ignore_index=True)
train_full_df = train_df.copy()

print(f"✅ Combined train+valid: {train_full_df.shape}")
print(f"✅ Test (held out): {test_df.shape}")

# Create feature matrices and targets
X_train_full = train_full_df[feature_columns].copy()
y_train_full = train_full_df[target_columns].copy()

X_valid = valid_df[feature_columns].copy()
y_valid = valid_df[target_columns].copy()

#X_test = test_df[feature_columns].copy()
#y_test = test_df[target_columns].copy()

# Create year groups for GroupKFold (temporal grouping)
train_full_df['year'] = train_full_df['Date'].dt.year
groups_train_full = train_full_df['year'].values

print(f"\n📅 Year distribution in train_full:")
print(train_full_df['year'].value_counts().sort_index())

print(f"\n✅ X_train_full: {X_train_full.shape}")
print(f"✅ y_train_full: {y_train_full.shape}")
print(f"✅ X_valid: {X_valid.shape}")
print(f"✅ y_valid: {y_valid.shape}")

# Data quality checks
print(f"\n🔍 DATA QUALITY CHECKS:")
print(f"   Missing values in X_train_full: {X_train_full.isnull().sum().sum()}")
print(f"   Missing values in y_train_full: {y_train_full.isnull().sum().sum()}")
print(f"   All features numeric: {all(X_train_full.dtypes.apply(lambda x: x in ['int64', 'float64']))}")

# Handle any remaining NaN in targets (drop rows)
#if y_train_full.isnull().sum().sum() > 0:
#    print(f"\n⚠️ Dropping {y_train_full.isnull().any(axis=1).sum()} rows with NaN targets")
#    valid_idx = ~y_train_full.isnull().any(axis=1)
#    X_train_full = X_train_full[valid_idx]
#    y_train_full = y_train_full[valid_idx]
#    groups_train_full = groups_train_full[valid_idx]
#    train_full_df = train_full_df[valid_idx].reset_index(drop=True)  # ← IMPORTANT: Keep train_full_df aligned
#    print(f"✅ After dropping: X_train_full {X_train_full.shape}, y_train_full {y_train_full.shape}")

# %%
# ================================================================================
# HANDLE NaN IN TARGETS - DON'T DROP ROWS!
# ================================================================================

# Check for NaN in targets
if y_train_full.isnull().sum().sum() > 0:
    print(f"\n⚠️  Found {y_train_full.isnull().sum().sum()} NaN values in targets")
    print(f"📊 NaN distribution by bond:")
    for col in y_train_full.columns:
        nan_count = y_train_full[col].isnull().sum()
        if nan_count > 0:
            print(f"   {col.replace('_spread_target', '')}: {nan_count} NaN ({nan_count/len(y_train_full)*100:.1f}%)")
    
    print(f"\n✅ KEEPING ALL ROWS - XGBoost will handle NaN during training")
    print(f"   Rationale: Different bonds have different birth dates")
    print(f"   Solution: Use sample_weight or mask during training")
    print(f"   Total rows: {len(y_train_full)}")
else:
    print(f"\n✅ No NaN values in targets")

# Handle NaN in features (fill with 0)
if X_train_full.isnull().sum().sum() > 0:
    print(f"\n⚠️ Found {X_train_full.isnull().sum().sum()} NaN values in features")
    print(f"🔧 Filling NaN with 0 (conservative approach for bond features)")
    print(f"   Rationale: Most features are changes/ratios where 0 = no change")
    X_train_full = X_train_full.fillna(0)
    print(f"✅ NaN values filled in X_train_full")

if X_valid.isnull().sum().sum() > 0:
    print(f"\n⚠️ Found {X_valid.isnull().sum().sum()} NaN values in test features")
    print(f"🔧 Filling NaN with 0")
    X_valid = X_valid.fillna(0)
    print(f"✅ NaN values filled in X_valid")

# Verify no NaN in features
print(f"\n✅ FINAL VERIFICATION:")
print(f"   X_train_full shape: {X_train_full.shape}")
print(f"   y_train_full shape: {y_train_full.shape}")
print(f"   X_train_full NaN: {X_train_full.isnull().sum().sum()}")
print(f"   y_train_full NaN: {y_train_full.isnull().sum().sum()}")
print(f"   X_valid NaN: {X_valid.isnull().sum().sum()}")
print(f"   y_valid NaN: {y_valid.isnull().sum().sum()}")

# Handle NaN in features (fill with 0)
if X_train_full.isnull().sum().sum() > 0:
    print(f"\n⚠️ Found {X_train_full.isnull().sum().sum()} NaN values in features")
    print(f"🔧 Filling NaN with 0 (conservative approach for bond features)")
    print(f"   Rationale: Most features are changes/ratios where 0 = no change")
    X_train_full = X_train_full.fillna(0)
    print(f"✅ NaN values filled in X_train_full")

if X_valid.isnull().sum().sum() > 0:
    print(f"\n⚠️ Found {X_valid.isnull().sum().sum()} NaN values in test features")
    print(f"🔧 Filling NaN with 0")
    X_valid = X_valid.fillna(0)
    print(f"✅ NaN values filled in X_valid")

# Verify no NaN remaining
print(f"\n✅ FINAL VERIFICATION:")
print(f"   X_train_full NaN: {X_train_full.isnull().sum().sum()}")
print(f"   y_train_full NaN: {y_train_full.isnull().sum().sum()}")
print(f"   X_valid NaN: {X_valid.isnull().sum().sum()}")
print(f"   y_test NaN: {y_valid.isnull().sum().sum()}")



# ================================================================================
# ⚖️ NEW SECTION: CREATE SAMPLE WEIGHTS - GIVE MORE IMPORTANCE TO RECENT YEARS
# ================================================================================
print(f"\n" + "="*80)
print(f"⚖️ CREATING SAMPLE WEIGHTS (Recent years get higher weight)")
print("="*80)

def calculate_time_weights(years, decay_rate=0.15):
    """
    Calculate exponential time-based weights
    
    Args:
        years: Array of years
        decay_rate: How fast weights decay (0.15 = 15% decay per year back)
                   Higher = more aggressive recency bias
                   0.10 = Mild (10% decay per year)
                   0.15 = Moderate (15% decay per year) ← RECOMMENDED
                   0.20 = Strong (20% decay per year)
                   0.30 = Very strong (30% decay per year)
                   
    Returns:
        Normalized weights (sum to len(years))
    """
    max_year = years.max()
    years_ago = max_year - years
    
    # Exponential decay: weight = exp(-decay_rate * years_ago)
    # Example: If max_year=2024, decay_rate=0.15
    #   2024: exp(-0.15 * 0) = 1.00 (100% weight)
    #   2023: exp(-0.15 * 1) = 0.86 (86% weight)
    #   2022: exp(-0.15 * 2) = 0.74 (74% weight)
    #   2021: exp(-0.15 * 3) = 0.64 (64% weight)
​    weights = np.exp(-decay_rate * years_ago)
​    
    # Normalize so sum = number of samples (sklearn convention)
​    weights = weights * len(weights) / weights.sum()
​    
​    return weights

# Calculate weights based on year
sample_weights = calculate_time_weights(train_full_df['year'].values, decay_rate=0.15)

# Show weight distribution by year
print("\n📊 Sample Weight Distribution by Year:")
weight_by_year = pd.DataFrame({
    'Year': train_full_df['year'],
    'Weight': sample_weights
}).groupby('Year')['Weight'].agg(['mean', 'sum', 'count'])

weight_by_year['Avg_Weight_Per_Sample'] = weight_by_year['mean']
weight_by_year['Total_Weight'] = weight_by_year['sum']
weight_by_year['N_Samples'] = weight_by_year['count']
weight_by_year['Relative_Importance'] = weight_by_year['mean'] / weight_by_year['mean'].min()

print(weight_by_year[['N_Samples', 'Avg_Weight_Per_Sample', 'Relative_Importance']].round(2))

print(f"\n💡 Interpretation:")
print(f"   - Relative_Importance shows how much more important recent years are")
print(f"   - Example: If 2024 has Relative_Importance = 3.0, it's 3x more important than oldest year")
print(f"   - Decay rate = 0.15 means ~15% weight reduction per year back in time")
print(f"   - Recent years (2022-2024) will have MORE influence on model training")
print(f"   - Older years (2018-2020) will have LESS influence on model training")

print(f"\n✅ Sample weights created: {len(sample_weights)} samples")
print(f"   Min weight: {sample_weights.min():.4f}")
print(f"   Max weight: {sample_weights.max():.4f}")
print(f"   Mean weight: {sample_weights.mean():.4f}")
print(f"   Sum of weights: {sample_weights.sum():.0f} (should equal {len(sample_weights)})")

# ================================================================================
# END OF NEW SECTION: SAMPLE WEIGHTS
# ================================================================================



from sklearn.model_selection import GroupKFold, TimeSeriesSplit

*# Define CV strategies*

OUTER_CV_FOLDS = 5  *# For unbiased performance estimation*

INNER_CV_FOLDS = 2  *# For hyperparameter tuning*

RANDOM_SEARCH_ITERATIONS = 30  *# Hyperparameter search iterations*

*# Create CV objects*

outer_cv = GroupKFold(n_splits=OUTER_CV_FOLDS)

inner_cv = TimeSeriesSplit(n_splits=INNER_CV_FOLDS)

print(**f**"\n  🔄 Outer CV: {OUTER_CV_FOLDS} folds (GroupKFold by year)")

print(**f**"  🔄 Inner CV: {INNER_CV_FOLDS} folds (TimeSeriesSplit)")

print(**f**"  🔍 Random Search: {RANDOM_SEARCH_ITERATIONS} iterations per inner fold")

print(**f**"  📊 Total model trainings: ~{OUTER_CV_FOLDS * INNER_CV_FOLDS * RANDOM_SEARCH_ITERATIONS} per model")

print()

print("💡 CV Strategy:")

print("  - Outer CV: GroupKFold ensures no year leakage between train/test")

print("  - Inner CV: TimeSeriesSplit for hyperparameter tuning (sequential splits)")

print("  - This combination works with any number of years!")

print("  - Sample weights: Recent years get higher importance in training")  *# ← NEW COMMENT*



# %%
# ================================================================================
# CUSTOM MULTI-OUTPUT REGRESSOR THAT HANDLES NaN IN TARGETS
# ================================================================================

from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
import numpy as np
import pandas as pd

class NaNHandlingMultiOutputRegressor(BaseEstimator, RegressorMixin):
    """
    Multi-output regressor that handles NaN values in targets.
    
    Each target's model is trained only on samples where that target is not NaN.
    This allows different bonds to have different birth dates.
    
    Parameters
    ----------
​    estimator : estimator object
​        The base estimator to fit on each target.
​    
    Attributes
    ----------
​    estimators_ : list of estimators
​        Fitted estimators, one per target.
​    """
​    
​    def __init__(self, estimator):
​        self.estimator = estimator
​    
​    def fit(self, X, y, sample_weight=None):
​        """
​        Fit one estimator per target, using only non-NaN samples for each.
​        
        Parameters
        ----------
​        X : array-like of shape (n_samples, n_features)
​            Training data
​        y : array-like of shape (n_samples, n_targets)
​            Target values. Can contain NaN.
​        sample_weight : array-like of shape (n_samples,), optional
​            Sample weights. Will be filtered per target along with NaN removal.
​        
        Returns
        -------
​        self : object
​        """
        # Convert to numpy/pandas if needed
​        if isinstance(y, pd.DataFrame):
​            y_array = y.values
​            self.target_names_ = y.columns.tolist()
​        else:
​            y_array = np.array(y)
​            self.target_names_ = [f'target_{i}' for i in range(y_array.shape[1])]
​        
​        if isinstance(X, pd.DataFrame):
​            X_array = X.values
​        else:
​            X_array = np.array(X)
​        
        # Store number of targets
​        self.n_targets_ = y_array.shape[1]
​        
        # Fit one estimator per target
​        self.estimators_ = []
​        
​        for i in range(self.n_targets_):
            # Get target column
​            y_i = y_array[:, i]
​            
            # Find non-NaN samples for this target
​            valid_mask = ~np.isnan(y_i)
​            
​            if valid_mask.sum() == 0:
                # No valid samples for this target - create a dummy estimator
​                print(f"      ⚠️ Warning: No valid samples for target {i} ({self.target_names_[i]})")
​                self.estimators_.append(None)
​                continue
​            
            # Filter X, y, and sample_weight to non-NaN samples
​            X_i = X_array[valid_mask]
​            y_i_valid = y_i[valid_mask]
​            
            # Clone the base estimator
​            estimator_i = clone(self.estimator)
​            
            # Fit with or without sample weights
​            if sample_weight is not None:
​                weight_i = sample_weight[valid_mask]
​                try:
​                    estimator_i.fit(X_i, y_i_valid, sample_weight=weight_i)
​                except TypeError:
                    # Model doesn't support sample_weight
​                    estimator_i.fit(X_i, y_i_valid)
​            else:
​                estimator_i.fit(X_i, y_i_valid)
​            
​            self.estimators_.append(estimator_i)
​        
​        return self
​    
​    def predict(self, X):
​        """
​        Predict using fitted estimators.
​        
        Parameters
        ----------
​        X : array-like of shape (n_samples, n_features)
​            Samples to predict
​        
        Returns
        -------
​        y_pred : array of shape (n_samples, n_targets)
​            Predicted values
​        """
​        check_is_fitted(self, 'estimators_')
​        
​        if isinstance(X, pd.DataFrame):
​            X_array = X.values
​        else:
​            X_array = np.array(X)
​        
        # Predict with each estimator
​        predictions = np.zeros((X_array.shape[0], self.n_targets_))
​        
​        for i, estimator in enumerate(self.estimators_):
​            if estimator is None:
                # No valid samples for this target - predict NaN
​                predictions[:, i] = np.nan
​            else:
​                predictions[:, i] = estimator.predict(X_array)
​        
​        return predictions
​    
​    def get_params(self, deep=True):
​        """Get parameters for this estimator."""
​        return {'estimator': self.estimator}
​    
​    def set_params(self, **params):
​        """Set parameters for this estimator."""
​        if 'estimator' in params:
​            self.estimator = params['estimator']
        # Handle nested parameters (e.g., estimator__max_depth)
​        estimator_params = {}
​        for key, value in params.items():
​            if key.startswith('estimator__'):
​                param_name = key.replace('estimator__', '')
​                estimator_params[param_name] = value
​        
​        if estimator_params:
​            self.estimator.set_params(**estimator_params)
​        
​        return self

print("✅ NaNHandlingMultiOutputRegressor class defined")
print("   This custom regressor trains each target only on its non-NaN samples")
print("   Perfect for bonds with different birth dates!")



# ================================================================================
# SECTION 5: MODEL DEFINITIONS AND HYPERPARAMETER GRIDS
# ================================================================================

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from sklearn.multioutput import MultiOutputRegressor

print("\n" + "="*80)
print("🤖 SECTION 5: MODEL DEFINITIONS AND HYPERPARAMETER GRIDS")
print("="*80)
print()

# ================================================================================
# BASELINE: LINEAR REGRESSION (NO HYPERPARAMETERS)
# ================================================================================
# Use our custom NaN-handling regressor instead of sklearn's MultiOutputRegressor
models = {
    'Linear Regression': {
        'model': NaNHandlingMultiOutputRegressor(LinearRegression()),
        'params': {}
    },
    'Random Forest': {
        'model': NaNHandlingMultiOutputRegressor(RandomForestRegressor(random_state=42, n_jobs=-1)),
        'params': {
            'estimator__n_estimators': [50, 100, 200, 400],
            'estimator__max_depth': [10, 15, 20, None],
            'estimator__min_samples_split': [2, 5, 10],
            'estimator__min_samples_leaf': [2, 4,8],
            'estimator__max_features': ['sqrt', 'log2',0.7]
        }
    },
    'XGBoost': {
        'model': NaNHandlingMultiOutputRegressor(XGBRegressor(random_state=42, n_jobs=-1, tree_method='hist')),
        'params': {
            'estimator__max_depth': [3, 4, 5, 6],
            'estimator__min_child_weight': [3, 5, 10],
            'estimator__learning_rate': [0.007, 0.01, 0.02, 0.03],
            'estimator__n_estimators': [300, 500, 700],
            'estimator__reg_alpha': [0.0, 1.0, 5.0],
            'estimator__reg_lambda': [1.0, 5.0, 10.0, 20.0],
            'estimator__subsample': [0.6, 0.7, 0.8],
            'estimator__colsample_bytree': [0.7, 0.8],
            'estimator__gamma': [0.0, 5.0, 1.0]
        }
    },
    'LightGBM': {
        'model': NaNHandlingMultiOutputRegressor(LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1)),
        'params': {
            'estimator__max_depth': [4, 5, 8],
            'estimator__num_leaves': [15, 31, 63],
            'estimator__min_child_samples': [30, 50, 100],
            'estimator__learning_rate': [0.007, 0.01, 0.03],
            'estimator__n_estimators': [300, 500, 700],
            'estimator__reg_alpha': [0.0, 1.0, 5.0],
            'estimator__reg_lambda': [1.0, 5.0, 10.0, 20.0],
            'estimator__subsample': [0.6, 0.7, 0.8],
            'estimator__colsample_bytree': [0.7, 0.8],
            'estimator__subsample_freq': [1],
            'estimator__min_split_gain': [0.1, 0.5]
        }
    }
}

print("✅ Models defined with NaNHandlingMultiOutputRegressor")

# ================================================================================
# PRINT GRID SIZES
# ================================================================================

print("📊 Hyperparameter Grid Sizes:")
print()

for model_name, model_config in models.items():
    grid = model_config['params']
    if grid:
        total_combinations = np.prod([len(values) for values in grid.values()])
        print(f"   {model_name}: {total_combinations:,} total combinations")
    else:
        print(f"   {model_name}: No hyperparameters (baseline)")

print()
print("💡 Grid Sizes:")
print("   - Random Forest: 288 combinations (unchanged)")
print("   - XGBoost: 2,187 combinations (3^7 = focused but thorough)")
print("   - LightGBM: 2,187 combinations (3^7 = focused but thorough)")
print()
print("⏱️ Expected Runtime:")
print("   - Random Forest: ~15 minutes")
print("   - XGBoost: ~30-45 minutes")
print("   - LightGBM: ~30-45 minutes")
print("   - TOTAL: ~1.5-2 hours")
print()



# %%
# SECTION 6: NESTED CROSS-VALIDATION IMPLEMENTATION
# ================================================================================
print("\n🎯 NESTED CROSS-VALIDATION IMPLEMENTATION")
print("=" * 70)

def calculate_multi_target_metrics(y_true, y_pred, target_names):
    """
    Calculate comprehensive metrics for multi-target regression

​    Returns metrics per target and aggregated metrics
​    """
​    metrics = {}

    # Per-target metrics
​    for i, target_name in enumerate(target_names):
​        y_true_i = y_true.iloc[:, i] if isinstance(y_true, pd.DataFrame) else y_true[:, i]
​        y_pred_i = y_pred[:, i]

        # Remove NaN values for this target
​        valid_mask = ~np.isnan(y_true_i)
​        if valid_mask.sum() == 0:
​            continue

​        y_true_clean = y_true_i[valid_mask]
​        y_pred_clean = y_pred_i[valid_mask]

​        rmse = np.sqrt(mean_squared_error(y_true_clean, y_pred_clean))
​        mae = mean_absolute_error(y_true_clean, y_pred_clean)
​        r2 = r2_score(y_true_clean, y_pred_clean)

        # Convert to basis points (multiply by 100)
​        rmse_bp = rmse * 100
​        mae_bp = mae * 100

​        metrics[target_name] = {
​            'rmse_bp': rmse_bp,
​            'mae_bp': mae_bp,
​            'r2': r2,
​            'n_samples': valid_mask.sum()
​        }

    # Aggregated metrics (mean across targets)
​    avg_rmse_bp = np.mean([m['rmse_bp'] for m in metrics.values()])
​    avg_mae_bp = np.mean([m['mae_bp'] for m in metrics.values()])
​    avg_r2 = np.mean([m['r2'] for m in metrics.values()])

​    metrics['aggregated'] = {
​        'avg_rmse_bp': avg_rmse_bp,
​        'avg_mae_bp': avg_mae_bp,
​        'avg_r2': avg_r2
​    }

​    return metrics


def nested_cross_validation_multi_target(model, param_grid, X, y, groups,
                                         outer_cv, inner_cv, model_name, target_names,
                                         sample_weights=None):  # ← NEW PARAMETER: sample_weights
    """
    Perform nested cross-validation for multi-target regression

​    ⚖️ NEW: Supports sample_weights to give more importance to recent years

​    Args:
​        model: Base model (wrapped in MultiOutputRegressor)
​        param_grid: Hyperparameter grid for tuning
​        X, y: Training data and targets
​        groups: Group labels for GroupKFold (year)
​        outer_cv, inner_cv: Cross-validation objects
​        model_name: Name for reporting
​        target_names: List of target column names
​        sample_weights: Array of sample weights (same length as X) ← NEW

​    Returns:
​        dict: Comprehensive nested CV results
​    """
​    print(f"\n🔄 Starting Nested CV for {model_name}")
​    print(f"   📊 Outer folds: {outer_cv.n_splits}, Inner folds: {inner_cv.n_splits}")
​    print(f"   🎯 Primary metric: Average RMSE (bp) across {len(target_names)} bonds")

    # ⚖️ NEW: Show if using sample weights
​    if sample_weights is not None:
​        print(f"   ⚖️ Using sample weights (recent years get higher importance)")
​    else:
​        print(f"   ⚖️ No sample weights (all years equally important)")

    # Storage for results
​    outer_scores_rmse_bp = []
​    outer_scores_mae_bp = []
​    outer_scores_r2 = []
​    best_params_per_fold = []
​    fold_details = []
​    per_bond_rmse = {bond: [] for bond in target_names}

    # Outer CV loop
​    for fold_idx, (train_idx, val_idx) in enumerate(outer_cv.split(X, y, groups), 1):
​        print(f"\n   🔄 Outer Fold {fold_idx}/{outer_cv.n_splits}")

        # Split data for this outer fold
​        X_train_outer = X.iloc[train_idx]
​        X_val_outer = X.iloc[val_idx]
​        y_train_outer = y.iloc[train_idx]
​        y_val_outer = y.iloc[val_idx]
​        groups_train_outer = groups[train_idx]

        # ⚖️ NEW: Split sample weights for this outer fold
​        if sample_weights is not None:
​            weights_train_outer = sample_weights[train_idx]
​            weights_val_outer = sample_weights[val_idx]
​        else:
​            weights_train_outer = None
​            weights_val_outer = None

​        print(f"      📊 Fold {fold_idx} sizes: Train={len(train_idx)}, Val={len(val_idx)}")

        # Inner CV: Hyperparameter tuning
​        print(f"      🔧 Inner CV: Hyperparameter tuning...")

        # Handle Linear Regression (no hyperparameters)
​        if model_name == 'Linear Regression':
​            best_model = model
            # ⚖️ NOTE: LinearRegression in MultiOutputRegressor doesn't support sample_weight
            # So we fit without weights (baseline comparison)
​            best_model.fit(X_train_outer, y_train_outer)
​            best_params = {}
​            best_params_per_fold.append(best_params)
​            print(f"      ✅ Linear Regression (no hyperparameters to tune)")
​            print(f"      ⚠️ Linear Regression doesn't support sample_weight in MultiOutputRegressor")
​        else:
            # For other models, perform hyperparameter search
            # Custom scoring function for multi-target RMSE
​            def multi_target_rmse_scorer(estimator, X, y):
​                y_pred = estimator.predict(X)
                # Calculate average RMSE across all targets
​                rmse_per_target = []
​                for i in range(y.shape[1]):
​                    valid_mask = ~np.isnan(y.iloc[:, i])
​                    if valid_mask.sum() > 0:
​                        rmse = np.sqrt(mean_squared_error(y.iloc[:, i][valid_mask],
​                                                          y_pred[valid_mask, i]))
​                        rmse_per_target.append(rmse)
​                avg_rmse = np.mean(rmse_per_target)
​                return -avg_rmse  # Negative because sklearn maximizes

​            from sklearn.metrics import make_scorer
​            custom_scorer = make_scorer(multi_target_rmse_scorer, greater_is_better=True)

            # Handle TimeSeriesSplit (no groups) vs GroupKFold (uses groups)
​            from sklearn.model_selection import TimeSeriesSplit

​            if isinstance(inner_cv, TimeSeriesSplit):
                # TimeSeriesSplit doesn't use groups
​                cv_splits = inner_cv.split(X_train_outer, y_train_outer)
​            else:
                # GroupKFold uses groups
​                cv_splits = inner_cv.split(X_train_outer, y_train_outer, groups_train_outer)

​            random_search = RandomizedSearchCV(
​                estimator=model,
​                param_distributions=param_grid,
​                n_iter=RANDOM_SEARCH_ITERATIONS,
​                cv=cv_splits,
​                scoring=custom_scorer,
​                n_jobs=-1,
​                random_state=42,
​                verbose=0
​            )

            # ⚖️ NEW: Fit with sample weights if available
​            if weights_train_outer is not None:
                # For tree-based models (RF, XGBoost, LightGBM), pass sample_weight
                # RandomizedSearchCV will automatically split sample_weight across CV folds
                # and pass it to the estimator's fit method
​                try:
​                    random_search.fit(X_train_outer, y_train_outer, sample_weight=weights_train_outer)
​                    print(f"      ⚖️ Fitted with sample weights (recent years prioritized)")
​                except TypeError as e:
                    # If model doesn't support sample_weight, fit without it
​                    print(f"      ⚠️ Model doesn't support sample_weight: {e}")
​                    print(f"      ⚠️ Fitting without weights")
​                    random_search.fit(X_train_outer, y_train_outer)
​            else:
​                random_search.fit(X_train_outer, y_train_outer)

​            best_model = random_search.best_estimator_
​            best_params = random_search.best_params_
​            best_params_per_fold.append(best_params)

​            best_inner_rmse = -random_search.best_score_
​            print(f"      ✅ Best inner CV RMSE: {best_inner_rmse*100:.2f} bp")

        # Evaluate best model on outer validation fold
​        y_pred_outer = best_model.predict(X_val_outer)

        # Calculate comprehensive metrics
​        fold_metrics = calculate_multi_target_metrics(y_val_outer, y_pred_outer, target_names)

​        fold_rmse_bp = fold_metrics['aggregated']['avg_rmse_bp']
​        fold_mae_bp = fold_metrics['aggregated']['avg_mae_bp']
​        fold_r2 = fold_metrics['aggregated']['avg_r2']

        # Store scores
​        outer_scores_rmse_bp.append(fold_rmse_bp)
​        outer_scores_mae_bp.append(fold_mae_bp)
​        outer_scores_r2.append(fold_r2)

        # Store per-bond RMSE
​        for bond in target_names:
​            if bond in fold_metrics:
​                per_bond_rmse[bond].append(fold_metrics[bond]['rmse_bp'])

​        print(f"      📊 Outer fold performance:")
​        print(f"         🎯 Avg RMSE: {fold_rmse_bp:.2f} bp")
​        print(f"         🎯 Avg MAE:  {fold_mae_bp:.2f} bp")
​        print(f"         📈 Avg R²:   {fold_r2:.4f}")

        # Show per-bond RMSE
​        print(f"      📊 Per-bond RMSE (bp):")
​        for bond in target_names:
​            if bond in fold_metrics:
​                print(f"         {bond}: {fold_metrics[bond]['rmse_bp']:.2f} bp")

        # Store detailed results
​        fold_details.append({
​            'fold': fold_idx,
​            'avg_rmse_bp': fold_rmse_bp,
​            'avg_mae_bp': fold_mae_bp,
​            'avg_r2': fold_r2,
​            'per_bond_metrics': fold_metrics,
​            'best_params': best_params,
​            'train_size': len(train_idx),
​            'val_size': len(val_idx)
​        })

    # Calculate final nested CV results
​    nested_cv_results = {
​        'model_name': model_name,
        # Aggregated metrics
​        'outer_cv_rmse_bp_mean': np.mean(outer_scores_rmse_bp),
​        'outer_cv_rmse_bp_std': np.std(outer_scores_rmse_bp),
​        'outer_cv_mae_bp_mean': np.mean(outer_scores_mae_bp),
​        'outer_cv_mae_bp_std': np.std(outer_scores_mae_bp),
​        'outer_cv_r2_mean': np.mean(outer_scores_r2),
​        'outer_cv_r2_std': np.std(outer_scores_r2),
        # Raw scores
​        'outer_scores_rmse_bp': outer_scores_rmse_bp,
​        'outer_scores_mae_bp': outer_scores_mae_bp,
​        'outer_scores_r2': outer_scores_r2,
        # Per-bond RMSE
​        'per_bond_rmse': per_bond_rmse,
​        'per_bond_rmse_mean': {bond: np.mean(scores) for bond, scores in per_bond_rmse.items() if scores},
​        'per_bond_rmse_std': {bond: np.std(scores) for bond, scores in per_bond_rmse.items() if scores},
        # Hyperparameters
​        'best_params_per_fold': best_params_per_fold,
​        'fold_details': fold_details,
        # Selection metric
​        'selection_metric': 'rmse_bp',
​        'selection_score': np.mean(outer_scores_rmse_bp)
​    }

​    print(f"\n   🏆 {model_name} Nested CV Summary:")
​    print(f"      🎯 Avg RMSE: {nested_cv_results['outer_cv_rmse_bp_mean']:.2f} ± {nested_cv_results['outer_cv_rmse_bp_std']:.2f} bp")
​    print(f"      🎯 Avg MAE:  {nested_cv_results['outer_cv_mae_bp_mean']:.2f} ± {nested_cv_results['outer_cv_mae_bp_std']:.2f} bp")
​    print(f"      📈 Avg R²:   {nested_cv_results['outer_cv_r2_mean']:.4f} ± {nested_cv_results['outer_cv_r2_std']:.4f}")

​    return nested_cv_results

print("✅ Nested CV function defined for multi-target regression")
print("⚖️ NEW: Function now supports sample_weights parameter")  # ← NEW COMMENT



# %%
# SECTION 7: RUN NESTED CROSS-VALIDATION FOR ALL MODELS
# ================================================================================

# ================================================================================
# EXTRACT base_models AND param_grids FROM models DICTIONARY
# ================================================================================

# The 'models' dictionary from Section 5 has this structure:
# models = {
#     'Linear Regression': {'model': ..., 'params': {...}},
#     'Random Forest': {'model': ..., 'params': {...}},
#     ...
# }

# Extract base_models (the model objects)
base_models = {name: config['model'] for name, config in models.items()}

# Extract param_grids (the hyperparameter grids)
param_grids = {name: config['params'] for name, config in models.items()}

print("\n" + "="*80)
print("📦 EXTRACTED MODELS AND PARAMETER GRIDS")
print("="*80)
print()

print("Base Models:")
for name in base_models.keys():
    print(f"   ✓ {name}")

print()
print("Parameter Grids:")
for name, params in param_grids.items():
    if params:
        n_combinations = np.prod([len(values) for values in params.values()])
        print(f"   ✓ {name}: {n_combinations:,} combinations")
    else:
        print(f"   ✓ {name}: No hyperparameters (baseline)")

print()
print("="*80)
print()



# %%
# SECTION 7: RUN NESTED CROSS-VALIDATION FOR ALL MODELS
# ================================================================================
print("\n🚀 RUNNING NESTED CROSS-VALIDATION FOR ALL MODELS")
print("=" * 70)
print("⚠️  This will take 1-2 hours depending on your hardware...")
print(f"   Each model will be trained ~{OUTER_CV_FOLDS * INNER_CV_FOLDS * RANDOM_SEARCH_ITERATIONS} times")
print("🎯 Optimizing for average RMSE (bp) across 6 bonds")
print("📊 Model progression: Linear Regression (baseline) → Random Forest → XGBoost → LightGBM")
print()
print("💡 NEW: Stronger regularization for XGBoost/LightGBM to fix flat predictions")
print("⚖️ NEW: Using sample weights - recent years (2022-2024) get higher importance")  # ← NEW COMMENT
print()

# Storage for all nested CV results
nested_cv_results = {}
total_start_time = datetime.now()

# Run nested CV for each model
for model_idx, (model_name, base_model) in enumerate(base_models.items(), 1):
    print(f"\n{'='*80}")
    print(f"NESTED CV {model_idx}/{len(base_models)}: {model_name.upper()}")
    print(f"{'='*80}")

​    model_start_time = datetime.now()

    # ⚖️ NEW: Run nested cross-validation WITH sample_weights
​    results = nested_cross_validation_multi_target(
​        model=base_model,
​        param_grid=param_grids[model_name],
​        X=X_train_full,
​        y=y_train_full,
​        groups=groups_train_full,
​        outer_cv=outer_cv,
​        inner_cv=inner_cv,
​        model_name=model_name,
​        target_names=target_columns,
​        sample_weights=sample_weights  # ← NEW: Pass sample weights
​    )

​    nested_cv_results[model_name] = results

​    model_end_time = datetime.now()
​    model_duration = (model_end_time - model_start_time).total_seconds() / 60

​    print(f"\n   ⏱️ {model_name} completed in {model_duration:.1f} minutes")

    # Show progress
​    remaining_models = len(base_models) - model_idx
​    if remaining_models > 0:
​        estimated_remaining = model_duration * remaining_models
​        print(f"   📊 Progress: {model_idx}/{len(base_models)} models complete")
​        print(f"   ⏰ Estimated remaining time: {estimated_remaining:.1f} minutes")

total_end_time = datetime.now()
total_duration = (total_end_time - total_start_time).total_seconds() / 60

print(f"\n🎉 ALL NESTED CV COMPLETED!")
print(f"⏱️ Total execution time: {total_duration:.1f} minutes")
print()
print("="*80)
print()



# %%
# SECTION 8: NESTED CV RESULTS ANALYSIS AND MODEL COMPARISON
# ================================================================================
print("\n📊 NESTED CV RESULTS ANALYSIS AND MODEL COMPARISON")
print("=" * 70)

# Create comprehensive comparison DataFrame
comparison_data = []
for model_name, results in nested_cv_results.items():
    comparison_data.append({
        'Model': model_name,
        'Avg_RMSE_bp_Mean': results['outer_cv_rmse_bp_mean'],
        'Avg_RMSE_bp_Std': results['outer_cv_rmse_bp_std'],
        'Avg_MAE_bp_Mean': results['outer_cv_mae_bp_mean'],
        'Avg_MAE_bp_Std': results['outer_cv_mae_bp_std'],
        'Avg_R2_Mean': results['outer_cv_r2_mean'],
        'Avg_R2_Std': results['outer_cv_r2_std'],
        'Selection_Score': results['selection_score']
    })

nested_comparison_df = pd.DataFrame(comparison_data)
# Sort by RMSE (lower is better)
nested_comparison_df = nested_comparison_df.sort_values('Avg_RMSE_bp_Mean', ascending=True)

print("\n🏆 NESTED CV PERFORMANCE COMPARISON (Sorted by RMSE - Lower is Better):")
print("=" * 90)
print(nested_comparison_df.round(2).to_string(index=False))

# Identify best model
best_model_nested = nested_comparison_df.iloc[0]['Model']
best_rmse_nested = nested_comparison_df.iloc[0]['Avg_RMSE_bp_Mean']
best_rmse_std_nested = nested_comparison_df.iloc[0]['Avg_RMSE_bp_Std']
best_mae_nested = nested_comparison_df.iloc[0]['Avg_MAE_bp_Mean']
best_mae_std_nested = nested_comparison_df.iloc[0]['Avg_MAE_bp_Std']
best_r2_nested = nested_comparison_df.iloc[0]['Avg_R2_Mean']
best_r2_std_nested = nested_comparison_df.iloc[0]['Avg_R2_Std']



print(f"\n🥇 BEST MODEL (Based on RMSE): {best_model_nested}")
print(f"   🎯 Unbiased RMSE: {best_rmse_nested:.2f} ± {best_rmse_std_nested:.2f} bp")
print(f"   🎯 Unbiased MAE:  {best_mae_nested:.2f} ± {best_mae_std_nested:.2f} bp")
print(f"   📈 Unbiased R²:   {best_r2_nested:.4f} ± {best_r2_std_nested:.4f}")
print(f"   ⚖️ Trained with sample weights (recent years prioritized)")  # ← NEW COMMENT

# Calculate confidence intervals
rmse_ci_lower = best_rmse_nested - 1.96 * best_rmse_std_nested
rmse_ci_upper = best_rmse_nested + 1.96 * best_rmse_std_nested
print(f"   📊 95% Confidence Interval (RMSE): [{rmse_ci_lower:.2f}, {rmse_ci_upper:.2f}] bp")

# Performance assessment
print(f"\n📈 PERFORMANCE ASSESSMENT:")
if best_rmse_nested <= 100:
    performance_level = "EXCELLENT"
    emoji = "🎉"
elif best_rmse_nested <= 150:
    performance_level = "GOOD"
    emoji = "✅"
elif best_rmse_nested <= 200:
    performance_level = "ACCEPTABLE"
    emoji = "👍"
else:
    performance_level = "NEEDS IMPROVEMENT"
    emoji = "⚠️"

print(f"   {emoji} Performance Level: {performance_level}")
print(f"   💰 RMSE = {best_rmse_nested:.2f} bp (Average prediction error)")
print(f"   💰 MAE = {best_mae_nested:.2f} bp (Median prediction error)")

# Model ranking summary
print(f"\n📋 MODEL RANKING (by RMSE):")
for idx, row in nested_comparison_df.iterrows():
    rank = nested_comparison_df.index.get_loc(idx) + 1
    model = row['Model']
    rmse = row['Avg_RMSE_bp_Mean']
    rmse_std = row['Avg_RMSE_bp_Std']
    print(f"   {rank}. {model:<20}: RMSE = {rmse:.2f} ± {rmse_std:.2f} bp")

print(f"\n💡 INTERPRETATION:")
print(f"   🎯 RMSE measures average prediction error in basis points")
print(f"   🎯 MAE measures typical prediction error (less sensitive to outliers)")
print(f"   📈 R² measures proportion of variance explained (0-1 scale)")
print(f"   ✅ Lower RMSE/MAE = Better model for bond spread prediction")
print(f"   📊 Linear Regression provides interpretable baseline performance")
print(f"   ⚖️ Sample weights give 2-3x more importance to recent years (2022-2024)")  # ← NEW COMMENT

print("\n" + "="*80)
print("⚖️ SAMPLE WEIGHTS SUMMARY")
print("="*80)
print(f"✅ Recent years (2022-2024) have higher influence on model training")
print(f"✅ Older years (2018-2020) have lower influence on model training")
print(f"✅ Decay rate: 0.15 (15% weight reduction per year back in time)")
print(f"✅ This helps models learn current market dynamics better")
print(f"✅ Adjust decay_rate in line ~200 to change recency bias strength")
print("="*80)



# ============================================================================
# 🎯 MANUAL MODEL SELECTION OVERRIDE
# ============================================================================
# Uncomment ONE of the lines below to manually select a different model:

# MANUAL_MODEL_SELECTION = 'Linear Regression'  # Test Linear Regression
# MANUAL_MODEL_SELECTION = 'Random Forest'      # Test Random Forest
# MANUAL_MODEL_SELECTION = 'XGBoost'            # Test XGBoost
MANUAL_MODEL_SELECTION = 'LightGBM'           # Test LightGBM
# MANUAL_MODEL_SELECTION = None  # Use automatic selection (best model)

# Apply manual override if specified
if MANUAL_MODEL_SELECTION is not None:
    print(f"\n⚠️ MANUAL MODEL OVERRIDE ACTIVE!")
    print(f"   🎯 Automatically selected: {best_model_nested}")
    print(f"   👉 Manually overriding to: {MANUAL_MODEL_SELECTION}")
    
    # Check if manual selection is valid
​    if MANUAL_MODEL_SELECTION in nested_cv_results:
        # Get metrics for manually selected model
​        manual_row = nested_comparison_df[nested_comparison_df['Model'] == MANUAL_MODEL_SELECTION].iloc[0]
​        
        # Override the selection
​        best_model_nested = MANUAL_MODEL_SELECTION
​        best_rmse_nested = manual_row['Avg_RMSE_bp_Mean']
​        best_rmse_std_nested = manual_row['Avg_RMSE_bp_Std']
​        best_mae_nested = manual_row['Avg_MAE_bp_Mean']
​        best_mae_std_nested = manual_row['Avg_MAE_bp_Std']
​        best_r2_nested = manual_row['Avg_R2_Mean']
​        best_r2_std_nested = manual_row['Avg_R2_Std']
​        
​        print(f"   ✅ Model selection overridden successfully!")
​        print(f"   📊 {MANUAL_MODEL_SELECTION} RMSE: {best_rmse_nested:.2f} ± {best_rmse_std_nested:.2f} bp")
​    else:
​        print(f"   ❌ ERROR: '{MANUAL_MODEL_SELECTION}' not found in trained models!")
​        print(f"   📋 Available models: {list(nested_cv_results.keys())}")
​        print(f"   🔄 Reverting to automatic selection: {best_model_nested}")
else:
​    print(f"\n✅ Using automatic model selection (best RMSE)")



# %%
# SECTION 9: BASELINE COMPARISON ANALYSIS
# ================================================================================
print("\n📈 BASELINE COMPARISON ANALYSIS")
print("-" * 60)

if 'Linear Regression' in nested_cv_results:
    lr_results = nested_cv_results['Linear Regression']
    lr_rmse = lr_results['outer_cv_rmse_bp_mean']
    lr_rmse_std = lr_results['outer_cv_rmse_bp_std']

​    lr_row = nested_comparison_df[nested_comparison_df['Model'] == 'Linear Regression']
​    lr_idx = lr_row.index[0]
​    lr_rank = nested_comparison_df.index.get_loc(lr_idx) + 1

​    print(f"🎯 LINEAR REGRESSION BASELINE PERFORMANCE:")
​    print(f"   📊 RMSE: {lr_rmse:.2f} ± {lr_rmse_std:.2f} bp")
​    print(f"   🏆 Ranking: #{lr_rank} out of {len(base_models)} models")

    # Calculate improvement over baseline
​    print(f"\n📊 IMPROVEMENT OVER LINEAR REGRESSION BASELINE:")
​    for idx, row in nested_comparison_df.iterrows():
​        model = row['Model']
​        rmse = row['Avg_RMSE_bp_Mean']

​        if model != 'Linear Regression':
​            improvement = ((lr_rmse - rmse) / lr_rmse) * 100
​            improvement_bp = lr_rmse - rmse

​            if improvement > 0:
​                print(f"   ✅ {model:<20}: {improvement:+5.1f}% improvement ({improvement_bp:+6.2f} bp)")
​            else:
​                print(f"   ❌ {model:<20}: {improvement:+5.1f}% worse ({improvement_bp:+6.2f} bp)")

    # Business interpretation
​    print(f"\n💡 BASELINE INSIGHTS:")
​    if lr_rank == len(base_models):
​        print(f"   ✅ EXCELLENT! Complex models significantly outperform baseline")
​        print(f"   💼 Investment in advanced algorithms is clearly justified")
​        print(f"   🚀 Linear Regression serves as proof that complexity adds value")
​    elif lr_rank >= len(base_models) - 1:
​        print(f"   ✅ Complex models substantially outperform baseline")
​        print(f"   💼 Advanced algorithms provide meaningful improvements")
​    elif lr_rank <= 2:
​        print(f"   🚨 LINEAR REGRESSION PERFORMS SURPRISINGLY WELL!")
​        print(f"   💼 Consider using Linear Regression (simpler, interpretable)")
​    else:
​        print(f"   👍 Linear Regression performs competitively")
​        print(f"   💼 Complex models provide modest improvements")

    # Complexity value assessment
​    best_improvement = max([((lr_rmse - row['Avg_RMSE_bp_Mean']) / lr_rmse) * 100
​                           for _, row in nested_comparison_df.iterrows()
​                           if row['Model'] != 'Linear Regression'])

​    print(f"\n🎯 COMPLEXITY VALUE ASSESSMENT:")
​    if best_improvement >= 15:
​        print(f"   🎉 OUTSTANDING: Best model improves {best_improvement:.1f}% over baseline")
​        print(f"   💰 Strong business case for complex models")
​    elif best_improvement >= 10:
​        print(f"   ✅ GOOD: Best model improves {best_improvement:.1f}% over baseline")
​        print(f"   💼 Solid justification for model complexity")
​    elif best_improvement >= 5:
​        print(f"   👍 MODERATE: Best model improves {best_improvement:.1f}% over baseline")
​        print(f"   ⚖️ Consider cost-benefit of complexity")
​    else:
​        print(f"   ⚠️ MINIMAL: Best model improves only {best_improvement:.1f}% over baseline")
​        print(f"   🤔 Question whether complexity is worth it")

​    print(f"\n🔍 LINEAR REGRESSION ADVANTAGES (as baseline):")
​    print(f"   ✅ Highly interpretable (feature coefficients)")
​    print(f"   ✅ Fast training and prediction")
​    print(f"   ✅ No hyperparameter tuning needed")
​    print(f"   ✅ Robust to overfitting")
​    print(f"   ✅ Easy to deploy and maintain")
​    print(f"   📊 Serves as performance floor - complex models must beat this!")

else:
    print("   ⚠️ Linear Regression results not found.")



# %%
# SECTION 10: PER-BOND PERFORMANCE ANALYSIS
# ================================================================================
print("\n📊 PER-BOND PERFORMANCE ANALYSIS")
print("-" * 60)

# Analyze performance for each bond across all models
print(f"\n🎯 RMSE (bp) PER BOND FOR EACH MODEL:")
print("=" * 90)

# Create per-bond comparison table
per_bond_data = []
for model_name, results in nested_cv_results.items():
    row_data = {'Model': model_name}
    for bond in target_columns:
        if bond in results['per_bond_rmse_mean']:
            rmse_mean = results['per_bond_rmse_mean'][bond]
            rmse_std = results['per_bond_rmse_std'][bond]
            row_data[bond] = f"{rmse_mean:.1f}±{rmse_std:.1f}"
        else:
            row_data[bond] = "N/A"
    per_bond_data.append(row_data)

per_bond_df = pd.DataFrame(per_bond_data)
print(per_bond_df.to_string(index=False))

# Find best model for each bond
print(f"\n🏆 BEST MODEL PER BOND:")
print("-" * 60)
for bond in target_columns:
    bond_rmse = {}
    for model_name, results in nested_cv_results.items():
        if bond in results['per_bond_rmse_mean']:
            bond_rmse[model_name] = results['per_bond_rmse_mean'][bond]

​    if bond_rmse:
​        best_model_for_bond = min(bond_rmse, key=bond_rmse.get)
​        best_rmse_for_bond = bond_rmse[best_model_for_bond]
​        print(f"   {bond}: {best_model_for_bond} ({best_rmse_for_bond:.2f} bp)")

# Identify most challenging bonds
print(f"\n📈 BOND DIFFICULTY RANKING (by average RMSE across models):")
print("-" * 60)
bond_difficulty = {}
for bond in target_columns:
    rmse_values = []
    for model_name, results in nested_cv_results.items():
        if bond in results['per_bond_rmse_mean']:
            rmse_values.append(results['per_bond_rmse_mean'][bond])
    if rmse_values:
        bond_difficulty[bond] = np.mean(rmse_values)

sorted_bonds = sorted(bond_difficulty.items(), key=lambda x: x[1], reverse=True)
for rank, (bond, avg_rmse) in enumerate(sorted_bonds, 1):
    if avg_rmse > 150:
        emoji = "🔴"
        difficulty = "HARD"
    elif avg_rmse > 100:
        emoji = "🟡"
        difficulty = "MODERATE"
    else:
        emoji = "🟢"
        difficulty = "EASY"
    print(f"   {rank}. {bond}: {avg_rmse:.2f} bp {emoji} ({difficulty})")



# %%
# SECTION 11: HYPERPARAMETER STABILITY ANALYSIS
# ================================================================================
print("\n🔧 HYPERPARAMETER STABILITY ANALYSIS")
print("-" * 70)

for model_name, results in nested_cv_results.items():
    print(f"\n📋 {model_name} - Hyperparameter Stability:")
    print("-" * 50)

​    best_params_list = results['best_params_per_fold']

    # Get all unique parameter names
​    all_param_names = set()
​    for params in best_params_list:
​        all_param_names.update(params.keys())

    # Handle models with no hyperparameters
​    if len(all_param_names) == 0:
​        print("   📊 No hyperparameters to analyze")
​        print("   ✅ PERFECT STABILITY: No hyperparameters = No sensitivity")
​        continue

​    stable_params = 0
​    total_params = len(all_param_names)

​    for param_name in sorted(all_param_names):
​        param_values = [params.get(param_name, 'N/A') for params in best_params_list]
​        unique_values = list(set(param_values))

​        if len(unique_values) == 1:
​            consistency = "✅ STABLE"
​            stable_params += 1
​        elif len(unique_values) == 2:
​            consistency = "⚠️ MODERATE"
​        else:
​            consistency = "❌ UNSTABLE"

​        value_counts = Counter(param_values)
​        most_common = value_counts.most_common(1)[0]

​        print(f"   {param_name:<35}: {consistency}")
​        print(f"      Most frequent: {most_common[0]} ({most_common[1]}/{len(param_values)} folds)")

    # Calculate stability percentage
​    stability_pct = (stable_params / total_params) * 100
​    print(f"\n   📊 Hyperparameter Stability: {stable_params}/{total_params} stable ({stability_pct:.1f}%)")

​    if stability_pct >= 80:
​        print("   ✅ HIGH STABILITY: Hyperparameters robust across data splits")
​    elif stability_pct >= 60:
​        print("   👍 MODERATE STABILITY: Some variation across splits")
​    else:
​        print("   ⚠️ LOW STABILITY: High sensitivity to data splits")



# %%
# SECTION 12: FINAL MODEL TRAINING WITH AGGREGATED BEST HYPERPARAMETERS
# ================================================================================
print("\n🎯 FINAL MODEL TRAINING WITH AGGREGATED BEST HYPERPARAMETERS")
print("=" * 70)

def get_most_frequent_params(best_params_list):
    """
    Get the most frequently selected hyperparameters across CV folds
    """
    all_param_names = set()
    for params in best_params_list:
        all_param_names.update(params.keys())

​    final_params = {}
​    for param_name in all_param_names:
​        param_values = [params.get(param_name) for params in best_params_list if param_name in params]
​        if param_values:
​            most_common = Counter(param_values).most_common(1)[0][0]
​            final_params[param_name] = most_common

​    return final_params

# Get best hyperparameters for the winning model
best_model_results = nested_cv_results[best_model_nested]
best_params_final = get_most_frequent_params(best_model_results['best_params_per_fold'])

print(f"🏆 Training final {best_model_nested} model with aggregated best parameters:")
if best_params_final:
    print("📋 Final hyperparameters (most frequent across CV folds):")
    for param, value in sorted(best_params_final.items()):
        print(f"   {param:<35}: {value}")
else:
    print("📋 No hyperparameters to set (Linear Regression)")

# Create and train final model on full training data
print(f"\n🚀 Training final {best_model_nested} model on train+valid...")
if best_params_final:
    final_model = base_models[best_model_nested].set_params(**best_params_final)
else:
    final_model = base_models[best_model_nested]

final_model.fit(X_train_full, y_train_full)

print(f"✅ Final {best_model_nested} model trained on full training set")
print(f"   📊 Training data: {X_train_full.shape[0]:,} samples")
print(f"   🔧 Features: {len(feature_columns)} variables")
print(f"   🎯 Targets: {len(target_columns)} bonds")
print(f"   🎯 Expected RMSE: {best_rmse_nested:.2f} ± {best_rmse_std_nested:.2f} bp")



*#load test set*

X_test = test_df[feature_columns].copy()

y_test = test_df[target_columns].copy()



# %%
# SECTION 13: FINAL MODEL EVALUATION ON TEST SET
# ================================================================================
print("\n🎯 FINAL MODEL EVALUATION ON TEST SET")
print("-" * 60)

# Make predictions on test set (held-out data never seen during nested CV)
y_pred_test = final_model.predict(X_test)

# Calculate comprehensive test metrics
test_metrics = calculate_multi_target_metrics(y_test, y_pred_test, target_columns)

test_rmse_bp = test_metrics['aggregated']['avg_rmse_bp']
test_mae_bp = test_metrics['aggregated']['avg_mae_bp']
test_r2 = test_metrics['aggregated']['avg_r2']

print(f"🏆 FINAL TEST PERFORMANCE ({best_model_nested}):")
print("=" * 60)
print(f"   🎯 Test Avg RMSE: {test_rmse_bp:.2f} bp")
print(f"   🎯 Test Avg MAE:  {test_mae_bp:.2f} bp")
print(f"   📈 Test Avg R²:   {test_r2:.4f}")

# Per-bond test performance
print(f"\n📊 PER-BOND TEST PERFORMANCE:")
print("-" * 60)
for bond in target_columns:
    if bond in test_metrics:
        bond_rmse = test_metrics[bond]['rmse_bp']
        bond_mae = test_metrics[bond]['mae_bp']
        bond_r2 = test_metrics[bond]['r2']
        print(f"   {bond}:")
        print(f"      RMSE: {bond_rmse:.2f} bp, MAE: {bond_mae:.2f} bp, R²: {bond_r2:.4f}")

# Compare with nested CV estimates
print(f"\n📊 NESTED CV vs TEST SET COMPARISON:")
print("-" * 60)
print(f"   Metric    | Nested CV Estimate      | Test Set    | Difference")
print(f"   ----------|------------------------|-------------|----------")
print(f"   RMSE (bp) | {best_rmse_nested:.2f} ± {best_rmse_std_nested:.2f}          | {test_rmse_bp:.2f}        | {abs(test_rmse_bp - best_rmse_nested):.2f}")
print(f"   MAE (bp)  | {best_mae_nested:.2f} ± {best_mae_std_nested:.2f}          | {test_mae_bp:.2f}        | {abs(test_mae_bp - best_mae_nested):.2f}")
print(f"   R²        | {best_r2_nested:.4f} ± {best_r2_std_nested:.4f}    | {test_r2:.4f}     | {abs(test_r2 - best_r2_nested):.4f}")

# Assess nested CV prediction accuracy
rmse_within_ci = abs(test_rmse_bp - best_rmse_nested) <= 2 * best_rmse_std_nested
mae_within_ci = abs(test_mae_bp - best_mae_nested) <= 2 * best_mae_std_nested
r2_within_ci = abs(test_r2 - best_r2_nested) <= 2 * best_r2_std_nested

print(f"\n✅ NESTED CV VALIDATION:")
print(f"   RMSE within 95% CI: {'✅ YES' if rmse_within_ci else '⚠️ NO'}")
print(f"   MAE within 95% CI:  {'✅ YES' if mae_within_ci else '⚠️ NO'}")
print(f"   R² within 95% CI:   {'✅ YES' if r2_within_ci else '⚠️ NO'}")

if rmse_within_ci and mae_within_ci:
    print("   🎉 EXCELLENT: Nested CV provided accurate performance estimates!")
elif rmse_within_ci or mae_within_ci:
    print("   👍 GOOD: Nested CV estimates reasonably accurate")
else:
    print("   ⚠️ WARNING: Test performance differs from nested CV estimates")



# %%
# =============================================================================
# SECTION 13E: GENERATE COMPREHENSIVE PERFORMANCE REPORT
# =============================================================================

print("\\n" + "="*80)
print("SECTION 13E: COMPREHENSIVE PERFORMANCE REPORT")
print("="*80)

# Generate the complete performance report
performance_report = generate_complete_report(
    model=final_model,
    X_train=X_train_full,
    y_train=y_train_full,
    X_valid=X_valid,
    y_valid=y_valid,
    X_test=X_test,
    y_test=y_test,
    feature_columns=feature_columns,
    target_columns=target_columns,
    model_name=best_model_nested,
    bias_corrector=bias_corrector,
    nested_cv_results=nested_cv_results.get(best_model_nested),
    output_dir='models/production/reports'
)

print("\\n✅ Performance report generated!")
print(f"   Report saved to: models/production/reports/")



*# =============================================================================*

*# UPDATED SECTION 13F: FINAL SUMMARY WITH HONEST METRICS*

*# =============================================================================*

print("\\n" + "="*80)

print("FINAL SUMMARY - HONEST OUT-OF-SAMPLE PERFORMANCE")

print("="*80)

print()

print("🎯 MODEL:", best_model_nested)

print()

print("📊 METHODOLOGY:")

print("  ✅ Bias calibrated on VALIDATION set (not test)")

print("  ✅ CI parameters from VALIDATION residuals")

print("  ✅ Test metrics are TRUE out-of-sample performance")

print()

print("📊 TEST PERFORMANCE (HONEST METRICS):")

print(**f**"  RMSE before correction: {bias_results['test_evaluation']['before_correction']['rmse_bp']**:.2f**} bp")

print(**f**"  RMSE after correction:  {bias_results['test_evaluation']['after_correction']['rmse_bp']**:.2f**} bp")

print(**f**"  Bias before: {bias_results['test_evaluation']['before_correction']['bias_bp']**:.2f**} bp")

print(**f**"  Bias after:  {bias_results['test_evaluation']['after_correction']['bias_bp']**:.2f**} bp")

print()

print("📊 CI COVERAGE:")

print(**f**"  95% CI coverage on test: {coverage_results['average_coverage']**:.1%**}")

print()

print("💾 ARTIFACTS SAVED:")

print("  ✅ models/production/bias_correction_params_v2.json")

print("  ✅ models/production/reports/performance_report.json")

print("  ✅ models/production/reports/performance_summary.txt")

print()

print("🚀 PRODUCTION READY:")

print("  The model and bias correction parameters are saved.")

print("  Use predict_with_validation_based_corrections() for new predictions.")

print()

print("="*80)

print("✅ MODELING PROCESS COMPLETE!")

print("="*80)



