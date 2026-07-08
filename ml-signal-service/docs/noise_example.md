# %%
# =============================================================================
# GENERATE NOISE FEATURES
# =============================================================================

print("🎲 STEP 5: GENERATING NOISE FEATURES FOR VOTING SYSTEM")
print("-" * 80)

# Set random seed for reproducibility
np.random.seed(42)

# Get data size
data_size = len(X_clean_filled)
print(f"✓ Data size: {data_size:,} records")
print()

# Generate diverse noise features
print("Generating noise features...")

# Gaussian noise with different parameters
noise_gaussian_1 = np.random.normal(loc=0, scale=1, size=data_size)
noise_gaussian_2 = np.random.normal(loc=0, scale=2, size=data_size)
noise_gaussian_3 = np.random.normal(loc=5, scale=1, size=data_size)

# Uniform noise with different ranges
noise_uniform_1 = np.random.uniform(low=-1, high=1, size=data_size)
noise_uniform_2 = np.random.uniform(low=0, high=10, size=data_size)
noise_uniform_3 = np.random.uniform(low=-10, high=10, size=data_size)

# Poisson noise
noise_poisson_1 = np.random.poisson(lam=3, size=data_size)
noise_poisson_2 = np.random.poisson(lam=6, size=data_size)

# Random walk (cumulative sum)
noise_random_walk = np.cumsum(np.random.normal(0, 1, data_size))

# Sinusoidal noise (periodic pattern)
x = np.linspace(0, 10, data_size)
noise_sinusoidal = np.sin(x) + np.random.normal(0, 0.1, data_size)

# Add noise features to X
X_with_noise = X_clean_filled.copy()
X_with_noise['Noise_Gaussian_Std1'] = noise_gaussian_1
X_with_noise['Noise_Gaussian_Std2'] = noise_gaussian_2
X_with_noise['Noise_Gaussian_Mean5'] = noise_gaussian_3
X_with_noise['Noise_Uniform_Range2'] = noise_uniform_1
X_with_noise['Noise_Uniform_Range20'] = noise_uniform_3
X_with_noise['Noise_Poisson_Lambda3'] = noise_poisson_1
X_with_noise['Noise_Poisson_Lambda6'] = noise_poisson_2
X_with_noise['Noise_RandomWalk'] = noise_random_walk
X_with_noise['Noise_Sinusoidal'] = noise_sinusoidal

# List of noise feature names
noise_features = [
    'Noise_Gaussian_Std1', 'Noise_Gaussian_Std2', 'Noise_Gaussian_Mean5',
    'Noise_Uniform_Range2', 'Noise_Uniform_Range20',
    'Noise_Poisson_Lambda3', 'Noise_Poisson_Lambda6',
    'Noise_RandomWalk', 'Noise_Sinusoidal'
]

print(f"✓ Generated {len(noise_features)} noise features:")
for i, noise_feat in enumerate(noise_features, 1):
    print(f"   {i}. {noise_feat}")
print()
print(f"✓ X_with_noise shape: {X_with_noise.shape}")
print()



# %%
# =============================================================================
# TRAIN MULTI-TARGET REGRESSION MODELS
# =============================================================================

print("🤖 STEP 6: TRAINING MULTI-TARGET REGRESSION MODELS")
print("-" * 80)

print("Training models for feature importance extraction...")
print("(This may take a few minutes...)")
print()

# Model 1: Random Forest MultiOutputRegressor
print("1️⃣ Training Random Forest...")
model1 = MultiOutputRegressor(
    RandomForestRegressor(
        n_estimators=300,
        max_depth=15,
        min_samples_split=10,
        min_samples_leaf=5,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1,
        verbose=0
    )
)
model1.fit(X_with_noise, y_clean)
print("   ✓ Random Forest trained")

# Model 2: LightGBM MultiOutputRegressor
print("2️⃣ Training LightGBM...")
model2 = MultiOutputRegressor(
    lgb.LGBMRegressor(
        n_estimators=500,
        max_depth=16,
        learning_rate=0.05,
        num_leaves=150,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1
    )
)
model2.fit(X_with_noise, y_clean)
print("   ✓ LightGBM trained")

