"""Step c: Benchmark construction and turnover/cost reconciliation."""
import sys; sys.path.insert(0, ".")
import json
import numpy as np
import pandas as pd
from pathlib import Path
from data.pipelines.dataset import load_and_validate
from core.instruments import InstrumentMaster
from portfolio.builder import equal_weight
from backtest.engine import run_backtest

OUT = Path("audits/AUDIT-2026-09-23-PHASE-5-5/diagnostics")
OUT.mkdir(parents=True, exist_ok=True)

master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")
prices, meta = load_and_validate("data/raw/yahoo/daily", master)
common = prices.dropna().index
ret = np.log(prices / prices.shift(1)).loc[common]

# ── Rebuild equal-weight benchmark with FULL accounting trace ──────────────
ew = equal_weight(prices.loc[common])
r_base, m_base, _ = run_backtest(
    "config/universe.yaml", "config/cost_model.yaml", "data/raw/yahoo/daily", ew
)

# ── 1. Is equal-weight rebalanced or buy-and-hold? ─────────────────────────
# equal_weight() emits 1/N on EVERY date (verified in builder.py). The
# accounting engine computes turnover on weight DIFFS -> zero after entry.
# Positions (lagged weights) are REBALANCED to 1/N daily.
# -> Benchmark is CONTINUOUSLY REBALANCED, not buy-and-hold.
#   buy-and-hold would let weights drift with returns; this does not.

# ── 2. Reconcile zero turnover with positive cost/gross ────────────────────
txn = r_base.costs["txn_cost"]
hold = r_base.costs["hold_cost"]
entry_days = (txn > 0).sum()

print("=== BENCHMARK TURNOVER/COST RECONCILIATION ===")
print(f"Reported annualized turnover : {m_base['annualized_turnover']:.4f}")
print(f"Reported cost/gross PnL      : {m_base['cost_to_gross_pnl']:.4f}")
print(f"Days with txn cost > 0       : {entry_days}")
print(f"  -> should be ~1 (first entry) + possible ffill boundary")
print(f"Total txn cost (NAV units)   : {txn.sum():.6f}")
print(f"Total hold cost (NAV units)  : {hold.sum():.6f}")
print(f"Total cost                   : {txn.sum() + hold.sum():.6f}")
print(f"Hold cost share of total     : {hold.sum()/(txn.sum()+hold.sum())*100:.1f}%")

# Per-instrument hold cost contribution
print("\nPer-instrument daily hold cost rate (from cost model):")
from core.costs import CostModel
cm = CostModel(); cm.load_from_yaml("config/cost_model.yaml")
for t in sorted(cm.all_tickers()):
    rate = cm.daily_holding_cost_pct(t)
    if rate > 0:
        print(f"  {t}: {rate:.6f}/day ({rate*252*100:.2f}% ann)")
    else:
        print(f"  {t}: 0.0 (no financing modeled)")

# ── 3. Cost/gross ratio math ───────────────────────────────────────────────
gross = r_base.returns["gross_return"]
print(f"\nTotal gross PnL (NAV)         : {gross.sum():.6f}")
print(f"Cost / gross                  : {(txn.sum()+hold.sum())/abs(gross.sum()):.4f}")
print(f"  vs reported                : {m_base['cost_to_gross_pnl']:.4f}")

# ── 4. Benchmark attribution by asset class ────────────────────────────────
print("\n=== BENCHMARK ATTRIBUTION (gross, full period) ===")
port_ret = r_base.positions * ret
class_map = {"fx": "FX", "equity_index": "Equity", "govt_bond": "Bonds", "commodity": "Commodity"}
contrib = {}
for t in port_ret.columns:
    ac = class_map.get(master.asset_class(t), "Other")
    contrib.setdefault(ac, []).append(port_ret[t].sum())
for ac, vals in sorted(contrib.items()):
    print(f"  {ac:<10}: {sum(vals)*100:+.2f}% cumulative gross")

result = {
    "rebalanced_or_buy_hold": "continuously_rebalanced_toward_1N",
    "reported_turnover": m_base["annualized_turnover"],
    "reported_cost_gross": m_base["cost_to_gross_pnl"],
    "days_txn_positive": int(entry_days),
    "total_txn_cost": float(txn.sum()),
    "total_hold_cost": float(hold.sum()),
    "hold_cost_pct_of_total": float(hold.sum()/(txn.sum()+hold.sum())*100),
    "recomputed_cost_gross": float((txn.sum()+hold.sum())/abs(gross.sum())),
    "reconciliation_ok": abs(m_base["cost_to_gross_pnl"] - (txn.sum()+hold.sum())/abs(gross.sum())) < 0.01,
}
with open(OUT / "step_c_benchmark_reconcile.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
print("\nSaved: step_c_benchmark_reconcile.json")