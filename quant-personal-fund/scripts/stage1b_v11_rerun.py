#!/usr/bin/env python
"""Stage 1B v1.1 rerun — evaluation start date changed to 2020-05-29 only.

Identical to stage1b_baselines.py except:
  - START = "2020-05-29" (first investable date; 60-day min history satisfied)
  - outputs under data/processed/stage1b_v1.1/
  - COVID stress window labeled outside evaluable sample (not reported)
Everything else identical (universe, returns, costs, rebalance, vol/cov, solver).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.fx import convert_cross_eurjpy, convert_local_to_usd  # noqa: E402
from core.costs import CostModel  # noqa: E402
from core.instruments import InstrumentMaster  # noqa: E402
from data.pipelines.dataset import load_and_validate  # noqa: E402
from portfolio.accounting_v2 import (  # noqa: E402
    PortfolioResultV2,
    _daily_hold_cost,
    _drift_weights,
    _exposures,
    _rebalance_dates,
)
from portfolio.risk_parity import ensure_psd, risk_parity_weights  # noqa: E402
from risk.metrics import (  # noqa: E402
    annualized_return,
    annualized_volatility,
    drawdown_episodes,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
)

OUT = Path("quant-personal-fund/data/processed/stage1b_v1.1")
OUT.mkdir(parents=True, exist_ok=True)

# ── Load + convert (identical to v1.0, but START = 2020-05-29) ──────────────
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

START = "2020-05-29"   # v1.1: first investable date
rets = local.loc[START:"2026-09-23"].dropna(how="all").fillna(0.0)
tickers = sorted(master.tickers(active_only=True))
tickers = [t for t in tickers if t in rets.columns]

cm = CostModel()
cm.load_from_yaml("quant-personal-fund/config/cost_model.yaml")

HALFLIFE, MIN_HIST = 60, 60


def ewma_vol(s):
    return s.pow(2).ewm(halflife=HALFLIFE, min_periods=MIN_HIST).mean().pow(0.5) * np.sqrt(252)


def ewma_cov(panel):
    clean = panel.dropna()
    if len(clean) < MIN_HIST:
        raise ValueError("insufficient history")
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
        except ValueError:
            return None
    return None


def run_baseline(method, freq="M"):
    reb = set(_rebalance_dates(rets.index, freq))
    rows = []
    for i, dt in enumerate(rets.index):
        if dt in reb:
            w = weights_at(i, method)
            if w is not None:
                rows.append((dt, w))
    if not rows:
        return {}
    idx = [d for d, _ in rows]
    wdf = pd.DataFrame(np.array([w for _, w in rows]), index=idx, columns=tickers)
    wdf = wdf.reindex(rets.index).ffill().fillna(0.0)

    dates = rets.index
    n_days = len(dates)
    one_way = {t: cm.one_way_transaction_cost(t, notional=1.0, pip_value=0.0001) for t in tickers}
    target_df = wdf[tickers].reindex(dates).ffill().fillna(0.0)
    holdings = pd.DataFrame(0.0, index=dates, columns=tickers)
    targets = pd.DataFrame(0.0, index=dates, columns=tickers)
    trades = pd.DataFrame(0.0, index=dates, columns=tickers)
    gross_ret = pd.Series(0.0, index=dates)
    txn = pd.Series(0.0, index=dates)
    turn = pd.Series(0.0, index=dates)
    t0 = target_df.iloc[0].reindex(tickers).fillna(0.0)
    if abs(t0.sum() - 1) > 1e-6 and abs(t0.sum()) > 1e-10:
        t0 = t0 / t0.sum()
    targets.iloc[0] = t0.values
    holdings.iloc[0] = t0.values
    trades.iloc[0] = t0.values
    entry = sum(w * one_way[t] for t, w in zip(tickers, t0.values))
    entry_turn = 0.5 * t0.abs().sum()
    for i in range(1, n_days):
        r_t = rets[tickers].iloc[i]
        gross_ret.iloc[i] = float((holdings.iloc[i - 1] * r_t.fillna(0)).sum())
        drifted = _drift_weights(holdings.iloc[i - 1], r_t)
        if dates[i] in reb:
            ti = target_df.loc[dates[i]].reindex(tickers).fillna(0.0)
            if abs(ti.sum() - 1) > 1e-6 and abs(ti.sum()) > 1e-10:
                ti = ti / ti.sum()
            targets.iloc[i] = ti.values
            trade = ti - drifted
            trades.iloc[i] = trade.values
            holdings.iloc[i] = ti.values
            turn.iloc[i] = 0.5 * trade.abs().sum()
            txn.iloc[i] = sum(abs(x) * one_way[t] for t, x in zip(tickers, trade.values))
        else:
            targets.iloc[i] = targets.iloc[i - 1].values
            holdings.iloc[i] = drifted.values
    txn.iloc[1] += entry
    turn.iloc[1] += entry_turn
    hold = pd.Series(0.0, index=dates)
    for i in range(1, n_days):
        hold.iloc[i] = _daily_hold_cost(holdings.iloc[[i - 1]], cm).iloc[0]
    nav_gross = (1 + gross_ret.fillna(0)).cumprod()
    net = gross_ret - txn - hold
    nav_net = (1 + net.fillna(0)).cumprod()
    exposures = _exposures(holdings, pd.Series(0.0, index=dates))
    result = PortfolioResultV2(
        nav=pd.DataFrame({"nav_gross": nav_gross, "nav_net": nav_net}),
        returns=pd.DataFrame({"gross_return": gross_ret, "net_return": net}),
        holdings_w=holdings, target_w=targets, trade_w=trades,
        turnover=turn, costs=pd.DataFrame({"txn_cost": txn, "hold_cost": hold}),
        exposures=exposures, collateral_margin=None,
    )
    return {"weights": wdf, "result": result}


def metrics_of(res):
    nav = res.nav["nav_net"]
    net_ret = res.returns["net_return"].dropna()
    gross_ret = res.returns["gross_return"].dropna()
    dd, peak, trough = max_drawdown(nav)
    episodes = drawdown_episodes(nav, min_depth=0.02)
    total_cost = float(res.costs["txn_cost"].sum() + res.costs["hold_cost"].sum())
    gross_pnl = float(gross_ret.sum())
    return {
        "annualized_return": annualized_return(nav),
        "annualized_volatility": annualized_volatility(net_ret),
        "sharpe": sharpe_ratio(net_ret),
        "sortino": sortino_ratio(net_ret),
        "calmar": annualized_return(nav) / abs(dd) if dd != 0 else float("inf"),
        "max_drawdown": dd,
        "drawdown_duration_days": int((trough - peak).days),
        "turnover": float(res.turnover.sum()),
        "total_cost": total_cost,
        "gross_pnl": gross_pnl,
        "cost_to_gross": total_cost / abs(gross_pnl) if abs(gross_pnl) > 1e-12 else float("inf"),
        "n_drawdown_episodes": len(episodes),
        "cumulative_return": float(nav.iloc[-1] / nav.iloc[0] - 1),
    }


methods = ["equal", "inverse_vol", "risk_parity"]
report = {
    "spec_revision": "docs/governance/STAGE_1B_DESIGN_SPEC_v1.1.md",
    "label": "PORTFOLIO BASELINE — NOT ALPHA EVIDENCE",
    "evaluation_start": START,
    "covid_window_label": "OUTSIDE EVALUABLE SAMPLE — not a portfolio outcome",
    "universe": tickers,
    "period": [str(rets.index.min().date()), str(rets.index.max().date())],
    "baselines": {},
}

for m in methods:
    b = run_baseline(m, "M")
    res = b["result"]
    wdf = b["weights"]
    report["baselines"][m] = {"metrics": metrics_of(res), "mean_weights": wdf.mean().to_dict()}
    res.nav.to_csv(OUT / f"{m}_nav.csv")
    res.returns.to_csv(OUT / f"{m}_returns.csv")
    wdf.to_csv(OUT / f"{m}_weights.csv")

with open(OUT / "baselines_metrics_v1.1.json", "w") as f:
    json.dump(report, f, indent=2, default=str)

print(json.dumps({m: report["baselines"][m]["metrics"] for m in methods}, indent=1, default=str))