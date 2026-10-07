#!/usr/bin/env python
"""eod_review.py — end-of-day review generator for the Frival desk.

Deterministic FACTS only: it reads the ledger and writes a dated review file
plus a one-line index entry. The agent then fills the "Lessons" and "Changes"
sections with interpretation. Idempotent: refuses if the day's file exists
unless --force.

Triggered by the desk's AFTER-CLOSE rule (server 00:00-01:00 = local 16:00-17:00)
or by the dedicated 16:05-local cron. It never places or modifies orders.

Usage:
    python eod_review.py                 # review for the current server date
    python eod_review.py --date YYYY-MM-DD
    python eod_review.py --force
"""
import csv
import datetime as dt
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "trade_log.csv"
CF = HERE / "counterfactuals.csv"
STATE = HERE / "executor_state.json"
OUTDIR = HERE / "reviews"
SERVER_OFFSET_H = 3          # broker server clock = UTC+3 (authoritative day boundary)


def server_now():
    return dt.datetime.utcnow() + dt.timedelta(hours=SERVER_OFFSET_H)


def load(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def account_equity():
    """Best-effort live equity; blank if MT5 is unavailable."""
    try:
        import MetaTrader5 as mt5
        from mt5_path import resolve_terminal_path
    except Exception:
        return None
    try:
        if not mt5.initialize(path=resolve_terminal_path(HERE)):
            return None
        acct = mt5.account_info()
        eq = float(acct.equity) if acct and acct.equity else None
        mt5.shutdown()
        return eq
    except Exception:
        return None


def main():
    args = sys.argv[1:]
    day = None
    force = "--force" in args
    for i, a in enumerate(args):
        if a == "--date" and i + 1 < len(args):
            day = args[i + 1]
    day = day or server_now().strftime("%Y-%m-%d")

    OUTDIR.mkdir(exist_ok=True)
    out = OUTDIR / f"{day}.md"
    if out.exists() and not force:
        print(f"[EOD] {out.name} already exists; nothing to do (use --force to overwrite).")
        return

    tl = load(LOG)
    today = [r for r in tl if (r.get("logged_at_server") or "")[:10] == day]
    closed = [r for r in today if r.get("status") == "CLOSED"]
    pending = [r for r in today if r.get("status") in ("PENDING_FILL", "ORDER_PLACED", "OPEN")]
    skipped = [r for r in today if r.get("status") == "SKIPPED"]

    pnl = sum(fnum(r.get("pnl_usd")) for r in closed)
    R = sum(fnum(r.get("r_multiple")) for r in closed)
    wins = sum(1 for r in closed if fnum(r.get("pnl_usd")) > 0)

    cf = load(CF)
    cf_today = [r for r in cf if (r.get("logged_at_server") or "")[:10] == day]
    cf_res = [r for r in cf_today if (r.get("outcome") or "").strip()]
    cf_tp = sum(1 for r in cf_res if str(r.get("outcome", "")).upper().startswith("TP"))

    st = {}
    if STATE.exists():
        try:
            st = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            st = {}
    eq = account_equity()

    missing_exit = [r.get("log_id") for r in closed if not (r.get("exit_price") or "").strip()]

    L = []
    L.append(f"# Daily review — {day} (server date)")
    L.append("")
    L.append(f"Generated {(server_now()).strftime('%Y-%m-%d %H:%M')} server by eod_review.py. "
             "Facts only — the agent fills the Lessons/Changes sections.")
    L.append("")
    L.append("## Result")
    L.append(f"- Closed trades: {len(closed)}  ({wins} win / {len(closed) - wins} loss)")
    L.append(f"- Day P&L: ${pnl:,.2f}   Day R: {R:+.2f}")
    eq_s = f"${eq:,.2f}" if eq else "n/a"
    sess = fnum(st.get("session_start_equity"))
    sess_s = f"${sess:,.2f}" if sess else "n/a"
    L.append(f"- Equity now: {eq_s}   session-start equity: {sess_s}")
    L.append(f"- Breaker: consecutive losses {st.get('consecutive_losses', 0)}/4   "
             f"daily realised ${fnum(st.get('daily_realised')):,.2f}")
    if missing_exit:
        L.append(f"- **WARNING**: closed rows missing exit price: {', '.join(missing_exit)} "
                 "(reconcile from broker deals before trusting P&L).")
    L.append("")
    L.append("## Trades closed")
    if closed:
        L.append("| id | sym | side | vol | entry | exit | PnL $ | R | MFE | MAE | mom | exit reason |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
        for r in closed:
            L.append("| {log} | {sym} | {side} | {vol} | {entry} | {exit} | {pnl} | {R} | {mfe} | {mae} | {mom} | {why} |".format(
                log=r.get("log_id"), sym=r.get("symbol"), side=r.get("side"), vol=r.get("volume"),
                entry=r.get("fill_price") or r.get("entry_price"), exit=r.get("exit_price"),
                pnl=r.get("pnl_usd"), R=r.get("r_multiple"), mfe=r.get("mfe_usd"), mae=r.get("mae_usd"),
                mom=r.get("mom_alignment"), why=(r.get("exit_reason") or "")[:48]))
    else:
        L.append("_none_")
    L.append("")
    L.append("## Other activity")
    L.append(f"- Pending/open at day end: {len(pending)}")
    L.append(f"- Skipped rows: {len(skipped)}")
    L.append(f"- Counterfactuals logged today: {len(cf_today)}  (resolved: {len(cf_res)}, TP-first: {cf_tp})")
    if cf_today:
        c = Counter((r.get("reject_reason") or "?") for r in cf_today)
        L.append("  - reject reasons: " + ", ".join(f"{k} {v}" for k, v in c.items()))
    L.append("")
    L.append("## Lessons (agent)")
    L.append("_3-5 sentences: what the day taught; any rule change proposed._")
    L.append("")
    L.append("## Changes made")
    L.append("_Code/rule/doc changes committed today (reference commit hashes)._")
    L.append("")

    out.write_text("\n".join(L) + "\n", encoding="utf-8")

    idx = OUTDIR / "INDEX.md"
    with idx.open("a", encoding="utf-8") as f:
        f.write(f"- {day}: {len(closed)} closed, ${pnl:+,.2f}, {R:+.2f}R — reviews/{day}.md\n")

    print(f"[EOD] wrote {out}")
    print(f"[EOD] day {day}: {len(closed)} closed, ${pnl:+,.2f}, {R:+.2f}R, cf {len(cf_today)}")
    print("[EOD] now fill 'Lessons (agent)' and 'Changes made' in the file.")


if __name__ == "__main__":
    main()
