"""Step i: LOO/LACO diagnostics + reproducibility manifest."""
import sys; sys.path.insert(0, ".")
import json
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import equal_weight
from backtest.engine import run_backtest
from risk.metrics import annualized_return, annualized_volatility, sharpe_ratio, max_drawdown

OUT = Path("audits/AUDIT-2026-09-23-PHASE-5-5/diagnostics")
OUT.mkdir(parents=True, exist_ok=True)

master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]
tickers = prices.columns.tolist()

CLASS = {
    "EURUSD":"fx","USDJPY":"fx","GBPUSD":"fx","AUDUSD":"fx","USDCAD":"fx",
    "USDCHF":"fx","NZDUSD":"fx","EURJPY":"fx",
    "SPX":"eq","NDX":"eq","SX5E":"eq","NKY":"eq",
    "US10Y":"bd","BUND":"bd","JGB":"bd",
    "XAUUSD":"co","WTI":"co","COPPER":"co",
}

def metrics_for(ticker_subset):
    """Equal-weight on a ticker subset, full accounting, return metrics."""
    sub = [t for t in tickers if t in ticker_subset]
    w = pd.DataFrame(1.0/len(sub), index=common, columns=sub)
    r, m, _ = run_backtest("config/universe.yaml", "config/cost_model.yaml",
                           "data/raw/yahoo/daily", w)
    nav = r.nav["nav_net"]
    net = r.returns["net_return"].dropna()
    return {
        "n_assets": len(sub),
        "annualized_return": m["annualized_return"],
        "annualized_volatility": m["annualized_volatility"],
        "sharpe_ratio": m["sharpe_ratio"],
        "max_drawdown": m["max_drawdown"],
        "cumulative_return": m["cumulative_return"],
    }

# ── Full benchmark ─────────────────────────────────────────────────────────
print("=== LOO / LACO DIAGNOSTICS ===")
full = metrics_for(tickers)
print(f"Full 18-asset: Sharpe={full['sharpe_ratio']:.4f}  AnnRet={full['annualized_return']:.4f}  MaxDD={full['max_drawdown']:.4f}")

# ── Leave-one-asset-out ────────────────────────────────────────────────────
print("\nLeave-one-asset-out:")
loo = {}
for t in tickers:
    m = metrics_for([x for x in tickers if x != t])
    loo[t] = m
    d = m["sharpe_ratio"] - full["sharpe_ratio"]
    print(f"  drop {t:<7}: Sharpe={m['sharpe_ratio']:.4f} ({d:+.4f})  AnnRet={m['annualized_return']:.4f}")

loo_df = pd.DataFrame(loo).T
loo_df.to_csv(OUT / "step_i_loo.csv")

# ── Leave-one-asset-class-out ──────────────────────────────────────────────
print("\nLeave-one-asset-class-out:")
laco = {}
for ac, label in [("fx","FX"),("eq","Equity"),("bd","Bonds"),("co","Commodity")]:
    subset = [t for t in tickers if CLASS[t] != ac]
    m = metrics_for(subset)
    laco[ac] = m
    print(f"  drop {label:<10}: Sharpe={m['sharpe_ratio']:.4f}  AnnRet={m['annualized_return']:.4f}  MaxDD={m['max_drawdown']:.4f}")

# ── Reproducibility manifest ───────────────────────────────────────────────
print("\n=== REPRODUCIBILITY MANIFEST ===")
def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]

config_files = ["config/universe.yaml", "config/cost_model.yaml"]
for cf in config_files:
    print(f"  {cf}: {sha256(cf)}")

# Key source files used in the results
src_files = [
    "portfolio/builder.py", "portfolio/accounting.py", "backtest/engine.py",
    "core/costs.py", "core/returns.py", "risk/metrics.py",
    "signals/trend/signal.py", "signals/trend/scaling.py",
]
for sf in src_files:
    print(f"  {sf}: {sha256(sf)}")

# Data files (raw, the actual inputs)
data_hashes = {}
for f in sorted(Path("data/raw/yahoo/daily").glob("*.parquet")):
    data_hashes[f.name] = sha256(f)
print(f"  Raw data files hashed: {len(data_hashes)}")

result = {
    "full_benchmark": full,
    "loo_summary": {t: m["sharpe_ratio"] for t, m in loo.items()},
    "laco_summary": {ac: m["sharpe_ratio"] for ac, m in laco.items()},
    "config_hashes": {cf: sha256(cf) for cf in config_files},
    "data_hashes_count": len(data_hashes),
}
with open(OUT / "step_i_loo_laco.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
print("\nSaved: step_i_loo_laco.json")