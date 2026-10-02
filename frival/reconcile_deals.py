#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Deal reconciler — closes trade-log observations from live MT5 deal history.

The operator executes manually in MT5 (§11.1 of fx-manual-trades.md). This
module reads that execution back out of the broker's deal ledger and stamps
fill / exit / PnL / R onto the matching observation in trade_log.csv, so the
evidence base never depends on the operator reporting numbers by hand.

SAFETY CONTRACT
---------------
READ-ONLY against MT5. It calls only:
    mt5.history_deals_get(), mt5.history_orders_get(), mt5.account_info()
It NEVER calls order_send, order_check, order_close, positions_close,
positions_get for modification, or any state-changing function. No argument
can make this script place, modify or cancel an order.

MATCHING RULE
-------------
A setup is identified by the operator's order COMMENT, which §11.2 mandates in
the form FRIVAL_<setup_id>. Deals are grouped by (symbol, comment). Within a
group the IN deal (entry 0) becomes the fill; the opposite-direction OUT deal
becomes the exit. R is computed against the SL distance recorded in the log.

Usage:
    python reconcile_deals.py scan              # match log <-> broker, report
    python reconcile_deals.py apply             # stamp confirmed matches
    python reconcile_deals.py apply --id T003   # single observation
    python reconcile_deals.py audit             # history coverage / orphans
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "trade_log.csv"
TERMINAL_PATH = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"

SERVER_UTC_OFFSET_H = 3
LOCAL_UTC_OFFSET_H = -5

DEAL_IN, DEAL_OUT = 0, 1
COMMENT_PREFIX = "FRIVAL"

# Read-only guard: any accidental use of an order function in this module is a bug.
FORBIDDEN = ("order_send", "order_check", "order_close", "order_modify",
             "positions_close", "orders_delete", "order_delete", "set_sl_close")


def _mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[ERROR] MetaTrader5 package missing. Use anaconda3 python.")
        sys.exit(1)
    if not mt5.initialize(path=TERMINAL_PATH):
        print(f"[ERROR] mt5.initialize failed: {mt5.last_error()}")
        sys.exit(1)
    return mt5


def _now():
    utc = dt.datetime.utcnow()
    return (utc + dt.timedelta(hours=LOCAL_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S")


def _log_rows():
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(rows):
    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in rows[0].keys()})


def _pip_value(symbol: str, info) -> float:
    """USD value of ONE PIP for 1.00 lot, from the broker's own contract data."""
    digits = info.digits
    pip_size = 0.01 if digits in (3, 5) and symbol.endswith(("JPY", "JPYm", "USDJPY")) else 0.0001
    if symbol.endswith("JPY"):
        pip_size = 0.01
    elif digits == 2:
        pip_size = 0.01        # metals / indices quoted to 2dp
    else:
        pip_size = 0.0001
    ticks_per_pip = pip_size / info.trade_tick_size
    return info.trade_tick_value * ticks_per_pip


def _price_move_usd(symbol: str, move: float, volume: float, info) -> float:
    """USD P/L for a raw price move. Used for metals (digits==2) directly."""
    return move * volume * info.trade_contract_size


