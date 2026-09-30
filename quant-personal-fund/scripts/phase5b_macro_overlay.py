"""Phase 5b: ML vol forecast overlay with FRED macro features.

Extends the Phase 5 experiment with a genuinely different information
source: FRED macro series (US 3M/10Y yields, term spread, VIX, CPI,
unemployment), leakage-safe aligned.

Pre-registered hypothesis: if macro conditions (rate level, term spread,
VIX, inflation, labor market) contain information about future volatility
that price-derived features do not, the ML overlay should improve on the
no-macro version — and potentially beat the equal-weight baseline.
"""
import sys; sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import equal_weight
from backtest.engine import run_backtest
from risk.metrics import performance_summary
from signals.ml_overlays.features import compute_daily_features
from signals.ml_overlays.vol_forecast import build_regression_dataset, train_vol_model, forecast_volatility
from signals.ml_overlays.selection import select_features_by_noise_voting
from signals.ml_overlays.sizing import volatility_scaling_factor
from signals.ml_overlays.macro import load_fred_series, align_macro_features, macro_feature_deltas

# ── Load data ──────────────────────────────────────────────────────────────
master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]
print(f"Period: {common[0].date()} to {common[-1].date()} ({len(common)} days)")

# ── Load and align macro features ──────────────────────────────────────────
macro_raw = load_fred_series("data/raw/fred")
macro_feat = align_macro_features(common, macro_raw, publication_lag_days=45)
macro_feat = macro_feature_deltas(macro_feat, windows=[21, 63])
print(f"Macro features: {len(macro_feat.columns)} columns, "
      f"{macro_feat.notna().sum().min()} min valid days")
print(f"  Columns: {list(macro_feat.columns)}")

# ── Chronological splits (pre-registered) ─────────────────────────────────
TRAIN_END = "2022-12-31"
VAL_END = "2023-12-31"
TEST_START = "2024-01-01"

# ── Baseline ───────────────────────────────────────────────────────────────
ew_full = equal_weight(prices.loc[common])
r_base, m_base, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", ew_full
)
print("\n=== EQUAL-WEIGHT BASELINE ===")
print(f"  Sharpe: {m_base['sharpe_ratio']:.3f}  AnnRet: {m_base['annualized_return']:.4f}  MaxDD: {m_base['max_drawdown']:.4f}")

# ── ML overlay with macro features ─────────────────────────────────────────
print("\n=== Building features + macro, training models ===")
scale_dict = {}

for ticker in prices.columns:
    feat = compute_daily_features(prices, ret, ticker)
    if len(feat) < 500:
        continue

    # Merge macro features (aligned to feat index)
    macro_aligned = macro_feat.reindex(feat.index)
    feat_m = pd.concat([feat, macro_aligned], axis=1).dropna()

    if len(feat_m) < 500:
        continue

    ret_t = ret[ticker]
    X, y = build_regression_dataset(feat_m, ret_t, horizon=30)

    train_mask = X.index <= TRAIN_END
    val_mask = (X.index > TRAIN_END) & (X.index <= VAL_END)

    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]

    if len(X_train) < 300 or len(X_val) < 50:
        continue

    # Noise-voting selection (regression mode) on TRAIN ONLY
    selected, imp_df = select_features_by_noise_voting(
        X_train, y_train, min_strategy_support=1, seed=42,
        verbose=False, task="regression",
    )
    if len(selected) < 3:
        continue

    # Track how many macro features survived selection
    n_macro_selected = sum(1 for f in selected if any(
        m in f for m in ["us_3m", "us_10y", "spread", "vix", "cpi", "unemployment"]
    ))

    # Train
    model, sel = train_vol_model(X_train[selected], y_train, model_type="lgbm", seed=42)
    pred = forecast_volatility(model, feat_m, sel)
    pred.name = "vol_forecast"

    baseline_vol = feat_m["realized_vol_60"]
    scale = volatility_scaling_factor(pred, baseline_vol, min_scale=0.5, max_scale=1.0, k=1.0)
    scale = scale.reindex(ret.index).fillna(1.0)
    scale_dict[ticker] = (scale, n_macro_selected)
    print(f"  {ticker}: {len(selected)} features, {n_macro_selected} macro")

# ── Apply overlay ──────────────────────────────────────────────────────────
scale_df = pd.DataFrame({t: s for t, (s, _) in scale_dict.items()}).reindex(common).fillna(1.0)
w_scaled = ew_full.copy()
for ticker in scale_df.columns:
    if ticker in w_scaled.columns:
        w_scaled[ticker] = ew_full[ticker] * scale_df[ticker]
gross = w_scaled.sum(axis=1).replace(0, np.nan)
w_scaled = w_scaled.div(gross, axis=0).fillna(0.0)

r_ml, m_ml, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", w_scaled
)

print("\n=== ML VOL OVERLAY WITH MACRO vs BASELINE ===")
header = f"{'Metric':<28} {'Baseline':>10} {'ML+Macro':>10}"
print(header); print("-" * len(header))
for k in ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown",
          "sortino_ratio", "calmar_ratio", "cost_to_gross_pnl"]:
    print(f"{k:<28} {m_base[k]:>10.4f} {m_ml[k]:>10.4f}")

# ── Sealed test period ─────────────────────────────────────────────────────
test_dates = ret.index[ret.index > TEST_START]
nav_base = r_base.nav["nav_net"].reindex(test_dates)
nav_ml = r_ml.nav["nav_net"].reindex(test_dates)

def simple_sharpe(r):
    return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0

print("\n=== SEALED TEST (2024-01-01 onward) ===")
print(f"  Baseline Sharpe:  {simple_sharpe(nav_base.pct_change().fillna(0)):.3f}")
print(f"  ML+Macro Sharpe:  {simple_sharpe(nav_ml.pct_change().fillna(0)):.3f}")
print(f"  Baseline total:   {nav_base.iloc[-1]/nav_base.iloc[0]-1:+.4f}")
print(f"  ML+Macro total:   {nav_ml.iloc[-1]/nav_ml.iloc[0]-1:+.4f}")