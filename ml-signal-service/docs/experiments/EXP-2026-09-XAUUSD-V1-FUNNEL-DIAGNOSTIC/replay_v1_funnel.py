#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""EXP-2026-09 — XAUUSD Gold Rules Engine V1 offline funnel diagnostic.

Offline, read-only replay of the FROZEN Gold Rules Engine V1 (engine.py /
bias.py / levels.py) over already-local XAUUSD M15/H1 history.

It does NOT touch production: it only IMPORTS the frozen pure modules, builds
causal snapshots from local parquet, calls engine.evaluate() and records the
decision stream. No MT5, no orders, no network, no PnL/performance metrics.

Causal contract (mirrors production run_gold_rules.py):
  - decision instant for the last M15 bar opening at T is t = T + 16 minutes
    (production uses `last_time + timedelta(minutes=16)`);
  - only M15 bars with open <= T are visible;
  - only M30 bars whose close (open+30m) <= t are visible;
  - only H1 bars whose close (open+60m) <= t are visible;
  - state persists across M15 bars; each unique M15 close is evaluated once.

Outputs (exactly three CSVs, into --outdir):
  FUNNEL_RESULTS.csv, REJECTION_TAXONOMY.csv, MONTHLY_FUNNEL.csv
Everything else (validation, hashes, determinism) is printed to stdout.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import os
import sys
from collections import Counter, OrderedDict

import numpy as np
import pandas as pd
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
DEFAULT_GOLD = os.path.join(DEFAULT_REPO, "frival", "gold_rules")
DEFAULT_M15 = os.path.join(
    DEFAULT_REPO, "quant-personal-fund", "experiments",
    "EXP-2026-05-INVALIDATION-REVERSAL", "audits", "PHASE-1B",
    "data", "processed", "XAUUSD_M15_processed.parquet")
DEFAULT_H1 = os.path.join(
    DEFAULT_REPO, "quant-personal-fund", "experiments",
    "EXP-2026-05-INVALIDATION-REVERSAL", "audits", "PHASE-1B",
    "data", "processed", "XAUUSD_H1_processed.parquet")

DECISION_MINUTES = 16          # production: last M15 open + 16 min
M15_BAR_MIN = 15
M30_BAR_MIN = 30
H1_BAR_MIN = 60
WIN_M15 = 1000                 # production fetch caps
WIN_M30 = 400
WIN_H1 = 200

FROZEN = ["engine.py", "bias.py", "levels.py", "config.yaml"]

STAGES = OrderedDict([
    ("N_M15_CLOSED", None),
    ("N_H1_NON_FLAT", "bias_ok"),
    ("N_BIAS_CONSISTENT_LEVEL_ARMED", "armed"),
    ("N_BREAK_EVENT", "break_ev"),
    ("N_REJECTION_EVENT", "rej_ev"),
    ("N_WAIT_CANDLE_CLOSE", "wait"),
    ("N_RETEST_REJECTION", "retest_rej"),
    ("N_CONFIRMED", "confirmed"),
    ("N_CONFIRM_EXTREME_BROKEN", "ext_broken"),
    ("N_ENTRY_READY", "entry_ready"),
    ("N_ENTRY_INTENT", "entry"),
    ("N_DROP", "drop"),
    ("N_ERROR", "error"),
])


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def load_ohlc(path: str) -> dict:
    df = pd.read_parquet(path)
    df = df.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    return {
        "t": pd.to_datetime(df["time"], unit="s").to_numpy("datetime64[ns]"),
        "o": df["open"].to_numpy(float),
        "h": df["high"].to_numpy(float),
        "l": df["low"].to_numpy(float),
        "c": df["close"].to_numpy(float),
        "v": df["tick_volume"].to_numpy(float),
        "raw_t": df["time"].to_numpy("int64"),
    }


def derive_m30(m15: dict) -> dict:
    """Deterministic OHLC aggregation of M15 into 30-minute UTC buckets.

    Only COMPLETE buckets (exactly two M15 bars) are kept, so a partial bucket
    can never fabricate an M30 bar. No interpolation / fill / repair.
    """
    idx = pd.DatetimeIndex(m15["t"]).floor("30min")
    df = pd.DataFrame({
        "bucket": idx, "o": m15["o"], "h": m15["h"], "l": m15["l"],
        "c": m15["c"], "v": m15["v"],
    })
    g = df.groupby("bucket", sort=True).agg(
        o=("o", "first"), h=("h", "max"), l=("l", "min"),
        c=("c", "last"), v=("v", "sum"), n=("o", "size"))
    g = g[g["n"] == 2]
    t = g.index.to_numpy("datetime64[ns]")
    return {"t": t, "o": g["o"].to_numpy(float), "h": g["h"].to_numpy(float),
            "l": g["l"].to_numpy(float), "c": g["c"].to_numpy(float),
            "v": g["v"].to_numpy(float)}


