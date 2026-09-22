#!/usr/bin/env python
"""EXP-2026-11 — volatility-anchored exit policies on the same manual gold entries.

Same entries as EXP-2026-10, but 1R = ATR(H1,14) at entry (fair anchor), not the
operator's too-tight SL. See experiment.yaml for the pre-registered gate.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # ml-signal-service/
DATA10 = ROOT / "experiments" / "EXP-2026-10-GOLD-EXIT-MANAGEMENT" / "data"
REPORTS = HERE / "reports"
CONTRACT, HORIZON_H = 100.0, 48

POLICIES = {                                  # name -> (atr_mult, tp_mult, be_at)
    "A_1ATR_1.5R": (1.0, 1.5, None),
    "B_1ATR_2.0R": (1.0, 2.0, None),
    "C_1ATR_3.0R": (1.0, 3.0, None),
    "D_1.5ATR_2.0R": (1.5, 2.0, None),
    "E_1ATR_1.5R_BE1R": (1.0, 1.5, 1.0),
}


def atr_at(h1: pd.DataFrame, ts: pd.Timestamp) -> float | None:
    sub = h1[h1["datetime"] <= ts]
    if len(sub) < 15:
        return None
    tr = pd.concat([(sub["high"] - sub["low"]),
                    (sub["high"] - sub["close"].shift()).abs(),
                    (sub["low"] - sub["close"].shift()).abs()], axis=1).max(axis=1)
    a = tr.rolling(14).mean().iloc[-1]
    return float(a) if pd.notna(a) else None


def simulate(m5, t, R, tp_mult, be_at):
    sign = 1.0 if t["direction"] == "buy" else -1.0
    entry = float(t["entry"])
    if R <= 0:
        return None
    start = t["open_time"].floor("5min")
    path = m5[(m5["time"] >= start) & (m5["time"] <= start + pd.Timedelta(hours=HORIZON_H))]
    if len(path) < 2:
        return None
    sl = entry - sign * R
    tp = entry + sign * tp_mult * R
    be_level = entry + sign * be_at * R if be_at else None
    exit_px = None
    for _, b in path.iterrows():
        hi, lo = float(b["high"]), float(b["low"])
        sl_hit = lo <= sl if sign > 0 else hi >= sl
        tp_hit = hi >= tp if sign > 0 else lo <= tp
        if sl_hit:                      # ambiguous -> SL first (conservative)
            exit_px = sl
            break
        if tp_hit:
            exit_px = tp
            break
        if be_level is not None and sl != entry:
            if (hi >= be_level) if sign > 0 else (lo <= be_level):
                sl = entry
    if exit_px is None:
        exit_px = float(path.iloc[-1]["close"])
    return sign * (exit_px - entry) * CONTRACT * float(t["volume"])


def summarize(name, pnls):
    w, l = pnls[pnls > 0], pnls[pnls <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else float("inf")
    return {"policy": name, "n": len(pnls), "net_usd": round(pnls.sum(), 2),
            "ev_per_trade": round(pnls.mean(), 2), "win_pct": round(100 * len(w) / len(pnls), 1),
            "pf": round(pf, 2), "avg_win": round(w.mean(), 2) if len(w) else 0.0,
            "avg_loss": round(l.mean(), 2) if len(l) else 0.0}


def main():
    m5 = pd.read_csv(DATA10 / "xauusd_m5.csv", parse_dates=["time"])
    h1 = pd.read_csv(ROOT / "data" / "raw" / "mt5" / "H1" / "XAUUSD_H1.csv", parse_dates=["datetime"])
    trades = pd.read_csv(DATA10 / "gold_manual_trades.csv", parse_dates=["open_time"])
    g = trades[(trades.symbol == "XAUUSD") & trades.entry.notna()].copy()

    # precompute ATR at each entry
    g["atr"] = [atr_at(h1, t) for t in g["open_time"]]
    g = g[g["atr"].notna()]
    print(f"gold trades with ATR: {len(g)}  (median ATR {g['atr'].median():.2f} pts)")

    results = []
    for name, (am, tpm, be) in POLICIES.items():
        pnls = []
        for _, t in g.iterrows():
            p = simulate(m5, t, am * t["atr"], tpm, be)
            if p is not None:
                pnls.append(p)
        results.append(summarize(name, pd.Series(pnls)))

    out = pd.DataFrame(results)
    REPORTS.mkdir(parents=True, exist_ok=True)
    out.to_csv(REPORTS / "atr_exit_comparison.csv", index=False)
    print(out.to_string(index=False))
    print(f"\nwrote {REPORTS / 'atr_exit_comparison.csv'}")


if __name__ == "__main__":
    main()