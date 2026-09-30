#!/usr/bin/env python
"""Phase 0.5 — READ-ONLY MT5 data-feasibility probe.

Reads, for each approved instrument x timeframe (M5/M15/M30/H1):
  - copy_rates_range envelope (earliest/latest retrievable, bars, dups, gaps)
  - repeated-query stability (two passes)
  - bar spread field presence
  - copy_ticks_range depth + bid/ask availability (recent window)
  - symbol_info contract metadata (current spec)

NO login() call (inherit active session). NO order operations. NO settings
changes. Max-bars setting is NOT read via terminal config (would disturb);
recorded as 'not changed, not read via terminal' — any limit observed through
copy_rates_range behavior is recorded instead.

Outputs to quant-personal-fund/audits/PHASE-0-5-DATA-AUDIT/:
  - mt5_probe_results.json
  - query_log rows appended to query_log.csv
"""
import json
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
TF_ATTR = {
    "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30", "H1": "TIMEFRAME_H1",
}

import MetaTrader5 as mt5
from dotenv import load_dotenv
import os

load_dotenv(Path("frival/execution_bot/config/credentials.env"))
path = os.getenv("MT5_TERMINAL_PATH") or r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

log_rows = []

def log_query(symbol, tf, what, ok, note):
    log_rows.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol, "timeframe": tf, "query": what,
        "result": "OK" if ok else "ERROR/NA", "note": note[:400],
    })

# ── initialize (read-only, inherit session) ────────────────────────────────
if not mt5.initialize(path=path):
    print(json.dumps({"fatal": f"initialize failed: {mt5.last_error()}"}))
    sys.exit(1)

results = {}
try:
    for sym in INSTRUMENTS:
        for tf in TIMEFRAMES:
            tf_id = getattr(mt5, TF_ATTR[tf])
            cell = {"instrument": sym, "timeframe": tf}

            # 1) Envelope probe: wide range
            start = datetime(2015, 1, 1, tzinfo=timezone.utc)
            end = datetime(2026, 12, 31, tzinfo=timezone.utc)
            rates = mt5.copy_rates_range(sym, tf_id, start, end)
            if rates is None:
                cell["envelope_error"] = str(mt5.last_error())
                log_query(sym, tf, "copy_rates_range wide", False, str(mt5.last_error()))
                results[f"{sym}_{tf}"] = cell
                continue
            df = pd.DataFrame(rates)
            cell["rows"] = int(len(df))
            cell["returned_first"] = str(df["time"].min())
            cell["returned_last"] = str(df["time"].max())
            cell["fields"] = [c for c in df.columns]
            cell["has_bar_spread"] = "spread" in df.columns

            # duplicates
            cell["duplicate_timestamps"] = int(df["time"].duplicated().sum())

            # gaps (bar interval expected per tf)
            expected_ms = {"M5": 5*60e3, "M15": 15*60e3, "M30": 30*60e3, "H1": 60*60e3}[tf]
            dt = pd.to_datetime(df["time"], unit="s")
            gaps = dt.diff().dropna()
            big = gaps[gaps > pd.Timedelta(milliseconds=expected_ms) * 1.5]
            cell["gaps_over_1.5x_interval"] = int(len(big))
            if len(big):
                cell["largest_gap_s"] = float(big.max().total_seconds())
            cell["tz_convention"] = "unix epoch (UTC-based); server offsets not decoded"

            # 2) Repeated-query stability (second pass, same range)
            time.sleep(0.3)
            rates2 = mt5.copy_rates_range(sym, tf_id, start, end)
            if rates2 is not None:
                df2 = pd.DataFrame(rates2)
                same = len(df) == len(df2) and bool((df["time"].values == df2["time"].values).all())
                cell["repeated_query_stable"] = bool(same)
            else:
                cell["repeated_query_stable"] = None
            log_query(sym, tf, "copy_rates_range x2", True,
                      f"rows={cell['rows']} first={cell.get('returned_first')} last={cell.get('returned_last')}")

            # 3) Tick probe (recent window; depth + bid/ask)
            t_start = datetime.now(timezone.utc) - timedelta(days=7)
            t_end = datetime.now(timezone.utc)
            ticks = mt5.copy_ticks_range(sym, t_start, t_end)
            if ticks is not None and len(ticks) > 0:
                tdf = pd.DataFrame(ticks)
                cell["tick_rows"] = int(len(tdf))
                cell["tick_fields"] = [c for c in tdf.columns]
                cell["tick_has_bid_ask"] = "bid" in tdf.columns and "ask" in tdf.columns
                cell["tick_first"] = str(pd.to_datetime(tdf["time"].min(), unit="s"))
                cell["tick_last"] = str(pd.to_datetime(tdf["time"].max(), unit="s"))
            else:
                cell["tick_rows"] = 0
                cell["tick_has_bid_ask"] = False
                cell["tick_note"] = f"no ticks in 7d window: {mt5.last_error()}"
            log_query(sym, tf, "copy_ticks_range 7d", cell["tick_rows"] > 0,
                      f"ticks={cell.get('tick_rows',0)} bid_ask={cell.get('tick_has_bid_ask',False)}")

            results[f"{sym}_{tf}"] = cell

    # ── Symbol specs (current) ─────────────────────────────────────────────
    specs = {}
    for sym in INSTRUMENTS:
        si = mt5.symbol_info(sym)
        if si is None:
            specs[sym] = {"error": str(mt5.last_error())}
            continue
        specs[sym] = {
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
finally:
    mt5.shutdown()

# ── Write outputs ──────────────────────────────────────────────────────────
out_json = OUT / "mt5_probe_results.json"
out_json.write_text(
    json.dumps({"cells": results, "symbol_specs": specs}, indent=2, default=str),
    encoding="utf-8")

qlog_path = OUT / "query_log.csv"
existing = pd.read_csv(qlog_path) if qlog_path.exists() else pd.DataFrame()
new_rows = pd.DataFrame(log_rows)
pd.concat([existing, new_rows], ignore_index=True).to_csv(qlog_path, index=False)

print(f"probed {len(results)} cells; specs for {len(specs)} symbols")
print(json.dumps({k: {"rows": v.get("rows"), "first": v.get("returned_first"),
                      "last": v.get("returned_last"), "tick_rows": v.get("tick_rows"),
                      "bid_ask": v.get("tick_has_bid_ask")}
                  for k, v in results.items()}, indent=1, default=str))