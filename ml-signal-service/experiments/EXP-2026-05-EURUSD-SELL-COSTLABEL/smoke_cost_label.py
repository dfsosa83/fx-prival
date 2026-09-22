#!/usr/bin/env python
"""EXP-2026-05 smoke test — executes the ACTUAL forked label code on real data.

Verifies (fast, no model training) the two P0.1 validation checks that can be
checked at the label layer (ROADMAP §9 P0.1):

1. Cost-adjusted label rate (% SELL=1) <= baseline label rate, every calendar
   year, on the TRAIN window (a stricter barrier can only reduce positives).
2. The forked `generate_sell_labels` runs end-to-end on the real EURUSD H1 CSV
   and produces a sane SELL label series on the train/val/test split.

This test extracts the label function from the forked NOTEBOOK itself
(eurusd_sell_costlabel.ipynb) so it tests the real artifact, not a copy.

Does not train any model; the sealed test set is not scored here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # ml-signal-service/
FORK = ROOT / "notebooks" / "eurusd" / "eurusd_sell_costlabel.ipynb"
CSV = ROOT / "data" / "raw" / "mt5" / "H1" / "EURUSD_H1.csv"

FORWARD_BARS = 6
ATR_PERIOD = 14
TRAIN_START = "2020-06-30 00:00:00"
TRAIN_END = "2025-06-30 23:00:00"
VAL_START = "2025-07-01 00:00:00"
VAL_END = "2025-12-31 23:00:00"
TEST_START = "2026-01-01 00:00:00"


def extract_label_function() -> str:
    """Return the cost-adjusted `generate_sell_labels` source from the fork."""
    nb = json.loads(FORK.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "def generate_sell_labels(" in src:
            # import block is injected at the top of this cell; keep only the def
            start = src.index("def generate_sell_labels(")
            return src[start:]
    raise RuntimeError("generate_sell_labels not found in forked notebook")


def compute_atr14(df: pd.DataFrame) -> pd.Series:
    """ATR(14) exactly as the production notebook computes it."""
    high_low = df["high"] - df["low"]
    high_pc = (df["high"] - df["close"].shift()).abs()
    low_pc = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_pc, low_pc], axis=1).max(axis=1)
    return true_range.rolling(ATR_PERIOD).mean()


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from experiments._core import costs

    # exec namespace with the globals the forked function expects
    ns: dict = {
        "np": np,
        "pd": pd,
        "PAIR": "EURUSD",
        "ROOT": ROOT,
        "EXP_COST_PIPS": 0.0,  # baseline: no friction
        "ROUND_TRIP_COST_PIPS": costs.ROUND_TRIP_COST_PIPS,
        "apply_cost_to_barrier": costs.apply_cost_to_barrier,
    }
    exec(extract_label_function(), ns)
    gen = ns["generate_sell_labels"]

    df = pd.read_csv(CSV, parse_dates=["datetime"]).sort_values("datetime")
    df["atr_14"] = compute_atr14(df)
    print(f"data: {len(df):,} H1 bars  {df['datetime'].min()} -> {df['datetime'].max()}")

    base = gen(df.copy(), FORWARD_BARS, 1.5, 1.0)  # EXP_COST_PIPS = 0.0

    ns2 = dict(ns)
    ns2["EXP_COST_PIPS"] = costs.cost_pips("EURUSD", "ALL")
    exec(extract_label_function(), ns2)
    costlbl = ns2["generate_sell_labels"](df.copy(), FORWARD_BARS, 1.5, 1.0)

    base["year"] = base["datetime"].dt.year
    costlbl["year"] = costlbl["datetime"].dt.year

    train_mask = lambda d: (d["datetime"] >= TRAIN_START) & (d["datetime"] <= TRAIN_END)
    b_tr, c_tr = base[train_mask(base)], costlbl[train_mask(costlbl)]

    print(f"\nbaseline SELL rate (train): {b_tr['sell_label'].mean()*100:.2f}%  "
          f"n={len(b_tr):,}")
    print(f"cost-adj  SELL rate (train): {c_tr['sell_label'].mean()*100:.2f}%  "
          f"n={len(c_tr):,}")

    rates = pd.DataFrame({
        "baseline": b_tr.groupby("year")["sell_label"].mean() * 100,
        "cost_adj": c_tr.groupby("year")["sell_label"].mean() * 100,
    })
    print("\nper-year SELL rate (%):\n", rates.round(3))

    viol = rates[rates["cost_adj"] > rates["baseline"] + 1e-9]
    if len(viol):
        raise AssertionError(
            f"cost-adjusted rate EXCEEDS baseline in years: {list(viol.index)} "
            f"— sign/unit bug (roadmap 9 P0.1 check 1)."
        )

    # split sanity: rows land where expected
    n_tr = len(c_tr); n_val = len(costlbl[(costlbl["datetime"]>=VAL_START)&(costlbl["datetime"]<=VAL_END)])
    n_te = len(costlbl[costlbl["datetime"] >= TEST_START])
    print(f"\nsplit rows -> train {n_tr:,} | val {n_val:,} | test {n_te:,}")
    assert n_tr > 10000 and n_val > 1000 and n_te > 500

    print("\nSMOKE_OK: cost-adjusted labels generated from the real forked code; "
          "rate <= baseline every year; splits populated.")


if __name__ == "__main__":
    main()