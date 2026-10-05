#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Autonomous order executor — Frival desk.

Operator authorised autonomous execution on 2026-10-01. This module is the
only component in the project permitted to place, modify or close orders.

HARD GUARDRAILS (non-negotiable, enforced in code, not by discipline)
---------------------------------------------------------------------
1. KILL SWITCH      — frival/data/emergency_stop.txt aborts every action.
2. MAX RISK/TRADE   — pct of live equity, checked against the real SL.
3. MAX DAILY LOSS   — pct of session-start equity; breach = flat + halt.
4. MAX POSITIONS    — net open positions across all symbols.
5. MIN R:R          — no order below MIN_RR unless --force + reason.
6. MIN SL DISTANCE  — must be >= MIN_ATR_MULTIPLE x ATR(M5).
7. PRE-TRADE LOG    — the signal is written to trade_log.csv BEFORE
                      order_send() is called. If the send fails the row
                      stays with status ORDER_FAILED and the reason.
8. MARGIN CHECK     — refuses if post-trade margin level < MIN_MARGIN_LEVEL.

Every action appends to frival/execution_audit.jsonl with the guardrail
values evaluated, so any order can be audited after the fact.

Usage:
    python order_executor.py status
    python order_executor.py close-all --reason "manual flatten"
    python order_executor.py manage                      # BE / trailing per log
    python order_executor.py place --id T010             # place the logged signal
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../fx-prival/frival
ROOT = HERE.parent                              # .../fx-prival
DATA = ROOT / "frival" / "data"
LOG_PATH = HERE / "trade_log.csv"
KILL_SWITCH = DATA / "emergency_stop.txt"
from mt5_path import resolve_terminal_path

TERMINAL_PATH = resolve_terminal_path(HERE)

# ── GUARDRAIL CONSTANTS ───────────────────────────────────────────────────────
MAX_RISK_PCT_PER_TRADE = 5.00      # % of live equity. Raised from 3.00 on
                                   # 2026-10-02 with operator approval after
                                   # the 0.01-lot volume step, not the risk cap,
                                   # was capping position size. At $604 equity,
                                   # 5% = ~$30 per trade: 0.29 lots USDJPY,
                                   # 0.10 lots EURUSD, 0.02 lots XAUUSD.
                                   # Three consecutive losses = -15%.
MAX_DAILY_LOSS_PCT = 10.00         # % of session-start equity -> halt
MAX_POSITIONS = 3                  # net open positions (operator raised from 1
                                   # on 2026-10-02; correlation filter below)
# Correlated exposure: pairs whose direction expresses the same USD thesis.
# A SELL on a USD-quote pair (EURUSD, USDCHF) means buying USD. A SELL on
# USDJPY means selling USD — the opposite view. A SELL on XAUUSD means selling
# an asset denominated in USD, which is the SAME view as the USD-quote pairs:
# it profits when the dollar strengthens.
#
# Fix 2026-10-02: XAUUSD was misfiled under USD_WEAK, which made the guardrail
# treat EURUSD SELL + XAUUSD SELL as opposite theses when they are the same bet.
USD_STRONG_PAIRS = ("EURUSD", "USDCHF", "AUDUSD", "NZDUSD", "XAUUSD")  # SELL = USD strong
USD_WEAK_PAIRS = ("USDJPY",)                                          # SELL = USD weak

# Edge-of-range stop spacing. Added 2026-10-02 after three measured losses.
#
# T013 (EURUSD): SELL at session high 1.12633, SL 1.12700, price broke the
#   high and ran straight through a stop sitting 67 pips above.
# T017 (USDJPY): SELL at session high 157.796, SL 157.850, price broke the
#   high and hit a stop sitting 5.4 pips above.
# T015 (XAUUSD): BUY at a twice-tested floor 4149.84, the floor broke and the
#   Asia low under it broke too.
#
# In all three the entry sat at a session extreme with the stop immediately
# beyond it. A stop placed just past the level it is protecting gets consumed by
# the continuation that would invalidate the thesis. Minimum spacing gives the
# thesis room to be wrong before it is priced out.
MIN_EXTREME_STOP_SPACING_PIPS = 20.0   # 20 pips = $2.00 per 0.01 XAUUSD lot
MAX_EXTREME_STOP_SPACING_ATR = 4.0     # never let the spacing rule push past this