# Model 3: Ridge Regression (linear model)
# Note: Ridge doesn't handle NaN, so we need to impute missing values
print("3️⃣ Training Ridge Regression...")
print("   (Imputing missing values for Ridge - uses median imputation)")

# Robust median imputation for Ridge (only for this model)
X_imputed = X_with_noise.copy()

# Check how many NaNs we have
total_nans = X_imputed.isnull().sum().sum()
print(f"   Total NaN values before imputation: {total_nans:,}")

for col in X_imputed.columns:
    if X_imputed[col].isnull().any():
        # Try median first
​        median_val = X_imputed[col].median()
​        
        # If median is NaN (entire column is NaN), use 0
​        if pd.isna(median_val):
​            X_imputed[col].fillna(0, inplace=True)
​        else:
​            X_imputed[col].fillna(median_val, inplace=True)

# Verify no NaNs remain
remaining_nans = X_imputed.isnull().sum().sum()
print(f"   Total NaN values after imputation: {remaining_nans:,}")

if remaining_nans > 0:
    print(f"   ⚠️  WARNING: {remaining_nans} NaN values still remain!")
    # Force fill any remaining NaNs with 0
​    X_imputed.fillna(0, inplace=True)
​    print(f"   ✓ Filled remaining NaNs with 0")

model3 = MultiOutputRegressor(
    Ridge(
        alpha=1.0,
        max_iter=2000,
        random_state=42
    )
)
model3.fit(X_imputed, y_clean)  # ← Use imputed data for Ridge
print("   ✓ Ridge Regression trained")
print()

print("✓ All 3 models trained successfully!")
print()



# %%
# =============================================================================
# EXTRACT FEATURE IMPORTANCES (MULTI-TARGET AGGREGATION)
# =============================================================================

print("📊 STEP 7: EXTRACTING FEATURE IMPORTANCES")
print("-" * 80)

print("Aggregating feature importances across all 6 targets...")
print()

# For MultiOutputRegressor, we need to aggregate importances across all estimators
# Each estimator corresponds to one target

# Random Forest: Average feature importances across all 6 estimators
rf_importances_per_target = np.array([est.feature_importances_ for est in model1.estimators_])
rf_importances_avg = rf_importances_per_target.mean(axis=0)

# LightGBM: Average feature importances across all 6 estimators
lgbm_importances_per_target = np.array([est.feature_importances_ for est in model2.estimators_])
lgbm_importances_avg = lgbm_importances_per_target.mean(axis=0)

# Ridge: Average absolute coefficients across all 6 estimators
ridge_coefs_per_target = np.array([np.abs(est.coef_) for est in model3.estimators_])
ridge_importances_avg = ridge_coefs_per_target.mean(axis=0)

print(f"✓ Random Forest importances shape: {rf_importances_avg.shape}")
print(f"✓ LightGBM importances shape: {lgbm_importances_avg.shape}")
print(f"✓ Ridge importances shape: {ridge_importances_avg.shape}")
print()



# %%
# =============================================================================
# CREATE FEATURE IMPORTANCE DATAFRAME
# =============================================================================

print("📋 STEP 8: CREATING FEATURE IMPORTANCE DATAFRAME")
print("-" * 80)

# Create comprehensive feature importance DataFrame
feature_importance_df = pd.DataFrame({
    'Feature': X_with_noise.columns,
    'RF_Importance': rf_importances_avg,
    'LGBM_Importance': lgbm_importances_avg,
    'Ridge_Importance': ridge_importances_avg
})

# Add noise indicator
feature_importance_df['Is_Noise'] = feature_importance_df['Feature'].isin(noise_features)

# Calculate weighted average importance
# Give more weight to tree-based models (they're better for this task)
feature_importance_df['Avg_Importance'] = (
    0.3 * feature_importance_df['RF_Importance'] + 
    0.6 * feature_importance_df['LGBM_Importance'] + 
    0.1 * feature_importance_df['Ridge_Importance']
)

# Sort by average importance
feature_importance_df = feature_importance_df.sort_values('Avg_Importance', ascending=False)

