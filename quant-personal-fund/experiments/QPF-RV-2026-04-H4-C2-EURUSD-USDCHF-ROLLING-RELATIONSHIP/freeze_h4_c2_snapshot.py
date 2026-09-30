#!/usr/bin/env python
"""QPF-RV-2026-04 H4-C2 EURUSD/USDCHF immutable internal-clock H1 snapshot freeze.

Data preparation only. Reads only `datetime` + `close` from the two authorized
raw CSVs, validates, builds the strict timestamp intersection, excludes exactly
the maximum common label, and writes an immutable snapshot + its SHA256.
No statistics, costs, PnL, signals, MT5, broker, network, or trading.
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
EUR = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "EURUSD_H1.csv"
CHF = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "USDCHF_H1.csv"
SNAP = EXP / "eurusd_usdchf_h1_internal_snapshot_v1.csv"
SNAP_HASH = EXP / "eurusd_usdchf_h1_internal_snapshot_v1.sha256"
COMMENT = ("# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; "
           "EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE")
COLS = ["internal_index_k", "timestamp_label_internal", "eurusd_close", "usdchf_close"]


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
    he, hc = sha256(EUR), sha256(CHF)
    de, err = load(EUR, "EURUSD")
    if err:
        return fail(err)
    dc, err = load(CHF, "USDCHF")
    if err:
        return fail(err)

    e_set, c_set = set(de["datetime"]), set(dc["datetime"])
    unmatched_eur = sorted(e_set - c_set)
    unmatched_chf = sorted(c_set - e_set)
    common = sorted(e_set & c_set)
    if len(common) < 2:
        return fail("strict intersection fewer than two labels", f"n={len(common)}")
    intersection_count = len(common)
    excluded_max = common[-1]
    retained = common[:-1]
    T = len(retained)

    e_map = dict(zip(de["datetime"], de["close"]))
    c_map = dict(zip(dc["datetime"], dc["close"]))
    rows = [(k, t, e_map[t], c_map[t]) for k, t in enumerate(retained, start=1)]

    # output integrity checks before writing
    out_labels = [r[1] for r in rows]
    if len(rows) != intersection_count - 1:
        return fail("row count != intersection-1")
    if len(set(out_labels)) != T or out_labels != sorted(out_labels):
        return fail("output labels not unique/strictly increasing")

    with open(SNAP, "w", encoding="utf-8", newline="") as f:
        f.write(COMMENT + "\n")
        f.write(",".join(COLS) + "\n")
        for k, t, ec, cc in rows:
            f.write(f"{k},{t},{ec},{cc}\n")

    hs = sha256(SNAP)
    SNAP_HASH.write_text(f"{hs}  {SNAP.name}\n", encoding="utf-8")

    print(json.dumps({
        "result": "SNAPSHOT_FROZEN_PENDING_H4_C2_SCREEN",
        "sources": {
            "EURUSD": {"path": "ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv",
                       "sha256": he, "rows": int(len(de)),
                       "label_min": str(de["datetime"].iloc[0]), "label_max": str(de["datetime"].iloc[-1])},
            "USDCHF": {"path": "ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv",
                       "sha256": hc, "rows": int(len(dc)),
                       "label_min": str(dc["datetime"].iloc[0]), "label_max": str(dc["datetime"].iloc[-1])}},
        "raw_strict_intersection_count": intersection_count,
        "excluded_max_common_label": str(excluded_max),
        "excluded_label_count": 1,
        "unmatched_eurusd_only": len(unmatched_eur),
        "unmatched_usdchf_only": len(unmatched_chf),
        "snapshot": {"path": SNAP.name, "columns": COLS, "rows": T,
                     "first_label": rows[0][1], "last_retained_label": rows[-1][1],
                     "sha256": hs, "sha256_file": SNAP_HASH.name, "not_utc": True},
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
