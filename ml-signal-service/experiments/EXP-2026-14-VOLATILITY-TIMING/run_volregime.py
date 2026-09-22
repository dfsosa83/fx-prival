#!/usr/bin/env python
"""EXP-2026-14 — volatility-regime conditioning, mechanical trade-EV check.

For each of the 4 majors: compute net-of-cost EV of a SELL 1.5R/1R 6-bar trade in
CALM vs VOLATILE regime, walk-forward (regime learned on past, evaluated 2025+).
Cost: round-trip spread pushed onto the TP barrier (harder to reach), SL meanwhile
unaffected — the same convention as the production cost-adjusted label.
No ML. Run: python .../run_volregime.py
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

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD"]
FB, TP_M, SL_M = 6, 1.5, 1.0
EVAL = "2025-01-01"


def load(pair: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data/raw/mt5/H1" / f"{pair}_H1.csv", parse_dates=["datetime"])
    df = df.sort_values("datetime").reset_index(drop=True)
    tr = pd.concat([(df["high"] - df["low"]),
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    df["atr"] = tr.rolling(14).mean()
    df["med"] = df["atr"].rolling(720).median()      # trailing ~30-day median
    df["calm"] = df["atr"] < df["med"]
    return df


def simulate(df: pd.DataFrame, cost_px: float):
    """Return per-bar net PnL in ABSOLUTE price units of a SELL 1.5R/1R 6-bar trade.

    hit  -> + (TP_M*atr[i] - cost_px)   (net of spread)
    miss -> - (SL_M*atr[i] + cost_px)
    """
    close, high, low, atr = (df["close"].values, df["high"].values,
                             df["low"].values, df["atr"].values)
    n = len(df)
    pnl = np.full(n, np.nan)
    for i in range(n - FB):
        if np.isnan(atr[i]) or atr[i] <= 0:
            continue
        tp = close[i] - TP_M * atr[i] - cost_px      # cost-adjusted TP (harder)
        sl = close[i] + SL_M * atr[i]
        out = 0.0
        for j in range(1, FB + 1):
            k = i + j
            if low[k] <= tp:
                out = 1.0
                break
            if high[k] >= sl:
                out = 0.0
                break
        pnl[i] = (TP_M * atr[i] - cost_px) if out == 1.0 else -(SL_M * atr[i] + cost_px)
    return pnl


def cell(sub: pd.DataFrame, pnl: np.ndarray, px: float) -> dict:
    hit = float((pnl > 0).mean())
    _, lo, hi = _bootstrap.block_bootstrap_ci(pnl, block_length=FB, seed=20260914)
    return {"n": len(sub), "hit": hit,
            "ev_bp": float(pnl.mean() / px * 1e4),
            "ci_lo": float(lo / px * 1e4), "ci_hi": float(hi / px * 1e4)}


def main() -> None:
    rows = []
    for pair in PAIRS:
        df = load(pair).dropna(subset=["atr", "med"]).reset_index(drop=True)
        cost_px = _costs.to_price(pair, _costs.cost_pips(pair, "ALL"))
        pnl = simulate(df, cost_px)
        df["pnl"] = pnl
        ev = df[df["datetime"] >= pd.Timestamp(EVAL)].dropna(subset=["pnl"])
        px = float(ev["close"].mean())
        c = cell(ev[ev["calm"]], ev[ev["calm"]]["pnl"].values, px)
        v = cell(ev[~ev["calm"]], ev[~ev["calm"]]["pnl"].values, px)
        rows.append({"pair": pair, "calm_ev_bp": c["ev_bp"], "vol_ev_bp": v["ev_bp"],
                     "diff": round(c["ev_bp"] - v["ev_bp"], 2),
                     "calm_ci": [round(c["ci_lo"], 2), round(c["ci_hi"], 2)],
                     "calm_n": c["n"], "vol_n": v["n"],
                     "calm_hit": round(c["hit"], 4), "vol_hit": round(v["hit"], 4)})
        print(f"{pair}: CALM ev={c['ev_bp']:+.2f}bp (n={c['n']}) ci={[round(c['ci_lo'],2),round(c['ci_hi'],2)]} | "
              f"VOL ev={v['ev_bp']:+.2f}bp | diff={c['ev_bp']-v['ev_bp']:+.2f}")

    res = pd.DataFrame(rows)
    out = res[["pair", "calm_ev_bp", "vol_ev_bp", "diff", "calm_n", "vol_n", "calm_hit", "vol_hit"]]
    HERE.joinpath("reports").mkdir(parents=True, exist_ok=True)
    out.to_csv(HERE / "reports" / "volregime_grid.csv", index=False)
    print(f"\nwrote {HERE / 'reports' / 'volregime_grid.csv'}")

    # gate: SUPPORTED if >=2 pairs have CALM EV>0 with ci_lo>-0.05 AND CALM > VOL
    sup = [(r["pair"], r["calm_ev_bp"], r["diff"], r["calm_ci"])
           for r in rows if r["calm_ev_bp"] > 0 and r["calm_ci"][0] > -0.05 and r["diff"] > 0]
    if len(sup) >= 2:
        print(f"\nGATE: SUPPORTED — pairs meeting bar: {[s[0] for s in sup]}")
    else:
        print(f"\nGATE: REJECTED — pairs meeting bar: {[s[0] for s in sup]} (need >= 2)")


if __name__ == "__main__":
    main()