print(f"✓ Feature importance dataframe created: {feature_importance_df.shape}")
print()
print("Top 10 features by average importance:")
print(feature_importance_df[['Feature', 'Avg_Importance', 'Is_Noise']].head(10).to_string(index=False))
print()



# %%
# =============================================================================
# VOTING SYSTEM WITH MULTIPLE THRESHOLDS
# =============================================================================

print("🗳️ STEP 9: IMPLEMENTING VOTING SYSTEM")
print("-" * 80)

# ============================================================================
# ⚙️ CONTROL POINT 0: VOTING THRESHOLD PERCENTILES
# ============================================================================
# 🔧 ADJUST THESE TO CONTROL WHICH FEATURES GET VOTES:
#    - Higher percentile (60-70) = Fewer features get votes (stricter)
#    - Lower percentile (30-40) = More features get votes (more inclusive)
#    - Default: 50 (top 50% of features get votes)
#
# 💡 IMPACT:
#    - Stricter voting → Fewer features selected overall
#    - More inclusive voting → More features selected overall
# ============================================================================
VOTING_PERCENTILE_THRESHOLD = 40  # ← CHANGE THIS TO ADJUST VOTING STRICTNESS (30-70 recommended)

# Define selection thresholds for each model
rf_threshold = np.percentile(rf_importances_avg, VOTING_PERCENTILE_THRESHOLD)
lgbm_threshold = np.percentile(lgbm_importances_avg, VOTING_PERCENTILE_THRESHOLD)
ridge_threshold = np.percentile(ridge_importances_avg, VOTING_PERCENTILE_THRESHOLD)

print(f"Voting thresholds (top {VOTING_PERCENTILE_THRESHOLD}%):")
print(f"   🌳 Random Forest: {rf_threshold:.6f}")
print(f"   🚀 LightGBM: {lgbm_threshold:.6f}")
print(f"   📈 Ridge: {ridge_threshold:.6f}")
print()

# Create voting columns
feature_importance_df['RF_Vote'] = (feature_importance_df['RF_Importance'] >= rf_threshold).astype(int)
feature_importance_df['LGBM_Vote'] = (feature_importance_df['LGBM_Importance'] >= lgbm_threshold).astype(int)
feature_importance_df['Ridge_Vote'] = (feature_importance_df['Ridge_Importance'] >= ridge_threshold).astype(int)

# Calculate total votes
feature_importance_df['Total_Votes'] = (
    feature_importance_df['RF_Vote'] + 
    feature_importance_df['LGBM_Vote'] + 
    feature_importance_df['Ridge_Vote']
)

print("✓ Voting system applied")
print()

# %%
# =============================================================================
# NOISE-BASED FEATURE SELECTION
# =============================================================================

print("🎯 STEP 10: NOISE-BASED FEATURE SELECTION")
print("-" * 80)

# Separate noise and real features
noise_df = feature_importance_df[feature_importance_df['Is_Noise']].copy()
real_features_df = feature_importance_df[~feature_importance_df['Is_Noise']].copy()

print(f"✓ Total features: {len(feature_importance_df)}")
print(f"✓ Noise features: {len(noise_df)}")
print(f"✓ Real features: {len(real_features_df)}")
print()

# Calculate noise statistics
noise_importances = noise_df['Avg_Importance'].values
noise_votes = noise_df['Total_Votes'].values

noise_importance_mean = np.mean(noise_importances)
noise_importance_std = np.std(noise_importances)
noise_importance_max = np.max(noise_importances)
noise_votes_max = np.max(noise_votes)

print(f"Noise feature statistics:")
print(f"   Mean importance: {noise_importance_mean:.6f}")
print(f"   Std importance:  {noise_importance_std:.6f}")
print(f"   Max importance:  {noise_importance_max:.6f}")
print(f"   Max votes:       {noise_votes_max}")
print()



# %%
# =============================================================================
# MULTIPLE SELECTION STRATEGIES
# =============================================================================

print("🎯 STEP 11: APPLYING MULTIPLE SELECTION STRATEGIES")
print("-" * 80)

