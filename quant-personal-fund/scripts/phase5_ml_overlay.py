"""Phase 5 ML volatility overlay: run full experiment on real data."""
import sys; sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import equal_weight
from portfolio.accounting import compute_portfolio
from risk.metrics import performance_summary
from signals.ml_overlays.features import compute_daily_features
from signals.ml_overlays.vol_forecast import build_regression_dataset, train_vol_model, forecast_volatility, forward_realized_volatility
from signals.ml_overlays.selection import select_features_by_noise_voting
from signals.ml_overlays.sizing import volatility_scaling_factor, apply_scaling

# ── Load data ──────────────────────────────────────────────────────────────
master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]

print(f"Period: {common[0].date()} to {common[-1].date()} ({len(common)} days)")
print(f"Instruments: {len(prices.columns)}")

# ── Chronological splits (pre-registered) ─────────────────────────────────
TRAIN_END = "2022-12-31"
VAL_END = "2023-12-31"
TEST_START = "2024-01-01"

# ── Baseline: equal weight, full period ───────────────────────────────────
ew_full = equal_weight(prices.loc[common])
from backtest.engine import run_backtest
r_base, m_base, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", ew_full
)
print("\n=== EQUAL-WEIGHT BASELINE (full period) ===")
print(f"  Sharpe: {m_base['sharpe_ratio']:.3f}  AnnRet: {m_base['annualized_return']:.4f}  MaxDD: {m_base['max_drawdown']:.4f}")

# ── ML overlay: build features per instrument ─────────────────────────────
print("\n=== Building features and training model ===")
scale_dict = {}

for ticker in prices.columns:
    feat = compute_daily_features(prices, ret, ticker)
    if len(feat) < 500:
        continue

    # Split
    feat_train = feat[feat.index <= TRAIN_END]
    feat_val = feat[(feat.index > TRAIN_END) & (feat.index <= VAL_END)]
    feat_test = feat[feat.index > TEST_START]

    ret_t = ret[ticker]
    X, y = build_regression_dataset(feat, ret_t, horizon=30)

    # Chronological split with purge
    train_mask = X.index <= TRAIN_END
    val_mask = (X.index > TRAIN_END) & (X.index <= VAL_END)

    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]

    if len(X_train) < 300 or len(X_val) < 50:
        continue

    # Noise-voting feature selection on TRAIN ONLY
    selected, imp_df = select_features_by_noise_voting(
        X_train, y_train, min_strategy_support=1, seed=42, verbose=False,
        task="regression",
    )
    if len(selected) < 3:
        continue

    # Train on selected features
    model, sel = train_vol_model(X_train[selected], y_train, model_type="lgbm", seed=42)

    # Forecast on full period
    feat_all = feat
    pred = forecast_volatility(model, feat_all, sel)
    pred.name = "vol_forecast"

    # Baseline vol for scaling
    baseline = feat_all["realized_vol_60"]

    # Scaling factor
    scale = volatility_scaling_factor(pred, baseline, min_scale=0.5, max_scale=1.0, k=1.0)

    # Only scale during test period (overlay applies post-training)
    scale = scale.reindex(ret.index).fillna(1.0)
    scale_dict[ticker] = scale

print(f"Models trained for {len(scale_dict)} instruments")

# ── Apply overlay to equal-weight baseline ────────────────────────────────
scale_df = pd.DataFrame(scale_dict).reindex(common).fillna(1.0)

# Scaled weights: equal weight * per-instrument scale
w_scaled = ew_full.copy()
for ticker in scale_df.columns:
    if ticker in w_scaled.columns:
        w_scaled[ticker] = ew_full[ticker] * scale_df[ticker]

# Re-normalize active positions to keep gross exposure reasonable
gross = w_scaled.sum(axis=1)
gross_safe = gross.replace(0, np.nan)
w_scaled = w_scaled.div(gross_safe, axis=0).fillna(0.0)

r_ml, m_ml, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", w_scaled
)

print("\n=== ML VOL OVERLAY vs BASELINE ===")
header = f"{'Metric':<28} {'Baseline':>10} {'ML Overlay':>10}"
print(header)
print("-" * len(header))
for k in ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown",
          "sortino_ratio", "calmar_ratio", "cost_to_gross_pnl"]:
    print(f"{k:<28} {m_base[k]:>10.4f} {m_ml[k]:>10.4f}")

# ── Test-period only comparison ───────────────────────────────────────────
test_dates = ret.index[ret.index > TEST_START]
nav_base = r_base.nav["nav_net"].reindex(test_dates)
nav_ml = r_ml.nav["nav_net"].reindex(test_dates)
ret_base_t = nav_base.pct_change().fillna(0)
ret_ml_t = nav_ml.pct_change().fillna(0)

def simple_sharpe(r):
    return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0

print("\n=== SEALED TEST PERIOD ONLY (2024-01-01 onward) ===")
print(f"  Baseline Sharpe: {simple_sharpe(ret_base_t):.3f}")
print(f"  ML Overlay Sharpe: {simple_sharpe(ret_ml_t):.3f}")
print(f"  Baseline total ret: {nav_base.iloc[-1]/nav_base.iloc[0]-1:+.4f}")
print(f"  ML Overlay total ret: {nav_ml.iloc[-1]/nav_ml.iloc[0]-1:+.4f}")