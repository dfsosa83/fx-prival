"""EXP-2026-03-SELECTIVE-DERISK-OVERLAY — sealed run.

Pre-registered 2026-09-23. Executed exactly once.
Only change vs EXP-2026-02: sizing rule = de-risk (0.5x) ONLY when forecast
vol is in the top decile (0.90 quantile) of its trailing 252-day rolling
distribution; otherwise full exposure (1.0x).
Everything else frozen: features, macro alignment, model, splits, costs.
"""
import sys; sys.path.insert(0, ".")
import numpy as np
import pandas as pd
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import equal_weight
from backtest.engine import run_backtest
from signals.ml_overlays.features import compute_daily_features
from signals.ml_overlays.vol_forecast import build_regression_dataset, train_vol_model, forecast_volatility
from signals.ml_overlays.selection import select_features_by_noise_voting
from signals.ml_overlays.macro import load_fred_series, align_macro_features, macro_feature_deltas

# ── Pre-registered parameters (frozen) ─────────────────────────────────────
DERISK_SCALE = 0.5
DERISK_QUANTILE = 0.90
QUANTILE_WINDOW = 252
TRAIN_END = "2022-12-31"
VAL_END = "2023-12-31"
TEST_START = "2024-01-01"
HORIZON = 30
PURGE_DAYS = 30
SEED = 42

# ── Load data ──────────────────────────────────────────────────────────────
master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]
print(f"Period: {common[0].date()} to {common[-1].date()} ({len(common)} days)")

# ── FRED macro features (leakage-safe, same as EXP-2026-02) ────────────────
macro_raw = load_fred_series("data/raw/fred")
macro_feat = align_macro_features(common, macro_raw, publication_lag_days=45)
macro_feat = macro_feature_deltas(macro_feat, windows=[21, 63])
print(f"Macro features: {len(macro_feat.columns)}")

# ── Baseline (same as all prior experiments) ───────────────────────────────
ew_full = equal_weight(prices.loc[common])
r_base, m_base, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", ew_full
)
print("\n=== BASELINE ===")
print(f"  Sharpe: {m_base['sharpe_ratio']:.4f}  MaxDD: {m_base['max_drawdown']:.4f}  "
      f"Cost/Gross: {m_base['cost_to_gross_pnl']:.4f}")

# ── Build model + selective de-risk scale for each instrument ──────────────
print("\n=== Training models + computing selective scale (top decile) ===")
scale_dict = {}

for ticker in prices.columns:
    feat = compute_daily_features(prices, ret, ticker)
    if len(feat) < 500:
        continue

    macro_aligned = macro_feat.reindex(feat.index)
    feat_m = pd.concat([feat, macro_aligned], axis=1).dropna()
    if len(feat_m) < 500:
        continue

    ret_t = ret[ticker]
    X, y = build_regression_dataset(feat_m, ret_t, horizon=HORIZON)

    train_mask = X.index <= TRAIN_END
    val_mask = (X.index > TRAIN_END) & (X.index <= VAL_END)
    X_train, y_train = X[train_mask], y[train_mask]
    X_val, y_val = X[val_mask], y[val_mask]

    if len(X_train) < 300 or len(X_val) < 50:
        continue

    # Feature selection on TRAIN ONLY (noise-voting, regression mode)
    selected, _ = select_features_by_noise_voting(
        X_train, y_train, min_strategy_support=1, seed=SEED,
        verbose=False, task="regression",
    )
    if len(selected) < 3:
        continue

    model, sel = train_vol_model(X_train[selected], y_train, model_type="lgbm", seed=SEED)
    pred = forecast_volatility(model, feat_m, sel)
    pred.name = "vol_forecast"

    # ── SELECTIVE DE-RISK RULE (the ONLY change vs EXP-2026-02) ──────────
    # Scale = 0.5 ONLY when forecast is above the 90th percentile of its
    # trailing 252-day rolling distribution; otherwise 1.0 (full exposure).
    rolling_q90 = pred.rolling(QUANTILE_WINDOW, min_periods=QUANTILE_WINDOW // 2).quantile(DERISK_QUANTILE)
    elevated = pred > rolling_q90
    scale = pd.Series(1.0, index=pred.index)
    scale[elevated.fillna(False)] = DERISK_SCALE

    scale = scale.reindex(ret.index).fillna(1.0)
    scale_dict[ticker] = scale
    print(f"  {ticker}: {len(selected)} features | de-risk days: {int(elevated.sum())}/{len(elevated)}")

# ── Apply overlay to equal-weight baseline ─────────────────────────────────
scale_df = pd.DataFrame(scale_dict).reindex(common).fillna(1.0)
w_scaled = ew_full.copy()
for ticker in scale_df.columns:
    if ticker in w_scaled.columns:
        w_scaled[ticker] = ew_full[ticker] * scale_df[ticker]
gross = w_scaled.sum(axis=1).replace(0, np.nan)
w_scaled = w_scaled.div(gross, axis=0).fillna(0.0)

r_ml, m_ml, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", w_scaled
)

# ── Results ────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print("EXP-2026-03 RESULTS (sealed run)")
print("=" * 60)
print(f"\n{'Metric':<28} {'Baseline':>12} {'Selective Overlay':>18}")
print("-" * 60)
for k in ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown",
          "sortino_ratio", "calmar_ratio", "cost_to_gross_pnl", "annualized_turnover"]:
    print(f"{k:<28} {m_base[k]:>12.4f} {m_ml[k]:>18.4f}")

# ── Pre-registered gate evaluation ─────────────────────────────────────────
print("\n" + "=" * 60)
print("PRE-REGISTERED GATE EVALUATION")
print("=" * 60)
sharpe = m_ml["sharpe_ratio"]
maxdd = m_ml["max_drawdown"]
cg = m_ml["cost_to_gross_pnl"]

gate_go_sharpe = sharpe >= 0.55
gate_go_dd = maxdd > -0.167
gate_go_cg = cg < 0.545

print(f"\nGO criteria:")
print(f"  Full Sharpe >= 0.55        : {sharpe:.4f} -> {'PASS' if gate_go_sharpe else 'FAIL'}")
print(f"  Max DD > -0.167            : {maxdd:.4f} -> {'PASS' if gate_go_dd else 'FAIL'}")
print(f"  Cost/Gross < 0.545         : {cg:.4f} -> {'PASS' if gate_go_cg else 'FAIL'}")

if gate_go_sharpe and gate_go_dd and gate_go_cg:
    verdict = "GO"
elif sharpe < 0.40 or maxdd <= -0.167 or cg >= 0.545:
    verdict = "STOP"
else:
    verdict = "HOLD"

print(f"\nVERDICT: {verdict}")

# Test-period view
test_dates = ret.index[ret.index > TEST_START]
nav_base = r_base.nav["nav_net"].reindex(test_dates)
nav_ml = r_ml.nav["nav_net"].reindex(test_dates)

def simple_sharpe(r):
    return r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0

print("\nSealed test period (2024-01-01 onward):")
print(f"  Baseline Sharpe:  {simple_sharpe(nav_base.pct_change().fillna(0)):.4f}")
print(f"  Overlay Sharpe:   {simple_sharpe(nav_ml.pct_change().fillna(0)):.4f}")
print(f"  Baseline total:   {nav_base.iloc[-1]/nav_base.iloc[0]-1:+.4f}")
print(f"  Overlay total:    {nav_ml.iloc[-1]/nav_ml.iloc[0]-1:+.4f}")