# Strategy 1: Features better than best noise
best_noise_rank = feature_importance_df[feature_importance_df['Is_Noise']].index.min()
strategy1_features = feature_importance_df.iloc[:best_noise_rank]['Feature'].tolist()
strategy1_features = [f for f in strategy1_features if f not in noise_features]

# Strategy 2: Features better than 70th percentile of noise
noise_70th_percentile = np.percentile(noise_importances, 70)
strategy2_features = feature_importance_df[
    (feature_importance_df['Avg_Importance'] > noise_70th_percentile) & 
    (~feature_importance_df['Is_Noise'])
]['Feature'].tolist()

# Strategy 3: Features with more votes than best noise
strategy3_features = feature_importance_df[
    (feature_importance_df['Total_Votes'] > noise_votes_max) & 
    (~feature_importance_df['Is_Noise'])
]['Feature'].tolist()

# Strategy 4: Statistical threshold (mean + 0.5*std)
statistical_threshold = noise_importance_mean + 0.5 * noise_importance_std
strategy4_features = feature_importance_df[
    (feature_importance_df['Avg_Importance'] > statistical_threshold) & 
    (~feature_importance_df['Is_Noise'])
]['Feature'].tolist()

# Strategy 5: At least 1 vote AND above noise mean
strategy5_features = feature_importance_df[
    (feature_importance_df['Total_Votes'] >= 1) & 
    (feature_importance_df['Avg_Importance'] > noise_importance_mean) & 
    (~feature_importance_df['Is_Noise'])
]['Feature'].tolist()

print(f"Strategy results:")
print(f"   1. Better than best noise:        {len(strategy1_features)} features")
print(f"   2. Better than 70th pct noise:    {len(strategy2_features)} features")
print(f"   3. More votes than best noise:    {len(strategy3_features)} features")
print(f"   4. Statistical threshold:         {len(strategy4_features)} features")
print(f"   5. 1+ votes + above noise mean:   {len(strategy5_features)} features")
print()



# %%
# =============================================================================
# CONSENSUS-BASED FINAL SELECTION
# =============================================================================

print("🤝 STEP 12: CONSENSUS-BASED FINAL SELECTION")
print("-" * 80)

# Collect all unique features from all strategies
all_candidate_features = set()
all_candidate_features.update(strategy1_features)
all_candidate_features.update(strategy2_features)
all_candidate_features.update(strategy3_features)
all_candidate_features.update(strategy4_features)
all_candidate_features.update(strategy5_features)

# Count how many strategies support each feature
feature_strategy_support = {}
for feature in all_candidate_features:
    support_count = 0
    if feature in strategy1_features: support_count += 1
    if feature in strategy2_features: support_count += 1
    if feature in strategy3_features: support_count += 1
    if feature in strategy4_features: support_count += 1
    if feature in strategy5_features: support_count += 1
    feature_strategy_support[feature] = support_count

# ============================================================================
# ⚙️ CONTROL POINT 1: MINIMUM STRATEGY SUPPORT THRESHOLD
# ============================================================================
# 🔧 ADJUST THIS TO CONTROL FEATURE SELECTION STRICTNESS:
#    - Higher value (3-5) = Fewer features (more conservative)
#    - Lower value (1-2) = More features (more inclusive)
# ============================================================================
min_strategy_support = 2  # ← CHANGE THIS VALUE TO ADJUST SELECTION STRICTNESS

consensus_features = [
    feature for feature, support in feature_strategy_support.items()
    if support >= min_strategy_support
]

print(f"✓ Features supported by {min_strategy_support}+ strategies: {len(consensus_features)}")
print()

# ============================================================================
# ⚙️ CONTROL POINT 2: MINIMUM FEATURE COUNT THRESHOLD
# ============================================================================
# 🔧 ADJUST THIS TO SET MINIMUM NUMBER OF FEATURES:
#    - If selection is too strict, this ensures minimum features
# ============================================================================
MINIMUM_FEATURES_THRESHOLD = 35  # ← CHANGE THIS TO SET MINIMUM FEATURES