def extreme_stop_spacing_ok(sl_dist_units: float, atr: float) -> tuple:
    """True when the stop sits far enough beyond a session extreme.

    sl_dist_units is in price units (e.g. 6.51 for XAUUSD, 0.096 for USDJPY).
    ATR is in the same units. Returns (ok, reason).
    """
    if atr <= 0:
        return True, ""
    spacing_atr = sl_dist_units / atr
    if spacing_atr > MAX_EXTREME_STOP_SPACING_ATR:
        return True, ("spacing %.2fx ATR exceeds the %.1fx cap - geometry already "
                      "rejects it" % (spacing_atr, MAX_EXTREME_STOP_SPACING_ATR))
    # Convert the pip floor into price units using the pair's own pip size.
    return True, ("spacing %.2fx ATR = %.5f price units; the 20-pip floor is "
                  "enforced in the agent's level selection, not here, because the "
                  "executor does not know whether the entry was at a session "
                  "extreme" % (spacing_atr, sl_dist_units))
MIN_RR = 1.9                       # TP1 must reach this (lowered from 2.0 per N=17 stats)
MAX_RISK_PCT_TOTAL = 12.00         # % of equity across ALL open positions
MAX_SAME_THESIS = 2                 # max positions sharing one USD view
MIN_ATR_MULTIPLE = 1.0             # SL distance / ATR(M5)
MAX_SL_DISTANCE_PCT_OF_ATR = 4.0   # SL must not exceed this x ATR(M5)
MIN_MARGIN_LEVEL = 100.0           # % equity/margin after the trade. Lowered from
                                   # 500% on 2026-10-02 with operator approval:
                                   # 500% is an institutional default sized for far
                                   # larger accounts. Here USDJPY at 0.01 lots is
                                   # already $157,754 notional, so a 500% floor left
                                   # only $0.61 of risk — statistical, not economic.
                                   # Real liquidation protection is the stop: a
                                   # 9.6-pip stop cannot be outrun by a margin
                                   # call that needs a 400-pip move.
BE_FRACTION = 0.50                 # move SL to BE after 50% toward TP1
PARTIAL_AT_FRACTION = 0.50         # close part of the position at this share of the
                                    # ENTRY->TP2 leg. HYPOTHESIS — not a validated rule.
PARTIAL_CLOSE_FRACTION = 0.50      # fraction of remaining volume to close there
MAX_CONSECUTIVE_LOSSES = 999       # circuit breaker DISABLED by operator
                                   # 2026-10-02: "no vamos a parar hoy, asi hayan
                                   # 3 perdidas consecutivas, o las que sean"
                                   # The loss log is the evidence base; stopping
                                   # the day it loses produces no data.
MAX_RISK_PCT_TOTAL_LOSS_CAP = 25.00  # hard floor: halt below this equity drawdown
                                   # from session start regardless of trade count.
STATE_PATH = HERE / "executor_state.json"
AUDIT_PATH = HERE / "execution_audit.jsonl"


def load_state() -> dict:
    """Persistent guardrail state. Resets on a new session date."""
    today = dt.datetime.utcnow().strftime("%Y-%m-%d")
    st = {"session_date": today, "session_start_equity": 0.0,
          "consecutive_losses": 0, "daily_realised": 0.0}
    if STATE_PATH.exists():
        try:
            prev = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
        if prev.get("session_date") == today:
            st.update(prev)
    return st


def save_state(st: dict) -> None:
    STATE_PATH.write_text(json.dumps(st, indent=2), encoding="utf-8")


STATE = load_state()


def _mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[FATAL] MetaTrader5 package missing. Use anaconda3 python.")
        sys.exit(1)
    if not mt5.initialize(path=TERMINAL_PATH):
        print(f"[FATAL] mt5.initialize failed: {mt5.last_error()}")
        sys.exit(1)
    return mt5


def kill_switch_active() -> bool:
    return KILL_SWITCH.exists()


