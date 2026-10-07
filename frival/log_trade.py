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
from mt5_path import resolve_terminal_path

TERMINAL_PATH = resolve_terminal_path(HERE)

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
    "mae_usd", "mom_alignment", "be_executed", "notes",
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
        rows = list(csv.DictReader(f))
    # Collapse historical duplicate log_id rows, keeping the most recent. A
    # 2026-10-02..05 bug appended on re-emit, leaving stale first rows that
    # `order_executor.py place` then read (see the T032 block).
    last = {}
    for i, r in enumerate(rows):
        last[r.get("log_id")] = i
    keep = set(last.values())
    return [r for i, r in enumerate(rows) if i in keep]


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
        return f"{tr.tail(14).mean():.5f}"
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


def _resolve_entry_fill(row):
    """Return the broker's true opening price for this log row, or None.

    The signal entry is an intention; the fill is what the broker paid. Until
    2026-10-06 the fill was never written for pending orders, so `exit` fell
    back to the signal entry and mis-stated realised PnL (e.g. T028 booked
    -1.04 from 4142.75 instead of -0.75 from the 4142.46 fill). The opening
    deal carries the comment ``FRIVAL_<log_id>``; ``entry == DEAL_ENTRY_IN``
    excludes SL/TP/partial exits, whose comments are ``[sl ...]`` etc.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    if not mt5.initialize(path=TERMINAL_PATH):
        return None
    try:
        log_id = row.get("log_id") or ""
        symbol = row.get("symbol")
        frm = dt.datetime.utcnow() - dt.timedelta(days=14)
        to = dt.datetime.utcnow() + dt.timedelta(days=1)
        deals = mt5.history_deals_get(frm, to) or []
        exact = "FRIVAL_%s" % log_id
        candidates = [
            d for d in deals
            if d.symbol == symbol and d.entry == mt5.DEAL_ENTRY_IN
            and (d.comment or "") == exact
        ]
        if not candidates:
            candidates = [
                d for d in deals
                if d.symbol == symbol and d.entry == mt5.DEAL_ENTRY_IN
                and log_id and log_id in (d.comment or "")
            ]
        if not candidates:
            return None
        first = min(candidates, key=lambda d: d.time)
        return float(first.price)
    except Exception:
        return None
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _broker_field(symbol: str, field: str, default):
    """Read a numeric field from the broker's symbol spec, or `default`."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return default
    if not mt5.initialize(path=TERMINAL_PATH):
        return default
    try:
        info = mt5.symbol_info(symbol)
        if not info:
            return default
        return float(getattr(info, field, default))
    except Exception:
        return default
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _account_equity(default: float = EQUITY_REFERENCE) -> float:
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return default
    if not mt5.initialize(path=TERMINAL_PATH):
        return default
    try:
        acct = mt5.account_info()
        return float(acct.equity) if acct and acct.equity else default
    except Exception:
        return default
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _size_volume(symbol: str, entry: float, sl: float, risk_pct: float) -> float:
    """Risk-based position size, rounded DOWN to the broker lot step.

        volume = (equity * risk_pct/100) / (sl_distance * money_per_price_unit)

    This is the desk's mandatory sizing rule. It exists as code because the
    per-unit value differs ~1000x across symbols (XAUUSD 100, EURUSD 100000,
    USDJPY ~632): reusing a gold lot count on an FX pair undersizes risk by
    30-50x (ledger T017 0.01 lot = -$0.61, T025 0.02 lot = -$0.71).
    """
    import math
    sld = abs(entry - sl)
    mv = _money_per_price_unit_per_lot(symbol)
    if sld <= 0 or mv <= 0:
        return 0.0
    raw = (_account_equity() * risk_pct / 100.0) / (sld * mv)
    step = _broker_field(symbol, "volume_step", 0.01) or 0.01
    vmin = _broker_field(symbol, "volume_min", 0.01) or 0.01
    vol = math.floor(raw / step) * step
    return round(max(vol, 0.0), 2) if vol >= vmin else round(vmin, 2)