if len(consensus_features) < MINIMUM_FEATURES_THRESHOLD:
    min_strategy_support = 2
    consensus_features = [
        feature for feature, support in feature_strategy_support.items()
        if support >= min_strategy_support
    ]
    print(f"⚠️ Lowered threshold to {min_strategy_support} strategy support: {len(consensus_features)} features")
    print()

# ============================================================================
# ⚙️ CONTROL POINT 3: TARGET FEATURE COUNT FOR TOP-UP
# ============================================================================
# 🔧 ADJUST THIS TO SET TARGET NUMBER OF FEATURES:
#    - If we have fewer than this, add top features by importance
# ============================================================================
TARGET_FEATURE_COUNT = 30  # ← CHANGE THIS TO SET TARGET FEATURE COUNT

if len(consensus_features) < TARGET_FEATURE_COUNT:
    top_by_importance = real_features_df.head(40)['Feature'].tolist()
    for f in top_by_importance:
        if f not in consensus_features:
            consensus_features.append(f)
    print(f"⚠️ Added top features by importance: {len(consensus_features)} features total")
    print()

selected_features_final = consensus_features



# %%
# =============================================================================
# FINAL VALIDATION AND CLEANUP
# =============================================================================

print("✅ STEP 13: FINAL VALIDATION AND CLEANUP")
print("-" * 80)

# Remove any noise features that might have slipped through
selected_features_final = [f for f in selected_features_final if f not in noise_features]

print(f"✓ Features after removing noise: {len(selected_features_final)}")
print()

# ============================================================================
# ⚙️ CONTROL POINT 4: FINAL FEATURE COUNT RANGE (MOST IMPORTANT!)
# ============================================================================
# 🔧 ADJUST THESE TO CONTROL THE FINAL NUMBER OF FEATURES:
#    - MIN_FINAL_FEATURES: Minimum features to use (add top features if below)
#    - MAX_FINAL_FEATURES: Maximum features to use (trim if above)
#
# 💡 RECOMMENDED RANGES FOR BOND MODELING:
#    - Conservative: 30-50 features (less overfitting, faster training)
#    - Balanced: 50-80 features (good trade-off)
#    - Comprehensive: 80-120 features (capture more patterns, risk overfitting)
# ============================================================================
MIN_FINAL_FEATURES = 25  # ← CHANGE THIS TO SET MINIMUM FINAL FEATURES
MAX_FINAL_FEATURES = 33  # ← CHANGE THIS TO SET MAXIMUM FINAL FEATURES

if len(selected_features_final) < MIN_FINAL_FEATURES:
    print(f"⚠️ Too few features ({len(selected_features_final)}), adding top features...")
    additional_needed = MIN_FINAL_FEATURES - len(selected_features_final)
    top_features = real_features_df.head(MIN_FINAL_FEATURES + additional_needed)['Feature'].tolist()
    for feature in top_features:
        if feature not in selected_features_final:
            selected_features_final.append(feature)
            if len(selected_features_final) >= MIN_FINAL_FEATURES:
                break
    print(f"   ✓ Now have {len(selected_features_final)} features")
    print()

elif len(selected_features_final) > MAX_FINAL_FEATURES:
    print(f"⚠️ Too many features ({len(selected_features_final)}), keeping top {MAX_FINAL_FEATURES}...")
    # Keep top MAX_FINAL_FEATURES by average importance
​    feature_scores = feature_importance_df[
​        feature_importance_df['Feature'].isin(selected_features_final)
​    ].sort_values('Avg_Importance', ascending=False)
​    selected_features_final = feature_scores.head(MAX_FINAL_FEATURES)['Feature'].tolist()
​    print(f"   ✓ Now have {len(selected_features_final)} features")
​    print()



# %%
# =============================================================================
# FINAL RESULTS AND REPORTING
# =============================================================================

print("=" * 80)
print("🎯 FINAL FEATURE SELECTION RESULTS")
print("=" * 80)
print()

print(f"✅ Selected features: {len(selected_features_final)}")
print(f"🎲 Noise features excluded: {len(noise_features)}")
print(f"📊 Selection rate: {len(selected_features_final)/len(real_features_df)*100:.1f}% of real features")
print(f"📉 Reduction: {len(feature_cols)} → {len(selected_features_final)} features ({(1-len(selected_features_final)/len(feature_cols))*100:.1f}% reduction)")
print()

