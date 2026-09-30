#!/usr/bin/env python
"""QPF-RV-2027-03 H6 single-instrument immutable H1 snapshot freeze (all seven).

Data preparation only. For each H6 instrument: verify raw schema/integrity, read
only `datetime` + `close`, build a single-instrument close-only snapshot, exclude
exactly the maximum available label, and write an immutable snapshot + SHA256.
No H6 events, no statistics, no costs/PnL, no MT5/broker, no trading.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd

EXP = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
H1 = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1"
SNAPROOT = EXP / "snapshots"
BANNER = ("# INTERNAL_CLOCK_ONLY; NOT_UTC; SINGLE_INSTRUMENT; "
          "EXCLUDE_MAX_AVAILABLE_LABEL; NO_COSTS; NO_TRADING_USE")
SYMS = [("EURUSD", "eurusd_close"), ("USDJPY", "usdjpy_close"), ("USDCHF", "usdchf_close"),
        ("USDCAD", "usdcad_close"), ("AUDUSD", "audusd_close"), ("NZDUSD", "nzdusd_close"),
        ("XAUUSD", "xauusd_close")]
CANON = ["datetime", "open", "high", "low", "close", "volume"]
LEGACY = ["open", "high", "low", "close", "volume", "datetime"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def header_cols(p: Path):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return [c.strip() for c in f.readline().strip().split(",")]


def load(path: Path, sym: str):
    if not path.exists():
        return None, "file_missing"
    df = pd.read_csv(path)
    for c in ("datetime", "close"):
        if c not in df.columns:
            return None, f"missing_column:{c}"
    df = df[["datetime", "close"]].copy()
    if len(df) < 2:
        return None, "fewer_than_two_rows"
    if df["datetime"].isna().any():
        return None, "null_datetime"
    if df["datetime"].duplicated().any():
        return None, "duplicate_datetime"
    if not df["datetime"].is_monotonic_increasing:
        return None, "not_strictly_ascending"
    close = pd.to_numeric(df["close"], errors="coerce")
    if close.isna().any() or not all(math.isfinite(float(v)) for v in close) or (close <= 0).any():
        return None, "invalid_close"
    return df.assign(close=close.astype(float)), None


def main() -> int:
    out = {"stage": "H6_SINGLE_INSTRUMENT_IMMUTABLE_SNAPSHOT_FREEZE",
           "banner": BANNER, "instruments": {}, "errors": []}
    for sym, col in SYMS:
        raw = H1 / f"{sym}_H1.csv"
        lower = sym.lower()
        rec = {"symbol": sym,
               "raw_path": f"ml-signal-service/data/raw/mt5/H1/{sym}_H1.csv"}
        hdr = header_cols(raw) if raw.exists() else []
        rec["raw_schema"] = ("canonical" if hdr == CANON else "legacy" if hdr == LEGACY else "unrecognized")
        rec["raw_sha256"] = sha256(raw) if raw.exists() else None
        df, err = load(raw, sym)
        if err:
            rec["status"] = "INVALID"; rec["error"] = err
            out["instruments"][sym] = rec; out["errors"].append(f"{sym}: {err}")
            continue
        labels = df["datetime"].astype(str).tolist()
        excluded_max = labels[-1]
        retained = labels[:-1]
        T = len(retained)
        cmap = dict(zip(labels, df["close"]))
        d = SNAPROOT / sym
        d.mkdir(parents=True, exist_ok=True)
        snap = d / f"{lower}_h1_internal_snapshot_v1.csv"
        cols = ["internal_index_k", "timestamp_label_internal", col]
        with open(snap, "w", encoding="utf-8", newline="") as f:
            f.write(BANNER + "\n")
            f.write(",".join(cols) + "\n")
            for k, t in enumerate(retained, start=1):
                f.write(f"{k},{t},{cmap[t]}\n")
        hs = sha256(snap)
        (d / f"{lower}_h1_internal_snapshot_v1.sha256").write_text(f"{hs}  {snap.name}\n", encoding="utf-8")
        rec.update({"raw_rows": int(len(df)), "excluded_max_available_label": str(excluded_max),
                    "snapshot_path": f"snapshots/{sym}/{snap.name}", "snapshot_rows": T,
                    "first_label": retained[0], "last_retained_label": retained[-1],
                    "snapshot_sha256": hs, "status": "FROZEN", "not_utc": True})
        out["instruments"][sym] = rec

    out["decision"] = ("H6_SNAPSHOTS_FROZEN_PENDING_SEPARATE_H6_SCREEN"
                       if not out["errors"] else "PAUSE_H6_SNAPSHOT_FREEZE")
    print(json.dumps(out, indent=2, default=str))
    return 0 if not out["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
