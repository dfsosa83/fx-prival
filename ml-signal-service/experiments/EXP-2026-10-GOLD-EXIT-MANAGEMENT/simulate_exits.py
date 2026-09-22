#!/usr/bin/env python
"""EXP-2026-10 — exit-management study on the real manual gold entries.

Holds each real trade's ENTRY fixed and replays the XAUUSD M5 path under the
five pre-registered exit policies (see experiment.yaml). Answers: would a
mechanical exit policy have made the operator's own entries profitable?

Output: reports/exit_policy_comparison.csv  + stdout summary.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPORTS = HERE / "reports"

CONTRACT = 100.0          # XAUUSD contract size (verified)
HORIZON_H = 48            # market-exit horizon if no barrier hit
BREAKEVEN_RATIO = 0.805   # (1-p)/p at the observed 55.4% win rate

# pre-registered policies: name -> (tp_mult, move_be_at)   be None = no BE
POLICIES = {
    "P1_1R_1.5R": (1.5, None),
    "P2_1R_2.0R": (2.0, None),
    "P3_1R_1.5R_BE1R": (1.5, 1.0),
    "P4_1R_1.0R": (1.0, None),
    "P5_1R_3.0R": (3.0, None),
}


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    m5 = pd.read_csv(DATA / "xauusd_m5.csv", parse_dates=["time"])
    trades = pd.read_csv(DATA / "gold_manual_trades.csv", parse_dates=["open_time"])
    gold = trades[(trades["symbol"] == "XAUUSD")
                  & trades["sl"].notna() & trades["entry"].notna()].copy()
    return m5, gold


def simulate_trade(m5: pd.DataFrame, t: pd.Series, tp_mult: float, be_at: float | None) -> dict | None:
    sign = 1.0 if t["direction"] == "buy" else -1.0
    entry, sl0 = float(t["entry"]), float(t["sl"])
    R = abs(entry - sl0)
    if R <= 0:
        return None
    # SL must be on the correct side
    if (sign > 0 and sl0 >= entry) or (sign < 0 and sl0 <= entry):
        return None

    start = t["open_time"].floor("5min")
    path = m5[(m5["time"] >= start) & (m5["time"] <= start + pd.Timedelta(hours=HORIZON_H))]
    if len(path) < 2:
        return None

    sl = sl0
    tp = entry + sign * tp_mult * R
    be_level = entry + sign * be_at * R if be_at else None

    exit_px = None
    for _, b in path.iterrows():
        hi, lo = float(b["high"]), float(b["low"])
        sl_hit = lo <= sl if sign > 0 else hi >= sl
        tp_hit = hi >= tp if sign > 0 else lo <= tp
        if sl_hit and tp_hit:          # ambiguous bar -> conservative SL first
            exit_px = sl
            break
        if sl_hit:
            exit_px = sl
            break
        if tp_hit:
            exit_px = tp
            break
        if be_level is not None and sl != entry:      # arm BE from the NEXT bar
            if (hi >= be_level) if sign > 0 else (lo <= be_level):
                sl = entry
    if exit_px is None:                 # horizon -> market at last close
        exit_px = float(path.iloc[-1]["close"])

    pnl = sign * (exit_px - entry) * CONTRACT * float(t["volume"])
    r_mult = sign * (exit_px - entry) / R
    return {"exit": exit_px, "pnl": pnl, "r": r_mult}


def summarize(name: str, pnls: pd.Series) -> dict:
    w = pnls[pnls > 0]
    l = pnls[pnls <= 0]
    pf = w.sum() / abs(l.sum()) if len(l) and l.sum() != 0 else float("inf")
    return {
        "policy": name,
        "n": len(pnls),
        "net_usd": round(pnls.sum(), 2),
        "ev_per_trade": round(pnls.mean(), 2),
        "win_pct": round(100 * len(w) / len(pnls), 1),
        "pf": round(pf, 2),
        "avg_win": round(w.mean(), 2) if len(w) else 0.0,
        "avg_loss": round(l.mean(), 2) if len(l) else 0.0,
        "win_loss_ratio": round(abs(w.mean() / l.mean()), 3) if len(w) and len(l) and l.mean() != 0 else None,
    }


def main() -> None:
    m5, gold = load()
    print(f"gold trades with valid SL+entry: {len(gold)}")

    results = []
    # P0 — actual operator exits
    actual = gold["profit"]
    results.append(summarize("P0_ACTUAL", actual))

    for name, (tp_mult, be_at) in POLICIES.items():
        rows = []
        for _, t in gold.iterrows():
            r = simulate_trade(m5, t, tp_mult, be_at)
            if r:
                rows.append(r["pnl"])
        results.append(summarize(name, pd.Series(rows)))

    out = pd.DataFrame(results)
    REPORTS.mkdir(parents=True, exist_ok=True)
    out.to_csv(REPORTS / "exit_policy_comparison.csv", index=False)

    print(f"\nbreakeven win/loss ratio at observed win rate: {BREAKEVEN_RATIO}")
    print(out.to_string(index=False))
    print(f"\nwrote {REPORTS / 'exit_policy_comparison.csv'}")


if __name__ == "__main__":
    main()