# Create final feature report
final_feature_report = feature_importance_df[
    feature_importance_df['Feature'].isin(selected_features_final)
].sort_values('Avg_Importance', ascending=False)

print("📋 TOP 20 SELECTED FEATURES:")
print(final_feature_report[['Feature', 'Avg_Importance', 'Total_Votes', 'RF_Importance', 'LGBM_Importance']].head(20).to_string(index=False))
print()

# Show noise feature positions for reference
print("🎲 NOISE FEATURE POSITIONS (for reference):")
print(noise_df[['Feature', 'Avg_Importance', 'Total_Votes']].to_string(index=False))
print()



# %%
# =============================================================================
# VISUALIZATION
# =============================================================================

print("📈 STEP 14: CREATING VISUALIZATIONS")
print("-" * 80)

# Create comprehensive visualization
fig, axes = plt.subplots(2, 2, figsize=(18, 12))

# Plot 1: Feature Votes (Top 50)
ax1 = axes[0, 0]
feature_plot_df = feature_importance_df.head(50)
colors = ['green' if f in selected_features_final else ('red' if is_noise else 'lightgray')
          for f, is_noise in zip(feature_plot_df['Feature'], feature_plot_df['Is_Noise'])]
ax1.bar(range(len(feature_plot_df)), feature_plot_df['Total_Votes'], color=colors)
ax1.set_xticks(range(len(feature_plot_df)))
ax1.set_xticklabels(feature_plot_df['Feature'], rotation=90, ha='right', fontsize=7)
ax1.set_ylabel('Total Votes', fontsize=10)
ax1.set_title('Feature Selection - Voting Pattern (Top 50)', fontsize=12, fontweight='bold')
ax1.axhline(y=noise_votes_max, color='red', linestyle='--', linewidth=2, label=f'Best noise votes: {noise_votes_max}')
ax1.legend()
ax1.grid(True, alpha=0.3)

# Plot 2: Feature Importance Scores (Top 50)
ax2 = axes[0, 1]
ax2.bar(range(len(feature_plot_df)), feature_plot_df['Avg_Importance'], color=colors)
ax2.set_xticks(range(len(feature_plot_df)))
ax2.set_xticklabels(feature_plot_df['Feature'], rotation=90, ha='right', fontsize=7)
ax2.set_ylabel('Average Importance', fontsize=10)
ax2.set_title('Feature Selection - Importance Scores (Top 50)', fontsize=12, fontweight='bold')
ax2.axhline(y=noise_importance_mean, color='orange', linestyle='--', linewidth=2,
            label=f'Noise mean: {noise_importance_mean:.4f}')
ax2.axhline(y=noise_importance_max, color='red', linestyle='--', linewidth=2,
            label=f'Best noise: {noise_importance_max:.4f}')
ax2.legend()
ax2.grid(True, alpha=0.3)

# Plot 3: Strategy Support Distribution
ax3 = axes[1, 0]
support_counts = pd.Series(feature_strategy_support).value_counts().sort_index()
ax3.bar(support_counts.index, support_counts.values, color='steelblue', edgecolor='black')
ax3.set_xlabel('Number of Strategies Supporting Feature', fontsize=10)
ax3.set_ylabel('Number of Features', fontsize=10)
ax3.set_title('Feature Support Distribution Across Strategies', fontsize=12, fontweight='bold')
ax3.axvline(x=min_strategy_support, color='red', linestyle='--', linewidth=2,
            label=f'Selection threshold: {min_strategy_support}')
ax3.legend()
ax3.grid(True, alpha=0.3)

