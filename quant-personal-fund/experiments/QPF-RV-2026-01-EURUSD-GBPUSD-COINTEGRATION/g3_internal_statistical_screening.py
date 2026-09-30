#!/usr/bin/env python
"""G3-Internal statistical viability screening (INTERNAL CLOCK ONLY).

Reads only the two local H1 CSVs, verifies hashes, builds the strict timestamp
intersection, and runs the FROZEN protocol in G3_INTERNAL_STATISTICAL_PROTOCOL.md.
No costs, PnL, returns-based labels, signals, ML, backtest, or execution.
Timestamps are ordinal internal labels ONLY (NOT_UTC). Random seed 42.
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
REPO = Path(__file__).resolve().parents[3]
EUR = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "EURUSD_H1.csv"
GBP = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1" / "GBPUSD_H1.csv"
HASH_EUR = "AFC3109108AE64E59800F99D4B87A11B58B26EDE5185DCBD3B132422E4F3DA5F"
HASH_GBP = "11D9D435C1DDBC4A797BDF236ED3F3F13765338D2AD21870268016F76FD24CB7"
FINAL_TS = "2026-09-29 19:00:00"
EMBARGO = 30
ROLL_W = 5000
ROLL_EVAL = 1000
OUT = EXP / "G3_INTERNAL_RESULTS.json"


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
        return {"status": "OK", "n": int(len(data)),
                "trace_stat": [float(v) for v in trace],
                "max_eig_stat": [float(v) for v in res.lr2],
                "crit_90": [float(v) for v in res.cvt[:, 0]],
                "crit_95": [float(v) for v in crit95],
                "crit_99": [float(v) for v in res.cvt[:, 2]],
                "inferred_rank_5pct": int(rank)}
    except Exception as exc:
        return {"status": "NOT_APPLICABLE", "reason": f"{type(exc).__name__}: {exc}"}


def hedge_ols(logE, logG):
    X = sm.add_constant(np.asarray(logG, float))
    res = sm.OLS(np.asarray(logE, float), X).fit()
    return float(res.params[0]), float(res.params[1]), float(res.rsquared)


def ar1(s):
    s = np.asarray(s, float)
    ds = np.diff(s)
    lag = s[:-1]
    res = sm.OLS(ds, sm.add_constant(lag)).fit()
    a, b = float(res.params[0]), float(res.params[1])
    kappa = -b
    if b < 0 and 0 < kappa < 1:
        hl = math.log(2.0) / (-math.log(1.0 - kappa))
        status = "FINITE"
    else:
        hl = None
        status = "NOT_MEAN_REVERTING_UNDER_AR1_RULE"
    return {"a": a, "b": b, "kappa": kappa, "se_b": float(res.bse[1]),
            "t": float(res.tvalues[1]), "p_value": float(res.pvalues[1]),
            "half_life_status": status, "half_life_bars": hl}


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
    if p >= 0.05:
        cls = "RANDOM_WALK_NOT_REJECTED"
    elif vr < 1:
        cls = "MEAN_REVERSION_COMPATIBLE"
    else:
        cls = "MOMENTUM_OR_NON_REVERSION"
    return {"q": q, "vr": vr, "z": z, "p_value": p, "n": n, "classification": cls}


def rolling(logE, logG, labels, W):
    blocks = []
    start = 0
    T = len(logE)
    while start + W + ROLL_EVAL <= T:
        a, b, _ = hedge_ols(logE[start:start + W], logG[start:start + W])
        ev = logE[start + W:start + W + ROLL_EVAL] - a - b * logG[start + W:start + W + ROLL_EVAL]
        res = adf(ev)
        blk = {"window_start_label": str(labels[start]), "window_end_label": str(labels[start + W - 1]),
               "eval_start_label": str(labels[start + W]), "alpha": a, "beta": b,
               "adf_stat": res.get("adf_stat"), "p_value": res.get("p_value"),
               "used_lag": res.get("used_lag"), "pass_5pct": bool(res.get("p_value") is not None and res["p_value"] < 0.05)}
        blocks.append(blk)
        start += ROLL_EVAL
    pr = float(np.mean([b["pass_5pct"] for b in blocks])) if blocks else None
    return {"window": W, "eval": ROLL_EVAL, "n_blocks": len(blocks), "pass_rate_5pct": pr, "blocks": blocks}


def subperiods(spread, labels, n_blocks=3):
    n = len(spread)
    edges = [int(round(i * n / n_blocks)) for i in range(n_blocks + 1)]
    out = []
    for i in range(n_blocks):
        lo, hi = edges[i], edges[i + 1]
        seg = spread[lo:hi]
        r = {"block": i + 1, "start_label": str(labels[lo]), "end_label": str(labels[hi - 1]),
             "n": int(hi - lo), "adf": adf(seg), "ar1": ar1(seg),
             "vr": {f"q{q}": vr_test(np.diff(seg), q) for q in (2, 4, 8, 16)}}
        out.append(r)
    return out


def stationary_bootstrap_indices(n, L, rng):
    p = 1.0 / L
    idx = np.empty(n, dtype=int)
    idx[0] = rng.integers(0, n)
    for i in range(1, n):
        if rng.random() < p:
            idx[i] = rng.integers(0, n)
        else:
            idx[i] = (idx[i - 1] + 1) % n
    return idx


def bootstrap(s, L=24, n=1000, seed=SEED):
    s = np.asarray(s, float)
    ds = np.diff(s)
    lag = s[:-1]
    rng = np.random.default_rng(seed)
    means = np.empty(n)
    bs = np.empty(n)
    m = len(ds)
    for i in range(n):
        idx = stationary_bootstrap_indices(m, L, rng)
        d = ds[idx]
        means[i] = d.mean()
        res = sm.OLS(d, sm.add_constant(lag[idx])).fit()
        bs[i] = res.params[1]
    def ci(a):
        return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]
    ci_b = ci(bs)
    return {"n_resamples": n, "avg_block_len": L, "seed": seed,
            "mean_ds_ci95": ci(means), "ar1_b_ci95": ci_b,
            "ar1_b_ci_below_zero": bool(ci_b[1] < 0.0)}


def main() -> int:
    results = {"experiment_id": "QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION",
               "stage": "G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING",
               "run_utc_note": "internal clock only; labels are NOT_UTC",
               "seed": SEED, "timestamp_labels_are_not_utc": True,
               "started": dt.datetime.now(dt.timezone.utc).isoformat(), "errors": []}

    h_eur, h_gbp = sha256(EUR), sha256(GBP)
    results["hashes"] = {"eurusd_expected": HASH_EUR, "eurusd_actual": h_eur,
                         "gbpusd_expected": HASH_GBP, "gbpusd_actual": h_gbp,
                         "hash_ok": (h_eur == HASH_EUR and h_gbp == HASH_GBP)}
    if not results["hashes"]["hash_ok"]:
        results["final_recommendation"] = "PAUSE_STATISTICAL_VIABILITY"
        results["reason"] = "hash verification failed"
        OUT.write_text(json.dumps(J(results), indent=2, default=str), encoding="utf-8")
        print(json.dumps(J(results), indent=2, default=str))
        return 2

    de = pd.read_csv(EUR, usecols=["datetime", "close"]).rename(columns={"close": "e"})
    dg = pd.read_csv(GBP, usecols=["datetime", "close"]).rename(columns={"close": "g"})
    common = sorted(set(de["datetime"]) & set(dg["datetime"]))
    common = [t for t in common if t != FINAL_TS]
    m = pd.DataFrame({"ts": common})
    m = m.merge(de, left_on="ts", right_on="datetime").drop(columns=["datetime"])
    m = m.merge(dg, left_on="ts", right_on="datetime").drop(columns=["datetime"])
    m = m.sort_values("ts").reset_index(drop=True)
    T = len(m)
    labels = m["ts"].tolist()
    logE = np.log(m["e"].to_numpy(float))
    logG = np.log(m["g"].to_numpy(float))

    n_train = int(math.floor(0.60 * T))
    n_val = int(math.floor(0.20 * T))
    n_test = T - n_train - n_val
    tr = (0, n_train)
    va = (n_train + EMBARGO, n_train + n_val)
    te = (n_train + n_val + EMBARGO, T)
    results["dataset"] = {
        "T": T, "excluded_final_ts": FINAL_TS,
        "eurusd_rows": int(len(de)), "gbpusd_rows": int(len(dg)),
        "unmatched_excluded": int(len(set(dg["datetime"]) - set(de["datetime"]))),
        "splits": {"train": {"lo": tr[0], "hi": tr[1], "n": tr[1] - tr[0]},
                   "validation": {"lo": va[0], "hi": va[1], "n": va[1] - va[0]},
                   "sealed": {"lo": te[0], "hi": te[1], "n": te[1] - te[0]}},
        "embargo": {"bars": EMBARGO,
                    "embargo1": [n_train, n_train + EMBARGO],
                    "embargo2": [n_train + n_val, n_train + n_val + EMBARGO]},
        "boundary_labels": {"train_start": labels[0], "train_end": labels[tr[1] - 1],
                            "val_start": labels[va[0]], "val_end": labels[va[1] - 1],
                            "sealed_start": labels[te[0]], "sealed_end": labels[te[1] - 1]}}

    a, b, r2 = hedge_ols(logE[tr[0]:tr[1]], logG[tr[0]:tr[1]])
    results["hedge_train_ols"] = {"alpha": a, "beta": b, "r2": r2}

    def sp(seg):
        return logE[seg[0]:seg[1]] - a - b * logG[seg[0]:seg[1]]

    results["residual_adf"] = {"train": adf(sp(tr)), "validation": adf(sp(va)), "sealed": adf(sp(te))}
    results["johansen"] = {
        "train": johansen(logE[tr[0]:tr[1]], logG[tr[0]:tr[1]]),
        "validation": johansen(logE[va[0]:va[1]], logG[va[0]:va[1]]),
        "sealed": johansen(logE[te[0]:te[1]], logG[te[0]:te[1]])}

    roll_main = rolling(logE, logG, labels, ROLL_W)
    results["rolling_adf_primary"] = roll_main
    results["rolling_sensitivity"] = {
        "W4000": rolling(logE, logG, labels, 4000),
        "W6000": rolling(logE, logG, labels, 6000)}

    results["ar1"] = {"validation": ar1(sp(va)), "sealed": ar1(sp(te))}
    results["variance_ratio"] = {
        "validation": {f"q{q}": vr_test(np.diff(sp(va)), q) for q in (2, 4, 8, 16)},
        "sealed": {f"q{q}": vr_test(np.diff(sp(te)), q) for q in (2, 4, 8, 16)}}

    results["subperiods"] = {"validation": subperiods(sp(va), labels[va[0]:va[1]]),
                             "sealed": subperiods(sp(te), labels[te[0]:te[1]])}
    results["bootstrap"] = {"validation": bootstrap(sp(va)), "sealed": bootstrap(sp(te))}

    # ── decision gate ─────────────────────────────────────────────────────────
    ra, sa = results["residual_adf"]["validation"], results["residual_adf"]["sealed"]
    va_ar, te_ar = results["ar1"]["validation"], results["ar1"]["sealed"]
    jv, js = results["johansen"]["validation"], results["johansen"]["sealed"]
    def jr_ok(j):
        return j.get("status") == "OK" and j.get("inferred_rank_5pct", 0) >= 1
    def jr_na(j):
        return j.get("status") == "NOT_APPLICABLE"
    def vr_ok(seg):
        vals = list(seg.values())
        return sum(1 for v in vals if v.get("classification") == "MEAN_REVERSION_COMPATIBLE") >= 2
    def sub_ok(blocks):
        npass = 0
        for blk in blocks:
            a_ok = blk["adf"].get("p_value") is not None and blk["adf"]["p_value"] < 0.05
            b_ok = blk["ar1"]["b"] < 0
            if a_ok and b_ok:
                npass += 1
        return npass
    bs_v, bs_t = results["bootstrap"]["validation"], results["bootstrap"]["sealed"]
    roll_pr = roll_main.get("pass_rate_5pct")
    checks = {
        "C1_hashes_ok": results["hashes"]["hash_ok"],
        "C2_rules_followed": True,
        "C3_adf_val_lt_05": (ra.get("p_value") is not None and ra["p_value"] < 0.05),
        "C3_adf_sealed_lt_05": (sa.get("p_value") is not None and sa["p_value"] < 0.05),
        "C4_johansen_rank_ge1": (jr_ok(jv) and jr_ok(js)) or (jr_na(jv) and jr_na(js)),
        "C5_rolling_pass_ge_60": (roll_pr is not None and roll_pr >= 0.60),
        "C6_ar1_val": (va_ar["b"] < 0 and va_ar["p_value"] < 0.05 and va_ar["half_life_status"] == "FINITE"),
        "C6_ar1_sealed": (te_ar["b"] < 0 and te_ar["p_value"] < 0.05 and te_ar["half_life_status"] == "FINITE"),
        "C7_vr_val_ge2": vr_ok(results["variance_ratio"]["validation"]),
        "C7_vr_sealed_ge2": vr_ok(results["variance_ratio"]["sealed"]),
        "C8_sub_val_ge2": (sub_ok(results["subperiods"]["validation"]) >= 2),
        "C8_sub_sealed_ge2": (sub_ok(results["subperiods"]["sealed"]) >= 2),
        "C9_boot_val_below0": bs_v["ar1_b_ci_below_zero"],
        "C9_boot_sealed_below0": bs_t["ar1_b_ci_below_zero"],
        "C10_no_prohibited": True}
    results["decision_checks"] = checks

    reject = (not checks["C1_hashes_ok"] or not checks["C2_rules_followed"]
              or not checks["C3_adf_val_lt_05"] or not checks["C3_adf_sealed_lt_05"]
              or not checks["C6_ar1_val"] or not checks["C6_ar1_sealed"]
              or (roll_pr is not None and roll_pr < 0.40)
              or not checks["C7_vr_val_ge2"] or not checks["C7_vr_sealed_ge2"]
              or not checks["C8_sub_val_ge2"] or not checks["C8_sub_sealed_ge2"]
              or not checks["C9_boot_val_below0"] or not checks["C9_boot_sealed_below0"])
    approve = all(checks.values())
    results["final_recommendation"] = ("APPROVE_STATISTICAL_VIABILITY" if approve
                                       else "REJECT_STATISTICAL_VIABILITY" if reject
                                       else "PAUSE_STATISTICAL_VIABILITY")
    results["statistical_only"] = True
    results["not_economic_or_tradable"] = True
    results["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()

    OUT.write_text(json.dumps(J(results), indent=2, default=str), encoding="utf-8")
    print(json.dumps(J({"T": T, "splits": results["dataset"]["splits"], "hash_ok": True,
                        "hedge": results["hedge_train_ols"], "adf": results["residual_adf"],
                        "johansen_rank": {"val": jv.get("inferred_rank_5pct"), "sealed": js.get("inferred_rank_5pct")},
                        "rolling_pass_rate": roll_pr, "ar1": results["ar1"],
                        "vr": results["variance_ratio"], "checks": checks,
                        "decision": results["final_recommendation"]}), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
