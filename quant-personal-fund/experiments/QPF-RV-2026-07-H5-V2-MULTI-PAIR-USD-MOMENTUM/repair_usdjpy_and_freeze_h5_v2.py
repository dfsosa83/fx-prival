#!/usr/bin/env python
"""QPF-RV-2026-07 H5-v2 USDJPY history-completeness repair + v2 snapshot freeze.

Data preparation only. Refuses to invoke the repository MT5 downloader when its
append schema is NOT compatible with the existing USDJPY raw file (which would
misalign/corrupt data). No market statistics, costs, PnL, signals, MT5 account
state, orders, or execution. Fail-closed.
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

EXP = Path(__file__).resolve().parent
REPO = Path(__file__).resolve().parents[3]
H1 = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1"
USDJPY = H1 / "USDJPY_H1.csv"
DOWNLOADER = REPO / "ml-signal-service" / "steps" / "01_download" / "mt5_downloader.py"
SNAP = EXP / "h5_v2_multiseries_h1_internal_snapshot.csv"
SNAP_HASH = EXP / "h5_v2_multiseries_h1_internal_snapshot.sha256"
COMMENT = ("# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_7WAY_INTERSECTION; "
           "EXCLUDE_MAX_COMMON_LABEL; NO_COSTS; NO_TRADING_USE")
CANONICAL_APPEND = ["datetime", "open", "high", "low", "close", "volume"]
SYMS = [("EURUSD", "eurusd_close"), ("GBPUSD", "gbpusd_close"), ("USDJPY", "usdjpy_close"),
        ("USDCHF", "usdchf_close"), ("USDCAD", "usdcad_close"), ("AUDUSD", "audusd_close"),
        ("NZDUSD", "nzdusd_close")]
COLS = ["internal_index_k", "timestamp_label_internal"] + [c for _, c in SYMS]
COMPLETENESS_THRESHOLD = "2026-09-24 18:00:00"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def header_columns(p: Path):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return [c.strip() for c in f.readline().strip().split(",")]


def validate(p: Path):
    df = pd.read_csv(p)
    for c in ("datetime", "close"):
        if c not in df.columns:
            return None, f"missing column '{c}'"
    df = df[["datetime", "close"]].copy()
    if len(df) < 2:
        return None, "fewer than two rows"
    if df["datetime"].isna().any():
        return None, "null datetime"
    if df["datetime"].duplicated().any():
        return None, "duplicate datetime"
    if not df["datetime"].is_monotonic_increasing:
        return None, "datetime not strictly ascending"
    close = pd.to_numeric(df["close"], errors="coerce")
    if close.isna().any() or not all(math.isfinite(float(v)) for v in close) or (close <= 0).any():
        return None, "invalid close"
    return df.assign(close=close.astype(float)), None


def pause(reason: str, detail: str = "") -> int:
    sys.stderr.write(json.dumps({"result": "PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY",
                                 "reason": reason, "detail": detail}) + "\n")
    return 2


def invoke_downloader_usdjpy():
    spec = importlib.util.spec_from_file_location("mt5_downloader", DOWNLOADER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        cfg, settings = mod.load_configs()
        if not mod.connect_mt5(settings):
            return False, "connect_mt5_failed"
        mod.download_pair("USDJPY", "H1", settings, cfg["history"]["start_date"])
        try:
            mod.mt5.shutdown()
        except Exception:
            pass
    return True, "ml-signal-service/steps/01_download/mt5_downloader.py"


def main() -> int:
    out = {"stage": "H5_V1B_USDJPY_HISTORY_COMPLETENESS_REPAIR", "read_only": True}
    if not USDJPY.exists():
        return pause("USDJPY raw file missing", str(USDJPY))

    old = {"sha256": sha256(USDJPY), "schema": header_columns(USDJPY), "rows": None,
           "first_label": None, "last_label": None}
    df_old, err = validate(USDJPY)
    if err:
        return pause("USDJPY pre-update validation failed", err)
    old.update(rows=int(len(df_old)), first_label=str(df_old["datetime"].iloc[0]),
               last_label=str(df_old["datetime"].iloc[-1]))
    out["usdjpy_before"] = old

    # ── SAFETY GATE: the repository downloader appends rows ordered
    #    CANONICAL_APPEND with no header for an existing file. If the existing
    #    USDJPY header differs, the append would misalign columns and corrupt
    #    the file. Refuse to invoke the downloader in that case.
    if old["schema"] != CANONICAL_APPEND:
        out["result"] = "PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY"
        out["blocker"] = ("downloader_schema_incompatible_with_existing_usdjpy_append_would_misalign")
        out["detail"] = {"existing_usdjpy_schema": old["schema"],
                         "downloader_append_schema": CANONICAL_APPEND,
                         "note": "invoking the downloader would write datetime-first rows into a "
                                 "datetime-last file; refusing to corrupt the raw source"}
        out["snapshot_created"] = False
        print(json.dumps(out, indent=2))
        return 2

    # (Reachable only if the existing schema matched the downloader's append order.)
    ok, note = invoke_downloader_usdjpy()
    if not ok:
        return pause("USDJPY download failed", note)
    df_new, err = validate(USDJPY)
    if err:
        return pause("USDJPY post-update validation failed", err)
    new = {"sha256": sha256(USDJPY), "rows": int(len(df_new)),
           "first_label": str(df_new["datetime"].iloc[0]),
           "last_label": str(df_new["datetime"].iloc[-1])}
    out["usdjpy_after"] = new
    out["extended"] = new["last_label"] > old["last_label"]
    if new["last_label"] < COMPLETENESS_THRESHOLD:
        out["result"] = "PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY"
        out["reason"] = "usdjpy_final_label_below_completeness_threshold"
        out["threshold"] = COMPLETENESS_THRESHOLD
        print(json.dumps(out, indent=2))
        return 2

    # ── build v2 snapshot ────────────────────────────────────────────────────
    frames, hashes, facts, errs = {}, {}, {}, []
    for sym, _ in SYMS:
        p = H1 / f"{sym}_H1.csv"
        hashes[sym] = sha256(p)
        df, e = validate(p)
        if e:
            errs.append(f"{sym}: {e}")
            continue
        frames[sym] = df
        facts[sym] = {"sha256": hashes[sym], "rows": int(len(df)),
                      "label_min": str(df["datetime"].iloc[0]), "label_max": str(df["datetime"].iloc[-1])}
    if errs:
        return pause("seven-source validation failed", "; ".join(errs))
    sets = {s: set(frames[s]["datetime"]) for s, _ in SYMS}
    common = sorted(set.intersection(*sets.values()))
    intersection_count = len(common)
    excluded_max = common[-1]
    retained = common[:-1]
    T = len(retained)
    unmatched = {s: len(sets[s] - set(common)) for s, _ in SYMS}
    maps = {s: dict(zip(frames[s]["datetime"], frames[s]["close"])) for s, _ in SYMS}
    with open(SNAP, "w", encoding="utf-8", newline="") as f:
        f.write(COMMENT + "\n")
        f.write(",".join(COLS) + "\n")
        for k, t in enumerate(retained, start=1):
            f.write(",".join(str(x) for x in ([k, t] + [maps[s][t] for s, _ in SYMS])) + "\n")
    hs = sha256(SNAP)
    SNAP_HASH.write_text(f"{hs}  {SNAP.name}\n", encoding="utf-8")
    out.update(result="SNAPSHOT_V2_FROZEN_PENDING_H5_V2_SCREEN", sources=facts,
               strict_seven_way_intersection_count=intersection_count, unmatched_counts=unmatched,
               excluded_max_common_label=str(excluded_max),
               snapshot={"path": SNAP.name, "columns": COLS, "rows": T,
                         "first_label": retained[0], "last_retained_label": retained[-1],
                         "sha256": hs, "sha256_file": SNAP_HASH.name, "not_utc": True})
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
