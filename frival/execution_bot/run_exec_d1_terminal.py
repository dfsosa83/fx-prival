# -*- coding: utf-8 -*-
"""EXEC-D1 → MT5 DEMO TERMINAL monitored runner (supervised activation).

AUTHORIZED 2026-09-29 (project owner): real orders on the FP Markets DEMO
terminal (account 7409623, FPMarketsSC-Demo, $5,000 demo) for ALL FOUR pairs,
with EXEC-D1 entry semantics:
  - executable quote inside the entry zone at processing -> immediate market entry;
  - otherwise PENDING up to 10 minutes from T0; touch fills at the qualifying
    (conservative) quote; no touch -> EXPIRED_UNFILLED, no order;
  - NO_VALID_PENDING -> never any order.

The runner is SUPERVISED: it must be started by the operator and streams a log
to output/logs/YYYY-MM-DD_exec_d1.log. Ctrl+C stops it cleanly. A real order is
only sent when the EXEC-D1 engine returns MARKET_FILLED / PENDING_TRIGGERED and
the executor preflight (emergency stop, demo env, position per pair, daily loss
cap, idempotency) passes.

It attaches PATH-ONLY to the already-logged-in terminal (production pattern);
credentials are never read or passed.

Usage:
    <deaf_agent python> run_exec_d1_terminal.py
"""

from __future__ import annotations

import glob
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

EXEC_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(EXEC_DIR))
sys.path.insert(0, str(EXEC_DIR / "core"))

from core.exec_d1_terminal import (DATA_DIR, EMERGENCY_STOP, LOGS_DIR,  # noqa: E402
                                   Mt5Gateway, TerminalExecutor, TickFreshness,
                                   entry_semantics, tick_to_quote)
import lifecycle as lc                                            # noqa: E402
from lifecycle_store import LifecycleStore                        # noqa: E402


def load_credentials():
    env = {}
    path = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\frival\execution_bot\config\credentials.env")
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


