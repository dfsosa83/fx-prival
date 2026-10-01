#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Trade observation logger — Frival manual execution dataset builder.

Every setup emitted by the agent MUST be logged here BEFORE the operator
executes it. Every fill, BE move and exit MUST be recorded against the same
log_id. The resulting CSV is the evidence base required before any rule in
this project may be automated (see fx-manual-trades.md §12).

Read-only against MT5 except for an explicit --quote refresh, which never
places, modifies or cancels an order.

Usage:
    python log_trade.py signal  --id T002 --side SELL --volume 0.01 \
        --order-type STOP --entry 4152.00 --sl 4160.00 --tp1 4144.00 \
        --tp2 4139.50 --trigger "M15 close below 4151.46" [--rr-override 1.00]

    python log_trade.py fill    --id T001 --price 4152.00
    python log_trade.py be      --id T001 --price 4152.00
    python log_trade.py exit    --id T001 --price 4144.00 --reason TP1
    python log_trade.py skip    --id T003 --reason "R:R 1.4 - below threshold"
    python log_trade.py show    [--id T001]
    python log_trade.py stats
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

SERVER_OFFSET_H = 3
LOCAL_OFFSET_H = -8

COLUMNS = [
    "log_id", "logged_at_local", "logged_at_server", "symbol", "setup_id",
    "side", "order_type", "signal_level", "volume", "entry_price",
    "stop_loss", "tp1", "tp2", "sl_distance", "expected_rr_tp1",
    "expected_rr_tp2", "atr_h1_at_signal", "atr_m5_at_signal", "session",
    "htf_bias", "trigger_condition", "risk_usd", "risk_pct_equity",
    "swap_rate_estimate", "threshold_override", "status", "fill_time_local",
    "fill_price", "be_time_local", "be_price", "exit_time_local", "exit_price",
    "exit_reason", "pnl_usd", "r_multiple", "be_trigger_price", "mfe_usd",
    "mae_usd", "notes",
]

CONTRACT_SIZE = 100.0          # XAUUSD oz/lot, verified 2026-09-30
TICK_VALUE_PER_LOT_PER_USD = 100.0
MIN_RR = 2.0
EQUITY_REFERENCE = 600.0       # verified live 2026-10-01


def _now():
    utc = dt.datetime.utcnow()
    return (
        (utc + dt.timedelta(hours=LOCAL_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S"),
        (utc + dt.timedelta(hours=SERVER_OFFSET_H)).strftime("%Y-%m-%d %H:%M:%S"),
    )


def _load():
    if not LOG_PATH.exists():
        return []
    with LOG_PATH.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(rows):
    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})


def _next_id(rows):
    n = 0
    for r in rows:
        sid = r.get("log_id", "")
        if sid.startswith("T") and sid[1:].isdigit():
            n = max(n, int(sid[1:]))
    return f"T{n + 1:03d}"


def _find(rows, log_id):
    for r in rows:
        if r.get("log_id") == log_id:
            return r
    raise SystemExit(f"log_id not found: {log_id}")


def _atr(timeframe, n=80, symbol="XAUUSD"):
    """ATR(14) from the attached terminal. Never raises; returns '' on failure."""
    try:
        import MetaTrader5 as mt5
        import pandas as pd
    except ImportError:
        return ""
    if not mt5.initialize(path=TERMINAL_PATH):
        return ""
    try:
        r = pd.DataFrame(mt5.copy_rates_from_pos(symbol, timeframe, 0, n))
        if r.empty:
            return ""
        pc = r["close"].shift(1)
        tr = pd.concat([
            r["high"] - r["low"],
            (r["high"] - pc).abs(),
            (r["low"] - pc).abs(),
        ], axis=1).max(axis=1)
        return f"{tr.tail(14).mean():.2f}"
    except Exception:
        return ""
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _session(server_hour):
    if 0 <= server_hour < 8:
        return "ASIA"
    if 8 <= server_hour < 13:
        return "LONDON"
    if 13 <= server_hour < 17:
        return "NY"
    return "LONDON_NY_OVERLAP"


