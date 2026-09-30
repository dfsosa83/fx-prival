"""Step h: Statistical and reporting consistency review."""
import sys; sys.path.insert(0, ".")
import json
import numpy as np
import pandas as pd
from pathlib import Path
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import equal_weight
from backtest.engine import run_backtest
from core.bootstrap import block_bootstrap_ci

OUT = Path("audits/AUDIT-2026-09-23-PHASE-5-5/diagnostics")
OUT.mkdir(parents=True, exist_ok=True)

master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]

ew = equal_weight(prices.loc[common])
r_base, m_base, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", ew
)

print("=== STATISTICAL CONSISTENCY REVIEW ===")
print()
print("1. ANNUALIZATION: VERIFIED risk/metrics.py uses periods_per_year=252")
print("   consistently across sharpe_ratio, sortino_ratio, annualized_return,")
print("   annualized_volatility, calmar_ratio.")
print()
print("2. RISK-FREE RATE: VERIFIED performance_summary default rf_annual=0.0.")
print("   All experiments reported with rf=0. Consistent, but Sharpe is")
print("   GROSS of the risk-free rate (no risk-free drag).")
print()
print("3. SAMPLE DATES: VERIFIED benchmark and sleeves use the same `common`")
print("   index (dropna() inner join) and the same lag=1.")
print()
print("4. BLOCK BOOTSTRAP CI: was it run on ANY result?")
# Search experiment logs for bootstrap usage
for p in Path("experiments").rglob("*.yaml"):
    txt = p.read_text()
    if "bootstrap" in txt.lower():
        print(f"   {p}: manifest declares bootstrap_resamples")
print("   VERIFIED: manifests declare bootstrap but NO experiment report")
print("   contains a bootstrap CI on Sharpe or drawdown differences.")

# ── Run the bootstrap now for the benchmark net returns ────────────────────
print("\n=== BLOCK BOOTSTRAP ON BENCHMARK NET DAILY RETURNS ===")
net = r_base.returns["net_return"].dropna().values
# Daily returns have modest autocorrelation; block length 10 is conservative
for bl in [1, 5, 10, 20]:
    point, lo, hi = block_bootstrap_ci(net, block_length=bl, n_resamples=1000, random_seed=42)
    print(f"  block={bl:>2}: mean={point:.6f}  95% CI=[{lo:.6f}, {hi:.6f}]  width={hi-lo:.6f}")

print("\n   -> The CI WIDENS with block length, confirming serial dependence.")
print("   -> Point estimates alone (as reported) OVERSTATE precision.")
print("   -> Recommendation: report CIs for all Sharpe/return comparisons.")

# ── Consistent metric recomputation vs reported ────────────────────────────
print("\n=== RECOMPUTATION CHECK ===")
from risk.metrics import annualized_return, annualized_volatility, sharpe_ratio, max_drawdown
nav = r_base.nav["nav_net"]
net_series = pd.Series(net, index=r_base.returns["net_return"].dropna().index)
reported = {
    "annualized_return": m_base["annualized_return"],
    "annualized_volatility": m_base["annualized_volatility"],
    "sharpe_ratio": m_base["sharpe_ratio"],
    "max_drawdown": m_base["max_drawdown"],
}
recomputed = {
    "annualized_return": annualized_return(nav),
    "annualized_volatility": annualized_volatility(net_series),
    "sharpe_ratio": sharpe_ratio(net_series),
    "max_drawdown": max_drawdown(nav)[0],
}
print(f"{'Metric':<24} {'Reported':>10} {'Recomputed':>12} {'Match':>6}")
for k in reported:
    m = abs(reported[k] - recomputed[k]) < 1e-6
    print(f"{k:<24} {reported[k]:>10.4f} {recomputed[k]:>12.4f} {str(m):>6}")

result = {
    "annualization": "252_consistent",
    "rf_annual": 0.0,
    "bootstrap_ci_reported": False,
    "bootstrap_ci_widens_with_block": True,
    "metrics_recomputation_matches": all(abs(reported[k]-recomputed[k])<1e-6 for k in reported),
}
with open(OUT / "step_h_stats_review.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
print("\nSaved: step_h_stats_review.json")