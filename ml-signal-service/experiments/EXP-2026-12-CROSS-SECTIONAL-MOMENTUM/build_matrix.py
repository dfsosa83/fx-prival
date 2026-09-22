#!/usr/bin/env python
"""Build the aligned daily-close matrix for the 12-instrument cross-sectional study.

Resamples each instrument's H1 closes to daily, then intersects the date index
across all instruments so the cross-sectional ranking is fair (same universe at
every rebalance). Caches data/daily_closes.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

H1 = Path(__file__).resolve().parents[2] / "data" / "raw" / "mt5" / "H1"
HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "daily_closes.csv"

SYMS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD",
        "EURGBP", "GBPJPY", "EURJPY", "XAUUSD", "US30"]  # USDX, WTI excluded: costs unmeasured


def main() -> None:
    closes = {}
    for s in SYMS:
        df = pd.read_csv(H1 / f"{s}_H1.csv", parse_dates=["datetime"]).sort_values("datetime")
        day = df.set_index("datetime")["close"].resample("1D").last().dropna()
        closes[s] = day

    m = pd.DataFrame(closes).sort_index()
    m = m.dropna(how="any")                       # common window: all 12 present
    OUT.parent.mkdir(parents=True, exist_ok=True)
    m.to_csv(OUT)

    print(f"matrix: {m.shape[0]:,} daily rows x {m.shape[1]} instruments")
    print(f"common window: {m.index.min().date()} -> {m.index.max().date()}")
    print(f"eval window (2025+): {int((m.index >= '2025-01-01').sum()):,} rows")
    print(f"rows by year:\n{m.index.year.value_counts().sort_index().to_string()}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()