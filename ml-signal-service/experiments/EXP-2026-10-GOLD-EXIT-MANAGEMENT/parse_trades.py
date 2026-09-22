#!/usr/bin/env python
"""Parse the real manual gold trades from the MT5 statement into a clean ledger.

Source: notebooks/xauusd/ReportHistory-81486396.xlsx (live account, real money).
The sheet has three sub-tables (Positions / Orders / Deals) with DIFFERENT column
layouts — the Positions table is the one with per-trade profit. We isolate it by
requiring Type in {buy,sell} AND a numeric Volume (Orders use "x / y", Deals use
in/out).

Output: data/gold_manual_trades.csv
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]           # ml-signal-service/
SRC = ROOT / "notebooks" / "xauusd" / "ReportHistory-81486396.xlsx"
OUT = Path(__file__).resolve().parent / "data" / "gold_manual_trades.csv"


def main() -> None:
    # the workbook is often open in Excel -> parse a temp copy
    tmp = Path(tempfile.gettempdir()) / "rh_parse.xlsx"
    shutil.copyfile(SRC, tmp)
    raw = pd.read_excel(tmp, header=None)

    rows = []
    for i in range(7, len(raw)):
        r = raw.iloc[i]
        typ = str(r[3]).strip().lower()
        vol = pd.to_numeric(r[4], errors="coerce")      # positions: numeric lot
        sym = str(r[2]).strip()
        if typ in ("buy", "sell") and pd.notna(vol) and sym and sym != "nan":
            profit = pd.to_numeric(r[12], errors="coerce")
            if pd.notna(profit):
                rows.append({
                    "open_time": str(r[0]).strip(),
                    "position_id": str(r[1]).strip(),
                    "symbol": sym,
                    "direction": typ,
                    "volume": float(vol),
                    "entry": pd.to_numeric(r[5], errors="coerce"),
                    "sl": pd.to_numeric(r[6], errors="coerce"),
                    "tp": pd.to_numeric(r[7], errors="coerce"),
                    "close_time": str(r[8]).strip(),
                    "close_price": pd.to_numeric(r[9], errors="coerce"),
                    "commission": pd.to_numeric(r[10], errors="coerce"),
                    "swap": pd.to_numeric(r[11], errors="coerce"),
                    "profit": float(profit),
                })

    df = pd.DataFrame(rows)
    df["open_time"] = pd.to_datetime(df["open_time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    df["close_time"] = pd.to_datetime(df["close_time"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
    df = df.sort_values("open_time").reset_index(drop=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)

    gold = df[df["symbol"] == "XAUUSD"]
    print(f"parsed {len(df)} positions ({len(gold)} XAUUSD) -> {OUT}")
    print(f"date range: {df['open_time'].min()} -> {df['open_time'].max()}")
    print(f"gold net: {gold['profit'].sum():+.2f}  | all net: {df['profit'].sum():+.2f}")
    print(f"gold rows missing SL: {int(gold['sl'].isna().sum())}  missing TP: {int(gold['tp'].isna().sum())}")
    print("\nsample:")
    print(gold[["open_time", "direction", "volume", "entry", "sl", "tp", "close_time", "close_price", "profit"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()