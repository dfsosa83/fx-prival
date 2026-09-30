#!/usr/bin/env python
"""G3-R0 immutable internal-clock snapshot freeze (INTERNAL CLOCK ONLY).

Reads only the two local H1 CSVs (datetime, close), validates schema /
monotonicity / duplicates / nulls / positivity, builds the strict timestamp
intersection, excludes the final label, and writes an immutable snapshot + its
SHA256. Deterministic; no statistical calculation; no market statistics.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

EXP = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
EUR = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "EURUSD_H1.csv"
GBP = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "GBPUSD_H1.csv"
SNAP = EXP / "g3_internal_clock_snapshot_v2.csv"
SNAP_HASH = EXP / "g3_internal_clock_snapshot_v2.sha256"
FINAL_TS = "2026-09-29 19:00:00"
COMMENT = "# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; NO_COSTS; NO_TRADING_USE"
COLS = ["internal_index_k", "timestamp_label_internal", "eurusd_close", "gbpusd_close"]


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
    if df["datetime"].isna().any() or df["close"].isna().any():
        return None, f"{name}: null datetime or close"
    if df["datetime"].duplicated().any():
        return None, f"{name}: duplicate datetime labels"
    if not df["datetime"].is_monotonic_increasing:
        return None, f"{name}: datetime not strictly monotonic"
    if (pd.to_numeric(df["close"], errors="coerce") <= 0).any():
        return None, f"{name}: non-positive close"
    return df, None


def main() -> int:
    he, hg = sha256(EUR), sha256(GBP)
    de, err = load(EUR, "EURUSD")
    if err:
        return fail(err)
    dg, err = load(GBP, "GBPUSD")
    if err:
        return fail(err)

    e_set, g_set = set(de["datetime"]), set(dg["datetime"])
    unmatched_eur = sorted(e_set - g_set)
    unmatched_gbp = sorted(g_set - e_set)
    common = sorted(e_set & g_set)
    final_present = FINAL_TS in common
    common = [t for t in common if t != FINAL_TS]
    T = len(common)
    if T < 100:
        return fail("intersection too small", f"T={T}")

    e_map = dict(zip(de["datetime"], de["close"]))
    g_map = dict(zip(dg["datetime"], dg["close"]))
    rows = [(k, t, e_map[t], g_map[t]) for k, t in enumerate(common, start=1)]

    with open(SNAP, "w", encoding="utf-8", newline="") as f:
        f.write(COMMENT + "\n")
        f.write(",".join(COLS) + "\n")
        for k, t, ec, gc in rows:
            f.write(f"{k},{t},{ec},{gc}\n")

    hs = sha256(SNAP)
    SNAP_HASH.write_text(f"{hs}  {SNAP.name}\n", encoding="utf-8")

    print(json.dumps({
        "result": "SNAPSHOT_FROZEN_PENDING_G3_V2",
        "sources": {
            "eurusd": {"path": "ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv",
                       "sha256": he, "rows": int(len(de)),
                       "date_label_min": str(de["datetime"].iloc[0]),
                       "date_label_max": str(de["datetime"].iloc[-1])},
            "gbpusd": {"path": "ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv",
                       "sha256": hg, "rows": int(len(dg)),
                       "date_label_min": str(dg["datetime"].iloc[0]),
                       "date_label_max": str(dg["datetime"].iloc[-1])}},
        "schema": ["datetime", "close"],
        "monotonicity": "PASS", "duplicates": "PASS", "nulls": "PASS", "positivity": "PASS",
        "intersection_count_raw": len(e_set & g_set),
        "final_label_excluded": bool(final_present),
        "final_label": FINAL_TS,
        "unmatched_eurusd_only": len(unmatched_eur),
        "unmatched_gbpusd_only": len(unmatched_gbp),
        "T": T,
        "snapshot": {"path": SNAP.name, "columns": COLS, "rows": T,
                     "sha256": hs, "sha256_file": SNAP_HASH.name,
                     "first_label": rows[0][1], "last_label": rows[-1][1],
                     "not_utc": True}},
        indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