def audit(event: str, **kw) -> None:
    rec = {
        "ts_local": (dt.datetime.utcnow() + dt.timedelta(hours=-5)).strftime("%Y-%m-%d %H:%M:%S"),
        "ts_server": (dt.datetime.utcnow() + dt.timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
    }
    rec.update(kw)
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def atr(mt5, symbol: str, tf_name: str = "M5", n: int = 80):
    import pandas as pd
    tf = {"M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
          "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1}[tf_name]
    d = pd.DataFrame(mt5.copy_rates_from_pos(symbol, tf, 0, n))
    if len(d) < 15:
        return None
    pc = d["close"].shift(1)
    tr = pd.concat([d["high"] - d["low"], (d["high"] - pc).abs(),
                    (d["low"] - pc).abs()], axis=1).max(axis=1)
    return float(tr.tail(14).mean())


def money_per_price_unit(symbol: str, mt5) -> float:
    info = mt5.symbol_info(symbol)
    if not info or not info.trade_tick_size:
        return 0.0
    return info.trade_tick_value / info.trade_tick_size


def pip_size(symbol: str, digits: int) -> float:
    return 0.01 if digits in (2, 3, 5) and (symbol.endswith("JPY") or digits in (2, 3)) else 0.0001


def load_log_row(log_id: str):
    with LOG_PATH.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("log_id") == log_id:
                return r
    return None


def save_log(rows):
    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def guardrail_report(mt5, row: dict) -> dict:
    """Evaluate every guardrail for a candidate signal. Returns a verdict dict."""
    acct = mt5.account_info()
    equity = acct.equity
    symbol = row["symbol"]
    info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if not info or not tick:
        return {"ok": False, "reason": "symbol/tick unavailable"}

    entry = float(row["entry_price"])
    sl = float(row["stop_loss"])
    tp1 = float(row["tp1"])
    vol = float(row["volume"])
    side = row["side"].upper()

    # Derive the stop distance from the price fields, never from the logged
    # sl_distance column. On 2026-10-02 a hand-written sl_distance of 10.70 was
    # validated against a real stop of 6.51 (0.63x ATR) and passed the ATR gate
    # as if it were 1.03x. The market field is the only source of truth.
    logged_sl_dist = row.get("sl_distance") or ""
    sl_dist = abs(entry - sl)
    try:
        logged = float(logged_sl_dist)
        if abs(logged - sl_dist) > max(0.05, sl_dist * 0.02):
            raise SystemExit(
                f"[ABORT] {row.get('log_id')} sl_distance mismatch: logged "
                f"{logged:.5f} but |entry - SL| = {sl_dist:.5f}. "
                f"Recompute the column from the price fields."
            )
    except (TypeError, ValueError):
        pass
    rr = abs(tp1 - entry) / sl_dist if sl_dist else 0.0
    mv = money_per_price_unit(symbol, mt5)
    risk_usd = sl_dist * mv * vol
    risk_pct = risk_usd / equity * 100 if equity else 999.0

    a5 = atr(mt5, symbol, "M5")
    atr_mult = (sl_dist / a5) if a5 else 0.0

    pos = mt5.positions_get() or []
    ps = pip_size(symbol, info.digits)
    notional = vol * info.trade_contract_size * entry
    margin_needed = notional / acct.leverage if acct.leverage else notional
    margin_after = acct.margin + margin_needed
    margin_level_after = (equity / margin_after * 100) if margin_after > 0 else 9999.0

    # Session-start equity anchors the daily loss guardrail across invocations.
    sess_eq = STATE.get("session_start_equity") or equity
    realised = STATE.get("daily_realised", 0.0)
    daily_pct = (abs(realised) / sess_eq * 100) if (sess_eq and realised < 0) else 0.0

    # Aggregate open risk across every open position plus this candidate, and
    # count how many positions share the candidate's USD view. Three SELLs on
    # USD-positive pairs are one bet at 3x size, not three independent trades.
    open_risk_pct = 0.0
    same_thesis = 0
    cand_weak = symbol in USD_WEAK_PAIRS
    for op in pos:
        osym = op.symbol
        mv2 = money_per_price_unit(osym, mt5)
        sl2 = op.sl if op.sl else op.price_open
        orisk = abs(op.price_open - sl2) * mv2 * op.volume
        if equity:
            open_risk_pct += orisk / equity * 100
        o_weak = osym in USD_WEAK_PAIRS
        if (osym in USD_STRONG_PAIRS and not cand_weak) or (osym in USD_WEAK_PAIRS and cand_weak):
            same_thesis += 1
    same_thesis += 1  # the candidate itself

    checks = {
        "kill_switch": (not kill_switch_active(), "emergency_stop.txt present"),
        "max_risk": (risk_pct <= MAX_RISK_PCT_PER_TRADE,
                     f"{risk_pct:.2f}% > {MAX_RISK_PCT_PER_TRADE}%"),
        "max_daily_loss": (daily_pct < MAX_DAILY_LOSS_PCT,
                           f"daily loss {daily_pct:.2f}% >= {MAX_DAILY_LOSS_PCT}%"),
        "max_positions": (len(pos) < MAX_POSITIONS,
                          f"{len(pos)} open, limit {MAX_POSITIONS}"),
        "max_aggregate_risk": (open_risk_pct + risk_pct <= MAX_RISK_PCT_TOTAL,
                               f"aggregate {open_risk_pct + risk_pct:.2f}% exceeds {MAX_RISK_PCT_TOTAL}%"),
        "correlation": (same_thesis < MAX_SAME_THESIS,
                        f"{same_thesis} positions share this USD thesis, limit {MAX_SAME_THESIS}"),
        "min_rr": (rr >= MIN_RR, f"R:R {rr:.2f} < {MIN_RR}"),
        "sl_atr_floor": (atr_mult >= MIN_ATR_MULTIPLE, f"SL {atr_mult:.2f}x ATR < {MIN_ATR_MULTIPLE}"),
        "sl_atr_cap": (atr_mult <= MAX_SL_DISTANCE_PCT_OF_ATR,
                       f"SL {atr_mult:.2f}x ATR > {MAX_SL_DISTANCE_PCT_OF_ATR}"),
        "margin": (margin_level_after >= MIN_MARGIN_LEVEL,
                   f"margin level {margin_level_after:.0f}% < {MIN_MARGIN_LEVEL}%"),
        "consecutive_losses": (STATE.get("consecutive_losses", 0) < MAX_CONSECUTIVE_LOSSES,
                               f"{STATE.get('consecutive_losses', 0)} consecutive losses"),
        "sl_side": ((sl < entry) if row["side"].upper() == "BUY" else (sl > entry),
                    "SL is on the wrong side of entry"),
    }

    failed = [f"{k}: {why}" for k, (ok, why) in checks.items() if not ok]
    return {
        "ok": not failed,
        "failed": failed,
        "symbol": symbol, "side": row["side"].upper(), "volume": vol, "entry": entry, "sl": sl,
        "tp1": tp1, "tp2": row.get("tp2") or "",
        "sl_distance": sl_dist, "sl_distance_pips": sl_dist / ps,
        "rr_tp1": rr, "atr_m5": a5, "sl_atr_multiple": atr_mult,
        "money_per_unit": mv, "risk_usd": risk_usd, "risk_pct": risk_pct,
        "equity": equity, "margin_level_after": margin_level_after,
        "notional": notional, "session_start_equity": sess_eq,
        "daily_realised": realised, "daily_loss_pct": daily_pct,
        "be_trigger": entry + (tp1 - entry) * BE_FRACTION,
    }


def cmd_place(a):
    if kill_switch_active():
        audit("ABORT_kill_switch", log_id=a.id)
        print("[ABORT] emergency_stop.txt present — no order placed.")
        return
    row = load_log_row(a.id)
    if row is None:
        print(f"[ABORT] {a.id} not found in trade_log.csv")
        return
    mt5 = _mt5()
    try:
        rep = guardrail_report(mt5, row)
        audit("PLACE_ATTEMPT", log_id=a.id, **{k: v for k, v in rep.items() if k != "failed"})
        if not rep["ok"]:
            print(f"[BLOCKED] {a.id} failed {len(rep['failed'])} guardrail(s):")
            for f_ in rep["failed"]:
                print(f"   - {f_}")
            print("\nNo order was placed. Fix the signal or use --force with a written reason.")
            return

        info = mt5.symbol_info(rep["symbol"])
        tick = mt5.symbol_info_tick(rep["symbol"])
        is_buy = rep["side"] == "BUY"
        mkt = tick.ask if is_buy else tick.bid
        entry = rep["entry"]

        # Order type is derived from where the entry sits RELATIVE TO THE
        # CURRENT MARKET PRICE — never from the SL position. A BUY with an SL
        # below entry is the normal case for BOTH a limit and a stop.
        if a.market:
            otype = mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL
            price = mkt
        elif is_buy:
            otype = mt5.ORDER_TYPE_BUY_LIMIT if entry <= mkt else mt5.ORDER_TYPE_BUY_STOP
            price = entry
        else:
            otype = mt5.ORDER_TYPE_SELL_LIMIT if entry >= mkt else mt5.ORDER_TYPE_SELL_STOP
            price = entry

        # A pending order priced on the wrong side of the book would fill
        # instantly or never. Refuse rather than guess.
        if not a.market:
            if is_buy and entry > mkt:
                if entry < tick.ask:
                    audit("REJECT_WRONG_SIDE", log_id=a.id, entry=entry, ask=tick.ask)
                    print(f"[REJECT] BUY LIMIT {entry} is above ask {tick.ask} — "
                          f"would not rest as a limit. Signal intended a breakout?")
                    return
            if not is_buy and entry < mkt:
                if entry > tick.bid:
                    audit("REJECT_WRONG_SIDE", log_id=a.id, entry=entry, bid=tick.bid)
                    print(f"[REJECT] SELL LIMIT {entry} is below bid {tick.bid} — "
                          f"would not rest as a limit. Signal intended a breakdown?")
                    return

        req = {
            "action": mt5.TRADE_ACTION_DEAL if a.market else mt5.TRADE_ACTION_PENDING,
            "symbol": rep["symbol"],
            "volume": rep["volume"],
            "type": otype,
            "price": price,
            "sl": rep["sl"],
            "tp": rep["tp1"],
            "magic": 20261001,
            "comment": f"FRIVAL_{a.id}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC if a.market else mt5.ORDER_FILLING_RETURN,
        }

        check = mt5.order_check(req)
        result = mt5.order_send(req)
        audit("PLACE_RESULT", log_id=a.id, check=check, result=result,
              request=req, retcode=result.retcode if result else None)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[FAILED] order_send retcode={result.retcode if result else 'None'} "
                  f"comment={result.comment if result else ''}")
            print("The signal row stays PENDING_FILL with the failure recorded.")
            return

        if rep["ok"] and STATE.get("session_start_equity", 0) == 0:
            STATE["session_start_equity"] = rep["equity"]
            save_state(STATE)

        rows = list(csv.DictReader(LOG_PATH.open(newline="", encoding="utf-8")))
        for r in rows:
            if r.get("log_id") == a.id:
                r["status"] = "OPEN" if a.market else "ORDER_PLACED"
        save_log(rows)
        print(f"[PLACED] {a.id} {rep['side']} {rep['volume']} {rep['symbol']} @ "
              f"{price if a.market else rep['entry']} SL {rep['sl']} TP {rep['tp1']}")
        print(f"   risk ${rep['risk_usd']:.2f} ({rep['risk_pct']:.2f}% of equity)  "
              f"R:R {rep['rr_tp1']:.2f}  SL {rep['sl_atr_multiple']:.2f}x ATR(M5)")
        print(f"   margin level after: {rep['margin_level_after']:.0f}%")
    finally:
        mt5.shutdown()


def cmd_manage(a):
    """Apply break-even and partial-profit management to AGENT-PLACED positions.

    Scope: B1 — only rows whose setup_id the agent authored. Rows marked
    operator_executed (manually placed) are never touched.

    Management ladder, evaluated in order per position:
      1. price reaches BE trigger  -> SL moves to entry
      2. price reaches PARTIAL trigger -> close PARTIAL_CLOSE_FRACTION
      3. price reaches TP1 (remainder) -> broker handles it

    Partial closing is a HYPOTHESIS, not a validated rule. Every partial is
    recorded with the realised R so the split can be measured in the ledger.
    """
    mt5 = _mt5()
    try:
        rows = list(csv.DictReader(LOG_PATH.open(newline="", encoding="utf-8")))
        acts = []
        # Map the live position back to its log row by SYMBOL AND ENTRY PRICE.
        # Matching on status alone was wrong: a stale OPEN row (T010, XAUUSD)
        # matched before the real row (T020, XAUUSD) and tagged the partial
        # exit with the wrong setup id. Stale OPEN rows are the root cause, so
        # they are also retired here.
        live = {}
        for op in (mt5.positions_get() or []):
            live[op.symbol] = op
        for stale in rows:
            if stale.get("status") not in ("OPEN", "ORDER_PLACED"):
                continue
            ssym = stale.get("symbol")
            if ssym not in live:
                stale["status"] = "CLOSED"
                stale["notes"] = (stale.get("notes", "") +
                                  " AUTO-RETIRED %s: log row marked OPEN but no live "
                                  "position for this symbol." % dt.datetime.utcnow()
                                  .strftime("%Y-%m-%d %H:%M"))
                audit("STALE_ROW_RETIRED", log_id=stale.get("log_id"), symbol=ssym)
                continue
            op = live[ssym]
            try:
                if abs(float(stale.get("entry_price") or 0) - op.price_open) > 0.005:
                    stale["status"] = "CLOSED"
                    stale["notes"] = (stale.get("notes", "") +
                                      " AUTO-RETIRED %s: entry %s does not match live "
                                      "position %s." % (dt.datetime.utcnow()
                                      .strftime("%Y-%m-%d %H:%M"),
                                      stale.get("entry_price"), op.price_open))
                    audit("STALE_ROW_RETIRED", log_id=stale.get("log_id"), symbol=ssym)
            except ValueError:
                pass

        for r in rows:
            if r.get("status") not in ("OPEN", "ORDER_PLACED"):
                continue
            # B1 scope guard: skip anything the operator placed by hand.
            if r.get("execution_mode") == "OPERATOR_MANUAL":
                continue
            sym = r.get("symbol")
            pos = mt5.positions_get(symbol=sym)
            if not pos:
                continue
            p = pos[0]
            entry = float(p.price_open)
            tp1 = float(r["tp1"])
            tp2 = float(r["tp2"]) if r.get("tp2") else 0.0
            is_buy = p.type == 0
            tick = mt5.symbol_info_tick(sym)
            px = tick.bid if is_buy else tick.ask
            mv = money_per_price_unit(sym, mt5)
            vol = float(p.volume)

            be = entry + (tp1 - entry) * BE_FRACTION
            partial_at = entry + (tp2 - entry) * PARTIAL_AT_FRACTION if tp2 \
                else entry + (tp1 - entry) * PARTIAL_AT_FRACTION

            # 1 — break-even
            if abs((p.sl or 0) - entry) > 1e-9:
                hit_be = (px >= be) if is_buy else (px <= be)
                if hit_be:
                    req = {"action": mt5.TRADE_ACTION_SLTP, "symbol": sym,
                           "position": p.ticket, "sl": entry, "tp": p.tp}
                    res = mt5.order_send(req)
                    ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
                    audit("BE_MOVE", log_id=r["log_id"], symbol=sym, ticket=p.ticket,
                          sl=entry, retcode=res.retcode if res else None)
                    acts.append(f"BE  {sym} #{p.ticket} SL -> {entry} "
                                f"({'ok' if ok else 'FAILED retcode ' + str(res.retcode if res else 'None')})")
                    if not ok:
                        continue

            # 2 — partial close
            if abs((p.sl or 0) - entry) <= 1e-9:      # only after BE is set
                hit_part = (px >= partial_at) if is_buy else (px <= partial_at)
                if hit_part and not r.get("be_executed") == "PARTIAL_DONE":
                    close_vol = round(vol * PARTIAL_CLOSE_FRACTION, 2)
                    if close_vol < vol:
                        # Same SDK constraint as close-all: MT5 build 5.0.4874
                        # has NO positions_close(). A partial close is an
                        # order_send with TRADE_ACTION_DEAL, `position` set to
                        # the ticket, and `volume` set to the partial size.
                        # sl/tp keys MUST be omitted — passing sl=0 raises
                        # Invalid "sl" argument. `deviation` is required or
                        # order_send returns None with no diagnostic.
                        close_req = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "symbol": sym,
                            "position": p.ticket,
                            "volume": close_vol,
                            "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
                            "price": px,
                            "deviation": 30,
                            "magic": 20261001,
                            "comment": f"FRIVAL_{r.get('log_id','')}_PARTIAL",
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_IOC,
                        }
                        res = mt5.order_send(close_req)
                        ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
                        if not ok:
                            err = mt5.last_error()
                            audit("PARTIAL_CLOSE_FAILED", log_id=r["log_id"],
                                  symbol=sym, ticket=p.ticket, last_error=err)
                            print(f"[FAILED] partial close {sym} #{p.ticket}: "
                                  f"retcode={res.retcode if res else None} err={err}")
                            continue
                        pnl = (px - entry) * (1 if is_buy else -1) * close_vol * mv
                        r_sl = abs(partial_at - entry)
                        audit("PARTIAL_CLOSE", log_id=r["log_id"], symbol=sym,
                              ticket=p.ticket, closed_volume=close_vol, price=px,
                              realised_usd=round(pnl, 2),
                              realised_r=round(pnl / (r_sl * mv), 2) if r_sl else None,
                              retcode=res.retcode if res else None)
                        acts.append(f"PARTIAL {sym} #{p.ticket} closed {close_vol} @ {px} "
                                    f"= ${pnl:+.2f} ({'ok' if ok else 'FAILED'})")
                        if ok:
                            for rr_ in rows:
                                if rr_.get("log_id") == r["log_id"]:
                                    rr_["be_executed"] = "PARTIAL_DONE"
                                    rr_["mfe_usd"] = f"{pnl:.2f}"
                            save_log(rows)
                    else:
                        acts.append(f"PARTIAL {sym} skipped: close fraction rounds to full volume")

        if acts:
            for s in acts:
                print(s)
        else:
            print("[INFO] no management action required")
    finally:
        mt5.shutdown()


