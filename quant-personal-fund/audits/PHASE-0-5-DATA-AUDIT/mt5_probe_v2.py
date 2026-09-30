#!/usr/bin/env python
"""Phase 0.5 — READ-ONLY MT5 data-feasibility probe (v2, bounded).

Design changes vs v1 (which timed out on wide M5 ranges):
  - Incremental writes: every cell result is appended to results.json as it
    completes, so a slow/failed cell never loses prior work.
  - Bounded envelope search: probe a few well-chosen 1-year windows to bracket
    server retention instead of requesting 2015-2026 outright (avoids a giant
    M5 transfer that stalls).
  - Per-cell row cap safety: record returned count; never assume size.
  - Tick probe on a 7-day window only.
  - No login(), no order ops, no settings changes.

Outputs: mt5_probe_v2_results.json + query_log.csv (append).
"""
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
OUT = Path("quant-personal-fund/audits/PHASE-0-5-DATA-AUDIT")

INSTRUMENTS = ["XAUUSD", "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
               "USDCAD", "USDCHF", "USDJPY", "EURJPY"]
TIMEFRAMES = ["M5", "M15", "M30", "H1"]
TF_ATTR = {"M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15",
           "M30": "TIMEFRAME_M30", "H1": "TIMEFRAME_H1"}

# Bracket windows (year, month, day) to probe retention
WINDOWS = [
    (2016, 1, 1), (2018, 1, 1), (2019, 1, 1), (2020, 1, 1),
    (2022, 1, 1), (2024, 1, 1), (2025, 1, 1), (2026, 1, 1),
]

import MetaTrader5 as mt5
from dotenv import load_dotenv

load_dotenv(Path("frival/execution_bot/config/credentials.env"))
path = os.getenv("MT5_TERMINAL_PATH") or r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

out_path = OUT / "mt5_probe_v2_results.json"
if out_path.exists():
    with open(out_path, encoding="utf-8") as f:
        state = json.load(f)
else:
    state = {"cells": {}, "symbol_specs": {}, "notes": []}


def log_query(symbol, tf, what, ok, note):
    rows = []
    if (OUT / "query_log.csv").exists():
        rows = pd.read_csv(OUT / "query_log.csv").to_dict("records")
    rows.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol, "timeframe": tf, "query": what,
        "result": "OK" if ok else "ERROR/NA", "note": note[:400],
    })
    pd.DataFrame(rows).to_csv(OUT / "query_log.csv", index=False)


def probe_envelope(mt5, sym, tf_id, cell):
    """Bracket the retrievable range with small probes; return first/last ts
    where bars exist, and a coarse count."""
    first_found = None
    last_found = None
    coarse_total = 0
    for (y, m, d) in WINDOWS:
        s = datetime(y, m, d, tzinfo=timezone.utc)
        e = s + timedelta(days=30)
        r = mt5.copy_rates_range(sym, tf_id, s, e)
        if r is None or len(r) == 0:
            continue
        df = pd.DataFrame(r)
        ts = pd.to_datetime(df["time"], unit="s")
        if first_found is None:
            first_found = str(ts.min())
        last_found = str(ts.max())
        coarse_total += int(len(df))
    cell["envelope_first"] = first_found
    cell["envelope_last"] = last_found
    cell["envelope_coarse_bars"] = coarse_total
    cell["envelope_note"] = (
        "Bracketed via 30-day probes at 2016/2018/2019/2020/2022/2024/2025/2026 "
        "origins; full-range transfer avoided (v1 timed out)."
    )


if not mt5.initialize(path=path):
    print(json.dumps({"fatal": f"initialize failed: {mt5.last_error()}"}))
    sys.exit(1)

