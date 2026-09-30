#!/usr/bin/env python
"""H4-C2 rolling-relationship statistical viability screen (EURUSD/USDCHF).

Input: eurusd_usdchf_h1_internal_snapshot_v1.csv ONLY (hash-verified; comment skipped).
Internal ordinal clock only (NOT_UTC). Frozen H4 protocol; seed 42.
No costs, PnL, returns, signals, ML, backtest, MT5, broker, or execution. Run once.
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
from statsmodels.tsa.stattools import adfuller

SEED = 42
EXP = Path(__file__).resolve().parent
SNAPSHOT = EXP / "eurusd_usdchf_h1_internal_snapshot_v1.csv"
SNAP_SHA = "67590790F8BF0E20A707792D8DE85077C6D1067BD45035B05744D5D235E1DBF6"
OUT = EXP / "H4_C2_ROLLING_RESULTS.json"
EXPECT_T = 48185
EMBARGO = 30
W_LIST = [1000, 2000, 5000]
E = 1000
COLS = ["internal_index_k", "timestamp_label_internal", "eurusd_close", "usdchf_close"]


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
                "nobs": int(nobs), "n": int(len(s)),
                "critical_values": {k: float(v) for k, v in crit.items()}}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def ar1(series):
    s = np.asarray(series, float)
    if len(s) < 20:
        return {"error": "insufficient_obs"}
    res = sm.OLS(np.diff(s), sm.add_constant(s[:-1])).fit()
    a, b = float(res.params[0]), float(res.params[1])
    kappa = -b
    if b < 0 and 0 < kappa < 1:
        hl, status = math.log(2.0) / (-math.log(1.0 - kappa)), "FINITE"
    else:
        hl, status = None, "NOT_MEAN_REVERTING_UNDER_AR1_RULE"
    return {"a": a, "b": b, "kappa": kappa, "se_b": float(res.bse[1]),
            "t": float(res.tvalues[1]), "p_value": float(res.pvalues[1]),
            "half_life_status": status, "half_life_bars": hl}


def fit_ols(x, y):
    res = sm.OLS(np.asarray(x, float), sm.add_constant(np.asarray(y, float))).fit()
    return float(res.params[0]), float(res.params[1])


def elig_reasons(adf_r, ar1_r):
    r = []
    if not (adf_r.get("p_value") is not None and adf_r["p_value"] < 0.05):
        r.append("adf_fit_p_ge_05")
    if not (ar1_r.get("b") is not None and ar1_r["b"] < 0):
        r.append("b_not_negative")
    if not (ar1_r.get("p_value") is not None and ar1_r["p_value"] < 0.05):
        r.append("ar1_fit_p_ge_05")
    if ar1_r.get("half_life_status") != "FINITE":
        r.append("half_life_not_finite")
    return r


def pass_reasons(adf_r, ar1_r):
    return elig_reasons(adf_r, ar1_r)


def evaluate_w(x, y, labels, seg_start, seg_end, W):
    blocks = []
    s = seg_start + W
    while s + E <= seg_end:
        fit_lo, fit_hi = s - W, s
        fut_hi = s + E
        alpha, beta = fit_ols(x[fit_lo:fit_hi], y[fit_lo:fit_hi])
        rf = x[fit_lo:fit_hi] - alpha - beta * y[fit_lo:fit_hi]
        a_fit, r1_fit = adf(rf), ar1(rf)
        reasons = elig_reasons(a_fit, r1_fit)
        eligible = len(reasons) == 0
        rec = {"segment": "validation" if seg_start < 30000 else "sealed", "W": W, "E": E,
               "fit_start_index": int(fit_lo), "fit_end_index": int(fit_hi - 1),
               "fit_start_label": str(labels[fit_lo]), "fit_end_label": str(labels[fit_hi - 1]),
               "eval_start_index": int(s), "eval_end_index": int(fut_hi - 1),
               "eval_start_label": str(labels[s]), "eval_end_label": str(labels[fut_hi - 1]),
               "alpha": alpha, "beta": beta,
               "in_window_adf": a_fit, "in_window_ar1": r1_fit,
               "historical_eligible": eligible, "eligibility_failure_reasons": reasons,
               "future": None}
        if eligible:
            rfut = x[s:fut_hi] - alpha - beta * y[s:fut_hi]
            a_fut, r1_fut = adf(rfut), ar1(rfut)
            freasons = pass_reasons(a_fut, r1_fut)
            rec["future"] = {"future_adf": a_fut, "future_ar1": r1_fut,
                             "future_pass": len(freasons) == 0,
                             "future_failure_reasons": freasons}
        blocks.append(rec)
        s += E
    complete = len(blocks)
    eligible_n = sum(1 for b in blocks if b["historical_eligible"])
    passes = sum(1 for b in blocks if b["future"] and b["future"]["future_pass"])
    summary = {"W": W, "complete_blocks": complete, "eligible_blocks": eligible_n,
               "future_passes": passes,
               "eligibility_rate": (eligible_n / complete) if complete else None,
               "future_pass_rate": (passes / eligible_n) if eligible_n else None,
               "not_eligible_for_selection": eligible_n < 3}
    return blocks, summary


def main() -> int:
    R = {"experiment_id": "QPF-RV-2026-04-H4-C2-EURUSD-USDCHF-ROLLING-RELATIONSHIP",
         "stage": "H4_C2_ROLLING_RELATIONSHIP_SCREEN", "seed": SEED,
         "internal_clock_only": True, "timestamp_labels_are_not_utc": True,
         "started": dt.datetime.now(dt.timezone.utc).isoformat()}
    actual = sha256(SNAPSHOT)
    R["snapshot_hash"] = {"expected": SNAP_SHA, "actual": actual, "hash_ok": actual == SNAP_SHA}
    if actual != SNAP_SHA:
        R["final_decision"] = "PAUSE_ROLLING_STATISTICAL_VIABILITY"
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
            errs.append("internal_index_k not 1..T")
        lab = df["timestamp_label_internal"].astype(str)
        if lab.isna().any() or lab.duplicated().any() or not lab.is_monotonic_increasing:
            errs.append("labels not unique/strictly ascending")
        for c in ("eurusd_close", "usdchf_close"):
            v = pd.to_numeric(df[c], errors="coerce")
            if v.isna().any() or not all(math.isfinite(float(z)) for z in v) or (v <= 0).any():
                errs.append(f"{c} invalid")
    R["input_validation"] = {"ok": not errs, "errors": errs}
    if errs:
        R["final_decision"] = "PAUSE_ROLLING_STATISTICAL_VIABILITY"
        R["reason"] = "; ".join(errs)
        OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
        print(json.dumps(J(R), indent=2, default=str))
        return 2

    T = len(df)
    labels = df["timestamp_label_internal"].astype(str).tolist()
    x = np.log(df["eurusd_close"].to_numpy(float))
    y = np.log(df["usdchf_close"].to_numpy(float))
    n_train = int(math.floor(0.60 * T)); n_val = int(math.floor(0.20 * T)); n_sealed = T - n_train - n_val
    tr = (0, n_train)
    va = (n_train + EMBARGO, n_train + n_val)
    te = (n_train + n_val + EMBARGO, T)
    R["splits"] = {"T": T, "embargo": EMBARGO,
                   "train": {"lo": tr[0], "hi": tr[1], "n": tr[1] - tr[0]},
                   "embargo_1": [n_train, n_train + EMBARGO],
                   "validation": {"lo": va[0], "hi": va[1], "n": va[1] - va[0]},
                   "embargo_2": [n_train + n_val, n_train + n_val + EMBARGO],
                   "sealed": {"lo": te[0], "hi": te[1], "n": te[1] - te[0]},
                   "boundary_labels": {"train_end": labels[tr[1] - 1], "val_start": labels[va[0]],
                                       "val_end": labels[va[1] - 1], "sealed_start": labels[te[0]],
                                       "sealed_end": labels[te[1] - 1]}}

    R["validation"] = {}
    for W in W_LIST:
        blocks, summary = evaluate_w(x, y, labels, va[0], va[1], W)
        summary["segment"] = "validation"
        R["validation"][f"W{W}"] = {"summary": summary, "blocks": blocks}

    # selection
    cands = []
    for W in W_LIST:
        s = R["validation"][f"W{W}"]["summary"]
        if not s["not_eligible_for_selection"]:
            cands.append((s["future_pass_rate"], -W, W))
    if cands:
        cands.sort(key=lambda t: (-t[0], t[1]))
        selected_W = cands[0][2]
    else:
        selected_W = None
    sel_summary = R["validation"][f"W{selected_W}"]["summary"] if selected_W else None
    qualified = bool(selected_W is not None
                     and sel_summary["eligible_blocks"] >= 3
                     and sel_summary["future_passes"] >= 2
                     and (sel_summary["future_pass_rate"] or 0) >= 0.60
                     and (sel_summary["eligibility_rate"] or 0) >= 0.20)
    R["selection"] = {"selected_W": selected_W,
                      "selection_reason": ("highest validation future pass rate; tie-break smallest W"
                                           if selected_W else "no W had >=3 eligible validation blocks"),
                      "selected_qualifies": qualified,
                      "per_W_eligible_for_selection": {f"W{W}": not R["validation"][f"W{W}"]["summary"]["not_eligible_for_selection"] for W in W_LIST}}

    if not qualified:
        R["sealed"] = {"evaluated": False,
                       "reason": "validation selection failed; sealed not evaluated"}
        R["final_decision"] = "REJECT_ROLLING_STATISTICAL_VIABILITY"
        R["failed_validation_requirements"] = {
            "selected_W": selected_W,
            "eligible_ge_3": bool(sel_summary and sel_summary["eligible_blocks"] >= 3),
            "passes_ge_2": bool(sel_summary and sel_summary["future_passes"] >= 2),
            "pass_rate_ge_060": bool(sel_summary and (sel_summary["future_pass_rate"] or 0) >= 0.60),
            "eligibility_rate_ge_020": bool(sel_summary and (sel_summary["eligibility_rate"] or 0) >= 0.20)}
    else:
        blocks, summary = evaluate_w(x, y, labels, te[0], te[1], selected_W)
        summary["segment"] = "sealed"
        R["sealed"] = {"evaluated": True, "selected_W": selected_W, "summary": summary, "blocks": blocks}
        ok = (summary["eligible_blocks"] >= 3 and summary["future_passes"] >= 2
              and (summary["future_pass_rate"] or 0) >= 0.60
              and (summary["eligibility_rate"] or 0) >= 0.20)
        R["final_decision"] = ("APPROVE_ROLLING_STATISTICAL_VIABILITY" if ok
                               else "REJECT_ROLLING_STATISTICAL_VIABILITY")
        R["sealed_confirmation_pass"] = ok

    R["statistical_only"] = True
    R["not_economic_or_tradable"] = True
    R["prohibition_attestation"] = {"no_costs_pnl_signals_ml_backtest_trading": True}
    R["finished"] = dt.datetime.now(dt.timezone.utc).isoformat()
    OUT.write_text(json.dumps(J(R), indent=2, default=str), encoding="utf-8")
    print(json.dumps(J({"hash_ok": True, "T": T, "splits": R["splits"],
                        "validation": {k: v["summary"] for k, v in R["validation"].items()},
                        "selection": R["selection"],
                        "sealed": R["sealed"].get("summary", R["sealed"]),
                        "decision": R["final_decision"]}), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
