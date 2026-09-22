#!/usr/bin/env python
"""EXP-2026-06 smoke test — executes the ACTUAL forked BUY label code on data.

Mirror of the EXP-2026-05 smoke test, on the BUY fork. Verifies (no training):
1. Cost-adjusted BUY label rate (% label=1) <= baseline rate, every calendar
   year, on the TRAIN window (a stricter TP barrier can only reduce positives).
2. The forked `generate_buy_labels` runs end-to-end on real EURUSD H1 and
   drops ambiguous/timeout bars exactly as production does (NaN semantics).

Extracts the label function from the fork itself (eurusd_buy_costlabel.ipynb),
so it tests the real artifact, not a copy. Does not train or score the test set.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # ml-signal-service/
FORK = ROOT / "notebooks" / "eurusd" / "eurusd_buy_costlabel.ipynb"
CSV = ROOT / "data" / "raw" / "mt5" / "H1" / "EURUSD_H1.csv"

FORWARD_BARS = 6
ATR_PERIOD = 14
# ACTUAL BUY production split (inherited from eurusd_buy_improved.ipynb).
# NOTE: differs from the SELL experiment (EXP-2026-05) — BUY's test window
# starts 2026-04-01, NOT 2026-01-01.
TRAIN_START = "2020-06-30 00:00:00"
TRAIN_END = "2025-10-31 23:00:00"
VAL_START = "2025-11-01 00:00:00"
VAL_END = "2026-03-31 23:00:00"
TEST_START = "2026-04-01 00:00:00"


def extract_label_function() -> str:
    nb = json.loads(FORK.read_text(encoding="utf-8"))
    for cell in nb["cells"]:
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "def generate_buy_labels(" in src:
            start = src.index("def generate_buy_labels(")
            return src[start:]
    raise RuntimeError("generate_buy_labels not found in forked BUY notebook")


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
        "np": np, "pd": pd, "PAIR": "EURUSD", "ROOT": ROOT,
        "EXP_COST_PIPS": 0.0,  # baseline: no friction
        "ROUND_TRIP_COST_PIPS": costs.ROUND_TRIP_COST_PIPS,
        "apply_cost_to_barrier": costs.apply_cost_to_barrier,
    }
    exec(extract_label_function(), ns)
    gen = ns["generate_buy_labels"]

    df = pd.read_csv(CSV, parse_dates=["datetime"]).sort_values("datetime")
    df["atr_14"] = compute_atr14(df)
    print(f"data: {len(df):,} H1 bars  {df['datetime'].min()} -> {df['datetime'].max()}")

    base = gen(df.copy(), FORWARD_BARS, 1.5, 1.0)          # EXP_COST_PIPS = 0.0

    ns2 = dict(ns)
    ns2["EXP_COST_PIPS"] = costs.cost_pips("EURUSD", "ALL")
    exec(extract_label_function(), ns2)
    costlbl = ns2["generate_buy_labels"](df.copy(), FORWARD_BARS, 1.5, 1.0)

    base["year"] = base["datetime"].dt.year
    costlbl["year"] = costlbl["datetime"].dt.year

    m = lambda d: (d["datetime"] >= TRAIN_START) & (d["datetime"] <= TRAIN_END)
    b_tr, c_tr = base[m(base)], costlbl[m(costlbl)]

    print(f"\nbaseline BUY rate (train): {b_tr['buy_label'].mean()*100:.2f}%  n={len(b_tr):,}")
    print(f"cost-adj  BUY rate (train): {c_tr['buy_label'].mean()*100:.2f}%  n={len(c_tr):,}")

    rates = pd.DataFrame({
        "baseline": b_tr.groupby("year")["buy_label"].mean() * 100,
        "cost_adj": c_tr.groupby("year")["buy_label"].mean() * 100,
    })
    print("\nper-year BUY rate (%):\n", rates.round(3))

    viol = rates[rates["cost_adj"] > rates["baseline"] + 1e-9]
    if len(viol):
        raise AssertionError(
            f"cost-adjusted BUY rate EXCEEDS baseline in years {list(viol.index)} "
            f"— sign/unit bug (roadmap P1 check 1)."
        )

    n_tr = len(c_tr)
    n_val = len(costlbl[(costlbl["datetime"] >= VAL_START) & (costlbl["datetime"] <= VAL_END)])
    n_te = len(costlbl[costlbl["datetime"] >= TEST_START])
    print(f"\nsplit rows -> train {n_tr:,} | val {n_val:,} | test {n_te:,}")
    assert n_tr > 10000 and n_val > 1000 and n_te > 500

    print("\nSMOKE_OK: cost-adjusted BUY labels generated from the real fork; "
          "rate <= baseline every year; splits populated.")


if __name__ == "__main__":
    main()