def make_df(a: dict, lo: int, hi: int) -> pd.DataFrame:
    return pd.DataFrame({
        "datetime": a["t"][lo:hi], "open": a["o"][lo:hi],
        "high": a["h"][lo:hi], "low": a["l"][lo:hi],
        "close": a["c"][lo:hi], "volume": a["v"][lo:hi],
    }).reset_index(drop=True)


def cut_index(close_times, t):
    """Number of bars whose CLOSE <= t (bars are sorted by open time)."""
    return int(np.searchsorted(close_times, t, side="right"))


def install_level_cache(levels_mod):
    """Exact memoization of build_active_levels (pure function of the M30
    window). The engine calls it twice per WATCH_ZONE bar with the SAME m30_df
    (once in _compute_bias_and_levels, once in _check_breakout), and the M30
    window only advances every second M15 bar. Keyed by the window's endpoints
    + params, this returns the identical object the frozen code would compute.
    It patches the module attribute only, never a production file."""
    orig = levels_mod.build_active_levels
    cache = {}

    def cached(df, lookback=200, atr_period=14, merge_atr_mult=0.5):
        if df is None or len(df) == 0:
            return orig(df, lookback, atr_period, merge_atr_mult)
        key = (int(df["datetime"].iloc[0].value),
               int(df["datetime"].iloc[-1].value), len(df),
               lookback, atr_period, merge_atr_mult)
        hit = cache.get(key)
        if hit is None:
            hit = orig(df, lookback, atr_period, merge_atr_mult)
            cache[key] = hit
        return hit

    levels_mod.build_active_levels = cached


def run_pass(cfg, m15, m30, h1, *, win_m15=WIN_M15, win_m30=WIN_M30,
             win_h1=WIN_H1, limit=None, start=0,
             seg_state_clone_at=None, collect=True):
    """Run one chronological replay pass. Returns (records, seg_state, seg_lo)."""
    import engine as eng  # frozen

    engine = eng.GoldRulesEngine(cfg)
    state = eng.EngineState()

    t15 = m15["t"]
    t30_close = m30["t"] + np.timedelta64(M30_BAR_MIN, "m")
    t1_close = h1["t"] + np.timedelta64(H1_BAR_MIN, "m")
    t15_close = t15 + np.timedelta64(M15_BAR_MIN, "m")

    n = len(t15) if limit is None else min(len(t15), start + limit)
    records = []
    seg_state = None
    seg_lo = None

    for i in range(start, n):
        T = t15[i]
        t = T + np.timedelta64(DECISION_MINUTES, "m")

        m15_lo = max(0, i + 1 - win_m15)
        m15_df = make_df(m15, m15_lo, i + 1)

        j30 = cut_index(t30_close, t)
        m30_lo = max(0, j30 - win_m30)
        m30_df = make_df(m30, m30_lo, j30) if j30 > 0 else make_df(m30, 0, 0)

        j1 = cut_index(t1_close, t)
        h1_lo = max(0, j1 - win_h1)
        h1_df = make_df(h1, h1_lo, j1) if j1 > 0 else make_df(h1, 0, 0)

        # causality guards
        if j30 > 0 and m30["t"][j30 - 1] + np.timedelta64(M30_BAR_MIN, "m") > t:
            raise AssertionError("M30 lookahead")
        if j1 > 0 and h1["t"][j1 - 1] + np.timedelta64(H1_BAR_MIN, "m") > t:
            raise AssertionError("H1 lookahead")
        if len(m15_df) and m15_df["datetime"].iloc[-1] != T:
            raise AssertionError("M15 last bar mismatch")

        if seg_state_clone_at is not None and i == seg_state_clone_at:
            seg_state = eng.EngineState.from_dict(state.to_dict())
            seg_lo = i

        close = float(m15["c"][i])
        snap = eng.Snapshot(
            m15_df=m15_df, m30_df=m30_df, h1_df=h1_df, utc_now=T + np.timedelta64(DECISION_MINUTES, "m"),
            bid=close, ask=close, open_positions=0, today_realized_pnl=0.0)

        state, dec = engine.evaluate(snap, state)

        if collect:
            reasons = dec.reason or ""
            gates = dec.gate_results or {}
            rec = {
                "i": i, "T": T, "month": pd.Timestamp(T).strftime("%Y-%m"),
                "action": dec.action, "state_after": state.state,
                "h1_bias": state.h1_bias, "reason": reasons,
                "armed": state.watched_level is not None,
                "gate_results": gates,
                "is_claim_c": "CLAIM-C" in reasons,
            }
            records.append(rec)
    return records, seg_state, seg_lo


