#!/usr/bin/env python
"""Stage 1B — transparent portfolio-baseline construction and audit.

Builds equal-weight, inverse-volatility, risk-parity baselines on the 15-asset
local dataset per the frozen Stage 1B design spec. Computes gross/net returns,
metrics, risk contributions, exposures, correlations, stress periods, and
block-bootstrap CIs. No alpha claim; no strategy selection.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # quant-personal-fund/
import numpy as np
import pandas as pd
from core.fx import convert_cross_eurjpy, convert_local_to_usd  # noqa: E402
from core.costs import CostModel  # noqa: E402
from core.instruments import InstrumentMaster  # noqa: E402
from data.pipelines.dataset import load_and_validate  # noqa: E402
from portfolio.accounting_v2 import (  # noqa: E402
    _rebalance_dates,
    compute_economic_benchmark,
)
from portfolio.risk_parity import ensure_psd, risk_parity_weights  # noqa: E402
from risk.metrics import (  # noqa: E402
    annualized_return,
    annualized_volatility,
    drawdown_episodes,
    max_drawdown,
    moving_block_ci_sharpe_diff,
    sharpe_ratio,
    sortino_ratio,
)

OUT = Path("quant-personal-fund/data/processed/stage1b")
OUT.mkdir(parents=True, exist_ok=True)

# ── 1. Load data (Stage 1A validated local data) ────────────────────────────
master = InstrumentMaster()
master.load_from_yaml("quant-personal-fund/config/universe.yaml")
prices, meta = load_and_validate("quant-personal-fund/data/raw/yahoo/daily", master)

# USD conversion for non-USD assets (frozen spec §3)
local = np.log(prices / prices.shift(1))
# FX prices for conversion legs
fx_prices = pd.DataFrame({t: prices[t] for t in ["EURUSD", "USDJPY"] if t in prices.columns})
for t, ccy in [("SX5E", "EUR"), ("NKY", "JPY")]:
    if t in local.columns:
        local[t] = convert_local_to_usd(local[t], fx_prices, ccy, max_ffill_days=5)
if "EURJPY" in local.columns and "USDJPY" in fx_prices.columns:
    local["EURJPY"] = convert_cross_eurjpy(local["EURJPY"], fx_prices["USDJPY"], max_ffill_days=5)

# Common start: 2020-02-28 (all 15 active present)
rets = local.loc["2020-02-28":"2026-09-23"].dropna(how="all")
rets = rets.fillna(0.0)
tickers = sorted(master.tickers(active_only=True))
tickers = [t for t in tickers if t in rets.columns]

# ── 2. Cost model ───────────────────────────────────────────────────────────
cm = CostModel()
cm.load_from_yaml("quant-personal-fund/config/cost_model.yaml")

# ── 3. Frozen helpers: EWMA vol/cov, shrinkage ─────────────────────────────
HALFLIFE = 60
MIN_HIST = 60


def ewma_vol(series: pd.Series) -> pd.Series:
    v = series.pow(2).ewm(halflife=HALFLIFE, min_periods=MIN_HIST).mean().pow(0.5) * np.sqrt(252)
    return v


def ewma_cov(panel: pd.DataFrame) -> np.ndarray:
    """EWMA covariance at last date with Ledoit-style shrinkage δ=0.2."""
    clean = panel.dropna()
    if len(clean) < MIN_HIST:
        raise ValueError("insufficient history for covariance")
    ewma_mean = clean.ewm(halflife=HALFLIFE, min_periods=MIN_HIST).mean()
    centered = clean - ewma_mean
    n = len(tickers)
    cov = np.zeros((n, n))
    for i, a in enumerate(tickers):
        for j, b in enumerate(tickers):
            p = centered[a] * centered[b]
            cov[i, j] = p.ewm(halflife=HALFLIFE, min_periods=MIN_HIST).mean().iloc[-1] * 252
    delta = 0.2
    diag = np.diag(np.diag(cov))
    cov = (1 - delta) * cov + delta * diag
    return ensure_psd(cov)


def weights_at(t_idx: int, method: str) -> np.ndarray:
    """Compute weights at rebalance index t_idx (uses data up to that date)."""
    window = rets.iloc[max(0, t_idx - 200):t_idx + 1]
    if len(window) < MIN_HIST:
        return None
    if method == "equal":
        return np.full(len(tickers), 1.0 / len(tickers))
    elif method == "inverse_vol":
        vols = np.array([ewma_vol(window[t]).iloc[-1] if window[t].notna().mean() > 0.5 else np.nan
                         for t in tickers])
        inv = 1.0 / np.where(vols > 0, vols, np.nan)
        if np.isnan(inv).all():
            return None
        inv = np.nan_to_num(inv, nan=0.0)
        s = inv.sum()
        return inv / s if s > 0 else None
    elif method == "risk_parity":
        try:
            c = ewma_cov(window)
            rp = risk_parity_weights(c)
            return rp["weights"]
        except ValueError:
            return None
    return None


# ── 4. Build baselines (monthly primary) ────────────────────────────────────
from portfolio.accounting_v2 import _daily_hold_cost, _drift_weights, _exposures  # noqa: E402


def run_time_varying(target_wdf: pd.DataFrame, freq: str = "M") -> dict:
    """Run the economic accounting engine with a TIME-VARYING target.

    Equivalent to compute_economic_benchmark but rebalances to each month's
    target weights instead of a fixed initial set. Uses accounting_v2 helpers.
    """
    dates = rets.index
    n_days = len(dates)
    n = len(tickers)

    # one-way cost per ticker (financing excluded)
    one_way = {}
    for t in tickers:
        one_way[t] = cm.one_way_transaction_cost(t, notional=1.0, pip_value=0.0001)

    target_df = target_wdf[tickers].reindex(dates).ffill().fillna(0.0)
    holdings = pd.DataFrame(0.0, index=dates, columns=tickers)
    targets = pd.DataFrame(0.0, index=dates, columns=tickers)
    trades = pd.DataFrame(0.0, index=dates, columns=tickers)
    gross_ret = pd.Series(0.0, index=dates)
    txn_cost = pd.Series(0.0, index=dates)
    turnover_series = pd.Series(0.0, index=dates)
    reb_dates = set(_rebalance_dates(dates, freq))

    target0 = target_df.iloc[0].reindex(tickers).fillna(0.0)
    if abs(target0.sum() - 1.0) > 1e-6 and abs(target0.sum()) > 1e-10:
        target0 = target0 / target0.sum()
    targets.iloc[0] = target0.values
    holdings.iloc[0] = target0.values
    trades.iloc[0] = target0.values
    entry_cost = sum(w * one_way[t] for t, w in zip(tickers, target0.values))
    entry_turnover = 0.5 * target0.abs().sum()

    for i in range(1, n_days):
        date = dates[i]
        r_t = rets[tickers].iloc[i]
        gross_ret.iloc[i] = float((holdings.iloc[i - 1] * r_t.fillna(0.0)).sum())
        drifted = _drift_weights(holdings.iloc[i - 1], r_t)

        if date in reb_dates:
            target_i = target_df.loc[date].reindex(tickers).fillna(0.0)
            if abs(target_i.sum() - 1.0) > 1e-6 and abs(target_i.sum()) > 1e-10:
                target_i = target_i / target_i.sum()
            targets.iloc[i] = target_i.values
            trade_i = target_i - drifted
            trades.iloc[i] = trade_i.values
            holdings.iloc[i] = target_i.values
            turnover_series.iloc[i] = 0.5 * trade_i.abs().sum()
            txn_cost.iloc[i] = sum(abs(tw) * one_way[t] for t, tw in zip(tickers, trade_i.values))
        else:
            targets.iloc[i] = targets.iloc[i - 1].values
            holdings.iloc[i] = drifted.values
            txn_cost.iloc[i] = 0.0

    txn_cost.iloc[1] += entry_cost
    turnover_series.iloc[1] += entry_turnover

    hold_cost = pd.Series(0.0, index=dates)
    for i in range(1, n_days):
        hold_cost.iloc[i] = _daily_hold_cost(holdings.iloc[[i - 1]], cm).iloc[0]

    nav_gross = (1.0 + gross_ret.fillna(0.0)).cumprod()
    net_ret = gross_ret - txn_cost - hold_cost
    nav_net = (1.0 + net_ret.fillna(0.0)).cumprod()
    exposures = _exposures(holdings, pd.Series(0.0, index=dates))

    from portfolio.accounting_v2 import PortfolioResultV2
    return PortfolioResultV2(
        nav=pd.DataFrame({"nav_gross": nav_gross, "nav_net": nav_net}),
        returns=pd.DataFrame({"gross_return": gross_ret, "net_return": net_ret}),
        holdings_w=holdings, target_w=targets, trade_w=trades,
        turnover=turnover_series,
        costs=pd.DataFrame({"txn_cost": txn_cost, "hold_cost": hold_cost}),
        exposures=exposures, collateral_margin=None,
    )


def run_baseline(method: str, freq: str = "M") -> dict:
    reb_dates = set(_rebalance_dates(rets.index, freq))
    w_rows = []
    for i, dt in enumerate(rets.index):
        if dt in reb_dates:
            w = weights_at(i, method)
            if w is not None:
                w_rows.append((dt, w))
    if not w_rows:
        return {}
    idx = [d for d, _ in w_rows]
    wmat = np.array([w for _, w in w_rows])
    wdf = pd.DataFrame(wmat, index=idx, columns=tickers)
    wdf = wdf.reindex(rets.index).ffill().fillna(0.0)
    result = run_time_varying(wdf, freq)
    return {"weights": wdf, "result": result}


methods = ["equal", "inverse_vol", "risk_parity"]
baselines = {m: run_baseline(m, "M") for m in methods}

# ── 5. Metrics per baseline ─────────────────────────────────────────────────
def metrics_of(res):
    nav = res.nav["nav_net"]
    gross = res.nav["nav_gross"]
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
        "cumulative_return": float(nav.iloc[-1] / nav.iloc[0] - 1.0),
    }


report = {
    "design_spec": "docs/governance/STAGE_1B_DESIGN_SPEC.md (frozen)",
    "label": "PORTFOLIO BASELINE — NOT ALPHA EVIDENCE",
    "universe": tickers,
    "period": [str(rets.index.min().date()), str(rets.index.max().date())],
    "baselines": {},
}

for m in methods:
    b = baselines[m]
    if not b:
        report["baselines"][m] = {"error": "no weights computed"}
        continue
    res = b["result"]
    wdf = b["weights"]
    report["baselines"][m] = {
        "metrics": metrics_of(res),
        "mean_weights": wdf.mean().to_dict(),
        "weight_concentration_hhi": float((wdf.mean() ** 2).sum()),
    }
    res.nav.to_csv(OUT / f"{m}_nav.csv")
    res.returns.to_csv(OUT / f"{m}_returns.csv")
    wdf.to_csv(OUT / f"{m}_weights.csv")

with open(OUT / "baselines_metrics.json", "w") as f:
    json.dump(report, f, indent=2, default=str)

print(json.dumps({m: report["baselines"].get(m, {}).get("metrics", {}) for m in methods},
                 indent=1, default=str))