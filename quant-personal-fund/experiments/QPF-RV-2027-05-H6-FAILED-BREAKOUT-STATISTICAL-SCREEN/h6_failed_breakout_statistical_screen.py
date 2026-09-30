#!/usr/bin/env python
"""H6 failed-breakout invalidation statistical screen (single-instrument).

Reads ONLY the seven frozen H1 snapshots named in the QPF-RV-2027-03 manifest,
verifies each SHA256 before parsing, and runs the frozen H6 event study.
FX and XAUUSD are separate strata; no pooling. No PnL/costs/backtest/trading.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
import yaml

REPO = Path(__file__).resolve().parents[3]
EXP = Path(__file__).resolve().parent
FREEZE = REPO / "quant-personal-fund" / "experiments" / "QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE"
MANIFEST = FREEZE / "data_manifest_h6.yaml"
OUT = EXP / "H6_FAILED_BREAKOUT_RESULTS.json"

LS = [12, 24, 48]
MS = [2, 4, 8]
HS = [4, 8, 24]
EMBARGO = 30
FX = ["EURUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
XAU = ["XAUUSD"]
EVENT_SIGN = {"FAILED_UPWARD_BREAKOUT": -1.0, "FAILED_DOWNWARD_BREAKOUT": 1.0}


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def J(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        v = float(x)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, dict):
        return {k: J(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [J(v) for v in x]
    if isinstance(x, float):
        return None if (math.isnan(x) or math.isinf(x)) else x
    return x


def load_and_validate(sym):
    lower = sym.lower()
    path = FREEZE / "snapshots" / sym / f"{lower}_h1_internal_snapshot_v1.csv"
    cols = ["internal_index_k", "timestamp_label_internal", f"{lower}_close"]
    df = pd.read_csv(path, comment="#")
    errs = []
    if list(df.columns) != cols:
        errs.append(f"columns:{list(df.columns)}")
    else:
        if not (df["internal_index_k"].to_numpy() == np.arange(1, len(df) + 1)).all():
            errs.append("index_not_1..T")
        lab = df["timestamp_label_internal"].astype(str)
        if lab.isna().any() or lab.duplicated().any() or not lab.is_monotonic_increasing:
            errs.append("labels")
        c = pd.to_numeric(df[f"{lower}_close"], errors="coerce")
        if c.isna().any() or not np.isfinite(c.to_numpy(float)).all() or (c <= 0).any():
            errs.append("close")
    return df, errs


def rolling_bounds(close, N):
    s = pd.Series(close)
    U = s.rolling(N).max().shift(1).to_numpy()
    L = s.rolling(N).min().shift(1).to_numpy()
    return U, L


def detect_events(close, N, M, cls):
    T = len(close)
    U, L = rolling_bounds(close, N)
    out = []
    next_allowed = 0
    for t in range(T):
        if t < next_allowed:
            continue
        if cls == "FAILED_UPWARD_BREAKOUT":
            if np.isnan(U[t]) or not (close[t] > U[t]):
                continue
            boundary = U[t]
            reentry = lambda k: close[t + k] < boundary
        else:
            if np.isnan(L[t]) or not (close[t] < L[t]):
                continue
            boundary = L[t]
            reentry = lambda k: close[t + k] > boundary
        kstar = None
        for k in range(1, M + 1):
            if t + k < T and reentry(k):
                kstar = k
                break
        if kstar is not None:
            e = t + kstar
            out.append((t, e))
            next_allowed = e + 1
    return out


def excl_mask(N, events_by_class, T):
    m = np.zeros(T, dtype=bool)
    for cls, evs in events_by_class.items():
        for (t, e) in evs:
            m[t:e + 1] = True
    return m


def in_segment(t, e, M, H, seg):
    lo, hi = seg
    return t >= lo and max(t + M, e + H) <= hi - 1


def control_pool(close, N, M, H, seg, excl, event_set):
    lo, hi = seg
    T = len(close)
    idx = np.arange(T)
    es = np.zeros(T, dtype=bool)
    if event_set:
        es[np.fromiter(event_set, dtype=int)] = True
    elig = ((idx >= lo) & (idx - N >= lo) & (idx + M <= hi - 1) & (idx + H <= hi - 1)
            & (~excl) & (~es))
    return np.where(elig)[0]


def hac_test(close, ev_idx, ct_idx, H, cls):
    sign = EVENT_SIGN[cls]
    ye = np.log(close[np.array(ev_idx) + H] / close[np.array(ev_idx)])
    yc = np.log(close[np.array(ct_idx) + H] / close[np.array(ct_idx)])
    ne, nc = len(ye), len(yc)
    delta = float(ye.mean() - yc.mean())
    X = sm.add_constant(np.r_[np.ones(ne), np.zeros(nc)])
    res = sm.OLS(np.r_[ye, yc], X).fit(cov_type="HAC", cov_kwds={"maxlags": max(0, H - 1)})
    hit = float(np.mean(np.sign(ye) == sign))
    return {"event_count": ne, "control_count": nc,
            "mean_event": float(ye.mean()), "mean_control": float(yc.mean()),
            "delta": delta, "aligned_event_mean": float(sign * ye.mean()),
            "aligned_delta": float(sign * delta), "hit_rate": hit,
            "hac_se": float(res.bse[1]), "hac_t": float(res.tvalues[1]), "hac_p": float(res.pvalues[1])}


def nonoverlap(close, ev_idx, ct_idx, H, cls):
    sign = EVENT_SIGN[cls]
    combined = sorted([(i, "e") for i in ev_idx] + [(i, "c") for i in ct_idx])
    keep_e, keep_c = [], []
    last = -10 ** 9
    for i, kind in combined:
        if i > last:
            (keep_e if kind == "e" else keep_c).append(i)
            last = i + H - 1
    if not keep_e or not keep_c:
        return {"nonoverlap_event_count": len(keep_e), "nonoverlap_control_count": len(keep_c),
                "nonoverlap_aligned_delta": None, "nonoverlap_hit_rate": None}
    ye = np.log(close[np.array(keep_e) + H] / close[np.array(keep_e)])
    yc = np.log(close[np.array(keep_c) + H] / close[np.array(keep_c)])
    return {"nonoverlap_event_count": len(keep_e), "nonoverlap_control_count": len(keep_c),
            "nonoverlap_aligned_delta": float(sign * (ye.mean() - yc.mean())),
            "nonoverlap_hit_rate": float(np.mean(np.sign(ye) == sign))}


def all_events(close, N):
    return {cls: detect_events(close, N, M, cls) for M in [1] for cls in
            ["FAILED_UPWARD_BREAKOUT", "FAILED_DOWNWARD_BREAKOUT"]}


def events_for(close, N, M, cls):
    return detect_events(close, N, M, cls)


def evaluate(close, N, M, H, cls, seg, excl):
    evs = events_for(close, N, M, cls)
    seg_events = [(t, e) for (t, e) in evs if in_segment(t, e, M, H, seg)]
    ev_idx = [e for (t, e) in seg_events]
    rec = {"N": N, "M": M, "H": H, "event_class": cls}
    if not ev_idx:
        rec.update({"status": "NOT_TESTABLE_INSUFFICIENT_EVENTS_OR_CONTROLS", "p_value": None})
        return rec
    phase = {(e - seg[0]) % H for e in ev_idx}
    pool = control_pool(close, N, M, H, seg, excl, set(ev_idx))
    ct_idx = [int(i) for i in pool if (int(i) - seg[0]) % H in phase]
    if len(ct_idx) < 1:
        rec.update({"status": "NOT_TESTABLE_INSUFFICIENT_EVENTS_OR_CONTROLS", "p_value": None})
        return rec
    m = hac_test(close, ev_idx, ct_idx, H, cls)
    nz = nonoverlap(close, ev_idx, ct_idx, H, cls)
    rec.update(m); rec.update(nz); rec["control_phase_rule"] = "(i-seg_start)%H matches an event phase"
    rec["status"] = "TESTED"
    return rec


def main() -> int:
    R = {"stage": "H6_FAILED_BREAKOUT_STATISTICAL_SCREEN",
         "started": dt.datetime.now(dt.timezone.utc).isoformat(),
         "intended_fx_family": 324, "intended_xauusd_family": 54, "records": {}}
    man = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    entries = {e["symbol"]: e for e in man["instruments"]}
    integrity = {}
    valid = {"FX": [], "XAUUSD": []}
    for sym in FX + XAU:
        e = entries[sym]
        path = FREEZE / e["snapshot_path"]
        exp_hash = e["snapshot_sha256"]
        act = sha256(path) if path.exists() else None
        ok = act == exp_hash
        rec = {"symbol": sym, "snapshot_path": e["snapshot_path"], "expected_sha256": exp_hash,
               "actual_sha256": act, "hash_ok": ok}
        if ok:
            df, errs = load_and_validate(sym)
            rec["validation_errors"] = errs
            rec["rows"] = int(len(df))
            if not errs:
                rec["status"] = "OK"
                (valid["FX"] if sym in FX else valid["XAUUSD"]).append(sym)
            else:
                rec["status"] = "PAUSE_H6_" + sym + "_INPUT_INTEGRITY"
        else:
            rec["status"] = "PAUSE_H6_" + sym + "_INPUT_INTEGRITY"
        integrity[sym] = rec
    R["integrity"] = integrity

    for stratum, syms in (("FX", valid["FX"]), ("XAUUSD", valid["XAUUSD"])):
        strat = {"valid_instruments": syms,
                 "family_size": len(syms) * 3 * 3 * 3 * 2,
                 "splits": {}, "records": [], "bh": None, "survivors": [], "selected": [],
                 "sealed": {"evaluated": False}}
        data = {}
        for sym in syms:
            df, _ = load_and_validate(sym)
            close = pd.to_numeric(df[f"{sym.lower()}_close"], errors="coerce").to_numpy(float)
            T = len(close)
            nt = int(math.floor(0.60 * T)); nv = int(math.floor(0.20 * T))
            tr = (0, nt); va = (nt + EMBARGO, nt + nv); se = (nt + nv + EMBARGO, T)
            data[sym] = {"close": close, "segments": {"train": tr, "validation": va, "sealed": se}}
            strat["splits"][sym] = {"T": T, "train": tr, "validation": va, "sealed": se, "embargo": EMBARGO,
                                     "validation_n": va[1] - va[0], "sealed_n": se[1] - se[0]}
        # validation grid
        for sym in syms:
            close = data[sym]["close"]; va = data[sym]["segments"]["validation"]
            excl_by_N = {}
            for N in LS:
                evs = {cls: events_for(close, N, M, cls) for M in [1]
                       for cls in ["FAILED_UPWARD_BREAKOUT", "FAILED_DOWNWARD_BREAKOUT"]}
                # exclusion uses the event intervals for all M? use M up to 8 union
                m = np.zeros(len(close), dtype=bool)
                for cls in ["FAILED_UPWARD_BREAKOUT", "FAILED_DOWNWARD_BREAKOUT"]:
                    for M in MS:
                        for (t, e) in events_for(close, N, M, cls):
                            m[t:e + 1] = True
                excl_by_N[N] = m
            for N in LS:
                for M in MS:
                    for H in HS:
                        for cls in ["FAILED_UPWARD_BREAKOUT", "FAILED_DOWNWARD_BREAKOUT"]:
                            rec = evaluate(close, N, M, H, cls, va, excl_by_N[N])
                            rec.update({"instrument": sym, "stratum": stratum})
                            strat["records"].append(rec)
        # BH
        numeric = [r for r in strat["records"] if r.get("status") == "TESTED" and r.get("hac_p") is not None]
        order = sorted(range(len(numeric)), key=lambda i: numeric[i]["hac_p"])
        m = len(order); running = 1.0; adj = {}
        for rank in range(m, 0, -1):
            i = order[rank - 1]
            q = numeric[i]["hac_p"] * m / rank
            running = min(running, q); adj[i] = (rank, running)
        for i, r in enumerate(numeric):
            r["bh_rank"], r["bh_q_value"] = adj[i][0], adj[i][1]
        for r in strat["records"]:
            if r.get("status") != "TESTED":
                r["bh_rank"] = None; r["bh_q_value"] = None
        strat["bh"] = {"family_size": len(strat["records"]), "numeric_p_values": m,
                       "not_testable": len(strat["records"]) - m, "fdr_q": 0.10}
        # survivors
        def get(sym, N, M, H, cls):
            for r in strat["records"]:
                if (r["instrument"] == sym and r["N"] == N and r["M"] == M and r["H"] == H
                        and r["event_class"] == cls and r.get("status") == "TESTED"):
                    return r
            return None
        def ok(r):
            if r is None:
                return False
            s = EVENT_SIGN[r["event_class"]]
            return (r["event_count"] >= 30 and r["control_count"] >= 200 and s * r["delta"] > 0
                    and r["aligned_event_mean"] > 0 and r["aligned_delta"] > 0 and r["hac_p"] < 0.05
                    and r["bh_q_value"] is not None and r["bh_q_value"] <= 0.10
                    and r["nonoverlap_aligned_delta"] is not None and s * r["nonoverlap_aligned_delta"] > 0)
        survivors = []
        for sym in syms:
            for N in LS:
                for M in MS:
                    for H in HS:
                        ru = get(sym, N, M, H, "FAILED_UPWARD_BREAKOUT")
                        rd = get(sym, N, M, H, "FAILED_DOWNWARD_BREAKOUT")
                        if ok(ru) and ok(rd):
                            survivors.append({"instrument": sym, "N": N, "M": M, "H": H,
                                              "max_bh_q": max(ru["bh_q_value"], rd["bh_q_value"]),
                                              "max_p": max(ru["hac_p"], rd["hac_p"]),
                                              "min_abs_aligned": min(abs(ru["aligned_delta"]), abs(rd["aligned_delta"])),
                                              "min_events": min(ru["event_count"], rd["event_count"])})
        survivors.sort(key=lambda s: (s["max_bh_q"], s["max_p"], -s["min_abs_aligned"], -s["min_events"],
                                      s["instrument"], s["N"], s["M"], s["H"]))
        strat["survivors"] = survivors
        strat["selected"] = survivors[:3]
        # sealed
        if strat["selected"]:
            sealed = []
            for cfg in strat["selected"]:
                sym = cfg["instrument"]; close = data[sym]["close"]; se = data[sym]["segments"]["sealed"]
                excl = np.zeros(len(close), dtype=bool)
                for cls in ["FAILED_UPWARD_BREAKOUT", "FAILED_DOWNWARD_BREAKOUT"]:
                    for M in MS:
                        for (t, e) in events_for(close, cfg["N"], M, cls):
                            excl[t:e + 1] = True
                sp = {}
                for cls in ["FAILED_UPWARD_BREAKOUT", "FAILED_DOWNWARD_BREAKOUT"]:
                    r = evaluate(close, cfg["N"], cfg["M"], cfg["H"], cls, se, excl)
                    sp[cls] = r
                def sok(r):
                    if r is None or r.get("status") != "TESTED":
                        return False
                    s = EVENT_SIGN[r["event_class"]]
                    return (r["event_count"] >= 30 and r["control_count"] >= 200 and s * r["delta"] > 0
                            and r["aligned_event_mean"] > 0 and r["aligned_delta"] > 0 and r["hac_p"] < 0.05
                            and r["nonoverlap_aligned_delta"] is not None
                            and s * r["nonoverlap_aligned_delta"] > 0)
                passed = sok(sp["FAILED_UPWARD_BREAKOUT"]) and sok(sp["FAILED_DOWNWARD_BREAKOUT"])
                sealed.append({"config": cfg, "sealed": sp,
                               "result": ("APPROVE_FAILED_BREAKOUT_STATISTICAL_VIABILITY" if passed
                                          else "REJECT_FAILED_BREAKOUT_STATISTICAL_VIABILITY")})
            strat["sealed"] = {"evaluated": True, "records": sealed}
            strat["decision"] = ("APPROVE_H6_" + stratum + "_STATISTICAL_VIABILITY"
                                 if any(x["result"].startswith("APPROVE") for x in sealed)
                                 else "REJECT_H6_" + stratum + "_STATISTICAL_VIABILITY")
        else:
            strat["decision"] = ("REJECT_H6_" + stratum + "_STATISTICAL_VIABILITY" if syms
                                 else "PAUSE_H6_" + stratum + "_STATISTICAL_VIABILITY")
        R["records"][stratum] = strat

    R["final"] = {k: R["records"][k]["decision"] for k in R["records"]}
    R["prohibition_attestation"] = {"no_pnl_cost_backtest_strategy_trading": True}
    R["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
    print(json.dumps(J({"integrity": {s: R["integrity"][s]["status"] for s in R["integrity"]},
                        "FX": {k: R["records"]["FX"][k] for k in ("family_size", "survivors", "selected", "decision")},
                        "XAUUSD": {k: R["records"]["XAUUSD"][k] for k in ("family_size", "survivors", "selected", "decision")},
                        "bh": {"FX": R["records"]["FX"]["bh"], "XAUUSD": R["records"]["XAUUSD"]["bh"]},
                        "final": R["final"]}), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