def classify_events(records):
    for r in records:
        rs = r["reason"]
        r["bias_ok"] = r["h1_bias"] in ("BULLISH", "BEARISH")
        r["break_ev"] = ("Break through" in rs)
        r["rej_ev"] = ("Rejection wick" in rs)
        r["retest_rej"] = ("retest rejection" in rs)
        r["wait"] = (r["state_after"] == "WAIT_CANDLE_CLOSE")
        r["confirmed"] = (r["state_after"] == "CONFIRMED")
        r["ext_broken"] = ("break of confirm-candle extreme" in rs)
        r["entry_ready"] = (r["state_after"] == "ENTRY_READY")
        r["entry"] = (r["action"] == "ENTRY")
        r["drop"] = (r["action"] == "DROP")
        r["error"] = (r["action"] == "ERROR")


def funnel_counts(records):
    return OrderedDict((name, int(sum(1 for r in records if r[key])))
                       for name, key in STAGES.items() if key is not None)


def tax_bucket(r):
    """First binding reason for a non-progressing evaluation."""
    rs = r["reason"]
    a = r["action"]
    if a == "ERROR" or r["error"]:
        return "DATA_OR_INDICATOR_ERROR"
    if rs.startswith("no bias-consistent intact level armed"):
        return "BIAS_FLAT" if not r["bias_ok"] else "NO_BIAS_CONSISTENT_LEVEL"
    if rs.startswith("watching "):
        return "NO_BREAK_OR_REJECTION"
    if "awaiting retest rejection candle" in rs:
        return "NO_BREAK_OR_REJECTION"
    if "awaiting close beyond confirmation extreme" in rs:
        return "NO_BREAK_OR_REJECTION"
    if "retest timeout" in rs:
        return "RETEST_TIMEOUT"
    if "confirmation extreme not broken in time" in rs:
        return "CONFIRMATION_TIMEOUT"
    if "bias flipped" in rs:
        return "BIAS_FLIP_VOID"
    if "no structural SL/TP resolvable" in rs:
        return "NO_STRUCTURAL_SL_TP"
    if "concurrent position occupied" in rs:
        return "CONCURRENCY_GATE_FAIL"
    if "gates failed" in rs:
        g = r["gate_results"]
        failed = sorted(k for k, v in g.items() if k != "pass" and v is False)
        if not failed:
            return "OTHER_ENGINE_DROP"
        if len(failed) > 1:
            return "MULTIPLE_GATES_FAIL"
        f = failed[0]
        return {"location": "LOCATION_GATE_FAIL", "rr": "RR_GATE_FAIL",
                "risk": "RISK_GATE_FAIL", "concurrency": "CONCURRENCY_GATE_FAIL",
                "daily": "DAILY_LOSS_GATE_FAIL"}.get(f, "MULTIPLE_GATES_FAIL")
    if a == "DROP":
        return "OTHER_ENGINE_DROP"
    if a == "NONE" and "terminal state cleared" in rs:
        return "OTHER_ENGINE_DROP"
    return "OTHER_ENGINE_DROP"


TAX_BUCKETS = [
    "BIAS_FLAT", "NO_BIAS_CONSISTENT_LEVEL", "LEVEL_CONSUMED_OR_INVALID",
    "NO_BREAK_OR_REJECTION", "RETEST_TIMEOUT", "CONFIRMATION_TIMEOUT",
    "BIAS_FLIP_VOID", "NO_STRUCTURAL_SL_TP", "LOCATION_GATE_FAIL",
    "RR_GATE_FAIL", "RISK_GATE_FAIL", "CONCURRENCY_GATE_FAIL",
    "DAILY_LOSS_GATE_FAIL", "MULTIPLE_GATES_FAIL", "DATA_OR_INDICATOR_ERROR",
    "OTHER_ENGINE_DROP",
]


