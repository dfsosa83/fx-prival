#!/usr/bin/env python
"""QPF-RV-2026-10 H5-v2 immutable multiseries H1 snapshot freeze.

Data preparation only. Reads only `datetime` + `close` from the seven mandatory
raw CSVs, validates each, asserts the USDJPY repair provenance, builds the strict
seven-way timestamp intersection, excludes exactly the maximum common label, and
writes an immutable snapshot + its SHA256. No market statistics, costs, PnL,
signals, MT5, broker, or trading.
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
SNAP = EXP / "h5_v2_multiseries_h1_internal_snapshot.csv"
SNAP_HASH = EXP / "h5_v2_multiseries_h1_internal_snapshot.sha256"
COMMENT = ("# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_7WAY_INTERSECTION; "
           "EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE")
SYMS = [("EURUSD", "eurusd_close"), ("GBPUSD", "gbpusd_close"), ("USDJPY", "usdjpy_close"),
        ("USDCHF", "usdchf_close"), ("USDCAD", "usdcad_close"), ("AUDUSD", "audusd_close"),
        ("NZDUSD", "nzdusd_close")]
COLS = ["internal_index_k", "timestamp_label_internal"] + [c for _, c in SYMS]
USDJPY_SHA = "810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858"
USDJPY_SCHEMA = ["datetime", "open", "high", "low", "close", "volume"]
USDJPY_FINAL = "2026-09-29 21:00:00"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def header_cols(p: Path):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return [c.strip() for c in f.readline().strip().split(",")]


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
    # ── USDJPY-specific integrity assertion (before anything else) ───────────
    usdjpy = H1 / "USDJPY_H1.csv"
    if not usdjpy.exists():
        return fail("usdjpy_missing")
    if sha256(usdjpy) != USDJPY_SHA:
        return fail("usdjpy_hash_assertion_failed", sha256(usdjpy))
    if header_cols(usdjpy) != USDJPY_SCHEMA:
        return fail("usdjpy_schema_assertion_failed", str(header_cols(usdjpy)))
    dj, err = load(usdjpy, "USDJPY")
    if err:
        return fail(err)
    if str(dj["datetime"].iloc[-1]) != USDJPY_FINAL:
        return fail("usdjpy_final_label_assertion_failed", str(dj["datetime"].iloc[-1]))

    frames, hashes, facts, errs = {}, {}, {}, []
    for sym, _ in SYMS:
        p = H1 / f"{sym}_H1.csv"
        hashes[sym] = sha256(p) if p.exists() else None
        df, e = load(p, sym)
        if e:
            errs.append(e)
            continue
        frames[sym] = df
        facts[sym] = {"path": f"ml-signal-service/data/raw/mt5/H1/{sym}_H1.csv",
                      "sha256": hashes[sym], "rows": int(len(df)),
                      "label_min": str(df["datetime"].iloc[0]),
                      "label_max": str(df["datetime"].iloc[-1])}
    if errs:
        return fail("mandatory input validation failed", "; ".join(errs))

    sets = {s: set(frames[s]["datetime"]) for s, _ in SYMS}
    common = sorted(set.intersection(*sets.values()))
    if len(common) < 2:
        return fail("strict seven-way intersection fewer than two labels", f"n={len(common)}")
    intersection_count = len(common)
    excluded_max = common[-1]
    retained = common[:-1]
    T = len(retained)
    unmatched = {s: len(sets[s] - set(common)) for s, _ in SYMS}

    maps = {s: dict(zip(frames[s]["datetime"], frames[s]["close"])) for s, _ in SYMS}
    rows = []
    for k, t in enumerate(retained, start=1):
        rows.append([k, t] + [maps[s][t] for s, _ in SYMS])

    if len(rows) != intersection_count - 1:
        return fail("row count != intersection-1")
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
        "result": "SNAPSHOT_V2_FROZEN_PENDING_H5_V2_SCREEN",
        "sources": facts,
        "usdjpy_assertion": {"sha256_ok": True, "schema_ok": True, "final_label_ok": True},
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
