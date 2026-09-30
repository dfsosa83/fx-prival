"""Step e: Cost waterfall and accounting trace per sleeve."""
import sys; sys.path.insert(0, ".")
import json
import numpy as np
import pandas as pd
from pathlib import Path
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import equal_weight, trend_weights, fx_carry_value_weights
from backtest.engine import run_backtest

OUT = Path("audits/AUDIT-2026-09-23-PHASE-5-5/diagnostics")
OUT.mkdir(parents=True, exist_ok=True)

master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]
fx_tickers = master.by_asset_class("fx")

# ── Build each sleeve's weights exactly as in the experiments ──────────────
configs = {
    "equal_weight": equal_weight(prices.loc[common]),
    "trend_monthly": trend_weights(prices.loc[common], ret, long_only=True, rebalance_freq="M"),
    "carry_value_monthly": fx_carry_value_weights(
        prices.loc[common], ret, fx_tickers, long_only=False, rebalance_freq="M"),
}

print("=== COST WATERFALL PER SLEEVE (full period) ===")
print(f"{'Sleeve':<22} {'TxnCost':>10} {'HoldCost':>10} {'TotalCost':>10} {'GrossPnL':>10} {'Cost/Gross':>10}")
print("-" * 76)

waterfalls = {}
for name, w in configs.items():
    allow_short = "carry" in name
    r, m, _ = run_backtest(
        "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily",
        w, allow_short=allow_short,
    )
    txn = r.costs["txn_cost"].sum()
    hold = r.costs["hold_cost"].sum()
    gross = r.returns["gross_return"].sum()
    total = txn + hold
    cg = total / abs(gross) if abs(gross) > 1e-12 else float("inf")
    print(f"{name:<22} {txn:>10.4f} {hold:>10.4f} {total:>10.4f} {gross:>10.4f} {cg:>10.4f}")
    waterfalls[name] = {"txn": float(txn), "hold": float(hold), "total": float(total),
                        "gross_pnl": float(gross), "cost_gross": float(cg),
                        "turnover": float(m["annualized_turnover"])}

# ── Turnover-to-cost consistency check per sleeve ──────────────────────────
print()
print("=== TURNOVER vs COST CONSISTENCY ===")
print(f"{'Sleeve':<22} {'AnnTurnover':>12} {'TxnCost':>10} {'TxnCost/Turnover':>16}")
print("-" * 76)
for name, w in configs.items():
    allow_short = "carry" in name
    r, m, _ = run_backtest(
        "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily",
        w, allow_short=allow_short,
    )
    # txn cost should scale with turnover (roughly): txn = sum(turnover_t * cost_rate)
    print(f"{name:<22} {m['annualized_turnover']:>12.1f} {r.costs['txn_cost'].sum():>10.4f} "
          f"{r.costs['txn_cost'].sum()/max(m['annualized_turnover'],1e-9):>16.6f}")

# ── Which instruments contribute the most txn cost in trend sleeve? ────────
print()
print("=== TREND SLEEVE: txn cost by instrument (approximation) ===")
w = configs["trend_monthly"]
# Replicate the per-instrument txn computation
weight_changes = w.diff().abs()
cm = __import__("core.costs", fromlist=["CostModel"]).CostModel()
cm.load_from_yaml("config/cost_model.yaml")
per_ticker_cost = {}
for t in w.columns:
    cost_rate = cm.round_trip_cost_pct(t, notional=1.0, pip_value=master.pip_value(t) if master.asset_class(t)=="fx" else 0.0001)
    per_ticker_cost[t] = 0.5 * weight_changes[t].sum() * cost_rate
cost_series = pd.Series(per_ticker_cost).sort_values(ascending=False)
for t, c in cost_series.items():
    if c > 0.001:
        print(f"  {t:<8} {c:.4f}")

with open(OUT / "step_e_cost_waterfall.json", "w") as f:
    json.dump(waterfalls, f, indent=2, default=str)
print("\nSaved: step_e_cost_waterfall.json")