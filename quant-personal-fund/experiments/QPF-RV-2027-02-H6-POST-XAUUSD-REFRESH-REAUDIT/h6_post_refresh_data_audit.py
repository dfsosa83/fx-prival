#!/usr/bin/env python
"""H6 post-XAUUSD-refresh H1 availability/integrity re-audit (read-only).

Re-checks the seven H6 H1 instruments after the XAUUSD refresh. Availability and
integrity only: no prices-derived analytics, no snapshot, no H6 screen.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
H1 = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1"
OUT = EXP / "h6_post_refresh_data_audit.json"
SYMS_FX = ["EURUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
SYMS_ALL = SYMS_FX + ["XAUUSD"]
CANON = ["datetime", "open", "high", "low", "close", "volume"]
LEGACY = ["open", "high", "low", "close", "volume", "datetime"]
THRESHOLD = "2026-09-24 18:00:00"
MINROWS = 30000
XAU_ASSERT = {"sha256": "6DB76DE379FCF0EF65E60597B1A14AC3DD5E3466E01216D7386702CB14FB7F36",
              "schema": CANON, "rows": 45809,
              "first_label": "2019-01-02 01:00:00", "final_label": "2026-09-30 14:00:00"}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def header_cols(p: Path):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return [c.strip() for c in f.readline().strip().split(",")]


def audit(sym: str):
    path = H1 / f"{sym}_H1.csv"
    rec = {"symbol": sym, "raw_path": f"ml-signal-service/data/raw/mt5/H1/{sym}_H1.csv"}
    if not path.exists():
        rec.update({"status": "H6_DATA_MISSING", "error": "file_missing"})
        return rec
    rec["sha256"] = sha256(path)
    hdr = header_cols(path)
    if hdr == CANON:
        rec["schema"] = "canonical"
    elif hdr == LEGACY:
        rec["schema"] = "legacy"
    else:
        rec.update({"schema": "unrecognized", "header": hdr,
                    "status": "BLOCKED_SCHEMA_REPAIR_REQUIRED", "error": f"unrecognized_schema:{hdr}"})
        return rec
    df = pd.read_csv(path)
    for c in ("datetime", "close"):
        if c not in df.columns:
            rec.update({"status": "H6_DATA_INVALID", "error": f"missing_column:{c}"})
            return rec
    lab = df["datetime"]
    close = pd.to_numeric(df["close"], errors="coerce")
    checks = {
        "no_null_datetime": bool(lab.notna().all()),
        "no_duplicate_datetime": bool(not lab.duplicated().any()),
        "strict_ascending": bool(lab.is_monotonic_increasing and not lab.duplicated().any()),
        "close_finite_positive": bool(close.notna().all() and (close > 0).all()
                                      and all(math.isfinite(float(x)) for x in close)),
        "at_least_30000_rows": bool(len(df) >= MINROWS),
    }
    rec.update({"rows": int(len(df)), "first_label": str(lab.iloc[0]), "final_label": str(lab.iloc[-1]),
                "validation": checks})
    if not all(checks.values()):
        if not checks["at_least_30000_rows"]:
            rec.update({"status": "H6_DATA_INSUFFICIENT_HISTORY", "error": f"rows<{MINROWS}"})
        else:
            rec.update({"status": "H6_DATA_INVALID",
                        "error": "validation_failed:" + ",".join(k for k, v in checks.items() if not v)})
        return rec
    if str(lab.iloc[-1]) < THRESHOLD:
        rec.update({"status": "H6_DATA_STALE", "error": f"final_label<{THRESHOLD}"})
        return rec
    rec["status"] = "H6_DATA_ELIGIBLE"
    return rec


def main() -> int:
    result = {"stage": "H6_POST_XAUUSD_REFRESH_DATA_REAUDIT",
              "universe": SYMS_ALL, "fx_instruments": SYMS_FX, "separate_stratum": "XAUUSD",
              "primary_multiplicity_family": "7 instruments x 3 N x 3 M x 3 H x 2 event classes = 378",
              "threshold_final_label": THRESHOLD, "min_rows": MINROWS,
              "instruments": {}}

    for sym in SYMS_ALL:
        result["instruments"][sym] = audit(sym)

    xau = result["instruments"]["XAUUSD"]
    xau_ok = (xau.get("sha256") == XAU_ASSERT["sha256"]
              and xau.get("schema") == "canonical"
              and xau.get("rows") == XAU_ASSERT["rows"]
              and xau.get("first_label") == XAU_ASSERT["first_label"]
              and xau.get("final_label") == XAU_ASSERT["final_label"]
              and xau.get("status") == "H6_DATA_ELIGIBLE")
    result["xauusd_assertion"] = {"expected": XAU_ASSERT,
                                  "passed": bool(xau_ok)}
    if not xau_ok:
        result["instruments"]["XAUUSD"]["status"] = "H6_DATA_INVALID"
        result["instruments"]["XAUUSD"]["error"] = "xauusd_specific_assertion_failed"

    fx_all = all(result["instruments"][s]["status"] == "H6_DATA_ELIGIBLE" for s in SYMS_FX)
    fx_any = any(result["instruments"][s]["status"] == "H6_DATA_ELIGIBLE" for s in SYMS_FX)
    xau_elig = result["instruments"]["XAUUSD"]["status"] == "H6_DATA_ELIGIBLE"
    if fx_all and xau_elig:
        dec = "H6_ALL_INSTRUMENTS_DATA_READY"
    elif fx_all and not xau_elig:
        dec = "H6_FX_READY_XAUUSD_BLOCKED"
    elif fx_any:
        dec = "H6_PARTIAL_DATA_READY"
    else:
        dec = "H6_DATA_AUDIT_PAUSE"
    if not xau_ok and dec in ("H6_ALL_INSTRUMENTS_DATA_READY",):
        dec = "H6_DATA_AUDIT_PAUSE"
    result["decision"] = dec
    result["no_market_statistics_calculated"] = True

    OUT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
