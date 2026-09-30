#!/usr/bin/env python
"""QPF-RV-2026-06 H5-v1 immutable multiseries H1 snapshot freeze.

Data preparation only. Reads only `datetime` + `close` from the seven mandatory
raw CSVs, validates each, builds the strict seven-way timestamp intersection,
excludes exactly the maximum common label, and writes an immutable snapshot +
its SHA256. No market statistics, costs, PnL, signals, MT5, broker, or trading.
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
SNAP = EXP / "h5_v1_multiseries_h1_internal_snapshot.csv"
SNAP_HASH = EXP / "h5_v1_multiseries_h1_internal_snapshot.sha256"
COMMENT = ("# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_7WAY_INTERSECTION; "
           "EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE")

# ordered: (symbol, lower-case column name in snapshot)
SYMS = [("EURUSD", "eurusd_close"), ("GBPUSD", "gbpusd_close"), ("USDJPY", "usdjpy_close"),
        ("USDCHF", "usdchf_close"), ("USDCAD", "usdcad_close"), ("AUDUSD", "audusd_close"),
        ("NZDUSD", "nzdusd_close")]
COLS = ["internal_index_k", "timestamp_label_internal"] + [c for _, c in SYMS]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def fail(reason: str, detail: str = "") -> int:
    sys.stderr.write(json.dumps({"result": "PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY",
                                 "reason": reason, "detail": detail}) + "\n")
    return 2


def load(path: Path, name: str):
    if not path.exists():
        return None, f"{name}: file missing"
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        return None, f"{name}: read_error:{type(exc).__name__}:{exc}"
    for c in ("datetime", "close"):
        if c not in df.columns:
            return None, f"{name}: missing required column '{c}'"
    df = df[["datetime", "close"]].copy()
    if len(df) < 2:
        return None, f"{name}: fewer than two rows"
    if df["datetime"].isna().any():
        return None, f"{name}: null datetime label"
    if df["datetime"].duplicated().any():
        return None, f"{name}: duplicate datetime label"
    if not df["datetime"].is_monotonic_increasing:
        return None, f"{name}: datetime not strictly ascending"
    close = pd.to_numeric(df["close"], errors="coerce")
    if close.isna().any():
        return None, f"{name}: non-numeric/null close"
    if not all(math.isfinite(float(v)) for v in close):
        return None, f"{name}: non-finite close"
    if (close <= 0).any():
        return None, f"{name}: non-positive close"
    return df.assign(close=close.astype(float)), None


def main() -> int:
    frames, hashes, facts, errs = {}, {}, {}, []
    for sym, _ in SYMS:
        path = H1 / f"{sym}_H1.csv"
        hashes[sym] = sha256(path) if path.exists() else None
        df, err = load(path, sym)
        if err:
            errs.append(err)
            continue
        frames[sym] = df
        facts[sym] = {"path": f"ml-signal-service/data/raw/mt5/H1/{sym}_H1.csv",
                      "sha256": hashes[sym], "rows": int(len(df)),
                      "label_min": str(df["datetime"].iloc[0]),
                      "label_max": str(df["datetime"].iloc[-1])}
    if errs:
        return fail("mandatory input validation failed", "; ".join(errs))

    sets = {sym: set(frames[sym]["datetime"]) for sym, _ in SYMS}
    common = set.intersection(*sets.values())
    common = sorted(common)
    if len(common) < 2:
        return fail("strict seven-way intersection fewer than two labels", f"n={len(common)}")
    intersection_count = len(common)
    excluded_max = common[-1]
    retained = common[:-1]
    T = len(retained)

    unmatched = {sym: len(sets[sym] - set(common)) for sym, _ in SYMS}

    maps = {sym: dict(zip(frames[sym]["datetime"], frames[sym]["close"])) for sym, _ in SYMS}
    rows = []
    for k, t in enumerate(retained, start=1):
        row = [k, t] + [maps[sym][t] for sym, _ in SYMS]
        rows.append(row)

    if len(rows) != intersection_count - 1:
        return fail("final row count != intersection-1")
    labels = [r[1] for r in rows]
    if len(set(labels)) != T or labels != sorted(labels):
        return fail("output labels not unique/strictly increasing")

    with open(SNAP, "w", encoding="utf-8", newline="") as f:
        f.write(COMMENT + "\n")
        f.write(",".join(COLS) + "\n")
        for row in rows:
            f.write(",".join(str(x) for x in row) + "\n")

    hs = sha256(SNAP)
    SNAP_HASH.write_text(f"{hs}  {SNAP.name}\n", encoding="utf-8")

    print(json.dumps({
        "result": "SNAPSHOT_FROZEN_PENDING_H5_V1_SCREEN",
        "sources": facts,
        "strict_seven_way_intersection_count": intersection_count,
        "unmatched_counts": unmatched,
        "excluded_max_common_label": str(excluded_max),
        "excluded_label_count": 1,
        "snapshot": {"path": SNAP.name, "columns": COLS, "rows": T,
                     "first_label": rows[0][1], "last_retained_label": rows[-1][1],
                     "sha256": hs, "sha256_file": SNAP_HASH.name, "not_utc": True},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
