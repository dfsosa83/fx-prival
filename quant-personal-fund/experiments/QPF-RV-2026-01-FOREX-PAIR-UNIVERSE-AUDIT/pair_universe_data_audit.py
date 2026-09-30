#!/usr/bin/env python
"""H1 data-availability audit for the FX pairs-research candidate universe.

Read-only data inspection + minimal acquisition of MISSING H1 files via the
repository's existing MT5 downloader. No statistical/market metrics, no costs,
no signals, no ML, no backtest, no trading. Standard library + pandas + hashlib
(+ the pre-existing downloader only when a file is missing).
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
OUT = EXP / "pair_universe_data_audit.json"

CANON = ["AUDUSD", "NZDUSD", "EURUSD", "USDCHF", "USDCAD", "EURGBP"]
PAIRS = [
    ("C1", "AUDUSD", "NZDUSD"),
    ("C2", "EURUSD", "USDCHF"),
    ("C3", "AUDUSD", "USDCAD"),
    ("C4", "EURGBP", "EURUSD"),
    ("C5", "NZDUSD", "USDCAD"),
]
MIN_COMMON = 30000


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def validate(path: Path):
    rec = {"resolved_path": str(path.relative_to(REPO)).replace("\\", "/"),
           "existed_before_stage": path.exists()}
    if not path.exists():
        rec["status"] = "MISSING"
        return rec, None
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        rec["status"] = "INVALID"
        rec["error"] = f"read_error:{type(exc).__name__}:{exc}"
        return rec, None
    rec["schema"] = list(df.columns)
    missing = [c for c in ("datetime", "close") if c not in df.columns]
    if missing:
        rec["status"] = "INVALID"
        rec["error"] = f"missing_required_columns:{missing}"
        return rec, None
    rec["rows"] = int(len(df))
    rec["first_label"] = str(df["datetime"].iloc[0])
    rec["last_label"] = str(df["datetime"].iloc[-1])
    rec["sha256"] = sha256(path)
    dtz = df["datetime"]
    close = pd.to_numeric(df["close"], errors="coerce")
    checks = {
        "no_nulls": bool(dtz.notna().all() and close.notna().all()),
        "no_duplicates": bool(not dtz.duplicated().any()),
        "monotonic": bool(dtz.is_monotonic_increasing),
        "finite_values": bool(close.notna().all() and all(math.isfinite(float(x)) for x in close.dropna())),
        "close_strictly_positive": bool((close > 0).all()),
    }
    rec["validation"] = checks
    ok = all(checks.values())
    rec["status"] = "AVAILABLE_VALID" if ok else "INVALID"
    if not ok:
        rec["error"] = "validation_failed:" + ",".join(k for k, v in checks.items() if not v)
        return rec, None
    return rec, df


def load_downloader():
    spec = importlib.util.spec_from_file_location("mt5_downloader", DOWNLOADER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def download_symbol(sym: str):
    """Download one MISSING symbol's H1 history via the repository downloader."""
    try:
        mod = load_downloader()
    except Exception as exc:
        return False, f"downloader_import_failed:{type(exc).__name__}:{exc}"
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            cfg, settings = mod.load_configs()
            if not mod.connect_mt5(settings):
                return False, "connect_mt5_failed"
            mod.download_pair(sym, "H1", settings, cfg["history"]["start_date"])
            try:
                mod.mt5.shutdown()
            except Exception:
                pass
        return True, "ml-signal-service/steps/01_download/mt5_downloader.py"
    except Exception as exc:
        return False, f"download_failed:{type(exc).__name__}:{exc}"


def main() -> int:
    result = {"stage": "PAIR_UNIVERSE_DATA_AVAILABILITY_AUDIT",
              "downloader": "ml-signal-service/steps/01_download/mt5_downloader.py",
              "candidate_universe": CANON, "symbols": {}, "candidates": []}

    labels = {}
    for sym in CANON:
        path = H1 / f"{sym}_H1.csv"
        rec, df = validate(path)
        rec["requested_symbol"] = sym
        rec["downloaded_this_stage"] = False
        if rec["status"] == "MISSING":
            ok, note = download_symbol(sym)
            rec["download_attempted"] = True
            rec["download_tool"] = note if ok else None
            if ok:
                rec2, df2 = validate(path)
                rec2["requested_symbol"] = sym
                rec2["existed_before_stage"] = False
                rec2["downloaded_this_stage"] = True
                rec2["download_tool"] = note
                if rec2["status"] == "AVAILABLE_VALID":
                    rec2["status"] = "DOWNLOADED_VALID"
                    rec = rec2
                    df = df2
                else:
                    rec2["source_status"] = rec2.get("status")
                    rec = rec2
                    df = None
            else:
                rec["error"] = note
                rec["download_attempted"] = True
        # store result + labels
        result["symbols"][sym] = rec
        if df is not None:
            labels[sym] = set(df["datetime"].astype(str))

    for cid, left, right in PAIRS:
        entry = {"candidate_id": cid, "ordered_symbols": [left, right]}
        lr, rr = result["symbols"][left]["status"], result["symbols"][right]["status"]
        both_valid = lr.endswith("VALID") and rr.endswith("VALID")
        entry["both_sources_valid"] = both_valid
        entry["left_label_range"] = [result["symbols"][left].get("first_label"), result["symbols"][left].get("last_label")]
        entry["right_label_range"] = [result["symbols"][right].get("first_label"), result["symbols"][right].get("last_label")]
        if not both_valid:
            entry["common_label_count"] = None
            entry["status"] = "BLOCKED_BY_DATA_QUALITY"
        else:
            L, R = labels[left], labels[right]
            inter = sorted(L & R)
            entry["common_label_count"] = len(inter)
            entry["first_common_label"] = inter[0] if inter else None
            entry["last_common_label"] = inter[-1] if inter else None
            entry["left_only_count"] = len(L - R)
            entry["right_only_count"] = len(R - L)
            entry["at_least_30000_common"] = len(inter) >= MIN_COMMON
            entry["status"] = ("ELIGIBLE_FOR_FUTURE_G3_FREEZE" if len(inter) >= MIN_COMMON
                               else "INSUFFICIENT_COMMON_HISTORY")
        result["candidates"].append(entry)

    primary = result["candidates"][0]
    result["acquisition_decision"] = ("AUDIT_COMPLETE_PRIMARY_PAIR_READY" if primary["status"] == "ELIGIBLE_FOR_FUTURE_G3_FREEZE"
                                      else "AUDIT_COMPLETE_PRIMARY_PAIR_BLOCKED")
    result["statistical_only"] = False
    result["no_market_statistics_calculated"] = True

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