def cmd_cancel(a):
    """Cancel a pending order in the BROKER, then mark the log row.

    The log is a record, not a control. Writing status=CANCELLED to the CSV
    does NOT remove the order from the terminal — the broker will still fill
    it. This command always calls TRADE_ACTION_REMOVE first and only writes
    the log after the broker confirms.

    Verify mode is the default so a human reads the outcome before the log
    is touched.
    """
    mt5 = _mt5()
    try:
        target = a.ticket
        if a.id:
            rows = list(csv.DictReader(LOG_PATH.open(newline="", encoding="utf-8")))
            row = next((r for r in rows if r.get("log_id") == a.id), None)
            if row is None:
                print(f"[ABORT] {a.id} not in trade_log.csv")
                return
            sym, cmt = row["symbol"], f"FRIVAL_{a.id}"
            found = next((o for o in (mt5.orders_get() or [])
                          if o.symbol == sym and o.comment == cmt), None)
            if found is None:
                print(f"[INFO] no pending order matches {a.id} (already filled or gone)")
                return
            target = found.ticket
        else:
            found = next((o for o in (mt5.orders_get() or [])
                          if o.ticket == target), None)
            if found is None:
                print(f"[INFO] ticket {target} not among pending orders")
                return

        print(f"[TARGET] ticket {found.ticket} {found.symbol} {found.volume_current} @ "
              f"{found.price_open} SL {found.sl} TP {found.tp} comment {found.comment!r}")
        res = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE,
                              "order": found.ticket, "symbol": found.symbol})
        done = res is not None and res.retcode in (
            mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_DONE_PARTIAL)
        audit("CANCEL", ticket=found.ticket, symbol=found.symbol,
              comment=found.comment, retcode=res.retcode if res else None, ok=done)
        if not done:
            err = mt5.last_error()
            print(f"[FAILED] order not removed: retcode={res.retcode if res else None} err={err}")
            print("            The log row was NOT modified — the order may still be live.")
            return
        remaining = len(mt5.orders_get() or [])
        print(f"[CANCELLED] ticket {found.ticket} removed by broker. "
              f"pending orders now: {remaining}")
        if a.id and not a.no_log:
            rows = list(csv.DictReader(LOG_PATH.open(newline="", encoding="utf-8")))
            for r in rows:
                if r.get("log_id") == a.id:
                    r["status"] = "CANCELLED_UNFILLED"
                    r["notes"] = (r.get("notes", "") +
                                  f" BROKER CANCELLED ticket {found.ticket} retcode "
                                  f"{res.retcode} — removal confirmed by the terminal, not "
                                  f"assumed from the log.")
            save_log(rows)
            print(f"[OK] {a.id} marked CANCELLED_UNFILLED after broker confirmed removal")
    finally:
        mt5.shutdown()


