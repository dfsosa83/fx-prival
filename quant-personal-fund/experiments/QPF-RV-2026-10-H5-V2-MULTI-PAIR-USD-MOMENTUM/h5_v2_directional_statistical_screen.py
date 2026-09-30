#!/usr/bin/env python
"""H5-v2 multi-pair USD momentum/volatility directional statistical screen.

Input: h5_v2_multiseries_h1_internal_snapshot.csv ONLY (hash-verified; comment skipped).
Internal ordinal clock only (NOT_UTC). Frozen H5 grid; no costs/PnL/strategy/backtest/trading.
Run once.
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

EXP = Path(__file__).resolve().parent
SNAPSHOT = EXP / "h5_v2_multiseries_h1_internal_snapshot.csv"
SNAP_SHA = "751EE1647D54E5402C762141DB8D8B547118C9825BDCBFB988F48F2DDA8B2588"
OUT = EXP / "H5_V2_DIRECTIONAL_RESULTS.json"
EXPECT_T = 48028
COLS = ["internal_index_k", "timestamp_label_internal", "eurusd_close", "gbpusd_close",
        "usdjpy_close", "usdchf_close", "usdcad_close", "audusd_close", "nzdusd_close"]
BASKET = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD"]
TARGETS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"]
BASKET_SIGN = {"EURUSD": -1.0, "GBPUSD": -1.0, "USDJPY": 1.0, "USDCHF": 1.0, "USDCAD": 1.0}
STRENGTH_SIGN = {"EURUSD": -1.0, "GBPUSD": -1.0, "USDJPY": 1.0, "USDCHF": 1.0, "USDCAD": 1.0,
                 "AUDUSD": -1.0, "NZDUSD": -1.0}
LS = [4, 8, 24, 48]
HS = [4, 8, 24]
VS = [24, 72]
KS = [3, 4]
DIRS = ["strength", "weakness"]
EMBARGO = 30


def sha256(p):
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


def write_pause(reason, detail=""):
    doc = {"result": "PAUSE_DIRECTIONAL_STATISTICAL_VIABILITY", "reason": reason, "detail": detail}
    OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(json.dumps(doc, indent=2))


def exp_sign(target, direction):
    s = STRENGTH_SIGN[target]
    return s if direction == "strength" else -s


def main() -> int:
    R = {"experiment_id": "QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM",
         "stage": "H5_V2_DIRECTIONAL_STATISTICAL_SCREEN", "seed": None,
         "internal_clock_only": True, "timestamp_labels_are_not_utc": True,
         "started": dt.datetime.now(dt.timezone.utc).isoformat()}
    actual = sha256(SNAPSHOT)
    R["snapshot_hash"] = {"expected": SNAP_SHA, "actual": actual, "hash_ok": actual == SNAP_SHA}
    if actual != SNAP_SHA:
        write_pause("snapshot hash mismatch", actual)
        return 2

    df = pd.read_csv(SNAPSHOT, comment="#")
    errs = []
    if list(df.columns) != COLS:
        errs.append(f"columns mismatch: {list(df.columns)}")
    if len(df) != EXPECT_T:
        errs.append(f"T mismatch: {len(df)}")
    if list(df.columns) == COLS and len(df) == EXPECT_T:
        if not (df["internal_index_k"].to_numpy() == np.arange(1, EXPECT_T + 1)).all():
            errs.append("internal_index_k not 1..T")
        lab = df["timestamp_label_internal"].astype(str)
        if lab.isna().any() or lab.duplicated().any() or not lab.is_monotonic_increasing:
            errs.append("labels not unique/strictly ascending")
        for c in COLS[2:]:
            v = pd.to_numeric(df[c], errors="coerce")
            if v.isna().any() or not np.isfinite(v.to_numpy(float)).all() or (v <= 0).any():
                errs.append(f"{c} invalid")
    R["input_validation"] = {"ok": not errs, "errors": errs}
    if errs:
        write_pause("input validation failed", "; ".join(errs))
        return 2

    T = len(df)
    labels = df["timestamp_label_internal"].astype(str).tolist()
    syms = {"EURUSD": "eurusd_close", "GBPUSD": "gbpusd_close", "USDJPY": "usdjpy_close",
            "USDCHF": "usdchf_close", "USDCAD": "usdcad_close", "AUDUSD": "audusd_close",
            "NZDUSD": "nzdusd_close"}
    logP = {s: np.log(df[syms[s]].to_numpy(float)) for s in syms}
    r1 = {}
    for s in syms:
        d = np.empty(T); d[0] = np.nan
        d[1:] = np.diff(logP[s])
        r1[s] = d

    n_train = int(math.floor(0.60 * T)); n_val = int(math.floor(0.20 * T)); n_sealed = T - n_train - n_val
    vs, ve = n_train + EMBARGO, n_train + n_val
    ss, te = n_train + n_val + EMBARGO, T
    R["splits"] = {"T": T, "embargo": EMBARGO,
                   "train": {"lo": 0, "hi": n_train, "n": n_train},
                   "embargo_1": [n_train, n_train + EMBARGO],
                   "validation": {"lo": vs, "hi": ve, "n": ve - vs},
                   "embargo_2": [n_train + n_val, n_train + n_val + EMBARGO],
                   "sealed": {"lo": ss, "hi": te, "n": te - ss},
                   "boundary_labels": {"val_start": labels[vs], "val_end": labels[ve - 1],
                                       "sealed_start": labels[ss], "sealed_end": labels[te - 1]},
                   "note": "feature window [t-5V, t] must not include any embargo bar -> t >= seg_start + 5V"}

    def rL(s, L):
        a = np.empty(T); a[:L] = np.nan; a[L:] = logP[s][L:] - logP[s][:-L]
        return a

    def members_for(target, treatment):
        if target in BASKET:
            return [s for s in BASKET if s != target] if treatment == "target_excluded" else list(BASKET)
        return list(BASKET)  # AUDUSD/NZDUSD: full 5-pair basket (treatments identical)

    def confirm(rlall):
        pos = np.zeros(T); neg = np.zeros(T)
        for s, sign in rlall:
            m = sign * r1_cache[s]
            pos += (m > 0).astype(float); neg += (m < 0).astype(float)
        return pos, neg

    # cache rL per (symbol,L)
    r1_cache = {}
    for L in LS:
        for s in syms:
            r1_cache[(s, L)] = rL(s, L)

    def cpairs(target, treatment, L):
        mem = members_for(target, treatment)
        return {s: BASKET_SIGN[s] * r1_cache[(s, L)] for s in mem}

    # volatility per (target,V)
    vol = {}
    for target in TARGETS:
        sig1 = r1[target]
        for V in VS:
            ss2 = np.full(T, np.nan)
            cum = np.concatenate([[0.0], np.cumsum(np.nan_to_num(sig1 ** 2))])
            for t in range(V, T):
                ss2[t] = math.sqrt(cum[t + 1] - cum[t - V] ) / math.sqrt(V)
            med = pd.Series(ss2).rolling(5 * V).median().shift(1).to_numpy()
            vol[(target, V)] = (ss2, med)

    def segment_masks(seg_start, seg_end, V, H):
        t = np.arange(T)
        valid = (t >= seg_start + 5 * V) & (t <= seg_end - 1 - H)
        return valid

    def evaluate(target, treatment, direction, L, H, V, K, seg):
        vs_, ve_ = (vs, ve) if seg == "validation" else (ss, te)
        valid = segment_masks(vs_, ve_, V, H)
        s2, med = vol[(target, V)]
        hv = np.zeros(T, dtype=bool)
        m = np.isfinite(s2) & np.isfinite(med)
        hv[m] = s2[m] > med[m]
        sample = valid & hv
        pairs = cpairs(target, treatment, L)
        pos = np.zeros(T); neg = np.zeros(T)
        for s, mvec in pairs.items():
            pos += (mvec > 0).astype(float); neg += (mvec < 0).astype(float)
        C = pos if direction == "strength" else neg
        event = sample & (C >= K)
        control = sample & (C < K)
        ns, nc = int(event.sum()), int(control.sum())
        sign = exp_sign(target, direction)
        y = np.full(T, np.nan)
        y[:T - H] = logP[target][H:] - logP[target][:-H]
        rec = {"target": target, "treatment": treatment, "direction": direction, "L": L, "H": H,
               "V": V, "K": K, "segment": seg, "n_signal": ns, "n_control": nc,
               "expected_sign": sign}
        if ns < 1 or nc < 1:
            rec.update({"testable": False, "reason": "NOT_TESTABLE_INSUFFICIENT_EVENTS",
                        "delta": None, "delta_aligned": None, "hac_p": None, "hac_t": None,
                        "hac_se": None, "aligned_signal_mean": None, "hit_rate": None,
                        "nonoverlap_aligned_diff": None, "nonoverlap_hit_rate": None,
                        "nonoverlap_n_signal": 0, "nonoverlap_n_control": 0})
            return rec
        ys = y[event]; yc = y[control]
        delta = float(np.nanmean(ys) - np.nanmean(yc))
        delta_al = sign * delta
        aligned_sig = float(np.nanmean(sign * ys))
        X = sm.add_constant(np.concatenate([np.ones(ns), np.zeros(nc)]))
        yy = np.concatenate([ys, yc])
        res = sm.OLS(yy, X).fit(cov_type="HAC", cov_kwds={"maxlags": max(0, H - 1)})
        hac_t = float(res.tvalues[1]); hac_p = float(res.pvalues[1]); hac_se = float(res.bse[1])
        hit = float(np.mean(np.sign(ys) == sign))
        idx = np.where(sample)[0]
        keep = []
        last = -10 ** 9
        for i in idx:
            if i > last:
                keep.append(i); last = i + H - 1
        keep = np.array(keep, dtype=int)
        if len(keep):
            ke = event[keep]; kc = control[keep]
            noal = None; nohit = None
            if ke.sum() and kc.sum():
                noal = float(sign * (np.nanmean(y[keep][ke]) - np.nanmean(y[keep][kc])))
                nohit = float(np.mean(np.sign(y[keep][ke]) == sign))
            rec.update({"testable": True, "delta": delta, "delta_aligned": delta_al,
                        "hac_p": hac_p, "hac_t": hac_t, "hac_se": hac_se,
                        "aligned_signal_mean": aligned_sig, "hit_rate": hit,
                        "nonoverlap_aligned_diff": noal, "nonoverlap_hit_rate": nohit,
                        "nonoverlap_n_signal": int(ke.sum()), "nonoverlap_n_control": int(kc.sum())})
        else:
            rec.update({"testable": True, "delta": delta, "delta_aligned": delta_al, "hac_p": hac_p,
                        "hac_t": hac_t, "hac_se": hac_se, "aligned_signal_mean": aligned_sig,
                        "hit_rate": hit, "nonoverlap_aligned_diff": None, "nonoverlap_hit_rate": None,
                        "nonoverlap_n_signal": 0, "nonoverlap_n_control": 0})
        return rec

    # ── validation primary grid (672) ────────────────────────────────────────
    primary = []
    for target in TARGETS:
        for L in LS:
            for H in HS:
                for V in VS:
                    for K in KS:
                        for d in DIRS:
                            primary.append(evaluate(target, "target_excluded", d, L, H, V, K, "validation"))
    R["primary_grid_total"] = len(primary)
    numeric = [r for r in primary if r.get("testable")]
    R["total_numeric_p_values"] = len(numeric)
    R["total_not_testable"] = len(primary) - len(numeric)

    # ── BH FDR q=0.10 over numeric primary validation p-values ───────────────
    order = sorted(range(len(numeric)), key=lambda i: numeric[i]["hac_p"])
    m = len(order)
    running = 1.0
    adj = {}
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        qv = numeric[i]["hac_p"] * m / rank
        running = min(running, qv)
        adj[i] = (rank, running)
    for i, r in enumerate(numeric):
        r["bh_rank"] = adj[i][0]
        r["bh_q_value"] = adj[i][1]
        r["bh_pass_010"] = bool(adj[i][1] <= 0.10)
    R["bh"] = {"method": "Benjamini-Hochberg", "fdr_q": 0.10, "m_numeric": m,
               "total_primary": len(primary), "not_testable": R["total_not_testable"]}

    # ── validation secondary (target-included) diagnostics ───────────────────
    secondary = []
    for target in TARGETS:
        for L in LS:
            for H in HS:
                for V in VS:
                    for K in KS:
                        for d in DIRS:
                            secondary.append(evaluate(target, "target_included", d, L, H, V, K, "validation"))
    R["secondary_grid_total"] = len(secondary)
    R["secondary_note"] = ("target_included is descriptive only; not in BH; for AUDUSD/NZDUSD "
                           "included==excluded (full 5-pair basket) and reported once each")

    # ── survivor rule ────────────────────────────────────────────────────────
    def by_key(t, L, H, V, K, d):
        for r in primary:
            if (r["target"] == t and r["L"] == L and r["H"] == H and r["V"] == V
                    and r["K"] == K and r["direction"] == d and r["testable"]):
                return r
        return None

    survivors = []
    reasons_none = {}
    for target in TARGETS:
        for L in LS:
            for H in HS:
                for V in VS:
                    for K in KS:
                        rs = by_key(target, L, H, V, K, "strength")
                        rw = by_key(target, L, H, V, K, "weakness")
                        if rs is None or rw is None:
                            continue
                        def ok(r):
                            return (r["n_signal"] >= 50 and r["n_control"] >= 200
                                    and (r["expected_sign"] * r["delta"] > 0)
                                    and (r["aligned_signal_mean"] > 0) and (r["delta_aligned"] > 0)
                                    and (r["hac_p"] < 0.05) and bool(r.get("bh_pass_010"))
                                    and (r["nonoverlap_aligned_diff"] is not None
                                         and r["expected_sign"] * r["nonoverlap_aligned_diff"] > 0))
                        if ok(rs) and ok(rw):
                            survivors.append({"target": target, "basket": "target_excluded", "L": L,
                                              "H": H, "V": V, "K": K,
                                              "max_bh_q": max(rs["bh_q_value"], rw["bh_q_value"]),
                                              "max_hac_p": max(rs["hac_p"], rw["hac_p"]),
                                              "min_abs_aligned_delta": min(abs(rs["delta_aligned"]), abs(rw["delta_aligned"])),
                                              "min_signal_count": min(rs["n_signal"], rw["n_signal"])})
    survivors.sort(key=lambda s: (s["max_bh_q"], s["max_hac_p"], -s["min_abs_aligned_delta"],
                                  -s["min_signal_count"], s["target"], s["L"], s["H"], s["V"], s["K"]))
    selected = survivors[:3]
    R["survivors_total"] = len(survivors)
    R["survivors"] = survivors
    R["selected_configurations"] = selected

    # ── sealed ───────────────────────────────────────────────────────────────
    if not selected:
        R["sealed"] = {"evaluated": False,
                       "reason": "no validation configuration survived; sealed intentionally not evaluated"}
        R["final_decision"] = "REJECT_DIRECTIONAL_STATISTICAL_VIABILITY"
    else:
        sealed_records = []
        overall_ok = True
        for cfg in selected:
            rs = evaluate(cfg["target"], "target_excluded", "strength", cfg["L"], cfg["H"], cfg["V"], cfg["K"], "sealed")
            rw = evaluate(cfg["target"], "target_excluded", "weakness", cfg["L"], cfg["H"], cfg["V"], cfg["K"], "sealed")
            def s_ok(r):
                return (r.get("testable") and r["n_signal"] >= 50 and r["n_control"] >= 200
                        and (r["expected_sign"] * r["delta"] > 0) and (r["aligned_signal_mean"] > 0)
                        and (r["delta_aligned"] > 0) and (r["hac_p"] < 0.05)
                        and (r["nonoverlap_aligned_diff"] is not None
                             and r["expected_sign"] * r["nonoverlap_aligned_diff"] > 0))
            ok = s_ok(rs) and s_ok(rw)
            overall_ok = overall_ok and ok
            sealed_records.append({"config": cfg, "strength": rs, "weakness": rw, "pass": ok})
        R["sealed"] = {"evaluated": True, "records": sealed_records}
        R["final_decision"] = ("APPROVE_DIRECTIONAL_STATISTICAL_VIABILITY" if overall_ok
                               else "REJECT_DIRECTIONAL_STATISTICAL_VIABILITY")

    R["primary_grid"] = primary
    R["secondary_grid"] = secondary
    R["statistical_only"] = True
    R["not_economic_or_tradable"] = True
    R["prohibition_attestation"] = {"no_costs_pnl_strategy_backtest_trading": True}
    R["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
    print(json.dumps(J({"hash_ok": True, "T": T, "splits": R["splits"],
                        "primary_total": R["primary_grid_total"], "numeric": R["total_numeric_p_values"],
                        "not_testable": R["total_not_testable"], "survivors": len(survivors),
                        "selected": [s for s in selected],
                        "sealed_evaluated": R["sealed"]["evaluated"],
                        "decision": R["final_decision"]}), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
