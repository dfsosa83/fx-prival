# -*- coding: utf-8 -*-
"""EXP-2026-04 — report generator (Deliverable 3).

Loads per-pair backtest results, computes the §4 metrics table + §5 decision
rule, and emits a human-readable report to results/SUMMARY.md.

P0.2 (ROADMAP-2026-Q4 §9 P0.2): EV/R is now reported NET of the shared
round-trip cost constant and with a block-bootstrap 95% CI, sourced from
ml-signal-service/experiments/_core (costs.py, bootstrap.py) via
frival/dashboard/backend/tag_metrics.py. The raw EV/R remains available in the
row but is never the headline figure — no zero-cost EV/R is reported as final.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

PAIRS = ["EURUSD", "USDJPY", "GBPUSD", "USDCAD"]

# import the shared tag metrics (which hooks experiments/_core) — insert parent
sys.path.insert(0, str(HERE.parent / "dashboard" / "backend"))
import tag_metrics as tagm  # noqa: E402


def evr_from_ledger(ledger: list, pair: str) -> dict:
    if not ledger:
        return {"n": 0}
    closed = [l for l in ledger if l.get("R") is not None]
    n = len(closed)
    if n == 0:
        return {"n": 0}
    Rs = [l["R"] for l in closed]
    wins = [r for r in Rs if r > 0]
    losses = [r for r in Rs if r <= 0]
    winpct = 100 * len(wins) / n
    ev = sum(Rs) / n

    # P0.2: enrich each row with the risk distance so the shared cost model can
    # express friction in R units (cost_R = round_trip_cost_in_price / |entry-sl|).
    for l in closed:
        entry, sl = l.get("entry"), l.get("sl")
        if entry is not None and sl is not None and float(entry) and float(sl):
            l["risk_price"] = abs(float(entry) - float(sl))
    scored = tagm.evr_series(closed, pair=pair)

    return {
        "n": n,
        "total_closed": len(closed),
        "censored": len(ledger) - len(closed),
        "win%": round(winpct, 1),
        "EV/R": round(ev, 3),                 # raw — audit only (P0.2)
        "EV/R_net": scored["evr_net"],        # headline — net of shared cost
        "EV/R_ci_95": [scored["ev_ci_95_lo"], scored["ev_ci_95_hi"]],
        "small_sample": scored.get("small_sample", False),
        "median_R": round(float(pd.Series(Rs).median()), 3),
        "best_R": round(max(Rs), 2),
        "worst_R": round(min(Rs), 2),
        "sum_pnl_usd": round(sum(l.get("sim_pnl_usd") or 0 for l in closed), 2),
        "cost_pips_used": scored["cost_pips_used"],
    }


def load_results(pair: str) -> dict:
    ledger_path = RESULTS / f"{pair}_ledger.csv"
    if not ledger_path.exists():
        return {"pair": pair, "error": "no ledger"}
    ledger = []
    if ledger_path.stat().st_size > 0:
        df = pd.read_csv(ledger_path)
        ledger = df.to_dict("records")
    # decision jsonl (summary stats)
    dec_path = RESULTS / f"{pair}_decisions.jsonl"
    decisions = []
    if dec_path.exists():
        for line in dec_path.read_text(encoding="utf-8").splitlines():
            try:
                decisions.append(json.loads(line))
            except Exception:
                pass
    return {"pair": pair, "ledger": ledger, "decisions": decisions}


def main():
    rows = []
    for pair in PAIRS:
        res = load_results(pair)
        m = evr_from_ledger(res.get("ledger", []), pair=pair)
        decs = res.get("decisions", [])
        entries = sum(1 for d in decs if d.get("action") == "ENTRY")
        rows.append({"pair": pair, **m, "would_entries": entries,
                     "n_decisions": len(decs)})

    print("=" * 78)
    print("EXP-2026-04 — FX RULE-ENGINE BACKTEST SUMMARY")
    print("=" * 78)
    hdr = f"{'Pair':<8}{'N':>5}{'Win%':>7}{'EV/R':>8}{'EV/Rn':>9}{'CI95':>13}" \
          f"{'MedR':>7}{'WorstR':>8}{'BestR':>7}{'PnL$':>9}{'Cens':>5}"
    print(hdr)
    for r in rows:
        if "error" in r:
            print(f"{r['pair']:<8} ERROR: {r['error']}")
            continue
        if r.get("n"):
            ci = r.get("EV/R_ci_95") or ["-", "-"]
            if ci not in (["-", "-"], [None, None]) and r.get("small_sample"):
                ci_s = f"(<{r['n']} trades)"   # block capped -> wide, not tight
            elif ci not in (["-", "-"], [None, None]):
                ci_s = f"[{ci[0]}, {ci[1]}]"
            else:
                ci_s = "-"
            print(f"{r['pair']:<8}{r.get('n',0):>5}"
                  f"{r.get('win%',0) if r.get('n') else '-':>7}"
                  f"{r.get('EV/R',0) if r.get('n') else '-':>8}"
                  f"{r.get('EV/R_net','-') if r.get('n') else '-':>9}"
                  f"{ci_s:>13}"
                  f"{r.get('median_R','-') if r.get('n') else '-':>7}"
                  f"{r.get('worst_R','-') if r.get('n') else '-':>8}"
                  f"{r.get('best_R','-') if r.get('n') else '-':>7}"
                  f"{r.get('sum_pnl_usd',0) if r.get('n') else 0:>9}"
                  f"{r.get('censored',0):>5}")

    print("\n" + "=" * 78)
    print("DECISION RULE (§5): EV/R > +0.3 & cadence-ok -> live-candidate;  -0.2..0.3 inconclusive;  <=-0.2 stop")
    for r in rows:
        if "error" in r or not r.get("n"):
            print(f"  {r['pair']}: no closed trades — no verdict possible")
            continue
        ev = r["EV/R"]
        net = r.get("EV/R_net")
        ci = r.get("EV/R_ci_95") or [None, None]
        # P0.2: verdict on NET EV/R where available (never on the raw audit number)
        verdict_base = net if net is not None else ev
        if verdict_base > 0.3 and r["n"] >= 20:
            verdict = "CANDIDATE (proceed to Claim-D spec)"
        elif verdict_base > 0.3:
            verdict = "positive but sample small — stay in study"
        elif verdict_base <= -0.2:
            verdict = "STOP — rules do not transfer to this pair"
        else:
            verdict = "inconclusive — expand/keep running"
        net_s = f"{net:+.3f}" if net is not None else "n/a"
        print(f"  {r['pair']}: EV/R={ev:+.3f} net={net_s} "
              f"CI95=[{ci[0]},{ci[1]}] n={r['n']}  -> {verdict}")

    # persist summary markdown
    md = ["# EXP-2026-04 Backtest Summary", ""]
    hdr_md = ("Pair | N | Win% | EV/R | EV/R_net | CI95_lo | CI95_hi | "
              "MedR | WorstR | BestR | PnL$ | Cens")
    lines = [hdr_md]
    for r in rows:
        if "error" in r:
            continue
        ci = r.get("EV/R_ci_95") or ["-", "-"]
        lines.append(
            f"{r['pair']}|{r.get('n',0)}|{r.get('win%','-')}|{r.get('EV/R','-')}|"
            f"{r.get('EV/R_net','-')}|{ci[0]}|{ci[1]}|"
            f"{r.get('median_R','-')}|{r.get('worst_R','-')}|{r.get('best_R','-')}|"
            f"{r.get('sum_pnl_usd',0)}|{r.get('censored',0)}"
        )
    md.append("\n".join(lines))
    (RESULTS / "SUMMARY.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n[report] written -> {RESULTS / 'SUMMARY.md'}")


if __name__ == "__main__":
    main()