#!/usr/bin/env python
"""QPF-RV-2026-02 AUDUSD/NZDUSD immutable internal-clock H1 snapshot freeze.

Deterministic, data-preparation only. Reads only `datetime` + `close` from the
two authorized raw CSVs, validates, builds the strict timestamp intersection,
excludes exactly the maximum common label, and writes an immutable snapshot +
its SHA256. No statistics, no costs, no trading, no MT5, no network.
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
AUD = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "AUDUSD_H1.csv"
NZD = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "NZDUSD_H1.csv"
SNAP = EXP / "audnzd_h1_internal_snapshot_v1.csv"
SNAP_HASH = EXP / "audnzd_h1_internal_snapshot_v1.sha256"
COMMENT = ("# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; "
           "EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE")
COLS = ["internal_index_k", "timestamp_label_internal", "audusd_close", "nzdusd_close"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def fail(reason: str, detail: str = "") -> int:
    sys.stderr.write(json.dumps({"result": "PAUSE_SNAPSHOT_FREEZE_FAILED",
                                 "reason": reason, "detail": detail}) + "\n")
    return 2


def load(path: Path, name: str):
    df = pd.read_csv(path)
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
    ha, hn = sha256(AUD), sha256(NZD)
    da, err = load(AUD, "AUDUSD")
    if err:
        return fail(err)
    dn, err = load(NZD, "NZDUSD")
    if err:
        return fail(err)

    fact = {
        "AUDUSD": {"path": "ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv", "sha256": ha,
                   "rows": int(len(da)), "label_min": str(da["datetime"].iloc[0]),
                   "label_max": str(da["datetime"].iloc[-1])},
        "NZDUSD": {"path": "ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv", "sha256": hn,
                   "rows": int(len(dn)), "label_min": str(dn["datetime"].iloc[0]),
                   "label_max": str(dn["datetime"].iloc[-1])},
    }

    a_set, n_set = set(da["datetime"]), set(dn["datetime"])
    unmatched_aud = sorted(a_set - n_set)
    unmatched_nzd = sorted(n_set - a_set)
    common = sorted(a_set & n_set)
    if len(common) < 2:
        return fail("strict intersection fewer than two labels", f"n={len(common)}")
    intersection_count = len(common)
    excluded_max = common[-1]
    retained = common[:-1]
    T = len(retained)

    a_map = dict(zip(da["datetime"], da["close"]))
    n_map = dict(zip(dn["datetime"], dn["close"]))
    rows = [(k, t, a_map[t], n_map[t]) for k, t in enumerate(retained, start=1)]

    with open(SNAP, "w", encoding="utf-8", newline="") as f:
        f.write(COMMENT + "\n")
        f.write(",".join(COLS) + "\n")
        for k, t, ac, nc in rows:
            f.write(f"{k},{t},{ac},{nc}\n")

    hs = sha256(SNAP)
    SNAP_HASH.write_text(f"{hs}  {SNAP.name}\n", encoding="utf-8")

    print(json.dumps({
        "result": "SNAPSHOT_FROZEN_PENDING_G3",
        "raw": fact,
        "intersection_count": intersection_count,
        "excluded_max_common_label": str(excluded_max),
        "excluded_label_count": 1,
        "unmatched_audusd_only": len(unmatched_aud),
        "unmatched_nzdusd_only": len(unmatched_nzd),
        "snapshot": {"path": SNAP.name, "columns": COLS, "rows": T,
                     "first_label": rows[0][1], "last_retained_label": rows[-1][1],
                     "sha256": hs, "sha256_file": SNAP_HASH.name,
                     "comment": COMMENT, "not_utc": True},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
