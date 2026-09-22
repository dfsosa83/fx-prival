#!/usr/bin/env python
"""EXP-2026-13 — event-driven macro reaction, mechanical a-priori sign rule.

Pre-registered in experiment.yaml. For each HIGH/MED calendar event with a
known Deviation, take the sign-matched price reaction over {1,4,24}h and report
net-of-cost EV per (pair x window) on the unseen 2025+ window.

Run:
    python experiments/EXP-2026-13-EVENT-DRIVEN/run_event.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]       # ml-signal-service/
FRIVAL = ROOT.parent / "frival"
HERE = Path(__file__).resolve().parent

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(FRIVAL))
from experiments._core import bootstrap as _bootstrap
from experiments._core import costs as _costs
from data.calendar import load_calendar          # frival/data/calendar.py

PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDJPY", "XAUUSD", "USDCAD"]
WINDOWS_H = (1, 4, 24)
EVAL_START = "2025-01-01"
EVENT_BLOCK = 5

BASE = {"EURUSD": "EUR", "GBPUSD": "GBP", "USDCHF": "CHF", "USDJPY": "JPY",
        "XAUUSD": None, "USDCAD": "CAD"}
QUOTE = {"EURUSD": "USD", "GBPUSD": "USD", "USDCHF": "USD", "USDJPY": "USD",
         "XAUUSD": "USD", "USDCAD": "USD"}


def h1_closes(pair: str) -> pd.Series:
    f = ROOT / "data" / "raw" / "mt5" / "H1" / f"{pair}_H1.csv"
    df = pd.read_csv(f, parse_dates=["datetime"]).sort_values("datetime")
    return df.set_index("datetime")["close"]


def sign(pair: str, currency: str, dev: float) -> int:
    """A-priori sign rule (zero fitted parameters)."""
    if dev == 0:
        return 0
    c = currency.upper()
    if c == BASE.get(pair):     # base currency surprise strengthens pair
        return 1 if dev > 0 else -1
    if c == QUOTE.get(pair):    # quote currency surprise weakens pair
        return -1 if dev > 0 else 1
    raise ValueError(f"{currency} not in pair {pair}")


def main() -> None:
    print(f"universe {PAIRS}  windows {WINDOWS_H}  eval {EVAL_START}+")
    rows = []

    for pair in PAIRS:
        try:
            cal = load_calendar(pair)
        except Exception as e:
            print(f"[{pair}] calendar load failed: {e}")
            continue
        close = h1_closes(pair)
        pix = _costs.to_price(pair, _costs.cost_pips(pair, "ALL"))
        px = {pair: pix}

        ev = cal[(cal["Impact"].isin(["HIGH", "MEDIUM"]))
                 & cal["Deviation"].notna()
                 & (cal["event_dt"] >= pd.Timestamp(EVAL_START))].copy()
        if len(ev) == 0:
            print(f"[{pair}] no qualifying events 2025+")
            continue

        for wh in WINDOWS_H:
            pnls = []
            for _, e in ev.iterrows():
                s = sign(pair, e["Currency"], e["Deviation"])
                if s == 0:
                    continue
                start = pd.Timestamp(e["event_dt"])
                entry_ts = close.index[close.index >= start]
                exit_ts = close.index[close.index >= start + pd.Timedelta(hours=wh)]
                if len(entry_ts) == 0 or len(exit_ts) == 0:
                    continue
                entry = float(close.loc[entry_ts[0]])
                exit_ = float(close.loc[exit_ts[0]])
                raw_ret = s * (exit_ - entry) / entry
                cost = px[pair] / entry                      # round-trip fraction
                pnls.append(raw_ret - cost)
            p = pd.Series(pnls)

            if len(p) == 0:
                rows.append({"pair": pair, "win_h": wh, "n": 0, "ev": None,
                             "win": None, "pf": None, "ci_lo": None,
                             "ci_hi": None, "maxdd": None})
                continue
            wins = p[p > 0]
            losses = p[p <= 0]
            pf = wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
            _, lo, hi = _bootstrap.block_bootstrap_ci(p.values, block_length=EVENT_BLOCK,
                                                       seed=20260913)
            cum = p.cumsum()
            dd = (cum - cum.cummax()).min()
            rows.append({
                "pair": pair, "win_h": wh, "n": len(p),
                "ev": round(p.mean() * 10000, 2),          # bp per event
                "win": round(100 * (p > 0).mean(), 1),
                "pf": round(float(pf), 2) if np.isfinite(pf) else None,
                "ci_lo": round(lo * 10000, 2), "ci_hi": round(hi * 10000, 2),
                "maxdd_bp": round(float(dd) * 10000, 1),
            })

            print(f"[{pair}] w={wh}h n={len(p):>3} ev={p.mean()*10000:+.2f}bp "
                  f"win={100*(p>0).mean():.1f}% pf={rows[-1]['pf']} "
                  f"ci=[{rows[-1]['ci_lo']:+}, {rows[-1]['ci_hi']:+}]")

    out = pd.DataFrame(rows)
    REPORT = HERE / "reports"
    REPORT.mkdir(parents=True, exist_ok=True)
    out.to_csv(REPORT / "event_grid.csv", index=False)

    ok = out[(out["n"] >= 30) & (out["ev"] > 0) & (out["ci_lo"] > -5.0)]
    if len(ok):
        print(f"\nGATE: GO — cells {ok[['pair','win_h']].values.tolist()}")
    elif len(out) and bool(out["ev"].notna().all()) and all((r["ev"] <= -5.0 and r["ci_hi"] is not None and r["ci_hi"] < 0)
            for _, r in out.iterrows()):
        print("\nGATE: STOP — all cells negative, CI<0")
    else:
        print("\nGATE: HOLD — no GO cell, not all STOP")

    print(f"\nwrote {REPORT / 'event_grid.csv'}")


if __name__ == "__main__":
    main()