def _prior_h1_body(symbol: str):
    """Direction of the last COMPLETED H1 candle body: BULL, BEAR or FLAT.

    Logged against every signal so the momentum-alignment filter (no entries
    against the prior H1 body) can be MEASURED before it is ever hard-enforced.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return ""
    if not mt5.initialize(path=TERMINAL_PATH):
        return ""
    try:
        d = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 3)
        if d is None or len(d) < 2:
            return ""
        prev = d[-2]                      # -1 is the forming bar
        o = float(prev["open"]); c = float(prev["close"])
        if abs(c - o) < 1e-12:
            return "FLAT"
        return "BULL" if c > o else "BEAR"
    except Exception:
        return ""
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _momentum_alignment(side: str, body):
    if body == "BULL":
        return "ALIGNED" if side.upper() == "BUY" else "AGAINST"
    if body == "BEAR":
        return "ALIGNED" if side.upper() == "SELL" else "AGAINST"
    return body or ""


def _resolve_realised_from_broker(row):
    """Total realised USD for this trade's position, summed over ALL its deals
    (partials + final), keyed by the entry deal's position_id. Returns None when
    unavailable.

    cmd_exit computes PnL as (exit-entry) x full volume, which ignores partial
    closes: T041 booked +78.75 when the broker actually paid +38.47, because
    0.03 of the 0.05 had already been closed early at +6.81. The broker total is
    authoritative, so prefer it whenever history is available.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return None
    if not mt5.initialize(path=TERMINAL_PATH):
        return None
    try:
        log_id = row.get("log_id") or ""
        symbol = row.get("symbol")
        frm = dt.datetime.utcnow() - dt.timedelta(days=14)
        to = dt.datetime.utcnow() + dt.timedelta(days=1)
        deals = mt5.history_deals_get(frm, to) or []
        entry = None
        for d in deals:
            if (d.symbol == symbol and d.entry == mt5.DEAL_ENTRY_IN
                    and (d.comment or "") == "FRIVAL_%s" % log_id):
                entry = d
                break
        if entry is None:
            return None
        pid = entry.position_id
        return float(sum(d.profit for d in deals if d.position_id == pid))
    except Exception:
        return None
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
    if not a.volume and not a.risk_pct:
        raise SystemExit("signal needs either --volume or --risk-pct")
    local_ts, server_ts = _now()
    entry = float(a.entry)
    sl = float(a.sl)
    tp1 = float(a.tp1)
    tp2 = float(a.tp2) if a.tp2 else ""
    if getattr(a, "risk_pct", None):
        volume = _size_volume(a.symbol, entry, sl, float(a.risk_pct))
        if volume <= 0:
            raise SystemExit("risk-based sizing failed: check entry/sl and symbol spec")
    else:
        volume = float(a.volume)
    direction = 1.0 if a.side.upper() == "BUY" else -1.0

    sl_dist = abs(entry - sl)
    rr1 = abs(tp1 - entry) / sl_dist if sl_dist else 0.0
    rr2 = abs(float(tp2) - entry) / sl_dist if (tp2 and sl_dist) else ""
    mv = _money_per_price_unit_per_lot(a.symbol)
    eq_now = _account_equity()
    risk = sl_dist * mv * volume
    srv_hour = int(server_ts[11:13])
    body = _prior_h1_body(a.symbol)
    mom = _momentum_alignment(a.side, body)

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
        "volume": f"{volume:.2f}",
        "entry_price": a.entry,
        "stop_loss": a.sl,
        "tp1": a.tp1,
        "tp2": a.tp2 or "",
        "sl_distance": f"{sl_dist:.5f}",
        "expected_rr_tp1": f"{rr1:.2f}",
        "expected_rr_tp2": f"{rr2:.2f}" if rr2 else "",
        "atr_h1_at_signal": _atr(__import__("MetaTrader5").TIMEFRAME_H1, symbol=a.symbol),
        "atr_m5_at_signal": _atr(__import__("MetaTrader5").TIMEFRAME_M5, symbol=a.symbol),
        "session": _session(srv_hour),
        "htf_bias": a.bias,
        "trigger_condition": a.trigger,
        "risk_usd": f"{risk:.2f}",
        "risk_pct_equity": f"{risk / eq_now * 100:.2f}" if eq_now else "",
        "swap_rate_estimate": a.swap,
        "threshold_override": "YES" if rr1 < MIN_RR else "NO",
        "status": "PENDING_FILL",
        "be_trigger_price": f"{entry - direction * sl_dist * 0.5:.5f}",
        "mom_alignment": mom,
        "notes": a.notes,
    })
    # Upsert by log_id: re-emitting a corrected signal for the same id must
    # UPDATE the existing row, never append a second one. Before 2026-10-06
    # this appended, so `order_executor.py place` read the stale first row and
    # a corrected stop could not clear the ATR floor (the T032 block).
    idx = next((i for i, rr in enumerate(rows) if rr.get("log_id") == log_id), None)
    if idx is None:
        rows.append(row)
        action = "logged"
    else:
        row["logged_at_local"] = rows[idx].get("logged_at_local") or local_ts
        row["logged_at_server"] = rows[idx].get("logged_at_server") or server_ts
        rows[idx] = row
        action = "updated"
    _save(rows)
    flag = "  << BELOW 2:1 THRESHOLD" if rr1 < MIN_RR else ""
    print(f"[{log_id}] {action} {a.side.upper()} {volume:.2f} @ {entry} "
          f"SL {sl} TP1 {tp1}{flag}")
    print(f"  risk ${risk:.2f} ({row['risk_pct_equity']}% of equity)  "
          f"RR1 {rr1:.2f}  ATR_H1 {row['atr_h1_at_signal']}  ATR_M5 {row['atr_m5_at_signal']}  "
          f"MOM {mom or 'n/a'}")
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
    raw_fill = (r.get("fill_price") or "").strip()
    if raw_fill:
        entry = float(raw_fill)
    else:
        # Fill unknown in the log (pending order filled at the broker): resolve
        # the true opening price so PnL/R are computed from the fill, not the
        # signal entry. Fall back to the signal entry only if history is absent.
        resolved = _resolve_entry_fill(r)
        if resolved is None:
            entry = float(r["entry_price"])
        else:
            entry = resolved
            r["fill_price"] = f"{entry:g}"
    volume = float(r["volume"])
    sign = 1.0 if r["side"].upper() == "BUY" else -1.0

    # The per-symbol USD value of a 1.00 price move must come from the broker's
    # contract data. It is NOT 100 for every symbol:
    #   XAUUSD 100 / EURUSD 100000 / USDJPY ~632.
    # Until 2026-10-05 this function used the module constant (100.0) directly,
    # so a USDJPY exit reported -0.11 when the broker paid -0.71, and the
    # r_multiple formula (pnl / sl_distance * volume * value) was dimensionally
    # wrong: it multiplied where it should have divided by risk_usd.
    mv = _money_per_price_unit_per_lot(r["symbol"])
    # Prefer the broker's realised total (sums partials + final); fall back to
    # the price-delta estimate when history is unavailable.
    broker_total = _resolve_realised_from_broker(r)
    if broker_total is not None:
        pnl = broker_total
    else:
        pnl = (float(a.price) - entry) * sign * volume * mv
    risk_usd = float(r["sl_distance"]) * volume * mv
    r_mult = (pnl / risk_usd) if risk_usd else 0.0
    r["exit_time_local"] = local_ts
    r["exit_price"] = a.price
    r["exit_reason"] = a.reason
    r["pnl_usd"] = f"{pnl:.2f}"
    r["r_multiple"] = f"{r_mult:.2f}"
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
    def _num(row, key):
        v = (row.get(key) or "").strip()
        return float(v) if v else 0.0

    pnl = sum(_num(r, "pnl_usd") for r in closed)
    rs = [float(r["r_multiple"]) for r in closed]
    wins = [r for r in rs if r > 0]
    print(f"total PnL ${pnl:.2f}  total R {sum(rs):.2f}  "
          f"win rate {len(wins)}/{len(rs)} = {len(wins)/len(rs)*100:.1f}%")
    print(f"avg R {sum(rs)/len(rs):.2f}  best {max(rs):.2f}  worst {min(rs):.2f}")
    ov = [r for r in rows if r.get("threshold_override") == "YES"]
    print(f"below-threshold signals logged: {len(ov)}")


