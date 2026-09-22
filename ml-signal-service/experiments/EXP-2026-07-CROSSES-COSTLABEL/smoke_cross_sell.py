#!/usr/bin/env python
"""EXP-2026-07 smoke test — executes the actual forked cross SELL label code.

Verifies (no training, fast) the P1 validation check on the cross fork:
1. Cost-adjusted SELL label rate (% label=1) <= baseline rate, EVERY calendar
   year, on the TRAIN window (a stricter TP barrier can only reduce positives).
2. The forked label function runs end-to-end on the real cross H1 CSV.

Extracts the label function from the fork itself (notebooks/crosses/…), so it
tests the real artifact. Does not train or score any test set.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # ml-signal-service/
PAIR = "EURGBP"                             # <-- the cross being smoke-tested
DIRECTION_LABEL = "sell_label"
FUNC = "def generate_sell_labels("
FORK = ROOT / "notebooks" / "crosses" / f"{PAIR.lower()}_sell_costlabel.ipynb"
CSV = ROOT / "data" / "raw" / "mt5" / "H1" / f"{PAIR}_H1.csv"

FORWARD_BARS = 6
ATR_PERIOD = 14
# Production SELL split (inherited from eurusd_sell_improved.ipynb config cell)
TRAIN_START = "2020-06-30 00:00:00"
TRAIN_END = "2025-06-30 23:00:00"
VAL_START = "2025-07-01 00:00:00"
VAL_END = "2025-12-31 23:00:00"
TEST_START = "2026-01-01 00:00:00"


def extract_label_function() -> str:
    nb = json.loads(FORK.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if FUNC in src:
            start = src.index(FUNC)
            return src[start:]
    raise RuntimeError(f"{FUNC} not found in {FORK}")


def compute_atr14(df: pd.DataFrame) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_pc = (df["high"] - df["close"].shift()).abs()
    low_pc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
    return tr.rolling(ATR_PERIOD).mean()


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from experiments._core import costs

    ns: dict = {
        "np": np, "pd": pd, "PAIR": PAIR, "ROOT": ROOT,
        "EXP_COST_PIPS": 0.0,  # baseline: no friction
        "ROUND_TRIP_COST_PIPS": costs.ROUND_TRIP_COST_PIPS,
        "apply_cost_to_barrier": costs.apply_cost_to_barrier,
    }
    exec(extract_label_function(), ns)
    gen = ns["generate_sell_labels"]

    df = pd.read_csv(CSV, parse_dates=["datetime"]).sort_values("datetime")
    df["atr_14"] = compute_atr14(df)
    print(f"data: {len(df):,} H1 bars  {df['datetime'].min()} -> {df['datetime'].max()}")

    base = gen(df.copy(), FORWARD_BARS, 1.5, 1.0)          # EXP_COST_PIPS = 0.0

    ns2 = dict(ns)
    ns2["EXP_COST_PIPS"] = costs.cost_pips(PAIR, "ALL")
    exec(extract_label_function(), ns2)
    costlbl = ns2["generate_sell_labels"](df.copy(), FORWARD_BARS, 1.5, 1.0)

    base["year"] = base["datetime"].dt.year
    costlbl["year"] = costlbl["datetime"].dt.year

    m = lambda d: (d["datetime"] >= TRAIN_START) & (d["datetime"] <= TRAIN_END)
    b_tr, c_tr = base[m(base)], costlbl[m(costlbl)]

    print(f"\nbaseline {PAIR} SELL rate (train): {b_tr[DIRECTION_LABEL].mean()*100:.2f}%  n={len(b_tr):,}")
    print(f"cost-adj  {PAIR} SELL rate (train): {c_tr[DIRECTION_LABEL].mean()*100:.2f}%  n={len(c_tr):,}")

    rates = pd.DataFrame({
        "baseline": b_tr.groupby("year")[DIRECTION_LABEL].mean() * 100,
        "cost_adj": c_tr.groupby("year")[DIRECTION_LABEL].mean() * 100,
    })
    print("\nper-year SELL rate (%):\n", rates.round(3))

    viol = rates[rates["cost_adj"] > rates["baseline"] + 1e-9]
    if len(viol):
        raise AssertionError(
            f"cost-adjusted SELL rate EXCEEDS baseline in years {list(viol.index)} "
            f"— sign/unit bug (roadmap P1 check 1)."
        )

    n_tr = len(c_tr)
    n_val = len(costlbl[(costlbl["datetime"] >= VAL_START) & (costlbl["datetime"] <= VAL_END)])
    n_te = len(costlbl[costlbl["datetime"] >= TEST_START])
    print(f"\nsplit rows -> train {n_tr:,} | val {n_val:,} | test {n_te:,}")
    assert n_tr > 10000 and n_val > 1000 and n_te > 500

    print(f"\nSMOKE_OK: {PAIR} SELL cost-adjusted labels from the real fork; "
          f"rate <= baseline every year; splits populated.")


if __name__ == "__main__":
    main()