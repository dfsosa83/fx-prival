#!/usr/bin/env python
"""EXP-2026-09 smoke — US30 redesigned-geometry (TP2.0/SL1.0) SELL labels on data.

Executes the ACTUAL geom fork's label function on real US30 H1. Asserts:
1. cost-adj label rate <= baseline EVERY year on train, and
2. splits land where expected (train/val/test) — no training, no test scoring.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # ml-signal-service/
PAIR = "US30"
FORK = ROOT / "notebooks" / "crosses" / "us30_sell_costlabel_geom.ipynb"
CSV = ROOT / "data" / "raw" / "mt5" / "H1" / "US30_H1.csv"
TP, SL, FB = 2.0, 1.0, 6
TRAIN = ("2020-06-30 00:00:00", "2025-06-30 23:00:00")
VAL = ("2025-07-01 00:00:00", "2025-12-31 23:00:00")
TEST_START = "2026-01-01 00:00:00"


def extract() -> str:
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

    fsrc = extract()

    def gen(cost_pips):
        ns = {"np": np, "pd": pd, "PAIR": PAIR, "ROOT": ROOT,
              "EXP_COST_PIPS": cost_pips,
              "ROUND_TRIP_COST_PIPS": costs.ROUND_TRIP_COST_PIPS,
              "apply_cost_to_barrier": costs.apply_cost_to_barrier}
        exec(fsrc, ns)
        return ns["generate_sell_labels"]

    df = pd.read_csv(CSV, parse_dates=["datetime"]).sort_values("datetime")
    tr = pd.concat([(df["high"] - df["low"]),
                    (df["high"] - df["close"].shift()).abs(),
                    (df["low"] - df["close"].shift()).abs()], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    base = gen(0.0)(df.copy(), FB, TP, SL)
    costlbl = gen(costs.cost_pips(PAIR, "ALL"))(df.copy(), FB, TP, SL)
    base["year"] = base["datetime"].dt.year
    costlbl["year"] = costlbl["datetime"].dt.year

    m = (base["datetime"] >= TRAIN[0]) & (base["datetime"] <= TRAIN[1])
    b, c = base[m], costlbl[m]
    print(f"{PAIR} SELL TP{TP}/SL{SL}: baseline={b['sell_label'].mean()*100:.2f}%  "
          f"costadj={c['sell_label'].mean()*100:.2f}%  (n={len(c):,})")

    rates = pd.DataFrame({
        "baseline": b.groupby("year")["sell_label"].mean() * 100,
        "cost_adj": c.groupby("year")["sell_label"].mean() * 100,
    })
    print(rates.round(3).to_string())
    viol = rates[rates["cost_adj"] > rates["baseline"] + 1e-9]
    assert len(viol) == 0, f"cost-adj EXCEEDS baseline in years {list(viol.index)}"

    nv = len(costlbl[(costlbl["datetime"] >= VAL[0]) & (costlbl["datetime"] <= VAL[1])])
    nt = len(costlbl[costlbl["datetime"] >= TEST_START])
    print(f"splits -> train {len(c):,} | val {nv:,} | test {nt:,}")
    assert len(c) > 10000 and nv > 1000 and nt > 500
    print(f"SMOKE_OK: {PAIR} TP{TP}/SL{SL} labels sane on the real fork.")


if __name__ == "__main__":
    main()