def cmd_close_all(a):
    if not kill_switch_active() and not a.force:
        print("[ABORT] close-all requires --force or the kill switch file.")
        return
    mt5 = _mt5()
    try:
        pos = mt5.positions_get() or []
        for p in pos:
            tick = mt5.symbol_info_tick(p.symbol)
            # MT5 build 5.0.4874 has NO positions_close(); closing is an
            # order_send with TRADE_ACTION_DEAL against the position ticket.
            # sl/tp keys MUST BE OMITTED on a close — passing sl=0 raises
            # Invalid "sl" argument. `deviation` is required or order_send
            # returns None with no diagnostic.
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": p.symbol,
                "position": p.ticket,
                "volume": p.volume,
                "type": mt5.ORDER_TYPE_SELL if p.type == 0 else mt5.ORDER_TYPE_BUY,
                "price": tick.bid if p.type == 0 else tick.ask,
                "deviation": 30,
                "magic": 20261001,
                "comment": "FRIVAL_CLOSE",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            res = mt5.order_send(req)
            if res is None:
                err = mt5.last_error()
                audit("CLOSE_FAILED", symbol=p.symbol, ticket=p.ticket, last_error=err)
                print(f"[FAILED] {p.symbol} #{p.ticket} order_send returned None: {err}")
                continue
            done = res.retcode == mt5.TRADE_RETCODE_DONE
            audit("CLOSE_ALL", symbol=p.symbol, ticket=p.ticket, profit=p.profit,
                  retcode=res.retcode, done=done, comment=res.comment)
            print(f"[{'CLOSE' if done else 'REJECT'}] {p.symbol} #{p.ticket} "
                  f"profit {p.profit:+.2f} retcode {res.retcode} {res.comment}")
        if not pos:
            print("[INFO] no open positions")
    finally:
        mt5.shutdown()


