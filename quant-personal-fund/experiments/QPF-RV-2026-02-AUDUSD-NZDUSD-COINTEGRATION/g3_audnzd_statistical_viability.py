#!/usr/bin/env python
"""G3 statistical viability screen — QPF-RV-2026-02 AUDUSD/NZDUSD.

Input: audnzd_h1_internal_snapshot_v1.csv ONLY (hash-verified; comment skipped).
Internal clock only (NOT_UTC). Frozen design, seed 42. No costs/PnL/returns/
signals/ML/backtest/MT5/execution. Run once.
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
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen

SEED = 42
EXP = Path(__file__).resolve().parent
SNAPSHOT = EXP / "audnzd_h1_internal_snapshot_v1.csv"
SNAP_SHA = "B4F90F302C5181FBC881318910CC3904E9CB9C95CC400AF3D29FA42218E71BB2"
OUT = EXP / "G3_AUDNZD_INTERNAL_RESULTS.json"
EXPECT_T = 48029
EMBARGO = 30
ROLL_W, ROLL_EVAL = 5000, 1000
COLS = ["internal_index_k", "timestamp_label_internal", "audusd_close", "nzdusd_close"]


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
                "nobs": int(nobs), "critical_values": {k: float(v) for k, v in crit.items()},
                "n": int(len(s))}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def johansen(logE, logG):
    try:
        data = np.column_stack([np.asarray(logE, float), np.asarray(logG, float)])
        if len(data) < 30:
            return {"status": "NOT_APPLICABLE", "reason": "insufficient_obs", "n": int(len(data))}
        res = coint_johansen(data, det_order=0, k_ar_diff=1)
        trace, c95 = res.lr1, res.cvt[:, 1]
        rank = 0
        for i in range(len(trace)):
            if trace[i] > c95[i]:
                rank = i + 1
            else:
                break
        return {"status": "OK", "n": int(len(data)), "trace_stat": [float(v) for v in trace],
                "max_eig_stat": [float(v) for v in res.lr2],
                "crit_90": [float(v) for v in res.cvt[:, 0]], "crit_95": [float(v) for v in c95],
                "crit_99": [float(v) for v in res.cvt[:, 2]], "inferred_rank_5pct": int(rank)}
    except Exception as exc:
        return {"status": "NOT_APPLICABLE", "reason": f"{type(exc).__name__}: {exc}"}


def hedge_ols(logE, logG):
    res = sm.OLS(np.asarray(logE, float), sm.add_constant(np.asarray(logG, float))).fit()
    return float(res.params[0]), float(res.params[1]), float(res.rsquared)


def ar1(s):
    s = np.asarray(s, float)
    res = sm.OLS(np.diff(s), sm.add_constant(s[:-1])).fit()
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
        blocks.append({"fit_start_label": str(labels[start]), "fit_end_label": str(labels[start + W - 1]),
                       "eval_start_label": str(labels[start + W]), "alpha": a, "beta": b,
                       "adf_stat": r.get("adf_stat"), "p_value": r.get("p_value"),
                       "used_lag": r.get("used_lag"),
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
        blk = {"block": i + 1, "start_label": str(labels[lo]), "end_label": str(labels[hi - 1]),
               "n": int(hi - lo), "adf": adf(seg), "ar1": ar1(seg),
               "vr": {f"q{q}": vr_test(np.diff(seg), q) for q in (2, 4, 8, 16)}}
        blk["pass"] = bool(blk["adf"].get("p_value") is not None and blk["adf"]["p_value"] < 0.05
                           and blk["ar1"]["b"] < 0)
        out.append(blk)
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
    ci_b = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    return {"label": "stationary-bootstrap resampling of aligned AR(1) observations",
            "is_uncertainty_of_fitted_b_not_ou_simulation": True,
            "n_resamples": n, "avg_block_len": L, "seed": seed,
            "mean_ds_ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
            "ar1_b_ci95": ci_b, "ar1_b_ci_below_zero": bool(ci_b[1] < 0.0)}


def main() -> int:
    R = {"experiment_id": "QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION",
         "stage": "G3_AUDNZD_STATISTICAL_VIABILITY_SCREENING", "seed": SEED,
         "internal_clock_only": True, "timestamp_labels_are_not_utc": True,
         "started": dt.datetime.now(dt.timezone.utc).isoformat()}
    actual = sha256(SNAPSHOT)
    R["snapshot_hash"] = {"expected": SNAP_SHA, "actual": actual, "hash_ok": actual == SNAP_SHA}
    if actual != SNAP_SHA:
        R["final_decision"] = "PAUSE_STATISTICAL_VIABILITY"
        R["reason"] = "snapshot hash mismatch"
        OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
        print(json.dumps(J(R), indent=2, default=str))
        return 2

    df = pd.read_csv(SNAPSHOT, comment="#")
    errs = []
    if list(df.columns) != COLS:
        errs.append(f"columns mismatch: {list(df.columns)}")
    if len(df) != EXPECT_T:
        errs.append(f"T mismatch: {len(df)}")
    if list(df.columns) == COLS and len(df) == EXPECT_T:
        if not (df["internal_index_k"].to_numpy() == np.arange(1, EXPECT_T + 1)).all():
            errs.append("internal_index_k not exactly 1..T")
        lab = df["timestamp_label_internal"].astype(str)
        if lab.isna().any() or lab.duplicated().any() or not lab.is_monotonic_increasing:
            errs.append("labels not unique/strictly ascending")
        for c in ("audusd_close", "nzdusd_close"):
            v = pd.to_numeric(df[c], errors="coerce")
            if v.isna().any() or not all(math.isfinite(float(x)) for x in v) or (v <= 0).any():
                errs.append(f"{c} invalid")
    if errs:
        R["final_decision"] = "PAUSE_STATISTICAL_VIABILITY"
        R["reason"] = "; ".join(errs)
        OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
        print(json.dumps(J(R), indent=2, default=str))
        return 2

    T = len(df)
    labels = df["timestamp_label_internal"].astype(str).tolist()
    logA = np.log(df["audusd_close"].to_numpy(float))
    logN = np.log(df["nzdusd_close"].to_numpy(float))
    n_train = int(math.floor(0.60 * T))
    n_val = int(math.floor(0.20 * T))
    tr = (0, n_train)
    va = (n_train + EMBARGO, n_train + n_val)
    te = (n_train + n_val + EMBARGO, T)
    R["dataset"] = {"T": T,
                    "splits": {"train": {"lo": tr[0], "hi": tr[1], "n": tr[1] - tr[0]},
                               "validation": {"lo": va[0], "hi": va[1], "n": va[1] - va[0]},
                               "sealed": {"lo": te[0], "hi": te[1], "n": te[1] - te[0]}},
                    "embargo_bars": EMBARGO,
                    "boundary_labels": {"train_start": labels[0], "train_end": labels[tr[1] - 1],
                                        "val_start": labels[va[0]], "val_end": labels[va[1] - 1],
                                        "sealed_start": labels[te[0]], "sealed_end": labels[te[1] - 1]}}

    a, b, r2 = hedge_ols(logA[tr[0]:tr[1]], logN[tr[0]:tr[1]])
    R["hedge_train_ols"] = {"alpha": a, "beta": b, "r2": r2}

    def spread(seg):
        return logA[seg[0]:seg[1]] - a - b * logN[seg[0]:seg[1]]

    R["residual_adf"] = {"train": adf(spread(tr)), "validation": adf(spread(va)), "sealed": adf(spread(te))}
    R["johansen"] = {"train": johansen(logA[tr[0]:tr[1]], logN[tr[0]:tr[1]]),
                     "validation": johansen(logA[va[0]:va[1]], logN[va[0]:va[1]]),
                     "sealed": johansen(logA[te[0]:te[1]], logN[te[0]:te[1]])}

    pre_idx = list(range(tr[0], tr[1])) + list(range(va[0], va[1]))
    R["rolling_pre_sealed"] = rolling(logA[pre_idx], logN[pre_idx], [labels[i] for i in pre_idx], ROLL_W)
    R["rolling_pre_sealed_sensitivity"] = {
        "W4000": rolling(logA[pre_idx], logN[pre_idx], [labels[i] for i in pre_idx], 4000),
        "W6000": rolling(logA[pre_idx], logN[pre_idx], [labels[i] for i in pre_idx], 6000)}
    sealed_n = te[1] - te[0]
    if sealed_n >= ROLL_W + ROLL_EVAL:
        R["rolling_sealed"] = rolling(logA[te[0]:te[1]], logN[te[0]:te[1]], labels[te[0]:te[1]], ROLL_W)
    else:
        R["rolling_sealed"] = {"status": "NOT_APPLICABLE_INSUFFICIENT_BARS", "n": sealed_n}

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

    def jr_ok(j):
        return j.get("status") == "OK" and j.get("inferred_rank_5pct", 0) >= 1

    def vr_ok(seg):
        return sum(1 for v in seg.values() if v.get("classification") == "MEAN_REVERSION_COMPATIBLE") >= 2

    def sub_ok(blocks):
        return sum(1 for b in blocks if b.get("pass")) 

    checks = {
        "C1_hashes_ok": True,
        "C2_rules_followed": True,
        "C3_adf_validation_lt_05": bool(ra.get("p_value") is not None and ra["p_value"] < 0.05),
        "C3_adf_sealed_lt_05": bool(sa.get("p_value") is not None and sa["p_value"] < 0.05),
        "C4_johansen_rank_ge1": bool(jr_ok(jv) and jr_ok(js)),
        "C5_presealed_rolling_pass_ge_60": bool(pr is not None and pr >= 0.60),
        "C6_ar1_validation": bool(var["b"] < 0 and var["p_value"] < 0.05 and var["half_life_status"] == "FINITE"),
        "C6_ar1_sealed": bool(sat["b"] < 0 and sat["p_value"] < 0.05 and sat["half_life_status"] == "FINITE"),
        "C7_vr_validation_ge2": bool(vr_ok(R["variance_ratio"]["validation"])),
        "C7_vr_sealed_ge2": bool(vr_ok(R["variance_ratio"]["sealed"])),
        "C8_subperiod_validation_ge2": bool(sub_ok(R["subperiods"]["validation"]) >= 2),
        "C8_subperiod_sealed_ge2": bool(sub_ok(R["subperiods"]["sealed"]) >= 2),
        "C9_bootstrap_validation_b_ci_below0": bool(R["bootstrap"]["validation"]["ar1_b_ci_below_zero"]),
        "C9_bootstrap_sealed_b_ci_below0": bool(R["bootstrap"]["sealed"]["ar1_b_ci_below_zero"]),
        "C10_no_prohibited_activity": True}
    R["decision_checks"] = checks
    R["rolling_pass_rates"] = {"pre_sealed_primary_5000": pr,
                               "pre_sealed_4000": R["rolling_pre_sealed_sensitivity"]["W4000"]["pass_rate_5pct"],
                               "pre_sealed_6000": R["rolling_pre_sealed_sensitivity"]["W6000"]["pass_rate_5pct"],
                               "sealed_5000": R["rolling_sealed"].get("pass_rate_5pct")
                               if "pass_rate_5pct" in R["rolling_sealed"] else R["rolling_sealed"].get("status")}
    R["subperiod_pass_counts"] = {"validation": sub_ok(R["subperiods"]["validation"]),
                                  "sealed": sub_ok(R["subperiods"]["sealed"])}

    reject = [not checks["C1_hashes_ok"], not checks["C2_rules_followed"],
              not checks["C3_adf_validation_lt_05"], not checks["C3_adf_sealed_lt_05"],
              not checks["C6_ar1_validation"], not checks["C6_ar1_sealed"],
              (pr is not None and pr < 0.40),
              not checks["C7_vr_validation_ge2"], not checks["C7_vr_sealed_ge2"],
              not checks["C8_subperiod_validation_ge2"], not checks["C8_subperiod_sealed_ge2"],
              not checks["C9_bootstrap_validation_b_ci_below0"],
              not checks["C9_bootstrap_sealed_b_ci_below0"], not checks["C10_no_prohibited_activity"]]
    approve = all(checks.values())
    R["final_decision"] = ("APPROVE_STATISTICAL_VIABILITY" if approve else
                           "REJECT_STATISTICAL_VIABILITY" if any(reject) else
                           "PAUSE_STATISTICAL_VIABILITY")
    R["statistical_only"] = True
    R["not_economic_or_tradable"] = True
    R["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
    print(json.dumps(J({"T": T, "splits": R["dataset"]["splits"], "hash_ok": True,
                        "hedge": R["hedge_train_ols"], "adf": R["residual_adf"],
                        "johansen_rank": {"train": R["johansen"]["train"].get("inferred_rank_5pct"),
                                          "validation": jv.get("inferred_rank_5pct"),
                                          "sealed": js.get("inferred_rank_5pct")},
                        "rolling": R["rolling_pass_rates"], "ar1": R["ar1"],
                        "subperiod_pass_counts": R["subperiod_pass_counts"],
                        "bootstrap": {k: {"b_ci95": v["ar1_b_ci95"], "below0": v["ar1_b_ci_below_zero"]}
                                      for k, v in R["bootstrap"].items()},
                        "vr": {k: {q: v["classification"] for q, v in seg.items()}
                               for k, seg in R["variance_ratio"].items()},
                        "checks": checks, "decision": R["final_decision"]}), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