def read_fired_signals():
    """FIRED (non-AGNOSTIC) signals from TODAY's journal file only."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stem = f"{today}.jsonl"
    root = ROOT / "frival" if (ROOT / "frival").exists() else ROOT
    out = []
    for path in Path(root / "output" / "signals" / datetime.now(timezone.utc).strftime("%Y-%m")).glob("*.jsonl"):
        if path.name != stem:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                sig = json.loads(line)
            except Exception:
                continue
            if sig.get("final_decision") == "FIRED" and not str(sig.get("symbol", "")).endswith("_AGNOSTIC"):
                out.append(sig)
    out.sort(key=lambda s: s.get("timestamp_utc", ""))
    return out


def main() -> int:
    import MetaTrader5 as mt5

    env = load_credentials()
    terminal = env.get("MT5_PATH", "").strip()
    login = env.get("MT5_LOGIN", "").strip()
    if not terminal:
        print("STOP: MT5_PATH not configured")
        return 2

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{today}_exec_d1.log"
    log = open(log_path, "a", encoding="utf-8")

    def note(msg):
        line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
        print(line)
        log.write(line + "\n")
        log.flush()

    gateway = Mt5Gateway(mt5)
    if not gateway.attach(terminal):
        note(f"STOP: initialize failed — {gateway.last_error()}")
        return 3

    acc = gateway.account()
    if acc is None or str(acc.get("login", "")) != login or acc.get("trade_mode") != 0:
        note(f"STOP: demo environment mismatch (trade_mode={acc and acc.get('trade_mode')})")
        gateway.detach()
        return 4
    note(f"demo env OK (account {acc['login'][:2]}...{acc['login'][-3:]}, "
         f"server={acc.get('server')}, balance={acc.get('balance')})")

    store_dir = DATA_DIR / "exec_d1_runtime"
    store = LifecycleStore(store_dir)
    engine = lc.LifecycleEngine(store, now_fn=lambda: datetime.now(timezone.utc),
                                entry_mode=entry_semantics())
    note(f"entry semantics: {engine.entry_mode}")
    executor = TerminalExecutor(gateway, login_expected=login)

    # Startup safety net: retract any open virtual position whose real order
    # never succeeded (e.g. legacy phantom opens left by a failed send), unless
    # the broker actually holds a position for that symbol.
    try:
        reconciled = engine.reconcile_executions(
            executor.executed_signal_ids(),
            {p.get("symbol") for p in gateway.positions()})
        for sid in reconciled:
            note(f"reconciled phantom open (no real order): {sid}")
    except Exception as exc:  # defensive
        note(f"startup reconcile error (continue): {type(exc).__name__}: {exc}")

    freshness = TickFreshness(max_stale_seconds=90.0)
    processed_ids = set()
    stale_notified = set()

    def route_fill(signal_id: str):
        pos = store.open_position(signal_id)
        if pos is None:
            return
        meta = store.signal_meta(signal_id)
        side = "SELL" if meta and meta["direction"] == "SELL" else "BUY"
        res = executor.execute_fill(
            signal_id=signal_id, symbol=meta["symbol"] if meta else "",
            direction=side, fill_price=float(pos["entry_used"]),
            sl=float(pos["stop_loss"]), tp=float(pos["take_profit"]))
        decision = res.get("decision")
        note(f"FILL {signal_id}: {decision} "
             f"ticket={res.get('ticket')} retcode={res.get('retcode')} "
             f"reason={res.get('reason')} error={res.get('error')}")
        if decision != "EXECUTED":
            # No real order behind the VIRTUAL_OPEN: retract the phantom open so
            # it is never advanced, closed, or counted as a trade.
            engine.mark_execution_failed(
                signal_id, reason=f"send_{str(decision).lower()}",
                detail=str(res.get("reason") or res.get("error") or ""),
                execution=res)

    note("monitoring… (Ctrl+C to stop)")
    try:
        while True:
            if EMERGENCY_STOP.exists():
                note("EMERGENCY STOP present — no new orders; waiting")
                time.sleep(5)
                continue

            try:
                # 0) prime tick-feed freshness for every traded pair so a frozen
                #    feed is detected before the next signal can act on it.
                for _symbol in ("EURUSD", "GBPUSD", "USDCHF", "USDCAD"):
                    _tick = gateway.tick(_symbol)
                    if _tick:
                        freshness.observe(_symbol, _tick.get("time"))
            except Exception as exc:  # defensive
                note(f"freshness-probe error (continue): {type(exc).__name__}: {exc}")

            try:
                # 1) new signals
                for sig in read_fired_signals():
                    sig_id = sig.get("signal_id")
                    if not sig_id or sig_id in processed_ids:
                        continue
                    if store.has_signal(sig_id):
                        processed_ids.add(sig_id)
                        continue
                    symbol = sig.get("symbol")
                    tick = gateway.tick(symbol)
                    if not tick:
                        continue
                    fresh = freshness.observe(symbol, tick.get("time"))
                    quote = tick_to_quote(tick, symbol)
                    if quote is None:
                        continue
                    if not fresh:
                        if sig_id not in stale_notified:
                            stale_notified.add(sig_id)
                            note(f"stale feed {symbol}: {sig_id} deferred (window open)")
                        continue
                    outcome = engine.process(sig, [quote])
                    note(f"signals {sig_id}: {outcome}")
                    if outcome in (lc.MARKET_FILLED, lc.PENDING_TRIGGERED):
                        route_fill(sig_id)
                    processed_ids.add(sig_id)
            except Exception as exc:  # defensive: never let one signal kill the loop
                note(f"signal-loop error (continue): {type(exc).__name__}: {exc}")

            try:
                # 2) advance pendings with live ticks
                for sid in list(store.pending()):
                    meta = store.signal_meta(sid)
                    if not meta:
                        continue
                    tick = gateway.tick(meta["symbol"])
                    if not tick:
                        continue
                    fresh = freshness.observe(meta["symbol"], tick.get("time"))
                    quote = tick_to_quote(tick, meta["symbol"])
                    if quote is None or not fresh:
                        continue
                    outcome = engine.advance_pending(sid, quote)
                    if outcome == lc.PENDING_TRIGGERED:
                        route_fill(sid)
                    elif outcome == lc.EXPIRED_UNFILLED:
                        note(f"expired {sid}")
                    # non-triggering quotes update the watermark by design
            except Exception as exc:  # defensive
                note(f"pending-loop error (continue): {type(exc).__name__}: {exc}")

            try:
                # 3) horizon closes (6h) — terminal SL/TP manage normal exits
                now = datetime.now(timezone.utc)
                for sid, pos in list(store.open_positions().items()):
                    meta = store.signal_meta(sid)
                    if not meta:
                        continue
                    if engine.close_timeout(sid, now) == lc.CLOSED_TIMEOUT:
                        note(f"horizon close {sid}")
            except Exception as exc:  # defensive
                note(f"open-loop error (continue): {type(exc).__name__}: {exc}")

            time.sleep(1.0)
    except KeyboardInterrupt:
        note("stopped by operator")
    finally:
        log.flush()
        gateway.detach()
        log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())