def analyze(recs):
    """Build the aggregate analysis for one pass from its decision records."""
    n_eval = len(recs)
    tax = Counter()
    tax_first = {}
    tax_months = {b: Counter() for b in TAX_BUCKETS}
    pre_entry = sum(1 for r in recs if r["entry_ready"] or r["entry"])
    for r in recs:
        if r["action"] not in ("NONE", "DROP", "ERROR"):
            continue
        if r["state_after"] == "IN_TRADE":
            continue
        b = tax_bucket(r)
        tax[b] += 1
        tax_months[b][r["month"]] += 1
        if b not in tax_first:
            tax_first[b] = [str(r["T"]),
                            f"action={r['action']} state={r['state_after']} "
                            f"bias={r['h1_bias']} reason={r['reason'][:80]}"]
    months = sorted({r["month"] for r in recs})
    monthly = []
    for m in months:
        sub = [r for r in recs if r["month"] == m]
        row = {"month": m, "N_M15_CLOSED": len(sub)}
        row.update(funnel_counts(sub))
        monthly.append(row)
    return {
        "n_eval": n_eval, "funnel": funnel_counts(recs),
        "taxonomy": {k: int(v) for k, v in tax.items()},
        "tax_first": tax_first,
        "tax_months": {k: dict(v) for k, v in tax_months.items()},
        "pre_entry": pre_entry, "monthly": monthly, "months": months,
    }


