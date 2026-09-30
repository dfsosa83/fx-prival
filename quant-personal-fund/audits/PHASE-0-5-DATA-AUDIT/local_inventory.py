#!/usr/bin/env python
"""Phase 0.5 Data-Feasibility Audit — LOCAL DATA INVENTORY + COVERAGE.

LOCAL-ONLY portion. NO MT5 connection (active terminal protection: MT5 portion
STOPPED per approved safeguard #2 — an isolated read-only connection cannot be
guaranteed without disturbing the active terminal session).

Builds:
  - data_inventory.csv            (every local data file + SHA-256 + coverage)
  - instrument_timeframe_coverage.csv  (36-cell table; local-only evidence)
  - query_log.csv                 (records the MT5 stop + no queries run)
"""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
ROOT = Path(".")
OUT = Path("quant-personal-fund/audits/PHASE-0-5-DATA-AUDIT")
OUT.mkdir(parents=True, exist_ok=True)

INSTRUMENTS = [
    "XAUUSD", "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD",
    "USDCAD", "USDCHF", "USDJPY", "EURJPY",
]
TIMEFRAMES = ["M5", "M15", "M30", "H1"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ts_first_last(path: Path, time_col: str = "datetime") -> tuple:
    """Read first/last timestamp quickly."""
    try:
        df = pd.read_csv(path, usecols=[time_col], parse_dates=[time_col])
        df = df.dropna()
        if df.empty:
            return None, None, 0
        return df[time_col].min(), df[time_col].max(), len(df)
    except Exception as e:
        return None, None, f"ERROR: {e}"


# ── 1. Local file inventory ─────────────────────────────────────────────────
local_files = []
sources = {
    "mt5_h1_cache": ROOT / "ml-signal-service" / "data" / "raw" / "mt5" / "H1",
    "gold_m5": ROOT / "ml-signal-service" / "experiments" / "EXP-2026-10-GOLD-EXIT-MANAGEMENT" / "data",
    "yahoo_daily": ROOT / "quant-personal-fund" / "data" / "raw" / "yahoo" / "daily",
}

for src_name, src_dir in sources.items():
    if not src_dir.exists():
        continue
    for f in sorted(src_dir.iterdir()):
        if f.suffix not in (".csv", ".parquet"):
            continue
        try:
            digest = sha256(f)
        except Exception:
            digest = "ERROR"
        size = f.stat().st_size
        local_files.append({
            "source": src_name,
            "file_path": str(f.relative_to(ROOT)),
            "file_size_bytes": size,
            "sha256": digest,
        })

# Enrich with first/last for the csv files we know
for row in local_files:
    p = Path(row["file_path"])
    if p.suffix == ".csv":
        tcol = "datetime" if "datetime" in pd.read_csv(p, nrows=2).columns else None
        if tcol:
            first, last, n = read_ts_first_last(p, tcol)
            row["first_ts"] = str(first) if first is not None else ""
            row["last_ts"] = str(last) if last is not None else ""
            row["rows"] = n if isinstance(n, int) else ""
    elif p.suffix == ".parquet":
        try:
            df = pd.read_parquet(p)
            row["rows"] = len(df)
        except Exception:
            row["rows"] = ""

inv = pd.DataFrame(local_files)
inv.to_csv(OUT / "data_inventory.csv", index=False)
print(f"data_inventory.csv: {len(inv)} rows")

# ── 2. 36-cell instrument x timeframe coverage (LOCAL-ONLY) ─────────────────
rows = []
for inst in INSTRUMENTS:
    for tf in TIMEFRAMES:
        row = {
            "instrument": inst,
            "timeframe": tf,
            "local_file": "",
            "local_rows": "",
            "local_first_ts": "",
            "local_last_ts": "",
            "local_coverage_ratio": "",
            "maxbars_setting": "STOPPED-NOT-READ (MT5 query not run)",
            "maxbars_constrains_copyrates": "UNKNOWN (MT5 query not run)",
            "returned_start": "",
            "returned_end": "",
            "bars_returned": "",
            "source_origin": "MT5 QUERY NOT RUN — active terminal protection",
            "server_retention_verified": False,
            "bars_spread_field": "",
            "tick_data_depth": "",
            "hist_bid_ask": "UNKNOWN (MT5 query not run)",
            "expected_bars": "",
            "coverage_ratio": "",
            "expected_closed_gaps": "",
            "unexplained_missing": "",
            "no_tick_intervals": "",
            "duplicate_timestamps": "",
            "stale_bar_max_delta": "",
            "tz_convention": "UNVERIFIED (MT5 query not run)",
            "fields_available": "",
            "contract_*": "",
            "calendar_assumption": "UNRESOLVED",
            "adequacy": "NOT ASSESSED (MT5 query not run)",
            "notes": "MT5 query portion STOPPED: active terminal64 session running; isolated read-only connection cannot be guaranteed without disturbing it (safeguard #2).",
        }
        # Local evidence where available
        if tf == "H1":
            f = Path("ml-signal-service") / "data" / "raw" / "mt5" / "H1" / f"{inst}_H1.csv"
            if f.exists():
                row["local_file"] = str(f)
                try:
                    df = pd.read_csv(f, parse_dates=["datetime"]).dropna()
                    row["local_rows"] = len(df)
                    row["local_first_ts"] = str(df["datetime"].min())
                    row["local_last_ts"] = str(df["datetime"].max())
                except Exception as e:
                    row["notes"] = f"local read error: {e}"
        if inst == "XAUUSD" and tf == "M5":
            f = Path("ml-signal-service") / "experiments" / "EXP-2026-10-GOLD-EXIT-MANAGEMENT" / "data" / "xauusd_m5.csv"
            if f.exists():
                row["local_file"] = str(f)
                try:
                    df = pd.read_csv(f, parse_dates=["time"]).dropna()
                    row["local_rows"] = len(df)
                    row["local_first_ts"] = str(df["time"].min())
                    row["local_last_ts"] = str(df["time"].max())
                except Exception as e:
                    row["notes"] = f"local read error: {e}"
        rows.append(row)

cov = pd.DataFrame(rows)
cov.to_csv(OUT / "instrument_timeframe_coverage.csv", index=False)
print(f"instrument_timeframe_coverage.csv: {len(cov)} rows (36 cells)")

# ── 3. Query log ────────────────────────────────────────────────────────────
query_log = pd.DataFrame([{
    "query_id": "NONE",
    "symbol": "",
    "timeframe": "",
    "date_range": "",
    "result": "STOPPED",
    "reason": (
        "Active terminal64 (FPMarkets MT5) process detected. Per approved "
        "safeguard #2, an isolated read-only MT5 connection cannot be "
        "established without risking disturbance of the active session "
        "(MT5 Python API is single-terminal IPC; a second instance would "
        "conflict on profile/ports). No MT5 query was run."
    ),
    "timestamp": "2026-09-24",
}])
query_log.to_csv(OUT / "query_log.csv", index=False)
print("query_log.csv: 1 row (STOP record)")