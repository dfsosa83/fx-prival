#!/usr/bin/env python
"""EXP-2026-12 — cross-sectional momentum, mechanical rank-then-hold backtest.

Pre-registered grid: lookback L in {5,10,20} days x k in {2,3} legs per side,
weekly rebalance on Mondays, equal notional, round-trip spread cost from
_experiments/_core/costs.py, walk-forward (rank uses only past data), evaluated
on 2025-01-01 -> present. Reports per cell: net, EV, win%, PF, block-bootstrap CI,
max drawdown — then applies the go/hold/stop gate.

Run:
    python experiments/EXP-2026-12-CROSS-SECTIONAL-MOMENTUM/run_momentum.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from experiments._core import bootstrap as _bootstrap
from experiments._core import costs as _costs

LOOKBACKS = (5, 10, 20)
KS = (2, 3)
EVAL_START = "2025-01-01"
BLOCK = 5           # bootstrap block in rebalances (weeks)


def cost_fraction(sym: str, level: float) -> float:
    """Round-trip spread cost as a fraction of price (one leg)."""
    px = _costs.to_price(sym, _costs.cost_pips(sym, "ALL"))
    return px / level


def run_cell(m: pd.DataFrame, L: int, k: int) -> dict:
    dates = m.index
    rets = m.pct_change().iloc[1:]
    close = m

    # rebalance on each Monday present in the index
    mondays = [d for d in dates if d.weekday() == 0]

    evals = []
    book = 1.0            # notional 1
    w = book / (2 * k)    # per leg

    for i, d in enumerate(mondays):
        next_dates = [x for x in dates if x > d]
        if len(next_dates) < 5:          # need a full week ahead
            continue
        h = next_dates[0]                # next Monday

        # trailing L-day return on each instrument (uses only data <= d)
        lo = dates[dates <= d]
        past = close.loc[lo]
        if len(past) < L + 1 or h < pd.Timestamp(EVAL_START):
            continue
        tr = (past.iloc[-1] / past.iloc[-L]).dropna()
        if len(tr) < 2 * k:
            continue

        ranked = tr.sort_values(ascending=False)
        longs = list(ranked.index[:k])
        shorts = list(ranked.index[-k:])

        # next-week return per instrument: close[h]/close[d] - 1
        fwd = close.loc[h] / close.loc[d] - 1.0

        pnl = 0.0
        for sym in longs:
            cfr = cost_fraction(sym, close.loc[d, sym])
            pnl += w * (fwd[sym] - cfr)
        for sym in shorts:
            cfr = cost_fraction(sym, close.loc[d, sym])
            pnl += w * (-fwd[sym] - cfr)
        evals.append({"date": d, "pnl": pnl})

    r = pd.DataFrame(evals)
    if len(r) == 0:
        return {"L": L, "k": k, "n": 0, "net": 0.0, "ev": 0.0, "win": 0.0,
                "pf": None, "ci_lo": None, "ci_hi": None, "maxdd": 0.0}
    net = float(r["pnl"].sum())
    wins = r[r["pnl"] > 0]
    losses = r[r["pnl"] <= 0]
    pf = wins["pnl"].sum() / abs(losses["pnl"].sum()) if len(losses) and losses["pnl"].sum() != 0 else float("inf")
    _, lo, hi = _bootstrap.block_bootstrap_ci(r["pnl"].values, block_length=BLOCK, seed=20260922)
    r["cum"] = r["pnl"].cumsum()
    r["peak"] = r["cum"].cummax()
    r["dd"] = r["cum"] - r["peak"]
    return {"L": L, "k": k, "n": len(r), "net": round(net, 4), "ev": round(net / len(r), 4),
            "win": round(100 * len(wins) / len(r), 1),
            "pf": round(pf, 2) if np.isfinite(pf) else None,
            "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
            "maxdd": round(float(r["dd"].min()), 4)}


def main() -> None:
    m = pd.read_csv(HERE / "data" / "daily_closes.csv", parse_dates=["datetime"]).set_index("datetime")
    syms = list(m.columns)
    print(f"universe ({len(syms)}): {', '.join(syms)}")
    print(f"window {m.index.min().date()} -> {m.index.max().date()}  "
          f"eval {pd.Timestamp(EVAL_START).date()}->")
    print(f"{'L':>3} {'k':>2} {'n':>5} {'net':>8} {'ev':>7} {'win%':>6} "
          f"{'PF':>6} {'ci_lo':>7} {'ci_hi':>7} {'maxdd':>8}")
    rows = []
    for L in LOOKBACKS:
        for k in KS:
            out = run_cell(m, L, k)
            rows.append(out)
            print(f"{L:>3} {k:>2} {out['n']:>5} {out['net']:>8.4f} {out['ev']:>7.4f} "
                  f"{out['win']:>5.1f} {str(out['pf']):>6} {str(out['ci_lo']):>7} "
                  f"{str(out['ci_hi']):>7} {out['maxdd']:>8.4f}")

    grid = pd.DataFrame(rows)
    out = HERE / "reports" / "momentum_grid.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    grid.to_csv(out, index=False)
    print(f"\nwrote {out}")

    # gate
    go = grid[(grid["n"] >= 30) & (grid["ev"] > 0) & (grid["ci_lo"] > -0.05)]
    stop = all((r["ev"] <= -0.05 and r["ci_hi"] is not None and r["ci_hi"] < 0) for _, r in grid.iterrows())
    if len(go):
        print(f"\nGATE: GO — cells {go[['L','k']].values.tolist()}")
    elif stop:
        print("\nGATE: STOP — all cells negative with CI upper < 0")
    else:
        print("\nGATE: HOLD — no GO cell, not all STOP")


if __name__ == "__main__":
    main()