def cmd_size(a):
    """Print the risk-based lot size for a symbol/entry/SL (the sizing rule)."""
    entry = float(a.entry); sl = float(a.sl)
    sld = abs(entry - sl)
    mv = _money_per_price_unit_per_lot(a.symbol)
    eq = _account_equity()
    rp = float(a.risk_pct)
    vol = _size_volume(a.symbol, entry, sl, rp)
    risk = sld * vol * mv
    print(f"{a.symbol}: equity ${eq:.2f}  risk {rp:.2f}% = ${eq * rp / 100.0:.2f}")
    print(f"  entry {entry}  SL {sl}  sl_distance {sld:.5f}  money_per_price_unit {mv:.4f}")
    print(f"  volume {vol:.2f} lots  ->  realised risk ${risk:.2f} "
          f"({risk / eq * 100:.2f}% of equity)" if eq else f"  volume {vol:.2f} lots")
    print(f"  use: log_trade.py signal ... --volume {vol:.2f}  (or --risk-pct {rp:g})")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("signal")
    s.add_argument("--id")
    s.add_argument("--setup-id")
    s.add_argument("--symbol", default="XAUUSD")
    s.add_argument("--side", required=True, choices=["BUY", "SELL"])
    s.add_argument("--order-type", default="LIMIT", choices=["LIMIT", "STOP", "MARKET"])
    s.add_argument("--volume")
    s.add_argument("--risk-pct")
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
    sz = sub.add_parser("size")
    sz.add_argument("--symbol", default="XAUUSD")
    sz.add_argument("--entry", required=True)
    sz.add_argument("--sl", required=True)
    sz.add_argument("--risk-pct", default="5.0")
    sz.set_defaults(func=cmd_size)

    a = ap.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()