def write_csvs(outdir, comb, ab):
    os.makedirs(outdir, exist_ok=True)

    def funnel_rows(scope, funnel, n_eval):
        out, prev = [], None
        for stage in funnel:
            val = funnel[stage]
            share = (val / n_eval) if n_eval else 0.0
            cond = "" if prev in (None, 0) else round(val / prev, 6)
            out.append([scope, stage, val, round(share, 6), cond, ""])
            prev = val
        return out

    rows = funnel_rows("COMBINED", comb["funnel"], comb["n_eval"])
    rows += funnel_rows("A/B_ONLY", ab["funnel"], ab["n_eval"])
    ce = comb.get("entry_c", 0)
    rows.append(["C_ONLY", "N_ENTRY_INTENT", ce,
                 round(ce / comb["n_eval"], 6) if comb["n_eval"] else 0.0, "",
                 "C-only intermediate stages are not separately emitted by the "
                 "engine; count = C ENTRYs"])
    with open(os.path.join(outdir, "FUNNEL_RESULTS.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scope", "stage", "count", "share_of_m15",
                    "conditional_from_prev", "note"])
        w.writerows(rows)

    with open(os.path.join(outdir, "REJECTION_TAXONOMY.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["bucket", "count", "share_all_m15",
                    "share_pre_entry_candidates", "month_distribution",
                    "representative_timestamp", "representative_summary"])
        for b in TAX_BUCKETS:
            cnt = comb["taxonomy"].get(b, 0)
            md = ";".join(f"{k}={v}" for k, v in
                          sorted(comb["tax_months"].get(b, {}).items()))
            ts_summ = comb["tax_first"].get(b, ["", ""])
            w.writerow([b, cnt,
                        round(cnt / comb["n_eval"], 6) if comb["n_eval"] else 0.0,
                        round(cnt / comb["pre_entry"], 6) if comb["pre_entry"] else 0.0,
                        md, ts_summ[0], ts_summ[1]])

    with open(os.path.join(outdir, "MONTHLY_FUNNEL.csv"), "w", newline="",
              encoding="utf-8") as f:
        cols = ["month"] + [s for s in STAGES]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in comb["monthly"]:
            w.writerow({k: row.get(k, 0) for k in cols})
    print("[out] wrote FUNNEL_RESULTS.csv, REJECTION_TAXONOMY.csv, MONTHLY_FUNNEL.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--m15", default=DEFAULT_M15)
    ap.add_argument("--h1", default=DEFAULT_H1)
    ap.add_argument("--gold-dir", default=DEFAULT_GOLD)
    ap.add_argument("--config", default=None)
    ap.add_argument("--outdir", default=HERE)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--win-m15", type=int, default=WIN_M15)
    ap.add_argument("--win-m30", type=int, default=WIN_M30)
    ap.add_argument("--win-h1", type=int, default=WIN_H1)
    ap.add_argument("--scope", choices=["both", "combined", "ab"], default="both")
    ap.add_argument("--dump-json", default=None)
    ap.add_argument("--merge", nargs=2, default=None,
                    help="merge two --dump-json files (combined, ab) into CSVs")
    ap.add_argument("--no-csv", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    args = ap.parse_args()

    if args.merge:
        comb = ab = None
        for p in args.merge:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d["role"] == "combined":
                comb = d
            elif d["role"] == "ab":
                ab = d
        write_csvs(args.outdir, comb, ab)
        print("MERGED " + json.dumps({"combined_eval": comb["n_eval"],
                                      "ab_eval": ab["n_eval"]}))
        return

    W = dict(win_m15=args.win_m15, win_m30=args.win_m30, win_h1=args.win_h1)
    sys.path.insert(0, args.gold_dir)
    import levels as levels_mod  # frozen
    if not args.no_cache:
        install_level_cache(levels_mod)
    cfg_path = args.config or os.path.join(args.gold_dir, "config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    print("== FROZEN SOURCE SHA-256 ==")
    hashes = {}
    for name in FROZEN:
        p = os.path.join(args.gold_dir, name)
        hashes[name] = sha256(p)
        print(f"  {name}: {hashes[name]}")

    m15 = load_ohlc(args.m15)
    h1 = load_ohlc(args.h1)
    m30 = derive_m30(m15)

    def rpt(name, a):
        t = pd.DatetimeIndex(a["t"])
        dup = int(pd.Series(a["raw_t"]).duplicated().sum()) if "raw_t" in a else 0
        print(f"[data] {name}: rows={len(a['t'])} first={t[0]} last={t[-1]} "
              f"dup_time={dup} tz=UTC(naive-from-epoch)")
    rpt("M15", m15)
    rpt("H1", h1)
    rpt("M30(derived_from_M15)", m30)
    cov_days = (pd.Timestamp(m15["t"][-1]) - pd.Timestamp(m15["t"][0])).days
    print(f"[data] M15 coverage_days={cov_days} bars={len(m15['t'])}")

    cfg_ab = copy.deepcopy(cfg)
    cfg_ab.setdefault("breakout", {})["enabled"] = False

    def do_determinism():
        lo = 50000 if args.limit is None else (args.start or 0)
        hi = min(len(m15["t"]), lo + 1500)
        a, _, _ = run_pass(cfg, m15, m30, h1, start=lo, limit=hi - lo, **W)
        b, _, _ = run_pass(cfg, m15, m30, h1, start=lo, limit=hi - lo, **W)
        ok = all((x["action"], x["state_after"], x["reason"]) ==
                 (y["action"], y["state_after"], y["reason"])
                 for x, y in zip(a, b))
        print(f"[determinism] segment [{lo},{hi}) twice identical = {ok} "
              f"(bars={len(a)})")
        return ok

    summary = {"frozen_hashes": hashes, "m15_rows": int(len(m15["t"])),
               "h1_rows": int(len(h1["t"])), "m30_rows_derived": int(len(m30["t"])),
               "coverage_days": int(cov_days)}

    if args.scope in ("both", "combined"):
        recs, _, _ = run_pass(cfg, m15, m30, h1, limit=args.limit,
                              start=args.start, **W)
        classify_events(recs)
        comb = analyze(recs)
        comb["entry_c"] = sum(1 for r in recs if r["entry"] and r["is_claim_c"])
        comb["entry_ab"] = sum(1 for r in recs if r["entry"] and not r["is_claim_c"])
        comb["det"] = do_determinism()
        print(f"[replay] combined evaluated M15 bars = {comb['n_eval']}")
        print("[replay] combined funnel =", json.dumps(comb["funnel"]))
        print(f"[replay] combined ENTRY_INTENT: A/B={comb['entry_ab']} "
              f"C={comb['entry_c']} total={comb['entry_ab'] + comb['entry_c']}")
        print("[taxonomy] counts =", json.dumps(comb["taxonomy"]))
        summary.update(evaluated_m15=comb["n_eval"], combined_funnel=comb["funnel"],
                       entry_ab=comb["entry_ab"], entry_c=comb["entry_c"],
                       taxonomy=comb["taxonomy"], determinism_ok=comb["det"],
                       months=len(comb["months"]))
        if args.scope == "combined":
            if args.dump_json:
                with open(args.dump_json, "w", encoding="utf-8") as f:
                    json.dump({"role": "combined", **comb}, f)
                print(f"[dump] {args.dump_json}")

    if args.scope in ("both", "ab"):
        recs_ab, _, _ = run_pass(cfg_ab, m15, m30, h1, limit=args.limit,
                                 start=args.start, **W)
        classify_events(recs_ab)
        ab = analyze(recs_ab)
        ab["entry_ab"] = sum(1 for r in recs_ab if r["entry"])
        print("[replay] A/B-only funnel =", json.dumps(ab["funnel"]))
        summary.update(ab_only_funnel=ab["funnel"])
        if args.scope == "ab":
            if args.dump_json:
                with open(args.dump_json, "w", encoding="utf-8") as f:
                    json.dump({"role": "ab", **ab}, f)
                print(f"[dump] {args.dump_json}")

    if args.scope == "both":
        if not args.no_csv:
            write_csvs(args.outdir, comb, ab)

    print("SUMMARY_JSON=" + json.dumps(summary))


if __name__ == "__main__":
    main()

