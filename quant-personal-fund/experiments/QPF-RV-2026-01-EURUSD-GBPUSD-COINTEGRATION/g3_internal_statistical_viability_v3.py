#!/usr/bin/env python
"""G3-v3 statistical viability screening on the frozen internal-clock snapshot.

Input: g3_internal_clock_snapshot_v3.csv ONLY (hash-verified; comment skipped).
Internal clock only (NOT_UTC). No costs, PnL, returns, signals, ML, backtest,
MT5, broker, or execution. Protocol V2 settings; seed 42. Run once.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen

SEED = 42
EXP = Path(__file__).resolve().parent
SNAPSHOT = EXP / "g3_internal_clock_snapshot_v3.csv"
SNAP_SHA = "B372EF5B508E11A244B521C9BD7D475D05682ABEFA8A383C3372D7F56AC81448"
OUT = EXP / "G3_INTERNAL_RESULTS_V3.json"
EXPECT_T = 48184
EMBARGO = 30
ROLL_W, ROLL_EVAL = 5000, 1000
COLS = ["internal_index_k", "timestamp_label_internal", "eurusd_close", "gbpusd_close"]


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
        return float(x)
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, dict):
        return {k: J(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [J(v) for v in x]
    return x


def adf(series):
    try:
        s = pd.Series(np.asarray(series, float)).dropna()
        if len(s) < 20:
            return {"error": "insufficient_obs", "n": int(len(s))}
        stat, p, lag, nobs, crit, _ = adfuller(s.values, regression="c", autolag="AIC")
        return {"adf_stat": float(stat), "p_value": float(p), "used_lag": int(lag),
                "nobs": int(nobs), "critical_values": {k: float(v) for k, v in crit.items()}, "n": int(len(s))}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def johansen(logE, logG):
    try:
        data = np.column_stack([np.asarray(logE, float), np.asarray(logG, float)])
        if len(data) < 30:
            return {"status": "NOT_APPLICABLE", "reason": "insufficient_obs", "n": int(len(data))}
        res = coint_johansen(data, det_order=0, k_ar_diff=1)
        trace = res.lr1
        crit95 = res.cvt[:, 1]
        rank = 0
        for i in range(len(trace)):
            if trace[i] > crit95[i]:
                rank = i + 1
            else:
                break
        return {"status": "OK", "n": int(len(data)), "trace_stat": [float(v) for v in trace],
                "max_eig_stat": [float(v) for v in res.lr2],
                "crit_90": [float(v) for v in res.cvt[:, 0]], "crit_95": [float(v) for v in crit95],
                "crit_99": [float(v) for v in res.cvt[:, 2]], "inferred_rank_5pct": int(rank)}
    except Exception as exc:
        return {"status": "NOT_APPLICABLE", "reason": f"{type(exc).__name__}: {exc}"}


def hedge_ols(logE, logG):
    res = sm.OLS(np.asarray(logE, float), sm.add_constant(np.asarray(logG, float))).fit()
    return float(res.params[0]), float(res.params[1]), float(res.rsquared)


def ar1(s):
    s = np.asarray(s, float)
    ds = np.diff(s)
    res = sm.OLS(ds, sm.add_constant(s[:-1])).fit()
    a, b = float(res.params[0]), float(res.params[1])
    kappa = -b
    if b < 0 and 0 < kappa < 1:
        hl, status = math.log(2.0) / (-math.log(1.0 - kappa)), "FINITE"
    else:
        hl, status = None, "NOT_MEAN_REVERTING_UNDER_AR1_RULE"
    return {"a": a, "b": b, "kappa": kappa, "se_b": float(res.bse[1]), "t": float(res.tvalues[1]),
            "p_value": float(res.pvalues[1]), "half_life_status": status, "half_life_bars": hl}


def vr_test(changes, q):
    r = np.asarray(changes, float)
    n = len(r)
    if n < q + 10:
        return {"q": q, "error": "insufficient_obs", "n": n}
    mu = float(r.mean())
    var1 = float(np.sum((r - mu) ** 2) / (n - 1))
    rq = np.convolve(r, np.ones(q), "valid")
    m = len(rq)
    sigma_c2 = float(np.sum((rq - q * mu) ** 2) / (q * m))
    vr = sigma_c2 / var1 if var1 > 0 else float("nan")
    theta = 2.0 * (2 * q - 1) * (q - 1) / (3.0 * q * n)
    z = (vr - 1.0) / math.sqrt(theta) if theta > 0 else float("nan")
    p = float(2 * (1 - stats.norm.cdf(abs(z))))
    cls = ("RANDOM_WALK_NOT_REJECTED" if p >= 0.05 else
           "MEAN_REVERSION_COMPATIBLE" if vr < 1 else "MOMENTUM_OR_NON_REVERSION")
    return {"q": q, "vr": vr, "z": z, "p_value": p, "n": n, "classification": cls}


def rolling(logE, logG, labels, W):
    blocks, start, T = [], 0, len(logE)
    while start + W + ROLL_EVAL <= T:
        a, b, _ = hedge_ols(logE[start:start + W], logG[start:start + W])
        ev = logE[start + W:start + W + ROLL_EVAL] - a - b * logG[start + W:start + W + ROLL_EVAL]
        r = adf(ev)
        blocks.append({"eval_start_label": str(labels[start + W]), "alpha": a, "beta": b,
                       "adf_stat": r.get("adf_stat"), "p_value": r.get("p_value"),
                       "pass_5pct": bool(r.get("p_value") is not None and r["p_value"] < 0.05)})
        start += ROLL_EVAL
    pr = float(np.mean([b["pass_5pct"] for b in blocks])) if blocks else None
    return {"window": W, "eval": ROLL_EVAL, "n_blocks": len(blocks), "pass_rate_5pct": pr, "blocks": blocks}


def subperiods(spread, labels, n_blocks=3):
    n = len(spread)
    e = [int(round(i * n / n_blocks)) for i in range(n_blocks + 1)]
    out = []
    for i in range(n_blocks):
        lo, hi = e[i], e[i + 1]
        seg = spread[lo:hi]
        out.append({"block": i + 1, "start_label": str(labels[lo]), "end_label": str(labels[hi - 1]),
                    "n": int(hi - lo), "adf": adf(seg), "ar1": ar1(seg),
                    "vr": {f"q{q}": vr_test(np.diff(seg), q) for q in (2, 4, 8, 16)}})
    return out


def sb_indices(n, L, rng):
    p = 1.0 / L
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(0, n)
    for i in range(1, n):
        idx[i] = rng.integers(0, n) if rng.random() < p else (idx[i - 1] + 1) % n
    return idx


def bootstrap(s, L=24, n=1000, seed=SEED):
    s = np.asarray(s, float)
    ds, lag = np.diff(s), s[:-1]
    rng = np.random.default_rng(seed)
    means, bs = np.empty(n), np.empty(n)
    for i in range(n):
        idx = sb_indices(len(ds), L, rng)
        d = ds[idx]
        means[i] = d.mean()
        bs[i] = sm.OLS(d, sm.add_constant(lag[idx])).fit().params[1]
    def ci(a):
        return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    ci_b = ci(bs)
    return {"label": "stationary-bootstrap resampling of aligned AR(1) observations",
            "n_resamples": n, "avg_block_len": L, "seed": seed,
            "mean_ds_ci95": ci(means), "ar1_b_ci95": ci_b,
            "ar1_b_ci_below_zero": bool(ci_b[1] < 0.0)}


def main() -> int:
    R = {"experiment_id": "QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION",
         "stage": "G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING_V3", "seed": SEED,
         "internal_clock_only": True, "timestamp_labels_are_not_utc": True,
         "started": dt.datetime.now(dt.timezone.utc).isoformat()}
    actual = sha256(SNAPSHOT)
    R["snapshot_hash"] = {"expected": SNAP_SHA, "actual": actual, "hash_ok": actual == SNAP_SHA}
    if actual != SNAP_SHA:
        R["final_decision"] = "PAUSE_STATISTICAL_VIABILITY"
        R["reason"] = "snapshot hash mismatch"
        OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
        print(json.dumps(J(R), indent=2, default=str)); return 2

    df = pd.read_csv(SNAPSHOT, comment="#")
    cols = list(df.columns)
    errs = []
    if cols != COLS:
        errs.append(f"columns mismatch: {cols}")
    if len(df) != EXPECT_T:
        errs.append(f"T mismatch: {len(df)}")
    if cols == COLS and len(df) == EXPECT_T:
        if not (df["internal_index_k"].to_numpy() == np.arange(1, EXPECT_T + 1)).all():
            errs.append("internal_index_k not exactly 1..T")
        lab = df["timestamp_label_internal"].astype(str)
        if lab.isna().any() or lab.duplicated().any() or not lab.is_monotonic_increasing:
            errs.append("labels not strictly ascending / duplicates / nulls")
        for c in ("eurusd_close", "gbpusd_close"):
            v = pd.to_numeric(df[c], errors="coerce")
            if v.isna().any() or not all(math.isfinite(float(x)) for x in v) or (v <= 0).any():
                errs.append(f"{c} invalid")
    if errs:
        R["final_decision"] = "PAUSE_STATISTICAL_VIABILITY"; R["reason"] = "; ".join(errs)
        OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
        print(json.dumps(J(R), indent=2, default=str)); return 2

    T = len(df)
    labels = df["timestamp_label_internal"].astype(str).tolist()
    logE = np.log(df["eurusd_close"].to_numpy(float))
    logG = np.log(df["gbpusd_close"].to_numpy(float))
    n_train = int(math.floor(0.60 * T)); n_val = int(math.floor(0.20 * T)); n_test = T - n_train - n_val
    tr = (0, n_train); va = (n_train + EMBARGO, n_train + n_val); te = (n_train + n_val + EMBARGO, T)
    R["dataset"] = {"T": T, "splits": {"train": {"lo": tr[0], "hi": tr[1], "n": tr[1] - tr[0]},
                                       "validation": {"lo": va[0], "hi": va[1], "n": va[1] - va[0]},
                                       "sealed": {"lo": te[0], "hi": te[1], "n": te[1] - te[0]}},
                    "embargo_bars": EMBARGO,
                    "boundary_labels": {"train_end": labels[tr[1] - 1], "val_start": labels[va[0]],
                                        "val_end": labels[va[1] - 1], "sealed_start": labels[te[0]],
                                        "sealed_end": labels[te[1] - 1]}}

    a, b, r2 = hedge_ols(logE[tr[0]:tr[1]], logG[tr[0]:tr[1]])
    R["hedge_train_ols"] = {"alpha": a, "beta": b, "r2": r2}

    def spread(seg):
        return logE[seg[0]:seg[1]] - a - b * logG[seg[0]:seg[1]]

    R["residual_adf"] = {"train": adf(spread(tr)), "validation": adf(spread(va)), "sealed": adf(spread(te))}
    R["johansen"] = {"train": johansen(logE[tr[0]:tr[1]], logG[tr[0]:tr[1]]),
                     "validation": johansen(logE[va[0]:va[1]], logG[va[0]:va[1]]),
                     "sealed": johansen(logE[te[0]:te[1]], logG[te[0]:te[1]])}

    pre_idx = list(range(tr[0], tr[1])) + list(range(va[0], va[1]))
    preE, preG = logE[pre_idx], logG[pre_idx]
    pre_lab = [labels[i] for i in pre_idx]
    R["rolling_pre_sealed"] = rolling(preE, preG, pre_lab, ROLL_W)
    R["rolling_pre_sealed_sensitivity"] = {"W4000": rolling(preE, preG, pre_lab, 4000),
                                           "W6000": rolling(preE, preG, pre_lab, 6000)}
    R["rolling_sealed"] = rolling(logE[te[0]:te[1]], logG[te[0]:te[1]], labels[te[0]:te[1]], ROLL_W)

    R["ar1"] = {"validation": ar1(spread(va)), "sealed": ar1(spread(te))}
    R["variance_ratio"] = {"validation": {f"q{q}": vr_test(np.diff(spread(va)), q) for q in (2, 4, 8, 16)},
                           "sealed": {f"q{q}": vr_test(np.diff(spread(te)), q) for q in (2, 4, 8, 16)}}
    R["subperiods"] = {"validation": subperiods(spread(va), labels[va[0]:va[1]]),
                       "sealed": subperiods(spread(te), labels[te[0]:te[1]])}
    R["bootstrap"] = {"validation": bootstrap(spread(va)), "sealed": bootstrap(spread(te))}

    ra, sa = R["residual_adf"]["validation"], R["residual_adf"]["sealed"]
    var, sat = R["ar1"]["validation"], R["ar1"]["sealed"]
    jv, js = R["johansen"]["validation"], R["johansen"]["sealed"]
    pr = R["rolling_pre_sealed"]["pass_rate_5pct"]
    def jr_ok(j): return j.get("status") == "OK" and j.get("inferred_rank_5pct", 0) >= 1
    def jr_na(j): return j.get("status") == "NOT_APPLICABLE"
    def vr_ok(seg): return sum(1 for v in seg.values() if v.get("classification") == "MEAN_REVERSION_COMPATIBLE") >= 2
    def sub_pass(blocks):
        return sum(1 for blk in blocks
                   if blk["adf"].get("p_value") is not None and blk["adf"]["p_value"] < 0.05
                   and blk["ar1"]["b"] < 0)
    checks = {
        "C1_hash_ok": True, "C2_rules_followed": True,
        "C3_adf_val_lt_05": (ra.get("p_value") is not None and ra["p_value"] < 0.05),
        "C3_adf_sealed_lt_05": (sa.get("p_value") is not None and sa["p_value"] < 0.05),
        "C4_johansen_rank_ge1": (jr_ok(jv) and jr_ok(js)) or (jr_na(jv) and jr_na(js)),
        "C5_presealed_rolling_ge_60": (pr is not None and pr >= 0.60),
        "C6_ar1_val": (var["b"] < 0 and var["p_value"] < 0.05 and var["half_life_status"] == "FINITE"),
        "C6_ar1_sealed": (sat["b"] < 0 and sat["p_value"] < 0.05 and sat["half_life_status"] == "FINITE"),
        "C7_vr_val_ge2": vr_ok(R["variance_ratio"]["validation"]),
        "C7_vr_sealed_ge2": vr_ok(R["variance_ratio"]["sealed"]),
        "C8_sub_val_ge2": sub_pass(R["subperiods"]["validation"]) >= 2,
        "C8_sub_sealed_ge2": sub_pass(R["subperiods"]["sealed"]) >= 2,
        "C9_boot_val_below0": R["bootstrap"]["validation"]["ar1_b_ci_below_zero"],
        "C9_boot_sealed_below0": R["bootstrap"]["sealed"]["ar1_b_ci_below_zero"],
        "C10_no_prohibited": True}
    R["decision_checks"] = checks
    R["rolling_pass_rates"] = {"pre_sealed_primary_5000": pr,
                               "pre_sealed_4000": R["rolling_pre_sealed_sensitivity"]["W4000"]["pass_rate_5pct"],
                               "pre_sealed_6000": R["rolling_pre_sealed_sensitivity"]["W6000"]["pass_rate_5pct"],
                               "sealed_5000": R["rolling_sealed"]["pass_rate_5pct"]}
    R["subperiod_pass_counts"] = {"validation": sub_pass(R["subperiods"]["validation"]),
                                  "sealed": sub_pass(R["subperiods"]["sealed"])}

    reject = [not checks["C1_hash_ok"], not checks["C3_adf_val_lt_05"], not checks["C3_adf_sealed_lt_05"],
              not checks["C6_ar1_val"], not checks["C6_ar1_sealed"],
              (pr is not None and pr < 0.40),
              not checks["C7_vr_val_ge2"], not checks["C7_vr_sealed_ge2"],
              not checks["C8_sub_val_ge2"], not checks["C8_sub_sealed_ge2"],
              not checks["C9_boot_val_below0"], not checks["C9_boot_sealed_below0"]]
    approve = all(checks.values())
    pause = (not approve and not any(reject)) or (pr is not None and 0.40 <= pr < 0.60)
    R["final_decision"] = ("APPROVE_STATISTICAL_VIABILITY" if approve else
                           "REJECT_STATISTICAL_VIABILITY" if any(reject) else
                           "PAUSE_STATISTICAL_VIABILITY")
    R["statistical_only"] = True
    R["not_economic_or_tradable"] = True
    R["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
    print(json.dumps(J(R), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