try:
    for sym in INSTRUMENTS:
        for tf in TIMEFRAMES:
            key = f"{sym}_{tf}"
            if key in state["cells"]:
                continue
            tf_id = getattr(mt5, TF_ATTR[tf])
            cell = {"instrument": sym, "timeframe": tf}
            try:
                probe_envelope(mt5, sym, tf_id, cell)

                # Representative recent window for fields/gaps/dups/stability
                s = datetime(2026, 8, 1, tzinfo=timezone.utc)
                e = datetime(2026, 9, 24, tzinfo=timezone.utc)
                r = mt5.copy_rates_range(sym, tf_id, s, e)
                if r is not None and len(r) > 0:
                    df = pd.DataFrame(r)
                    cell["fields"] = [c for c in df.columns]
                    cell["has_bar_spread"] = "spread" in df.columns
                    cell["rows_2026_08_09"] = int(len(df))
                    cell["dup_2026_08_09"] = int(df["time"].duplicated().sum())
                    dt = pd.to_datetime(df["time"], unit="s")
                    expected_ms = {"M5": 5*60e3, "M15": 15*60e3,
                                   "M30": 30*60e3, "H1": 60*60e3}[tf]
                    gaps = dt.diff().dropna()
                    big = gaps[gaps > pd.Timedelta(milliseconds=expected_ms) * 1.5]
                    cell["gaps_over_1.5x_2026_08_09"] = int(len(big))
                    # stability: second identical query
                    time.sleep(0.2)
                    r2 = mt5.copy_rates_range(sym, tf_id, s, e)
                    if r2 is not None and len(r2) > 0:
                        df2 = pd.DataFrame(r2)
                        cell["repeated_query_stable"] = bool(
                            (df["time"].values == df2["time"].values).all() and
                            len(df) == len(df2))
                    else:
                        cell["repeated_query_stable"] = None
                    log_query(sym, tf, "copy_rates_range recent+stability", True,
                              f"rows={len(df)} env_first={cell.get('envelope_first')} env_last={cell.get('envelope_last')}")
                else:
                    cell["recent_error"] = str(mt5.last_error())
                    log_query(sym, tf, "copy_rates_range recent", False,
                              str(mt5.last_error()))

                # Tick probe (7-day)
                t_end = datetime.now(timezone.utc)
                t_start = t_end - timedelta(days=7)
                ticks = mt5.copy_ticks_range(sym, t_start, t_end)
                if ticks is not None and len(ticks) > 0:
                    tdf = pd.DataFrame(ticks)
                    cell["tick_rows"] = int(len(tdf))
                    cell["tick_fields"] = [c for c in tdf.columns]
                    cell["tick_has_bid_ask"] = "bid" in tdf.columns and "ask" in tdf.columns
                else:
                    cell["tick_rows"] = 0
                    cell["tick_has_bid_ask"] = False
                    cell["tick_note"] = f"no ticks 7d: {mt5.last_error()}"
                log_query(sym, tf, "copy_ticks_range 7d", cell.get("tick_rows", 0) > 0,
                          f"ticks={cell.get('tick_rows',0)} bid_ask={cell.get('tick_has_bid_ask',False)}")
            except Exception as e:
                cell["error"] = str(e)
                log_query(sym, tf, "cell probe", False, str(e))

            state["cells"][key] = cell
            out_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
            print(f"[done] {key}: {json.dumps({k: cell.get(k) for k in ('envelope_first','envelope_last','rows_2026_08_09','tick_rows','tick_has_bid_ask')}, default=str)}", flush=True)

    # Symbol specs
    for sym in INSTRUMENTS:
        if sym in state["symbol_specs"]:
            continue
        si = mt5.symbol_info(sym)
        if si is None:
            state["symbol_specs"][sym] = {"error": str(mt5.last_error())}
        else:
            state["symbol_specs"][sym] = {
                "contract_size": getattr(si, "contract_size", None),
                "digits": getattr(si, "digits", None),
                "point": getattr(si, "point", None),
                "volume_min": getattr(si, "volume_min", None),
                "volume_step": getattr(si, "volume_step", None),
                "spread": getattr(si, "spread", None),
                "swap_long": getattr(si, "swap_long", None),
                "swap_short": getattr(si, "swap_short", None),
                "swap_rollover3days": getattr(si, "swap_rollover3days", None),
                "trade_mode": getattr(si, "trade_mode", None),
                "path": getattr(si, "path", None),
            }
    out_path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
finally:
    mt5.shutdown()

print(f"COMPLETE: {len(state['cells'])} cells, {len(state['symbol_specs'])} specs")
print(f"Output: {out_path}")