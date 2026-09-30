#!/usr/bin/env python
"""QPF-RV-2026-09 USDJPY real H1 history refresh + canonical rebuild.

Fail-closed, one-shot. Preflight-verifies the legacy USDJPY raw file, preserves an
immutable byte backup, retrieves USDJPY H1 bars read-only via the repository MT5
downloader (in memory), merges into the canonical schema with the synthetically
validated utility, and atomically replaces USDJPY_H1.csv. No other symbol is
touched. No account/execution state is queried. No statistics/PnL/trading.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import math
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
RAWDIR = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1"
USDJPY = RAWDIR / "USDJPY_H1.csv"
BACKUP = RAWDIR / "USDJPY_H1.pre_h5_refresh_20260929.csv"
DOWNLOADER = REPO / "ml-signal-service" / "steps" / "01_download" / "mt5_downloader.py"
UTILITY = REPO / "quant-personal-fund" / "tools" / "raw_data_schema_rebuild" / "safe_h1_csv_rebuild.py"

PRE_SHA = "BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC"
PRE_ROWS = 47152
PRE_FIRST = "2019-01-02 00:00:00"
PRE_LAST = "2026-07-30 14:00:00"
THRESHOLD = "2026-09-24 18:00:00"
CANON = ["datetime", "open", "high", "low", "close", "volume"]
LEGACY = ["open", "high", "low", "close", "volume", "datetime"]
NUM = ["open", "high", "low", "close", "volume"]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def header_cols(p: Path):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return [c.strip() for c in f.readline().strip().split(",")]


def pause(reason: str, detail: str = "") -> int:
    sys.stderr.write(json.dumps({"result": "PAUSE_USDJPY_REAL_REFRESH",
                                 "reason": reason, "detail": detail}) + "\n")
    return 2


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    out = {"stage": "USDJPY_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD", "read_only_mt5": True}
    if not USDJPY.exists():
        return pause("usdjpy_missing", str(USDJPY))

    # ── Step 1: preflight ────────────────────────────────────────────────────
    pre_sha = sha256(USDJPY)
    hdr = header_cols(USDJPY)
    if pre_sha != PRE_SHA:
        return pause("pre_hash_mismatch", pre_sha)
    if hdr != LEGACY:
        return pause("pre_schema_mismatch", str(hdr))
    df0 = pd.read_csv(USDJPY)
    if len(df0) != PRE_ROWS:
        return pause("pre_rowcount_mismatch", str(len(df0)))
    lab = df0["datetime"].astype(str)
    if lab.iloc[0] != PRE_FIRST or lab.iloc[-1] != PRE_LAST:
        return pause("pre_label_range_mismatch", f"{lab.iloc[0]} .. {lab.iloc[-1]}")
    if lab.isna().any() or lab.duplicated().any() or not lab.is_monotonic_increasing:
        return pause("pre_label_integrity_failed")
    for c in NUM:
        v = pd.to_numeric(df0[c], errors="coerce")
        if v.isna().any() or not all(math.isfinite(float(x)) for x in v):
            return pause(f"pre_numeric_invalid:{c}")
    if not (pd.to_numeric(df0["close"], errors="coerce") > 0).all():
        return pause("pre_close_nonpositive")
    out["preflight"] = {"sha256": pre_sha, "schema": hdr, "rows": int(len(df0)),
                        "first_label": str(lab.iloc[0]), "last_label": str(lab.iloc[-1]),
                        "validation": "PASS"}

    # ── Step 2: immutable backup ─────────────────────────────────────────────
    if BACKUP.exists():
        return pause("backup_already_exists", str(BACKUP))
    shutil.copy2(USDJPY, BACKUP)
    if sha256(BACKUP) != pre_sha:
        return pause("backup_hash_mismatch")
    (EXP / "USDJPY_H1_PRE_REBUILD_BACKUP.sha256").write_text(
        f"{pre_sha}  {BACKUP.name}\n", encoding="utf-8")
    out["backup"] = {"path": str(BACKUP.name), "sha256": pre_sha}

    # ── Step 3: read-only historical retrieval (USDJPY H1 only, in memory) ───
    try:
        dl = load_module("mt5_downloader", DOWNLOADER)
        cfg, settings = dl.load_configs()
    except Exception as exc:
        return pause("downloader_load_failed", f"{type(exc).__name__}: {exc}")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            if not dl.connect_mt5(settings):
                return pause("mt5_connect_failed")
            tf = getattr(dl.mt5, dl.MT5_TF_MAP["H1"])
            from_dt = pd.Timestamp(PRE_LAST, tz="UTC").to_pydatetime() + timedelta(hours=1)
            to_dt = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
            rates = dl.get_rates_with_retry("USDJPY", tf, from_dt, to_dt)
            try:
                dl.mt5.shutdown()
            except Exception:
                pass
    except Exception as exc:
        return pause("retrieval_failed", f"{type(exc).__name__}: {exc}")
    if rates is None or len(rates) == 0:
        return pause("no_new_rows")
    new = pd.DataFrame(rates)
    new["time"] = pd.to_datetime(new["time"], unit="s", utc=True)
    new = new.rename(columns={"time": "datetime", "tick_volume": "volume"})
    new = new[CANON].copy()
    new["datetime"] = new["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    for c in NUM:
        new[c] = pd.to_numeric(new[c], errors="coerce")
    out["retrieval"] = {"rows_retrieved": int(len(new)),
                        "first_label": str(new["datetime"].iloc[0]),
                        "last_label": str(new["datetime"].iloc[-1]),
                        "symbol": "USDJPY", "timeframe": "H1"}

    # ── Step 4: canonical full rebuild ───────────────────────────────────────
    try:
        rb = load_module("safe_h1_csv_rebuild", UTILITY)
        existing = rb.read_and_normalize(USDJPY)     # legacy -> canonical (pre-replace)
        rb.validate_canonical_frame(new)
        merged = rb.merge_existing_and_new(existing, new)
    except Exception as exc:
        return pause("rebuild_failed", f"{type(exc).__name__}: {exc}")
    added = int(len(merged) - len(existing))
    overlap = int(len(existing) + len(new) - len(merged))
    new_last = str(merged["datetime"].iloc[-1])
    if new_last <= PRE_LAST:
        return pause("no_extension_after_merge", new_last)
    try:
        res = rb.write_candidate_atomic(merged, USDJPY, backup_path=None)
    except Exception as exc:
        return pause("atomic_replace_failed", f"{type(exc).__name__}: {exc}")
    post_sha = sha256(USDJPY)
    if post_sha != res["candidate_sha256"]:
        return pause("post_replace_hash_mismatch")
    (EXP / "USDJPY_H1_POST_REBUILD.sha256").write_text(
        f"{post_sha}  {USDJPY.name}\n", encoding="utf-8")
    out["rebuild"] = {"schema": CANON, "rows": int(len(merged)), "first_label": str(merged["datetime"].iloc[0]),
                      "last_label": new_last, "sha256": post_sha, "added_labels": added,
                      "identical_overlap_rows": overlap, "atomics_replace_ok": True}

    # ── Step 5: completeness gate ────────────────────────────────────────────
    if new_last < THRESHOLD:
        out["result"] = "PAUSE_USDJPY_REAL_REFRESH"
        out["reason"] = "final_label_below_completeness_threshold"
        out["threshold"] = THRESHOLD
        print(json.dumps(out, indent=2))
        return 2
    out["result"] = "USDJPY_REAL_REFRESH_COMPLETE_PENDING_H5_V2_SNAPSHOT"
    out["completeness_threshold"] = THRESHOLD
    out["threshold_met"] = True
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