def fetch_deals(days: int = 30):
    """Return deals grouped by (symbol, comment) — newest last."""
    mt5 = _mt5()
    try:
        end = dt.datetime.utcnow()
        start = end - dt.timedelta(days=days)
        deals = mt5.history_deals_get(start, end)
        if not deals:
            return {}, {}
        # Group entry deals by their FRIVAL tag first.
        groups: dict[tuple, list] = {}
        for d in deals:
            cmt = (getattr(d, "comment", "") or "").strip()
            if not cmt.upper().startswith(COMMENT_PREFIX):
                continue
            key = (d.symbol, cmt)
            groups.setdefault(key, []).append(d)

        # When the broker closes on SL or TP it OVERWRITES the exit deal
        # comment with "[sl X]" or "[tp X]", so the FRIVAL tag only survives
        # on the entry deal. Attach those exits to the group of the same
        # symbol whose entry is closest in time BEFORE the exit.
        for d in deals:
            cmt = (getattr(d, "comment", "") or "").strip()
            if not (cmt.upper().startswith("[SL ") or cmt.upper().startswith("[TP ")):
                continue
            best = None
            for key, items in groups.items():
                if key[0] != d.symbol:
                    continue
                ins = [x for x in items if x.entry == DEAL_IN]
                if not ins:
                    continue
                if ins[0].time <= d.time:
                    delta = d.time - ins[0].time
                    if best is None or delta < best[0]:
                        best = (delta, key)
            if best is not None:
                groups[best[1]].append(d)

        info = {}
        for (sym, _), items in groups.items():
            if sym not in info:
                si = mt5.symbol_info(sym)
                if si:
                    info[sym] = si
        for k in groups:
            groups[k].sort(key=lambda x: x.time)
        return groups, info
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def match(rows, groups, info):
    """Pair each open/pending log row with its broker group."""
    out = []
    for r in rows:
        sid = r.get("setup_id", "")
        if not sid.upper().startswith(COMMENT_PREFIX):
            continue
        # The broker comment is the log_id tag ("FRIVAL_T013") while the log's
        # setup_id carries a date suffix ("FRIVAL_T013_20261002"). Match either
        # direction so a prefix relationship is not missed.
        key = next((k for k in groups
                    if k[1] == sid
                    or k[1].startswith(sid)
                    or sid.startswith(k[1])), None)
        if key is None:
            continue
        deals = groups[key]
        sym = key[0]
        si = info.get(sym)
        if si is None:
            continue
        pv = _pip_value(sym, si)
        entries = [d for d in deals if d.entry == DEAL_IN]
        exits = [d for d in deals if d.entry == DEAL_OUT]
        m = {
            "log_id": r.get("log_id"),
            "setup_id": sid,
            "symbol": sym,
            "status_log": r.get("status"),
            "n_deals": len(deals),
            "n_in": len(entries),
            "n_out": len(exits),
            "entry_price": "",
            "entry_time_local": "",
            "volume": r.get("volume", ""),
            "exit_price": "",
            "exit_time_local": "",
            "pnl_usd": "",
            "swap_usd": "",
            "comment_matched": key[1],
        }
        if entries:
            e = entries[0]
            m["entry_price"] = f"{e.price:.5f}"
            m["entry_time_local"] = (dt.datetime.utcfromtimestamp(e.time)
                                     + dt.timedelta(hours=LOCAL_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S")
        if exits:
            x = exits[-1]
            m["exit_price"] = f"{x.price:.5f}"
            m["exit_time_local"] = (dt.datetime.utcfromtimestamp(x.time)
                                    + dt.timedelta(hours=LOCAL_UTC_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S")
            if entries:
                e = entries[0]
                gross = sum(d.profit for d in deals if d.entry == DEAL_OUT)
                swap = sum(d.swap for d in deals)
                m["pnl_usd"] = f"{gross + swap:.2f}"
                m["swap_usd"] = f"{swap:.2f}"
        out.append(m)
    return out


def r_multiple(row, m, info):
    """R = realized USD / risked USD, where risk uses the LOGGED sl_distance."""
    if not m.get("pnl_usd"):
        return ""
    sl_txt = row.get("sl_distance", "")
    try:
        sl = float(sl_txt)
    except (TypeError, ValueError):
        return ""
    si = info.get(m["symbol"])
    if si is None or sl <= 0:
        return ""
    vol = float(row.get("volume") or 0)
    risk = sl * vol * si.trade_contract_size
    return f"{float(m['pnl_usd']) / risk:.2f}" if risk else ""


def cmd_scan(a):
    rows = _log_rows()
    groups, info = fetch_deals(a.days)
    matches = match(rows, groups, info)
    if not matches:
        print("[INFO] no FRIVAL-commented deals found in MT5 history")
        print(f"       scanned last {a.days} days, prefix={COMMENT_PREFIX}")
        return
    print(f"{'log_id':7s} {'symbol':7s} {'status':13s} {'in':>3s} {'out':>4s} "
          f"{'entry':>10s} {'exit':>10s} {'pnl':>8s} {'R':>6s}  comment")
    for m in matches:
        row = next(r for r in rows if r.get("log_id") == m["log_id"])
        rv = r_multiple(row, m, info)
        print(f"{m['log_id']:7s} {m['symbol']:7s} {m['status_log']:13s} {m['n_in']:3d} {m['n_out']:4d} "
              f"{m['entry_price'] or '-':>10s} {m['exit_price'] or '-':>10s} "
              f"{m['pnl_usd'] or '-':>8s} {rv or '-':>6s}  {m['comment_matched']}")


def cmd_apply(a):
    rows = _log_rows()
    groups, info = fetch_deals(a.days)
    matches = match(rows, groups, info)
    if a.id:
        matches = [m for m in matches if m["log_id"] == a.id]
    if not matches:
        print("[INFO] nothing to apply")
        return
    for m in matches:
        row = next(r for r in rows if r.get("log_id") == m["log_id"])
        if m["entry_price"]:
            row["fill_price"] = m["entry_price"]
            row["fill_time_local"] = m["entry_time_local"]
        if m["exit_price"]:
            row["exit_price"] = m["exit_price"]
            row["exit_time_local"] = m["exit_time_local"]
            row["pnl_usd"] = m["pnl_usd"]
            row["exit_reason"] = "BROKER_DEAL_HISTORY"
            row["status"] = "CLOSED"
        else:
            row["status"] = "OPEN"
        row["r_multiple"] = r_multiple(row, m, info)
        print(f"[{m['log_id']}] {m['symbol']} status={row['status']} "
              f"pnl={row['pnl_usd'] or '-'} R={row['r_multiple'] or '-'}")
    _save(rows)
    print("[OK] trade_log.csv updated from broker history")


def cmd_audit(a):
    rows = _log_rows()
    groups, info = fetch_deals(a.days)
    print(f"log rows: {len(rows)}   deal groups with {COMMENT_PREFIX} comment: {len(groups)}")
    matched = {m["log_id"] for m in match(rows, groups, info)}
    for r in rows:
        lid = r.get("log_id")
        tag = "matched" if lid in matched else ("no broker deal" if r.get("status") in ("PENDING_FILL", "OPEN") else "terminal state")
        print(f"  {lid:7s} {r.get('symbol',''):7s} {r.get('status',''):13s} {r.get('setup_id',''):32s} {tag}")
    orphans = [k for k in groups if k[1] not in {r.get("setup_id") for r in rows}]
    for sym, cmt in orphans:
        print(f"  ORPHAN DEAL {sym} comment={cmt} not present in trade_log.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30,
                    help="history window for deal lookup (default 30)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("scan", help="report log <-> broker matches, write nothing")
    p_apply = sub.add_parser("apply", help="stamp confirmed matches into trade_log.csv")
    p_apply.add_argument("--id", help="apply a single log_id")
    sub.add_parser("audit", help="coverage report including orphan broker deals")
    args = ap.parse_args()
    fn = {"scan": cmd_scan, "apply": cmd_apply, "audit": cmd_audit}[args.cmd]
    fn(args)


if __name__ == "__main__":
    src = (Path(__file__).read_text(encoding="utf-8"))
    for bad in FORBIDDEN:
        if f"mt5.{bad}(" in src:
            print(f"[FATAL] forbidden call mt5.{bad} present in source")
            sys.exit(2)
    main()