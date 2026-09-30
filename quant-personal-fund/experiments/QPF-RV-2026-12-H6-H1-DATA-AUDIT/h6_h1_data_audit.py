#!/usr/bin/env python
"""H6 H1 data-availability + quality audit (read-only; acquisition only if missing).

Audits the seven H6 H1 instruments for existence, schema, integrity, coverage and
hash provenance. Downloads a MISSING instrument via the repository MT5 downloader
only when safely possible (fresh canonical file). No market statistics, no
breakout/invalidation/outcome computation, no snapshot, no PnL/costs/trading.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import math
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
H1 = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1"
DOWNLOADER = REPO / "ml-signal-service" / "steps" / "01_download" / "mt5_downloader.py"
OUT = EXP / "h6_h1_data_audit.json"
SYMS_FX = ["EURUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
SYMS_ALL = SYMS_FX + ["XAUUSD"]
CANON = ["datetime", "open", "high", "low", "close", "volume"]
LEGACY = ["open", "high", "low", "close", "volume", "datetime"]
THRESHOLD = "2026-09-24 18:00:00"
MINROWS = 30000


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def header_cols(p: Path):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return [c.strip() for c in f.readline().strip().split(",")]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def download_symbol(sym: str):
    try:
        dl = load_module("mt5_downloader", DOWNLOADER)
        cfg, settings = dl.load_configs()
    except Exception as exc:
        return False, f"downloader_load_failed:{type(exc).__name__}:{exc}"
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            if not dl.connect_mt5(settings):
                return False, "connect_mt5_failed"
            dl.download_pair(sym, "H1", settings, cfg["history"]["start_date"])
            try:
                dl.mt5.shutdown()
            except Exception:
                pass
        return True, "ml-signal-service/steps/01_download/mt5_downloader.py"
    except Exception as exc:
        return False, f"download_failed:{type(exc).__name__}:{exc}"


def audit(sym: str, existed_before: bool, downloaded: bool):
    path = H1 / f"{sym}_H1.csv"
    rec = {"symbol": sym, "expected_path": f"ml-signal-service/data/raw/mt5/H1/{sym}_H1.csv",
           "existed_before": existed_before, "downloaded_this_stage": downloaded}
    if not path.exists():
        rec.update({"status": "H6_DATA_MISSING", "error": "file_missing"})
        return rec
    rec["sha256"] = sha256(path)
    try:
        hdr = header_cols(path)
    except Exception as exc:
        rec.update({"status": "H6_DATA_INVALID", "error": f"header_read_failed:{exc}"})
        return rec
    if hdr == CANON:
        rec["schema"] = "canonical"
    elif hdr == LEGACY:
        rec["schema"] = "legacy"
    else:
        rec.update({"schema": "unrecognized", "header": hdr,
                    "status": "BLOCKED_SCHEMA_REPAIR_REQUIRED",
                    "error": f"unrecognized_schema:{hdr}"})
        return rec
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        rec.update({"status": "H6_DATA_INVALID", "error": f"read_error:{type(exc).__name__}:{exc}"})
        return rec
    for c in ("datetime", "close"):
        if c not in df.columns:
            rec.update({"status": "H6_DATA_INVALID", "error": f"missing_column:{c}"})
            return rec
    lab = df["datetime"]
    close = pd.to_numeric(df["close"], errors="coerce")
    checks = {
        "at_least_two_rows": bool(len(df) >= 2),
        "no_null_datetime": bool(lab.notna().all()),
        "no_duplicate_datetime": bool(not lab.duplicated().any()),
        "strict_ascending": bool(lab.is_monotonic_increasing and not lab.duplicated().any()),
        "close_finite_positive": bool(close.notna().all() and (close > 0).all()
                                      and all(math.isfinite(float(x)) for x in close)),
    }
    rec.update({"rows": int(len(df)), "first_label": str(lab.iloc[0]), "final_label": str(lab.iloc[-1]),
                "validation": checks})
    if not all(checks.values()):
        rec.update({"status": "H6_DATA_INVALID",
                    "error": "validation_failed:" + ",".join(k for k, v in checks.items() if not v)})
        return rec
    if len(df) < MINROWS:
        rec.update({"status": "H6_DATA_INSUFFICIENT_HISTORY", "error": f"rows<{MINROWS}"})
        return rec
    if str(lab.iloc[-1]) < THRESHOLD:
        rec.update({"status": "H6_DATA_STALE", "error": f"final_label<{THRESHOLD}"})
        return rec
    rec["status"] = "H6_DATA_ELIGIBLE"
    return rec


def main() -> int:
    result = {"stage": "H6_H1_DATA_AVAILABILITY_AUDIT",
              "universe": SYMS_ALL, "fx_instruments": SYMS_FX,
              "separate_stratum": "XAUUSD",
              "primary_multiplicity_family": "7 instruments x 3 N x 3 M x 3 H x 2 event classes = 378",
              "threshold_final_label": THRESHOLD, "min_rows": MINROWS,
              "note": "XAUUSD remains a separate snapshot/result stratum; not pooled with FX",
              "instruments": {}}

    for sym in SYMS_ALL:
        path = H1 / f"{sym}_H1.csv"
        existed = path.exists()
        downloaded = False
        rec = audit(sym, existed, downloaded)
        if rec["status"] == "H6_DATA_MISSING":
            ok, note = download_symbol(sym)
            if ok and path.exists():
                rec2 = audit(sym, existed_before=False, downloaded=True)
                rec2["download_tool"] = note
                rec = rec2
            else:
                rec["download_attempted"] = True
                rec["download_tool"] = None
                rec["error"] = note
        result["instruments"][sym] = rec

    fx_all = all(result["instruments"][s]["status"] == "H6_DATA_ELIGIBLE" for s in SYMS_FX)
    xau_ok = result["instruments"]["XAUUSD"]["status"] == "H6_DATA_ELIGIBLE"
    fx_any = any(result["instruments"][s]["status"] == "H6_DATA_ELIGIBLE" for s in SYMS_FX)
    if fx_all and xau_ok:
        dec = "H6_ALL_INSTRUMENTS_DATA_READY"
    elif fx_all and not xau_ok:
        dec = "H6_FX_READY_XAUUSD_BLOCKED"
    elif fx_any:
        dec = "H6_PARTIAL_DATA_READY"
    else:
        dec = "H6_DATA_AUDIT_PAUSE"
    result["decision"] = dec
    result["statistical_only"] = False
    result["no_market_statistics_calculated"] = True

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
