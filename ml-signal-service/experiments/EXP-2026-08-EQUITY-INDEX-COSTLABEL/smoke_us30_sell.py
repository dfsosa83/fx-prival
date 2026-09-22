#!/usr/bin/env python
"""EXP-2026-08 smoke — US30 SELL cost-adjusted labels on real data (no training)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # ml-signal-service/
PAIR = "US30"
FORK = ROOT / "notebooks" / "crosses" / "us30_sell_costlabel.ipynb"
CSV = ROOT / "data" / "raw" / "mt5" / "H1" / "US30_H1.csv"
FORWARD_BARS = 6
ATR_PERIOD = 14
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
        if "def generate_sell_labels(" in src:
            return src[src.index("def generate_sell_labels("):]
    raise RuntimeError("generate_sell_labels not found")


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from experiments._core import costs

    ns = {"np": np, "pd": pd, "PAIR": PAIR, "ROOT": ROOT,
          "EXP_COST_PIPS": 0.0,
          "ROUND_TRIP_COST_PIPS": costs.ROUND_TRIP_COST_PIPS,
          "apply_cost_to_barrier": costs.apply_cost_to_barrier}
    exec(extract_label_function(), ns)
    gen = ns["generate_sell_labels"]

    df = pd.read_csv(CSV, parse_dates=["datetime"]).sort_values("datetime")
    tr = pd.concat([(df["high"] - df["low"]),
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(ATR_PERIOD).mean()
    print(f"data: {len(df):,} bars  {df['datetime'].min()} -> {df['datetime'].max()}")

    base = gen(df.copy(), FORWARD_BARS, 1.5, 1.0)

    ns2 = dict(ns)
    ns2["EXP_COST_PIPS"] = costs.cost_pips(PAIR, "ALL")
    exec(extract_label_function(), ns2)
    costlbl = ns2["generate_sell_labels"](df.copy(), FORWARD_BARS, 1.5, 1.0)

    base["year"] = base["datetime"].dt.year
    costlbl["year"] = costlbl["datetime"].dt.year
    m = lambda d: (d["datetime"] >= TRAIN_START) & (d["datetime"] <= TRAIN_END)
    b_tr, c_tr = base[m(base)], costlbl[m(costlbl)]

    print(f"\nbaseline US30 SELL (train): {b_tr['sell_label'].mean()*100:.2f}%  n={len(b_tr):,}")
    print(f"cost-adj  US30 SELL (train): {c_tr['sell_label'].mean()*100:.2f}%  n={len(c_tr):,}")
    rates = pd.DataFrame({
        "baseline": b_tr.groupby("year")["sell_label"].mean() * 100,
        "cost_adj": c_tr.groupby("year")["sell_label"].mean() * 100,
    })
    print("\nper-year SELL rate (%):\n", rates.round(3))
    viol = rates[rates["cost_adj"] > rates["baseline"] + 1e-9]
    if len(viol):
        raise AssertionError(f"cost-adj rate EXCEEDS baseline in years {list(viol.index)}")

    n_val = len(costlbl[(costlbl["datetime"] >= VAL_START) & (costlbl["datetime"] <= VAL_END)])
    n_te = len(costlbl[costlbl["datetime"] >= TEST_START])
    print(f"\nsplits -> train {len(c_tr):,} | val {n_val:,} | test {n_te:,}")
    assert len(c_tr) > 10000 and n_val > 1000 and n_te > 500
    print("\nSMOKE_OK: US30 SELL cost-adjusted labels from the real fork "
          "(rate <= baseline every year; splits populated).")


if __name__ == "__main__":
    main()