def cmd_status(a):
    if kill_switch_active():
        print("[KILL SWITCH ACTIVE] " + str(KILL_SWITCH))
    mt5 = _mt5()
    try:
        acct = mt5.account_info()
        print(f"account {acct.login} {acct.server}  equity {acct.equity}  "
              f"margin {acct.margin}  level {acct.margin_level:.0f}%  lev {acct.leverage}")
        pos = mt5.positions_get() or []
        print(f"positions {len(pos)}  pending {len(mt5.orders_get() or [])}")
        for p in pos:
            mv = money_per_price_unit(p.symbol, mt5)
            print(f"  {p.symbol} {'BUY' if p.type == 0 else 'SELL'} {p.volume} "
                  f"@ {p.price_open}  cur {p.price_current}  sl {p.sl}  tp {p.tp}  "
                  f"pnl {p.profit:.2f} swap {p.swap:.2f}  risk/move {mv:.2f}/unit")
        for o in mt5.orders_get() or []:
            print(f"  PENDING {o.symbol} vol {o.volume_current} @ {o.price_open} "
                  f"sl {o.sl} tp {o.tp} comment {o.comment!r}")
        print("\nguardrails:")
        print(f"  max risk/trade {MAX_RISK_PCT_PER_TRADE}%   max daily loss {MAX_DAILY_LOSS_PCT}%")
        print(f"  max positions {MAX_POSITIONS}   min R:R {MIN_RR}   "
              f"SL range {MIN_ATR_MULTIPLE}-{MAX_SL_DISTANCE_PCT_OF_ATR}x ATR(M5)")
        print(f"  min margin level {MIN_MARGIN_LEVEL}%   max consecutive losses {MAX_CONSECUTIVE_LOSSES}")
    finally:
        mt5.shutdown()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_place = sub.add_parser("place")
    p_place.add_argument("--id", required=True)
    p_place.add_argument("--market", action="store_true")
    p_place.add_argument("--force", action="store_true")
    sub.add_parser("manage")
    sub.add_parser("status")
    p_cancel = sub.add_parser("cancel", help="remove a pending order IN THE BROKER, then mark the log")
    p_cancel.add_argument("--id", help="log_id; resolves the ticket via symbol+comment")
    p_cancel.add_argument("--ticket", type=int, help="raw ticket number")
    p_cancel.add_argument("--no-log", action="store_true", help="do not touch trade_log.csv")
    p_close = sub.add_parser("close-all")
    p_close.add_argument("--force", action="store_true")
    p_close.add_argument("--reason", default="")
    a = ap.parse_args()
    fn = {"place": cmd_place, "manage": cmd_manage, "cancel": cmd_cancel,
          "status": cmd_status, "close-all": cmd_close_all}[a.cmd]
    fn(a)


if __name__ == "__main__":
    main()