# Plot 4: Model Agreement (Selected Features)
ax4 = axes[1, 1]
selected_report = final_feature_report.head(30)
x_pos = np.arange(len(selected_report))
width = 0.25
ax4.bar(x_pos - width, selected_report['RF_Vote'], width, label='RF', color='forestgreen', alpha=0.8)
ax4.bar(x_pos, selected_report['LGBM_Vote'], width, label='LGBM', color='dodgerblue', alpha=0.8)
ax4.bar(x_pos + width, selected_report['Ridge_Vote'], width, label='Ridge', color='coral', alpha=0.8)
ax4.set_xticks(x_pos)
ax4.set_xticklabels(selected_report['Feature'], rotation=90, ha='right', fontsize=7)
ax4.set_ylabel('Vote (0 or 1)', fontsize=10)
ax4.set_title('Model Agreement on Top 30 Selected Features', fontsize=12, fontweight='bold')
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('feature_selection_vote_system_results.png', dpi=150, bbox_inches='tight')
print("✓ Visualization saved: feature_selection_vote_system_results.png")
plt.show()
print()



# %%
# =============================================================================
# SAVE SELECTED FEATURES
# =============================================================================

print("💾 STEP 15: SAVING SELECTED FEATURES")
print("-" * 80)

# Save selected feature list
selected_features_df = final_feature_report[['Feature', 'Avg_Importance', 'Total_Votes',
                                              'RF_Importance', 'LGBM_Importance', 'Ridge_Importance']]
selected_features_df.to_csv('selected_features_vote_system.csv', index=False)
print("✓ Saved: selected_features_vote_system.csv")
print()

# Save full feature importance report
feature_importance_df.to_csv('full_feature_importance_report.csv', index=False)
print("✓ Saved: full_feature_importance_report.csv")
print()



*# %%*

*# =============================================================================*

*# SUMMARY STATISTICS*

*# =============================================================================*

print("=" * 80)

print("📊 SUMMARY STATISTICS")

print("=" * 80)

print()

print(**f**"Original features:     {len(feature_cols)}")

print(**f**"Noise features added:   {len(noise_features)}")

print(**f**"Total features tested:   {len(feature_cols) + len(noise_features)}")

print(**f**"Selected features:     {len(selected_features_final)}")

print(**f**"Reduction:         {(1 - len(selected_features_final)/len(feature_cols))*100**:.1f**}%")

print()

print(**f**"Noise statistics:")

print(**f**"  Best noise importance: {noise_importance_max**:.6f**}")

print(**f**"  Worst selected importance: {final_feature_report['Avg_Importance'].min()**:.6f**}")

print(**f**"  Ratio: {final_feature_report['Avg_Importance'].min() / noise_importance_max**:.2f**}x better")

print()

print(**f**"Strategy consensus:")

for support_level in range(5, 0, -1):

  count = sum(1 for s in feature_strategy_support.values() if s >= support_level)

  selected_count = sum(1 for f, s in feature_strategy_support.items()

​            if s >= support_level and f in selected_features_final)

  print(**f**"  {support_level}+ strategies: {count} features ({selected_count} selected)")

print()



# %%
# =============================================================================
# FINAL OUTPUT: SELECTED FEATURE LIST
# =============================================================================

print("=" * 80)
print("🎯 FINAL SELECTED FEATURES LIST")
print("=" * 80)
print()

print(f"Total: {len(selected_features_final)} features")
print()

for i, feature in enumerate(selected_features_final, 1):
    feat_info = feature_importance_df[feature_importance_df['Feature'] == feature].iloc[0]
    importance = feat_info['Avg_Importance']
    votes = feat_info['Total_Votes']
    print(f"{i:3d}. {feature:<50} | Importance: {importance:.6f} | Votes: {votes}")

print()
print("=" * 80)
print("✅ FEATURE SELECTION COMPLETE!")
print("=" * 80)
print()
print("Next steps:")
print("   1. Use these selected features for model training")
print("   2. Train baseline multi-target regression model")
print("   3. Evaluate performance on validation set")
print("   4. Tune hyperparameters")
print()

# %%
# Store selected features for next phase
print("📦 Storing selected features for next phase...")
selected_features_for_modeling = selected_features_final.copy()
print(f"✓ Stored {len(selected_features_for_modeling)} features in variable: selected_features_for_modeling")
print()
print("Ready for Phase 9 - Part 2: Model Training!")
print("=" * 80)



