"""Frival desk — OHLC bars viewer (read-only).

Prints the last M5/M15/H1 bars with O/H/L/C and volume for XAUUSD and EURUSD,
plus the current tick. Places NO orders.

Run from anywhere:
    python frival_bars.py
"""
import sys
import pathlib
import datetime as dt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import MetaTrader5 as mt5
import pandas as pd
from mt5_path import resolve_terminal_path

TERM = resolve_terminal_path(HERE)
if not mt5.initialize(path=TERM):
    print("init failed", mt5.last_error())
    sys.exit(1)

now = dt.datetime.now(dt.timezone.utc)
srv = now + dt.timedelta(hours=3)
print("server:", srv.strftime("%Y-%m-%d %H:%M"))


def show(sym):
    print(f"\n===== {sym} =====")
    for tf, n in (("M5", 15), ("M15", 8), ("H1", 6)):
        attr = getattr(mt5, "TIMEFRAME_" + tf)
        d = pd.DataFrame(mt5.copy_rates_from_pos(sym, attr, 0, n))
        d["t"] = pd.to_datetime(d["time"], unit="s").dt.strftime("%m-%d %H:%M")
        print(f"-- {tf} --")
        for r in d.itertuples():
            print(f"  {r.t}  O{r.open:>9} H{r.high:>9} L{r.low:>9} "
                  f"C{r.close:>9}  vol {r.tick_volume}")
    tk = mt5.symbol_info_tick(sym)
    print(f"  bid {tk.bid} ask {tk.ask} spread {tk.ask - tk.bid:.5f}")


for s in ("XAUUSD", "EURUSD"):
    show(s)
mt5.shutdown()
