"""Frival desk — live market-structure reader (STEP 1-2 helper).

Read-only. For XAUUSD/EURUSD/USDJPY it prints the current tick, spread,
tick age on the SERVER clock, clean ATR(M5), the last completed M15 range,
and the last M5/M15/H1 bars. It places NO orders and changes NO state.

Run from anywhere:
    python frival_read.py
"""
import sys
import datetime as dt
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import MetaTrader5 as mt5
import pandas as pd
from mt5_path import resolve_terminal_path

TERM = resolve_terminal_path(HERE)
if not mt5.initialize(path=TERM):
    print("init failed", mt5.last_error())
    sys.exit(1)

now_utc = dt.datetime.now(dt.timezone.utc)
print("now UTC:", now_utc.strftime("%Y-%m-%d %H:%M:%S"))
print("local(UTC-5):", (now_utc - dt.timedelta(hours=5)).strftime("%Y-%m-%d %H:%M:%S"))
print("server(UTC+3):", (now_utc + dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"))


def clean_atr(d, n=200):
    d = d.tail(n).copy()
    med = d["tick_volume"].median()
    mask = (d["high"] != d["low"]) & (d["tick_volume"] >= 0.30 * med)
    c = d[mask]
    pc = c["close"].shift(1)
    tr = pd.concat([c["high"] - c["low"], (c["high"] - pc).abs(),
                    (c["low"] - pc).abs()], axis=1).max(axis=1)
    return float(tr.tail(14).mean()), int(mask.sum()), int(len(d))


for sym in ("XAUUSD", "EURUSD", "USDJPY"):
    mt5.symbol_select(sym, True)
    tick = mt5.symbol_info_tick(sym)
    server_now = now_utc + dt.timedelta(hours=3)
    age = server_now.timestamp() - tick.time          # tick.time is server-clock
    spread = tick.ask - tick.bid
    m5 = pd.DataFrame(mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 220))
    m15 = pd.DataFrame(mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 60))
    h1 = pd.DataFrame(mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 40))
    catr, kept, tot = clean_atr(m5)
    last_m15_range = float(m15["high"].iloc[-1] - m15["low"].iloc[-1])
    print(f"\n=== {sym} ===")
    print(f"bid={tick.bid} ask={tick.ask} spread={spread:.5f} "
          f"tick_age={age:.0f}s ({age / 60:.1f}min)")
    print(f"clean_ATR(M5)={catr:.5f}  clean_bars={kept}/{tot}  "
          f"last_M15_range={last_m15_range:.5f}  ratio={last_m15_range / catr:.2f}")
    print(f"M15 last 6: {[(str(r.time), r.high, r.low, r.close, r.tick_volume) for r in m15.tail(6).itertuples()]}")
    print(f"H1 last 6:  {[(str(r.time), r.high, r.low, r.close, r.tick_volume) for r in h1.tail(6).itertuples()]}")
    print(f"M5 last 6:  {[(str(r.time), r.high, r.low, r.close, r.tick_volume) for r in m5.tail(6).itertuples()]}")
mt5.shutdown()
