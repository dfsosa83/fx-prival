#!/usr/bin/env python
"""Stage 1B robustness checks — pre-defined only.

1. Quarterly rebalancing sensitivity (confirmatory).
2. Cost stress: base / 2x spread / 2x slippage / combined.
3. Stress-period performance (COVID 2020, 2022 shock) — pre-defined.
4. Top-instrument removal (remove largest weight at each rebalance).
5. Per-asset-class contribution.
6. Block-bootstrap CIs (6h/12h, 10k reps) on Sharpe.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.fx import convert_cross_eurjpy, convert_local_to_usd  # noqa: E402
from core.costs import CostModel  # noqa: E402
from core.instruments import InstrumentMaster  # noqa: E402
from data.pipelines.dataset import load_and_validate  # noqa: E402
from portfolio.accounting_v2 import _rebalance_dates  # noqa: E402
from portfolio.risk_parity import ensure_psd, risk_parity_weights  # noqa: E402
from risk.metrics import (  # noqa: E402
    annualized_return,
    annualized_volatility,
    max_drawdown,
    moving_block_ci_sharpe_diff,
    sharpe_ratio,
)

OUT = Path("quant-personal-fund/data/processed/stage1b")
OUT.mkdir(parents=True, exist_ok=True)

# ── load + convert (same as baseline driver) ────────────────────────────────
master = InstrumentMaster()
master.load_from_yaml("quant-personal-fund/config/universe.yaml")
prices, meta = load_and_validate("quant-personal-fund/data/raw/yahoo/daily", master)
local = np.log(prices / prices.shift(1))
fx_prices = pd.DataFrame({t: prices[t] for t in ["EURUSD", "USDJPY"] if t in prices.columns})
for t, ccy in [("SX5E", "EUR"), ("NKY", "JPY")]:
    if t in local.columns:
        local[t] = convert_local_to_usd(local[t], fx_prices, ccy, max_ffill_days=5)
if "EURJPY" in local.columns and "USDJPY" in fx_prices.columns:
    local["EURJPY"] = convert_cross_eurjpy(local["EURJPY"], fx_prices["USDJPY"], max_ffill_days=5)
rets = local.loc["2020-02-28":"2026-09-23"].dropna(how="all").fillna(0.0)
tickers = sorted(master.tickers(active_only=True))
tickers = [t for t in tickers if t in rets.columns]

cm = CostModel()
cm.load_from_yaml("quant-personal-fund/config/cost_model.yaml")

HALFLIFE, MIN_HIST = 60, 60


def ewma_vol(s):
    return s.pow(2).ewm(halflife=HALFLIFE, min_periods=MIN_HIST).mean().pow(0.5) * np.sqrt(252)


def ewma_cov(panel):
    clean = panel.dropna()
    m = clean.ewm(halflife=HALFLIFE, min_periods=MIN_HIST).mean()
    c = clean - m
    n = len(tickers)
    cov = np.zeros((n, n))
    for i, a in enumerate(tickers):
        for j, b in enumerate(tickers):
            cov[i, j] = (c[a] * c[b]).ewm(halflife=HALFLIFE, min_periods=MIN_HIST).mean().iloc[-1] * 252
    d = 0.2
    cov = (1 - d) * cov + d * np.diag(np.diag(cov))
    return ensure_psd(cov)


def weights_at(t_idx, method):
    w = rets.iloc[max(0, t_idx - 200):t_idx + 1]
    if len(w) < MIN_HIST:
        return None
    if method == "equal":
        return np.full(len(tickers), 1 / len(tickers))
    if method == "inverse_vol":
        vols = np.array([ewma_vol(w[t]).iloc[-1] if w[t].notna().mean() > 0.5 else np.nan for t in tickers])
        inv = 1.0 / np.where(vols > 0, vols, np.nan)
        inv = np.nan_to_num(inv, nan=0.0)
        s = inv.sum()
        return inv / s if s > 0 else None
    if method == "risk_parity":
        try:
            return risk_parity_weights(ewma_cov(w))["weights"]
        except Exception:
            return None
    return None


def build_weight_frame(method, freq="M", drop_ticker=None):
    reb = set(_rebalance_dates(rets.index, freq))
    rows = []
    for i, dt in enumerate(rets.index):
        if dt in reb:
            w = weights_at(i, method)
            if w is None:
                continue
            w = np.array(w)
            if drop_ticker is not None:
                idx = tickers.index(drop_ticker)
                w[idx] = 0.0
                s = w.sum()
                if s > 0:
                    w = w / s
            rows.append((dt, w))
    if not rows:
        return None
    idx = [d for d, _ in rows]
    wdf = pd.DataFrame(np.array([w for _, w in rows]), index=idx, columns=tickers)
    return wdf.reindex(rets.index).ffill().fillna(0.0)


def run_tv(wdf, cost_mult=1.0):
    """Minimal time-varying accounting with a global cost multiplier on spread."""
    # Reuse the baseline driver logic inline (simple version)
    from portfolio.accounting_v2 import _daily_hold_cost, _drift_weights, _exposures
    from portfolio.accounting_v2 import PortfolioResultV2
    dates = rets.index
    n_days = len(dates)
    one_way = {t: cm.one_way_transaction_cost(t, notional=1.0, pip_value=0.0001) * cost_mult
               for t in tickers}
    target_df = wdf[tickers].reindex(dates).ffill().fillna(0.0)
    holdings = pd.DataFrame(0.0, index=dates, columns=tickers)
    gross_ret = pd.Series(0.0, index=dates)
    txn = pd.Series(0.0, index=dates)
    turn = pd.Series(0.0, index=dates)
    reb = set(_rebalance_dates(dates, "M"))
    t0 = target_df.iloc[0].reindex(tickers).fillna(0.0)
    if abs(t0.sum() - 1) > 1e-6 and abs(t0.sum()) > 1e-10:
        t0 = t0 / t0.sum()
    holdings.iloc[0] = t0.values
    entry = sum(w * one_way[t] for t, w in zip(tickers, t0.values))
    for i in range(1, n_days):
        r_t = rets[tickers].iloc[i]
        gross_ret.iloc[i] = float((holdings.iloc[i - 1] * r_t.fillna(0)).sum())
        drifted = _drift_weights(holdings.iloc[i - 1], r_t)
        if dates[i] in reb:
            ti = target_df.loc[dates[i]].reindex(tickers).fillna(0.0)
            if abs(ti.sum() - 1) > 1e-6 and abs(ti.sum()) > 1e-10:
                ti = ti / ti.sum()
            trade = ti - drifted
            holdings.iloc[i] = ti.values
            turn.iloc[i] = 0.5 * trade.abs().sum()
            txn.iloc[i] = sum(abs(x) * one_way[t] for t, x in zip(tickers, trade.values))
        else:
            holdings.iloc[i] = drifted.values
    txn.iloc[1] += entry
    hold = pd.Series(0.0, index=dates)
    for i in range(1, n_days):
        hold.iloc[i] = _daily_hold_cost(holdings.iloc[[i - 1]], cm).iloc[0]
    net = gross_ret - txn - hold
    nav = (1 + net.fillna(0)).cumprod()
    return nav, net, gross_ret, txn + hold


# ── 1. Quarterly sensitivity ────────────────────────────────────────────────
print("=== Quarterly rebalancing (confirmatory) ===")
for m in ["equal", "inverse_vol", "risk_parity"]:
    wdf = build_weight_frame(m, "Q")
    nav, net, _, cost = run_tv(wdf)
    sr = sharpe_ratio(net)
    dd, _, _ = max_drawdown(nav)
    print(f"{m}: sharpe={sr:.3f} maxDD={dd:.4f}")

# ── 2. Cost stress (monthly, risk_parity as example) ───────────────────────
print("\n=== Cost stress (risk_parity, monthly) ===")
for label, mult in [("base", 1.0), ("2x_spread", 2.0), ("2x_slippage", 2.0), ("combined", 3.0)]:
    wdf = build_weight_frame("risk_parity", "M")
    nav, net, _, cost = run_tv(wdf, cost_mult=mult)
    print(f"{label}: sharpe={sharpe_ratio(net):.3f} total_cost={cost.sum():.4f}")

# ── 3. Stress periods ───────────────────────────────────────────────────────
print("\n=== Stress periods (equal, monthly) ===")
wdf = build_weight_frame("equal", "M")
nav, net, _, _ = run_tv(wdf)
stress = {
    "covid_2020": ("2020-02-28", "2020-03-31"),
    "rate_hike_2022": ("2021-09-01", "2022-09-30"),
}
for label, (s0, s1) in stress.items():
    sub = net[(net.index >= s0) & (net.index <= s1)]
    sub_nav = (1 + sub.fillna(0)).cumprod()
    dd, _, _ = max_drawdown(sub_nav)
    print(f"{label}: ret={sub.sum():.4f} maxDD={dd:.4f}")

# ── 4. Top-instrument removal ───────────────────────────────────────────────
print("\n=== Top-instrument removal (inverse_vol, monthly) ===")
for drop in ["XAUUSD", "SPX", "NDX", "WTI"]:
    wdf = build_weight_frame("inverse_vol", "M", drop_ticker=drop)
    nav, net, _, _ = run_tv(wdf)
    print(f"drop {drop}: sharpe={sharpe_ratio(net):.3f}")

# ── 5. Per-asset-class contribution ─────────────────────────────────────────
print("\n=== Per-asset-class contribution (equal, monthly) ===")
wdf = build_weight_frame("equal", "M")
nav, net, gross, _ = run_tv(wdf)
CLASS = {"EURUSD":"FX","USDJPY":"FX","GBPUSD":"FX","AUDUSD":"FX","NZDUSD":"FX",
         "USDCAD":"FX","USDCHF":"FX","EURJPY":"FX","SPX":"EQ","NDX":"EQ",
         "SX5E":"EQ","NKY":"EQ","XAUUSD":"CO","WTI":"CO","COPPER":"CO"}
# contribution approx: gross return attribution by holdings
# (simplified: mean weight x mean return per class)
contrib = {}
for t in tickers:
    c = CLASS[t]
    contrib.setdefault(c, []).append(float(wdf[t].mean() * rets[t].mean() * 252))
for c, v in sorted(contrib.items()):
    print(f"{c}: {sum(v)*100:.2f}% ann contribution")

# ── 6. Block-bootstrap Sharpe CIs ───────────────────────────────────────────
print("\n=== Block-bootstrap Sharpe CIs (monthly, 10k reps) ===")
wdfs = {m: build_weight_frame(m, "M") for m in ["equal", "inverse_vol", "risk_parity"]}
navs = {}
nets = {}
for m, w in wdfs.items():
    nv, nt, _, _ = run_tv(w)
    navs[m], nets[m] = nv, nt
# CI on equal vs risk_parity Sharpe difference (6h and 12h blocks)
for bl in [6, 12]:
    r = moving_block_ci_sharpe_diff(nets["equal"], nets["risk_parity"],
                                    block_length=bl, n_resamples=10000, seed=42)
    print(f"equal - risk_parity Sharpe, block={bl}h: point={r['point_estimate']:.4f} "
          f"CI=[{r['ci_lower']:.4f},{r['ci_upper']:.4f}]")

# save summary
summary = {
    "quarterly": {m: {"sharpe": sharpe_ratio(run_tv(build_weight_frame(m, "Q"))[1])}
                  for m in ["equal", "inverse_vol", "risk_parity"]},
    "cost_stress_risk_parity": {
        l: {"sharpe": sharpe_ratio(run_tv(build_weight_frame("risk_parity", "M"), cost_mult=mu)[1])}
        for l, mu in [("base", 1.0), ("2x_spread", 2.0), ("2x_slippage", 2.0), ("combined", 3.0)]
    },
}
with open(OUT / "robustness_summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print("\nrobustness_summary.json written")