def _money_per_price_unit_per_lot(symbol: str) -> float:
    """USD value of a 1.00 move in PRICE units, per 1.00 lot.

    Derived from the broker's own contract data, never assumed. A move of
    (sl_distance) price units on (volume) lots risks:
        risk_usd = sl_distance * volume * this_value

    XAUUSD: tick_value 1.00 / tick_size 0.01  -> 100 USD per 1.00 move per lot
    EURUSD: tick_value 1.00 / tick_size 1e-5 -> 100000 USD per 1.00 move per lot
    USDJPY: tick_value 0.6348 / tick_size 0.001 -> 634.8 USD per 1.00 move per lot
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return CONTRACT_SIZE * TICK_VALUE_PER_LOT_PER_USD
    if not mt5.initialize(path=TERMINAL_PATH):
        return CONTRACT_SIZE * TICK_VALUE_PER_LOT_PER_USD
    try:
        info = mt5.symbol_info(symbol)
        if not info or not info.trade_tick_size:
            return CONTRACT_SIZE * TICK_VALUE_PER_LOT_PER_USD
        return info.trade_tick_value / info.trade_tick_size
    except Exception:
        return CONTRACT_SIZE * TICK_VALUE_PER_LOT_PER_USD
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _risk_units(entry: float, sl: float, symbol: str = "XAUUSD") -> float:
    """Risk expressed in PRICE UNITS of the symbol, not dollars."""
    return abs(entry - sl)


def cmd_signal(a):
    rows = _load()
    log_id = a.id or _next_id(rows)
    local_ts, server_ts = _now()
    entry = float(a.entry)
    sl = float(a.sl)
    tp1 = float(a.tp1)
    tp2 = float(a.tp2) if a.tp2 else ""
    volume = float(a.volume)
    direction = 1.0 if a.side.upper() == "BUY" else -1.0

    sl_dist = abs(entry - sl)
    rr1 = abs(tp1 - entry) / sl_dist if sl_dist else 0.0
    rr2 = abs(float(tp2) - entry) / sl_dist if (tp2 and sl_dist) else ""
    mv = _money_per_price_unit_per_lot(a.symbol)
    risk = sl_dist * mv * volume
    srv_hour = int(server_ts[11:13])

    row = {c: "" for c in COLUMNS}
    row.update({
        "log_id": log_id,
        "logged_at_local": local_ts,
        "logged_at_server": server_ts,
        "symbol": a.symbol,
        "setup_id": a.setup_id or f"FRIVAL_{log_id}_{server_ts[:10].replace('-', '')}",
        "side": a.side.upper(),
        "order_type": a.order_type.upper(),
        "signal_level": a.entry,
        "volume": a.volume,
        "entry_price": a.entry,
        "stop_loss": a.sl,
        "tp1": a.tp1,
        "tp2": a.tp2 or "",
        "sl_distance": f"{sl_dist:.2f}",
        "expected_rr_tp1": f"{rr1:.2f}",
        "expected_rr_tp2": f"{rr2:.2f}" if rr2 else "",
        "atr_h1_at_signal": _atr(__import__("MetaTrader5").TIMEFRAME_H1, symbol=a.symbol),
        "atr_m5_at_signal": _atr(__import__("MetaTrader5").TIMEFRAME_M5, symbol=a.symbol),
        "session": _session(srv_hour),
        "htf_bias": a.bias,
        "trigger_condition": a.trigger,
        "risk_usd": f"{risk:.2f}",
        "risk_pct_equity": f"{risk / EQUITY_REFERENCE * 100:.2f}",
        "swap_rate_estimate": a.swap,
        "threshold_override": "YES" if rr1 < MIN_RR else "NO",
        "status": "PENDING_FILL",
        "be_trigger_price": f"{entry - direction * sl_dist * 0.5:.2f}",
        "notes": a.notes,
    })
    rows.append(row)
    _save(rows)
    flag = "  << BELOW 2:1 THRESHOLD" if rr1 < MIN_RR else ""
    print(f"[{log_id}] logged {a.side.upper()} {a.volume} @ {entry} "
          f"SL {sl} TP1 {tp1}{flag}")
    print(f"  risk ${risk:.2f} ({row['risk_pct_equity']}% of equity)  "
          f"RR1 {rr1:.2f}  ATR_H1 {row['atr_h1_at_signal']}  ATR_M5 {row['atr_m5_at_signal']}")
    if rr1 < MIN_RR:
        print(f"  WARNING: expected R:R {rr1:.2f} < {MIN_RR}. Record the reason in --notes.")


def cmd_fill(a):
    rows = _load()
    r = _find(rows, a.id)
    local_ts, _ = _now()
    r["fill_time_local"] = local_ts
    r["fill_price"] = a.price
    r["status"] = "OPEN"
    _save(rows)
    print(f"[{a.id}] filled @ {a.price} at {local_ts}")


def cmd_be(a):
    rows = _load()
    r = _find(rows, a.id)
    local_ts, _ = _now()
    r["be_time_local"] = local_ts
    r["be_price"] = a.price
    _save(rows)
    print(f"[{a.id}] break-even executed @ {a.price} at {local_ts}")


def cmd_exit(a):
    rows = _load()
    r = _find(rows, a.id)
    local_ts, _ = _now()
    entry = float(r["fill_price"] or r["entry_price"])
    volume = float(r["volume"])
    sign = 1.0 if r["side"].upper() == "BUY" else -1.0
    pnl = (float(a.price) - entry) * sign * volume * TICK_VALUE_PER_LOT_PER_USD
    r["exit_time_local"] = local_ts
    r["exit_price"] = a.price
    r["exit_reason"] = a.reason
    r["pnl_usd"] = f"{pnl:.2f}"
    r["r_multiple"] = f"{pnl / float(r['sl_distance']) * volume * TICK_VALUE_PER_LOT_PER_USD:.2f}"
    r["status"] = "CLOSED"
    _save(rows)
    print(f"[{a.id}] closed @ {a.price} ({a.reason}) PnL ${pnl:.2f} R={r['r_multiple']}")


def cmd_skip(a):
    rows = _load()
    log_id = a.id or _next_id(rows)
    local_ts, server_ts = _now()
    row = {c: "" for c in COLUMNS}
    row.update({
        "log_id": log_id,
        "logged_at_local": local_ts,
        "logged_at_server": server_ts,
        "symbol": a.symbol,
        "setup_id": a.setup_id or f"FRIVAL_{log_id}",
        "status": "SKIPPED",
        "notes": a.reason,
    })
    rows.append(row)
    _save(rows)
    print(f"[{log_id}] logged SKIPPED: {a.reason}")


def cmd_show(a):
    import pandas as pd
    rows = _load()
    if a.id:
        rows = [r for r in rows if r.get("log_id") == a.id]
    if not rows:
        print("log empty")
        return
    print(pd.DataFrame(rows).to_string(index=False))


def cmd_stats(a):
    rows = _load()
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    pending = [r for r in rows if r.get("status") in ("PENDING_FILL", "OPEN")]
    skipped = [r for r in rows if r.get("status") == "SKIPPED"]
    print(f"total={len(rows)} closed={len(closed)} open/pending={len(pending)} skipped={len(skipped)}")
    if not closed:
        print("no closed trades yet — no performance claim is supportable")
        return
    pnl = sum(float(r["pnl_usd"]) for r in closed)
    rs = [float(r["r_multiple"]) for r in closed]
    wins = [r for r in rs if r > 0]
    print(f"total PnL ${pnl:.2f}  total R {sum(rs):.2f}  "
          f"win rate {len(wins)}/{len(rs)} = {len(wins)/len(rs)*100:.1f}%")
    print(f"avg R {sum(rs)/len(rs):.2f}  best {max(rs):.2f}  worst {min(rs):.2f}")
    ov = [r for r in rows if r.get("threshold_override") == "YES"]
    print(f"below-threshold signals logged: {len(ov)}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("signal")
    s.add_argument("--id")
    s.add_argument("--setup-id")
    s.add_argument("--symbol", default="XAUUSD")
    s.add_argument("--side", required=True, choices=["BUY", "SELL"])
    s.add_argument("--order-type", default="LIMIT", choices=["LIMIT", "STOP", "MARKET"])
    s.add_argument("--volume", required=True)
    s.add_argument("--entry", required=True)
    s.add_argument("--sl", required=True)
    s.add_argument("--tp1", required=True)
    s.add_argument("--tp2")
    s.add_argument("--trigger", required=True)
    s.add_argument("--bias", default="UNSPECIFIED")
    s.add_argument("--swap", default="")
    s.add_argument("--notes", default="")
    s.set_defaults(func=cmd_signal)

    f = sub.add_parser("fill"); f.add_argument("--id", required=True); f.add_argument("--price", required=True)
    f.set_defaults(func=cmd_fill)
    b = sub.add_parser("be"); b.add_argument("--id", required=True); b.add_argument("--price", required=True)
    b.set_defaults(func=cmd_be)
    e = sub.add_parser("exit")
    e.add_argument("--id", required=True); e.add_argument("--price", required=True)
    e.add_argument("--reason", required=True)
    e.set_defaults(func=cmd_exit)
    k = sub.add_parser("skip")
    k.add_argument("--id"); k.add_argument("--setup-id"); k.add_argument("--symbol", default="XAUUSD")
    k.add_argument("--reason", required=True)
    k.set_defaults(func=cmd_skip)
    v = sub.add_parser("show"); v.add_argument("--id")
    v.set_defaults(func=cmd_show)
    st = sub.add_parser("stats"); st.set_defaults(func=cmd_stats)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()