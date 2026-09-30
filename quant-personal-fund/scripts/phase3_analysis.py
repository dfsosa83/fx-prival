"""Phase 3 trend analysis: baseline comparison and year-by-year decomposition."""
import sys; sys.path.insert(0, ".")
import pandas as pd
import numpy as np
from backtest.engine import run_backtest
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import trend_weights, equal_weight
from risk.metrics import annualized_return, annualized_volatility, sharpe_ratio, max_drawdown, sortino_ratio

master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]

print(f"Period: {common[0].date()} to {common[-1].date()} ({len(common)} days)")
print(f"Instruments: {len(prices.columns)}")
print()

# Equal weight baseline
ew = equal_weight(prices.loc[common])
r_ew, m_ew, _ = run_backtest("config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", ew)

# Trend long-only (weekly rebalance)
w_lo = trend_weights(prices.loc[common], ret, long_only=True, rebalance_freq="W")
r_lo, m_lo, _ = run_backtest("config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", w_lo)

# Trend long/short (weekly rebalance)
w_ls = trend_weights(prices.loc[common], ret, long_only=False, rebalance_freq="W")
r_ls, m_ls, _ = run_backtest("config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", w_ls, allow_short=True)

print("=== BASELINE COMPARISON ===")
header = f"{'Metric':<28} {'Equal-Wt':>10} {'Trend LO':>10} {'Trend L/S':>10}"
print(header)
print("-" * len(header))
keys = ["annualized_return", "annualized_volatility", "sharpe_ratio", "max_drawdown",
        "sortino_ratio", "calmar_ratio", "cost_to_gross_pnl", "annualized_turnover"]
for k in keys:
    print(f"{k:<28} {m_ew[k]:>10.4f} {m_lo[k]:>10.4f} {m_ls[k]:>10.4f}")

print()
print("=== YEAR-BY-YEAR (Trend L/S net returns) ===")
net_ret = r_ls.returns["net_return"]
for yr in range(2016, 2027):
    yr_ret = net_ret[net_ret.index.year == yr]
    if len(yr_ret) < 10:
        continue
    nav_yr = (1 + yr_ret.fillna(0)).cumprod()
    ann = annualized_return(nav_yr)
    vol = annualized_volatility(yr_ret)
    sr = sharpe_ratio(yr_ret) if yr_ret.std() > 0 else 0
    dd, _, _ = max_drawdown(nav_yr)
    print(f"  {yr}: ret={ann:+.4f}  vol={vol:.3f}  sr={sr:+.3f}  dd={dd:+.4f}")

print()
print("=== LOOKBACK ROBUSTNESS (weekly rebalance) ===")
lookback_sets = {
    "1M only": [21],
    "3M only": [63],
    "6M only": [126],
    "12M only": [252],
    "Full (1-12M)": [21, 63, 126, 189, 252],
    "3M+6M+12M": [63, 126, 252],
    "6M+12M": [126, 252],
}
print(f"{'Lookbacks':<20} {'Ann Ret':>10} {'Sharpe':>8} {'Max DD':>8} {'Turnover':>10}")
print("-" * 58)
for name, lbs in lookback_sets.items():
    w = trend_weights(prices.loc[common], ret, lookbacks=lbs, long_only=False, rebalance_freq="W")
    r, m, _ = run_backtest("config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", w, allow_short=True)
    print(f"{name:<20} {m['annualized_return']:>10.4f} {m['sharpe_ratio']:>8.3f} {m['max_drawdown']:>8.3f} {m['annualized_turnover']:>10.1f}")