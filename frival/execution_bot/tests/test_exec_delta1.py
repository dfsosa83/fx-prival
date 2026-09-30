# -*- coding: utf-8 -*-
"""EXEC-D1 test suite — entry-zone / 10-minute expiry lifecycle (offline only).

Covers every EXEC-D1 final-plan test case, the corrected D-4 adverse-gap rule,
and the review-fix regression suite:

  C-1  deterministic multiprocessing tests: two concurrent processes on the
       same signal, and on the same (symbol, direction) slot with different
       signals, must produce exactly ONE accepted transition.
  M-1  crash/restart at the former fill-write boundary: replay derives the open
       position from the single authoritative VIRTUAL_OPEN event and never
       creates duplicates from legacy rows.
  M-2  advance_pending(): successive quote calls, normal touch, adverse gap,
       stale/duplicate quote rejection, post-expiry rejection, boundary fill at
       exactly t_exp, restart-while-pending.
  M-3  automatic startup reconciliation: expired pendings expire at store
       construction; valid pendings survive and stay advanceable; restart after
       open/close records preserves the close.
  Fix 5  synthetic SymbolInfo fixtures prove margin_stop is a REAL MT5 symbol
       field and margin_freeze/fill_mode/expiration_mode are NOT (the gate
       never reads them, and missing metadata fails closed).

All tests are deterministic and fully offline: fake clocks, scripted quote
streams, tempfile data dirs, and offline subprocess workers. No MT5, no orders,
no watcher/order-bot integration.

Run from frival/execution_bot:
    python -m unittest discover -s tests -p "test_exec_delta1.py" -v
"""

import json
import multiprocessing as mp
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

EXEC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXEC_DIR))
sys.path.insert(0, str(EXEC_DIR / "core"))   # flat layout: avoids core/__init__
                                             # (mt5_connector -> pytz) imports

import lifecycle as lc
import invalid_fills as inv
import lifecycle_store as ls
import broker_constraints as bc
from broker_constraints import (BROKER_CONSTRAINT_MALFORMED,
                                BROKER_CONSTRAINT_UNVERIFIED,
                                FREEZE_UNVERIFIED, MIN_STOP_VIOLATION,
                                BrokerConstraintGate, field_classification,
                                introspect_symbol_info_fields,
                                mt5_import_status)
from lifecycle_store import LifecycleStore


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def u(ts: str) -> datetime:
    """Parse an ISO timestamp, ASSUMING UTC when no offset is present."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class FakeClock:
    def __init__(self, ts: str):
        self._now = u(ts)

    def now(self):
        return self._now

    def advance(self, **kw):
        self._now = self._now + timedelta(**kw)


T0 = "2026-09-28T16:00:00"
TEXP = "2026-09-28T16:10:00"


def sell_sig(sid="EURUSD_H1_SELL_D1T", ts=T0, entry=1.13628,
             sl=1.13720, tp=1.13491, symbol="EURUSD"):
    return {
        "signal_id": sid, "symbol": symbol, "direction": "SELL",
        "pip_multiplier": 10000, "timestamp_utc": ts,
        "trade": {
            "entry": entry,
            "entry_zone": [round(entry + 0.0002, 5), round(entry - 0.0002, 5)],
            "stop_loss": sl, "take_profit": tp, "rr_ratio": 1.5,
            "expires_at_utc": "2026-09-28T22:00:00",
        },
        "final_decision": "FIRED",
        "gate_type": "borderline",
    }


def buy_sig(sid="EURUSD_H1_BUY_D1T", ts=T0, entry=1.13628,
            sl=1.13530, tp=1.13910):
    return {
        "signal_id": sid, "symbol": "EURUSD", "direction": "BUY",
        "pip_multiplier": 10000, "timestamp_utc": ts,
        "trade": {
            "entry": entry,
            "entry_zone": [round(entry - 0.0002, 5), round(entry + 0.0002, 5)],
            "stop_loss": sl, "take_profit": tp, "rr_ratio": 1.5,
            "expires_at_utc": "2026-09-28T22:00:00",
        },
        "final_decision": "FIRED",
        "gate_type": "borderline",
    }


def q(ts, bid=None, ask=None):
    d = {"ts": ts}
    if bid is not None:
        d["bid"] = bid
    if ask is not None:
        d["ask"] = ask
    return d


def make_env(ts=T0):
    tmp = tempfile.mkdtemp(prefix="exec_d1_test_")
    clock = FakeClock(ts)
    store = LifecycleStore(tmp, now_fn=clock.now)
    engine = lc.LifecycleEngine(store, now_fn=clock.now, per_pip_usd=0.10,
                                cost_pips=1.2)
    return tmp, clock, store, engine


def event_types(store):
    return [e["event_type"] for e in store.events()]


# ── Concurrency worker processes (offline; spawn context) ─────────────────────

def _mp_process_worker(data_dir, barrier, signal, quote, outq):
    """Child: open the shared store, barrier-synchronize, then process."""
    clock = FakeClock("2026-09-28T16:00:05")
    store = LifecycleStore(data_dir, now_fn=clock.now)
    engine = lc.LifecycleEngine(store, now_fn=clock.now)
    barrier.wait(timeout=30)
    try:
        result = engine.process(signal, [quote])
    except Exception as exc:                      # pragma: no cover
        result = f"ERR:{type(exc).__name__}:{exc}"
    outq.put(result)


class TestMarketFills(unittest.TestCase):
    def test_sell_market_fill_inside_zone(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:05", bid=1.13630, ask=1.13641)])
        self.assertEqual(out, lc.MARKET_FILLED)
        self.assertIn(lc.VIRTUAL_OPEN, event_types(store))
        pos = store.open_position("EURUSD_H1_SELL_D1T")
        self.assertEqual(pos["entry_used"], 1.13630)
        self.assertEqual(pos["filled_via"], lc.FILL_VIA_MARKET)

    def test_buy_market_fill_inside_zone(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(buy_sig(), [
            q("2026-09-28T16:00:05", bid=1.13619, ask=1.13630)])
        self.assertEqual(out, lc.MARKET_FILLED)
        pos = store.open_position("EURUSD_H1_BUY_D1T")
        self.assertEqual(pos["entry_used"], 1.13630)

    def test_zone_boundaries_are_inclusive_market(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(sell_sig("S_EDGE"), [
            q("2026-09-28T16:00:05", bid=1.13648, ask=1.13659)])
        self.assertEqual(out, lc.MARKET_FILLED)
        _, _, store2, engine2 = make_env("2026-09-28T16:00:05")
        out2 = engine2.process(buy_sig("B_EDGE"), [
            q("2026-09-28T16:00:05", bid=1.13599, ask=1.13608)])
        self.assertEqual(out2, lc.MARKET_FILLED)


class TestStopFills(unittest.TestCase):
    def _open_payload(self, store, sid="EURUSD_H1_SELL_D1T"):
        return store.open_position(sid)

    def test_sell_stop_normal_touch_fills_at_qualifying_bid(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:00:30", bid=1.13655, ask=1.13666),
            q("2026-09-28T16:01:00", bid=1.13648, ask=1.13659),
        ])
        self.assertEqual(out, lc.PENDING_TRIGGERED)
        pos = self._open_payload(store)
        self.assertEqual(pos["fill_quote"], 1.13648)
        self.assertEqual(pos["triggering_quote"], 1.13648)
        self.assertEqual(pos["trigger_level"], 1.13648)
        self.assertFalse(pos["gap_flag"])
        self.assertEqual(pos["adverse_gap_pips"], 0.0)
        self.assertEqual(pos["filled_via"], lc.FILL_VIA_STOP)
        self.assertEqual(store.open_position("EURUSD_H1_SELL_D1T")["entry_used"], 1.13648)

    def test_sell_stop_adverse_gap_fills_at_lower_bid(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:01:00", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:01:30", bid=1.13655, ask=1.13666),
            q("2026-09-28T16:02:00", bid=1.13640, ask=1.13651),  # gap THROUGH L
        ])
        self.assertEqual(out, lc.PENDING_TRIGGERED)
        pos = self._open_payload(store)
        self.assertTrue(pos["gap_flag"])
        self.assertEqual(pos["fill_quote"], 1.13640)
        self.assertEqual(pos["triggering_quote"], 1.13640)
        self.assertAlmostEqual(pos["adverse_gap_pips"], 0.8, places=3)
        self.assertEqual(store.open_position("EURUSD_H1_SELL_D1T")["entry_used"], 1.13640)

    def test_buy_stop_normal_touch_fills_at_qualifying_ask(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        out = engine.process(buy_sig(), [
            q("2026-09-28T16:01:00", bid=1.13594, ask=1.13605),
            q("2026-09-28T16:01:30", bid=1.13600, ask=1.13602),
            q("2026-09-28T16:02:00", bid=1.13606, ask=1.13608),
        ])
        self.assertEqual(out, lc.PENDING_TRIGGERED)
        pos = store.open_position("EURUSD_H1_BUY_D1T")
        self.assertEqual(pos["fill_quote"], 1.13608)
        self.assertFalse(pos["gap_flag"])
        self.assertEqual(store.open_position("EURUSD_H1_BUY_D1T")["entry_used"], 1.13608)

    def test_buy_stop_adverse_gap_fills_at_higher_ask(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        out = engine.process(buy_sig(), [
            q("2026-09-28T16:01:00", bid=1.13594, ask=1.13605),
            q("2026-09-28T16:02:00", bid=1.13618, ask=1.13620),  # gap ABOVE L
        ])
        self.assertEqual(out, lc.PENDING_TRIGGERED)
        pos = store.open_position("EURUSD_H1_BUY_D1T")
        self.assertTrue(pos["gap_flag"])
        self.assertEqual(pos["fill_quote"], 1.13620)
        self.assertAlmostEqual(pos["adverse_gap_pips"], 1.2, places=3)

    def test_no_limit_orders_ever_emitted(self):
        self.assertEqual(lc.EMITTABLE_PENDING_TYPES, ("SELL_STOP", "BUY_STOP"))
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        engine.process(sell_sig("A"), [q("2026-09-28T16:01:00", bid=1.13661,
                                         ask=1.13672)])
        engine.process(sell_sig("B"), [q("2026-09-28T16:01:00", bid=1.13630,
                                         ask=1.13641)])
        engine.process(sell_sig("C"), [q("2026-09-28T16:01:00", bid=1.13605,
                                         ask=1.13616)])
        for e in store.events():
            ptype = e.get("payload", {}).get("pending_type")
            self.assertNotIn(ptype, ("SELL_LIMIT", "BUY_LIMIT"))


class TestNoValidPending(unittest.TestCase):
    def test_sell_crossed_zone_below_no_pending(self):
        _, clock, store, engine = make_env("2026-09-28T16:00:05")
        clock.advance(seconds=1)
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:06", bid=1.13605, ask=1.13616)])
        self.assertEqual(out, lc.NO_VALID_PENDING)
        self.assertNotIn(lc.ENTRY_PENDING, event_types(store))
        self.assertTrue(store.acquires("EURUSD", "SELL"))

    def test_buy_crossed_zone_above_no_pending(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(buy_sig(), [
            q("2026-09-28T16:00:05", bid=1.13639, ask=1.13650)])
        self.assertEqual(out, lc.NO_VALID_PENDING)
        self.assertTrue(store.acquires("EURUSD", "BUY"))


class TestExpiry(unittest.TestCase):
    def test_expiry_no_touch_expired_unfilled(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:05:00", bid=1.13655, ask=1.13666),
            q("2026-09-28T16:09:59", bid=1.13652, ask=1.13663),
            q(TEXP, bid=1.13652, ask=1.13663),   # stream complete through texp
        ])
        self.assertEqual(out, lc.EXPIRED_UNFILLED)
        ev = [e for e in store.events() if e["event_type"] == lc.EXPIRED_UNFILLED][0]
        self.assertEqual(ev["payload"]["reason"], "no_touch")
        self.assertEqual(ev["payload"]["texp_utc"], lc._iso(u(TEXP)))
        self.assertTrue(store.acquires("EURUSD", "SELL"))
        self.assertIsNone(store.open_position("EURUSD_H1_SELL_D1T"))

    def test_touch_exactly_at_texp_fills(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q(TEXP, bid=1.13648, ask=1.13659),   # ts == texp: qualifies
        ])
        self.assertEqual(out, lc.PENDING_TRIGGERED)

    def test_quote_after_texp_never_fills(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:10:30", bid=1.13640, ask=1.13651),
        ])
        self.assertEqual(out, lc.EXPIRED_UNFILLED)
        self.assertIsNone(store.open_position("EURUSD_H1_SELL_D1T"))

    def test_processed_after_expiry_expired_unfilled(self):
        _, _, store, engine = make_env("2026-09-28T16:15:00")  # after texp
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:15:10", bid=1.13640, ask=1.13651)])
        self.assertEqual(out, lc.EXPIRED_UNFILLED)
        ev = [e for e in store.events() if e["event_type"] == lc.EXPIRED_UNFILLED][0]
        self.assertEqual(ev["payload"]["reason"], "processed_after_expiry")


class TestLiveQuoteRace(unittest.TestCase):
    """Regression for the 2026-09-29 `no_quote` race.

    The live runner fetches the tick BEFORE the engine reads its decision
    clock, so the just-fetched quote's timestamp precedes the processing
    instant `tp`. The engine must evaluate that freshest in-window quote and
    must never expire an in-window signal on the `q.ts >= tp` filter.
    """

    def test_quote_before_processing_instant_fills_in_zone(self):
        _, _, store, engine = make_env("2026-09-28T16:00:30")   # 30 s after T0
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:29.500000", bid=1.13630, ask=1.13641)])
        self.assertEqual(out, lc.MARKET_FILLED)
        self.assertIsNotNone(store.open_position("EURUSD_H1_SELL_D1T"))

    def test_quote_before_processing_instant_arms_pending_not_expired(self):
        _, _, store, engine = make_env("2026-09-28T16:00:30")
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:29.500000", bid=1.13661, ask=1.13672)])
        self.assertEqual(out, lc.ENTRY_PENDING)
        self.assertIn("EURUSD_H1_SELL_D1T", store.pending())

    def test_no_quote_reason_absent_when_a_fresh_quote_exists(self):
        _, _, store, engine = make_env("2026-09-28T16:00:30")
        engine.process(sell_sig(), [
            q("2026-09-28T16:00:29.500000", bid=1.13630, ask=1.13641)])
        reasons = [e["payload"].get("reason") for e in store.events()
                   if e["event_type"] == lc.EXPIRED_UNFILLED]
        self.assertNotIn("no_quote", reasons)

    def test_presignal_quote_is_not_used(self):
        # The fallback is bounded below by t0: a quote from before the signal
        # existed must never become the decision/fill quote.
        _, _, store, engine = make_env("2026-09-28T16:00:30")
        out = engine.process(sell_sig(), [
            q("2026-09-28T15:59:00", bid=1.13630, ask=1.13641)])   # < t0
        self.assertEqual(out, lc.EXPIRED_UNFILLED)
        self.assertIsNone(store.open_position("EURUSD_H1_SELL_D1T"))


class TestReanchorEntry(unittest.TestCase):
    """Reanchor entry mode (owner decision 2026-09-29): market-enter at the first
    in-window tick and re-anchor SL/TP on the ACTUAL fill, preserving the
    signal's pip distances. Removes the close-zone latency dependence."""

    def _reanchor_env(self, ts="2026-09-28T16:00:30"):
        _, _, store, engine = make_env(ts)
        engine.entry_mode = lc.ENTRY_MODE_REANCHOR
        return store, engine

    def test_fills_outside_zone_and_reanchors_levels(self):
        store, engine = self._reanchor_env()
        # quote 25 pips ABOVE the entry zone -> zone mode would STOP/void
        out = engine.process(sell_sig(), [
            q("2026-09-28T16:00:29.500000", bid=1.13878, ask=1.13889)])
        self.assertEqual(out, lc.MARKET_FILLED)
        pos = store.open_position("EURUSD_H1_SELL_D1T")
        self.assertIsNotNone(pos)
        self.assertAlmostEqual(pos["entry_used"], 1.13878, places=6)
        # signal pip distances preserved: SL 9.2 pips above, TP 13.7 pips below
        self.assertAlmostEqual(pos["stop_loss"] - pos["entry_used"], 0.00092, places=6)
        self.assertAlmostEqual(pos["entry_used"] - pos["take_profit"], 0.00137, places=6)
        self.assertAlmostEqual(pos["effective_rr"], round(13.7 / 9.2, 3), places=3)

    def test_reanchored_tp_drives_close(self):
        store, engine = self._reanchor_env()
        engine.process(sell_sig(), [
            q("2026-09-28T16:00:29.500000", bid=1.13878, ask=1.13889)])
        tp = store.open_position("EURUSD_H1_SELL_D1T")["take_profit"]
        res = engine.advance("EURUSD_H1_SELL_D1T", {
            "ts": "2026-09-28T16:05:00", "bid": tp - 0.00001, "ask": tp + 0.00010})
        self.assertEqual(res, lc.CLOSED_TP)

    def test_reanchored_sl_drives_close(self):
        store, engine = self._reanchor_env()
        engine.process(sell_sig(), [
            q("2026-09-28T16:00:29.500000", bid=1.13878, ask=1.13889)])
        sl = store.open_position("EURUSD_H1_SELL_D1T")["stop_loss"]
        res = engine.advance("EURUSD_H1_SELL_D1T", {
            "ts": "2026-09-28T16:05:00", "bid": sl + 0.00001, "ask": sl + 0.00010})
        self.assertEqual(res, lc.CLOSED_SL)


class TestPersistenceRestart(unittest.TestCase):
    def test_pending_and_open_survive_restart(self):
        tmp, clock, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("A_PEND", symbol="EURUSD"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:08:00", bid=1.13660, ask=1.13671)])
        engine.process(sell_sig("B_OPEN", symbol="GBPUSD"), [
            q("2026-09-28T16:00:06", bid=1.13630, ask=1.13641)])
        self.assertIn("A_PEND", store.pending())
        self.assertIn("B_OPEN", store.open_positions())

        # Simulated process restart: same data dir, brand-new instances
        clock2 = FakeClock("2026-09-28T16:00:10")
        store2 = LifecycleStore(tmp, now_fn=clock2.now)
        engine2 = lc.LifecycleEngine(store2, now_fn=clock2.now)
        self.assertIn("A_PEND", store2.pending())
        self.assertEqual(store2.pending()["A_PEND"]["pending_type"], "SELL_STOP")
        self.assertEqual(store2.open_positions()["B_OPEN"]["entry_used"], 1.13630)
        self.assertEqual(store2.event_count(), store.event_count())

    def test_reconcile_expires_stale_pending_on_restart(self):
        tmp, clock, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("PEND1"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:08:00", bid=1.13660, ask=1.13671)])
        self.assertIn("PEND1", store.pending())
        # Restart AFTER t_exp (16:10): the store auto-reconciles on startup (M-3)
        later = FakeClock("2026-09-28T16:30:00")
        store2 = LifecycleStore(tmp, now_fn=later.now)
        self.assertNotIn("PEND1", store2.pending())
        reasons = [e["payload"]["reason"] for e in store2.events()
                   if e["event_type"] == lc.EXPIRED_UNFILLED]
        self.assertIn("reconciled_expired", reasons)
        # Explicit reconcile is now a no-op (idempotent)
        self.assertEqual(store2.reconcile(later.now()), [])

    def test_events_file_is_append_only(self):
        tmp, clock, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("X"), [q("2026-09-28T16:00:05", bid=1.13630,
                                         ask=1.13641)])
        before = Path(store.events_path).read_bytes()
        clock.advance(seconds=5)
        engine.process(sell_sig("Y", symbol="GBPUSD"),
                       [q("2026-09-28T16:00:10", bid=1.13630, ask=1.13641)])
        after = Path(store.events_path).read_bytes()
        self.assertTrue(after.startswith(before), "events file must be append-only")
        self.assertTrue(after.startswith(b"# schema v"), "schema header first")


class TestIdempotencyConcurrency(unittest.TestCase):
    def test_duplicate_signal_skipped(self):
        _, clock, store, engine = make_env("2026-09-28T16:00:05")
        sig = sell_sig("DUP")
        out1 = engine.process(sig, [q("2026-09-28T16:00:05", bid=1.13630,
                                      ask=1.13641)])
        self.assertEqual(out1, lc.MARKET_FILLED)
        clock.advance(seconds=10)
        out2 = engine.process(sig, [q("2026-09-28T16:00:15", bid=1.13650,
                                      ask=1.13661)])
        self.assertEqual(out2, lc.DUPLICATE_SKIPPED)
        self.assertEqual(
            len([e for e in store.events() if e["event_type"] == lc.VIRTUAL_OPEN]),
            1, "a signal can never produce two virtual positions")

    def test_concurrency_same_symbol_direction_skipped(self):
        _, clock, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("A"), [q("2026-09-28T16:00:05", bid=1.13630,
                                         ask=1.13641)])
        clock.advance(seconds=5)
        out = engine.process(sell_sig("B"), [q("2026-09-28T16:00:10", bid=1.13630,
                                               ask=1.13641)])
        self.assertEqual(out, lc.CONCURRENCY_SKIPPED)

    def test_concurrency_blocks_while_pending(self):
        _, clock, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("P1"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:08:00", bid=1.13660, ask=1.13671)])  # stays pending
        clock.advance(seconds=5)
        out = engine.process(sell_sig("P2"), [q("2026-09-28T16:00:10", bid=1.13630,
                                                ask=1.13641)])
        self.assertEqual(out, lc.CONCURRENCY_SKIPPED)


class TestConcurrentProcesses(unittest.TestCase):
    """C-1: deterministic multiprocessing — cross-process idempotency."""

    def _run_workers(self, data_dir, signals_and_quotes):
        ctx = mp.get_context("spawn")
        barrier = ctx.Barrier(len(signals_and_quotes))
        outq = ctx.Queue()
        procs = [
            ctx.Process(target=_mp_process_worker,
                        args=(data_dir, barrier, sig, quote, outq))
            for sig, quote in signals_and_quotes
        ]
        for p in procs:
            p.start()
        for p in procs:
            p.join(timeout=30)
            self.assertEqual(p.exitcode, 0, "worker must exit cleanly")
        results = [outq.get(timeout=10) for _ in procs]
        outq.close()
        return results

    def test_two_processes_same_signal_no_duplicate(self):
        tmp, _, _, _ = make_env("2026-09-28T16:00:05")
        sig = sell_sig("RACE")
        quote = q("2026-09-28T16:00:05", bid=1.13630, ask=1.13641)
        results = self._run_workers(tmp, [(sig, quote), (sig, quote)])
        self.assertEqual(set(results), {lc.MARKET_FILLED, lc.DUPLICATE_SKIPPED})
        store = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:00:10"))
        opens = [e for e in store.events() if e["event_type"] == lc.VIRTUAL_OPEN]
        self.assertEqual(len(opens), 1, "exactly one accepted fill")
        self.assertEqual(len(store.open_positions()), 1)

    def test_two_processes_different_signals_same_slot_no_duplicate(self):
        tmp, _, _, _ = make_env("2026-09-28T16:00:05")
        quote = q("2026-09-28T16:00:05", bid=1.13630, ask=1.13641)
        sig_a = sell_sig("SLOT_A", symbol="EURUSD")
        sig_b = sell_sig("SLOT_B", symbol="EURUSD")
        results = self._run_workers(tmp, [(sig_a, quote), (sig_b, quote)])
        self.assertEqual(set(results), {lc.MARKET_FILLED, lc.CONCURRENCY_SKIPPED})
        store = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:00:10"))
        opens = [e for e in store.events() if e["event_type"] == lc.VIRTUAL_OPEN]
        self.assertEqual(len(opens), 1, "exactly one open for the slot")
        self.assertEqual(len(store.open_positions()), 1)

    def test_stale_claim_recovery_on_restart(self):
        tmp, clock, store, engine = make_env("2026-09-28T16:00:05")
        # Simulate a crashed holder: plant an old claim file for a signal
        claim_path = store._claim_path("signal", "GHOST")
        claim_path.parent.mkdir(parents=True, exist_ok=True)
        claim_path.write_text(json.dumps({"claimant": "dead", "created_epoch": 0}))
        old_age = clock.now().timestamp()
        import os
        os.utime(claim_path, (old_age - 10 * store.claim_ttl, old_age - 10 * store.claim_ttl))
        # A fresh store prunes the stale claim and the signal can be processed
        clock2 = FakeClock("2026-09-28T16:00:06")
        store2 = LifecycleStore(tmp, now_fn=clock2.now)
        self.assertFalse(claim_path.exists(), "stale claim must be reclaimed")
        out = lc.LifecycleEngine(store2, now_fn=clock2.now).process(
            sell_sig("GHOST"), [q("2026-09-28T16:00:06", bid=1.13630, ask=1.13641)])
        self.assertEqual(out, lc.MARKET_FILLED)


class TestAdvancePending(unittest.TestCase):
    """M-2: pending continuation across successive quote calls."""

    def _pending(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        out = engine.process(sell_sig("PEND"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672)])
        self.assertEqual(out, lc.ENTRY_PENDING)
        return store, engine

    def test_normal_touch_via_advance_pending(self):
        store, engine = self._pending()
        out = engine.advance_pending("PEND", q("2026-09-28T16:02:00",
                                               bid=1.13648, ask=1.13659))
        self.assertEqual(out, lc.PENDING_TRIGGERED)
        pos = store.open_position("PEND")
        self.assertEqual(pos["entry_used"], 1.13648)
        self.assertEqual(pos["triggering_quote"], 1.13648)
        self.assertFalse(pos["gap_flag"])
        self.assertNotIn("PEND", store.pending())

    def test_adverse_gap_via_advance_pending(self):
        store, engine = self._pending()
        out = engine.advance_pending("PEND", q("2026-09-28T16:02:00",
                                               bid=1.13640, ask=1.13651))
        self.assertEqual(out, lc.PENDING_TRIGGERED)
        pos = store.open_position("PEND")
        self.assertTrue(pos["gap_flag"])
        self.assertEqual(pos["fill_quote"], 1.13640)
        self.assertAlmostEqual(pos["adverse_gap_pips"], 0.8, places=3)

    def test_multiple_quotes_then_touch(self):
        store, engine = self._pending()
        self.assertEqual(engine.advance_pending(
            "PEND", q("2026-09-28T16:01:00", bid=1.13655, ask=1.13666)), "")
        self.assertEqual(engine.advance_pending(
            "PEND", q("2026-09-28T16:02:00", bid=1.13650, ask=1.13661)), "")
        self.assertEqual(engine.advance_pending(
            "PEND", q("2026-09-28T16:02:30", bid=1.13648, ask=1.13659)),
            lc.PENDING_TRIGGERED)
        self.assertEqual(store.open_position("PEND")["entry_used"], 1.13648)

    def test_stale_duplicate_quote_never_fills(self):
        store, engine = self._pending()
        self.assertEqual(engine.advance_pending(
            "PEND", q("2026-09-28T16:02:00", bid=1.13650, ask=1.13661)), "")
        # Re-releasing the same (stale cached) quote must be a no-op
        self.assertEqual(engine.advance_pending(
            "PEND", q("2026-09-28T16:02:00", bid=1.13650, ask=1.13661)), "")
        # but now a strictly later touch fills exactly once
        self.assertEqual(engine.advance_pending(
            "PEND", q("2026-09-28T16:03:00", bid=1.13648, ask=1.13659)),
            lc.PENDING_TRIGGERED)
        self.assertEqual(
            len([e for e in store.events() if e["event_type"] == lc.VIRTUAL_OPEN]), 1)

    def test_touch_exactly_at_texp_boundary(self):
        store, engine = self._pending()
        self.assertEqual(engine.advance_pending(
            "PEND", q(TEXP, bid=1.13648, ask=1.13659)), lc.PENDING_TRIGGERED)

    def test_quote_after_texp_expires_and_never_fills(self):
        store, engine = self._pending()
        self.assertEqual(engine.advance_pending(
            "PEND", q("2026-09-28T16:10:30", bid=1.13640, ask=1.13651)),
            lc.EXPIRED_UNFILLED)
        self.assertIsNone(store.open_position("PEND"))
        self.assertNotIn("PEND", store.pending())

    def test_restart_while_pending_then_fresh_quote_fills(self):
        tmp, _, _, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("P"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672)])
        clock2 = FakeClock("2026-09-28T16:05:00")      # still before t_exp
        store2 = LifecycleStore(tmp, now_fn=clock2.now)
        self.assertIn("P", store2.pending(), "valid pending survives startup")
        engine2 = lc.LifecycleEngine(store2, now_fn=clock2.now)
        self.assertEqual(engine2.advance_pending(
            "P", q("2026-09-28T16:07:00", bid=1.13648, ask=1.13659)),
            lc.PENDING_TRIGGERED)
        self.assertEqual(len([e for e in store2.events()
                              if e["event_type"] == lc.VIRTUAL_OPEN]), 1)

    def test_restart_rejects_stale_cached_quote(self):
        tmp, _, _, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("P"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672)])
        # consume one non-triggering quote -> watermark at 16:02:00
        self.assertEqual(engine.advance_pending(
            "P", q("2026-09-28T16:02:00", bid=1.13650, ask=1.13661)), "")
        clock2 = FakeClock("2026-09-28T16:05:00")
        store2 = LifecycleStore(tmp, now_fn=clock2.now)
        engine2 = lc.LifecycleEngine(store2, now_fn=clock2.now)
        # stale cache replay of the SAME quote must NOT fill after restart
        self.assertEqual(engine2.advance_pending(
            "P", q("2026-09-28T16:02:00", bid=1.13648, ask=1.13659)), "")
        self.assertIsNone(store2.open_position("P"))
        # a genuinely fresh quote (> watermark) fills exactly once
        self.assertEqual(engine2.advance_pending(
            "P", q("2026-09-28T16:06:00", bid=1.13648, ask=1.13659)),
            lc.PENDING_TRIGGERED)
        self.assertEqual(len([e for e in store2.events()
                              if e["event_type"] == lc.VIRTUAL_OPEN]), 1)


class TestCrashFillRecovery(unittest.TestCase):
    """M-1: the single authoritative VIRTUAL_OPEN event removes the fill
    write-window; replay recovers exactly one open position."""

    def test_crash_after_fill_event_replays_one_open(self):
        tmp, _, _, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("F"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672)])
        # authoritative fill committed
        out = engine.advance_pending(
            "F", q("2026-09-28T16:02:00", bid=1.13648, ask=1.13659))
        self.assertEqual(out, lc.PENDING_TRIGGERED)
        store2 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:05:00"))
        opens = store2.open_positions()
        self.assertEqual(list(opens.keys()), ["F"])
        self.assertEqual(opens["F"]["entry_used"], 1.13648)
        self.assertEqual(len([e for e in store2.events()
                              if e["event_type"] == lc.VIRTUAL_OPEN]), 1)

    def test_crash_before_fill_event_recovers_pending_not_open(self):
        # Crash AFTER the pending write-ahead but BEFORE the authoritative fill
        # event: restart must recover the pending (not an open position), and
        # the pending must remain advanceable with a fresh quote.
        tmp, _, _, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("F"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672)])
        store2 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:05:00"))
        self.assertIn("F", store2.pending(), "pending must survive the crash")
        self.assertEqual(list(store2.open_positions()), [])
        engine2 = lc.LifecycleEngine(store2, now_fn=lambda: u("2026-09-28T16:05:00"))
        self.assertEqual(engine2.advance_pending(
            "F", q("2026-09-28T16:06:00", bid=1.13648, ask=1.13659)),
            lc.PENDING_TRIGGERED)
        self.assertEqual(len([e for e in store2.events()
                              if e["event_type"] == lc.VIRTUAL_OPEN]), 1)

    def test_legacy_rows_replay_without_duplicate_opens(self):
        # Legacy shape: a PENDING_TRIGGERED row with NO following VIRTUAL_OPEN
        # must NOT create an open position; only VIRTUAL_OPEN does.
        tmp, clock, store, _ = make_env("2026-09-28T16:00:05")
        esig = lc.from_signal_dict(sell_sig("LEG"))
        store.append(lc.SIGNAL_RECEIVED, "LEG", "EURUSD", "SELL", {
            "entry": 1.13628, "stop_loss": 1.13720, "take_profit": 1.13491,
            "zone_lo": 1.13608, "zone_hi": 1.13648, "pip_mult": 10000.0,
            "t0_utc": lc._iso(u(T0)), "horizon_hours": 6.0,
        })
        store.append(lc.ENTRY_PENDING, "LEG", "EURUSD", "SELL", {
            "pending_type": "SELL_STOP", "trigger_level": 1.13648,
            "executable_side": "bid", "tp_utc": lc._iso(u("2026-09-28T16:00:05")),
            "texp_utc": lc._iso(u(TEXP)), "quote_at_tp": 1.13661,
            "prior_quote": 1.13661,
        })
        store.append(lc.PENDING_TRIGGERED, "LEG", "EURUSD", "SELL", {
            "prior_quote": 1.13661, "triggering_quote": 1.13648,
            "fill_quote": 1.13648, "trigger_level": 1.13648,
            "gap_flag": False, "adverse_gap_pips": 0.0,
            "tf_utc": lc._iso(u("2026-09-28T16:02:00")),
        })
        store2 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:05:00"))
        self.assertEqual(list(store2.open_positions()), [],
                         "legacy trigger alone must not create a position")
        # Now the authoritative open: exactly one position, no duplication
        store2.append(lc.VIRTUAL_OPEN, "LEG", "EURUSD", "SELL", {
            "ticket": "D1-LEG", "entry_used": 1.13648, "stop_loss": 1.13720,
            "take_profit": 1.13491, "filled_via": lc.FILL_VIA_STOP,
            "triggering_quote": 1.13648, "prior_quote": 1.13661,
            "trigger_level": 1.13648, "gap_flag": False, "adverse_gap_pips": 0.0,
            "effective_rr": 1.0, "effective_risk_pips": 7.2,
            "effective_reward_pips": 10.8, "risk_usd": 0.72, "cost_pips": 1.2,
        })
        store3 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:05:30"))
        self.assertEqual(list(store3.open_positions()), ["LEG"])
        self.assertEqual(len([e for e in store3.events()
                              if e["event_type"] == lc.VIRTUAL_OPEN]), 1)


class TestAutoReconcile(unittest.TestCase):
    """M-3: startup recovery is automatic — no integrator-remembered call."""

    def test_startup_auto_reconciles_expired_pending(self):
        tmp, _, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("P"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672)])
        self.assertIn("P", store.pending())
        store2 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:30:00"))
        self.assertNotIn("P", store2.pending())
        reasons = [e["payload"]["reason"] for e in store2.events()
                   if e["event_type"] == lc.EXPIRED_UNFILLED]
        self.assertIn("reconciled_expired", reasons)

    def test_startup_keeps_valid_pending_and_advanceable(self):
        tmp, _, _, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("P"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672)])
        store2 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:05:00"))
        self.assertIn("P", store2.pending())
        engine2 = lc.LifecycleEngine(store2, now_fn=lambda: u("2026-09-28T16:05:00"))
        self.assertEqual(engine2.advance_pending(
            "P", q("2026-09-28T16:07:00", bid=1.13648, ask=1.13659)),
            lc.PENDING_TRIGGERED)

    def test_startup_after_open_and_close_preserves_close(self):
        tmp, _, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("C"), [q("2026-09-28T16:00:05", bid=1.13630,
                                         ask=1.13641)])
        self.assertEqual(engine.advance("C", q("2026-09-28T16:05:00",
                                               bid=1.13720, ask=1.13731)),
                         lc.CLOSED_SL)
        store2 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:10:00"))
        self.assertEqual(list(store2.open_positions()), [])
        self.assertEqual([c["event_type"] for c in store2.closed_records()],
                         [lc.CLOSED_SL])


class TestFillAndPnL(unittest.TestCase):
    def test_fill_equals_eligible_quote_never_nominal(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        engine.process(sell_sig("GAP"), [
            q("2026-09-28T16:01:00", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:02:00", bid=1.13640, ask=1.13651),
        ])
        pos = store.open_position("GAP")
        self.assertEqual(pos["entry_used"], 1.13640)
        self.assertNotEqual(pos["entry_used"], 1.13628)
        self.assertEqual(pos["entry_used"], pos["fill_quote"])

    def test_pnl_risk_rr_from_actual_fill(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        engine.process(sell_sig("M"), [
            q("2026-09-28T16:01:00", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:02:00", bid=1.13640, ask=1.13651),
        ])
        pos = store.open_position("M")
        self.assertEqual(pos["stop_loss"], 1.13720)
        self.assertEqual(pos["take_profit"], 1.13491)
        self.assertAlmostEqual(pos["effective_risk_pips"], 8.0, places=3)
        self.assertAlmostEqual(pos["effective_reward_pips"], 14.9, places=3)
        self.assertAlmostEqual(pos["effective_rr"], 1.8625, delta=0.002)
        self.assertAlmostEqual(pos["risk_usd"], 0.80, places=4)

        engine.advance("M", q("2026-09-28T16:05:00", bid=1.13720, ask=1.13731))
        closed = store.closed_records()
        self.assertEqual(closed[0]["event_type"], lc.CLOSED_SL)
        self.assertEqual(closed[0]["payload"]["exit_price"], 1.13720)
        self.assertAlmostEqual(closed[0]["payload"]["r"], -1.0, places=4)
        self.assertAlmostEqual(closed[0]["payload"]["pips"], -8.0, places=3)
        self.assertEqual(closed[0]["payload"]["entry_used"], 1.13640)

    def test_tp_close_and_double_close_guard(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        engine.process(sell_sig("T"), [
            q("2026-09-28T16:01:00", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:02:00", bid=1.13640, ask=1.13651),
        ])
        engine.advance("T", q("2026-09-28T16:20:00", bid=1.13491, ask=1.13502))
        self.assertEqual([c["event_type"] for c in store.closed_records()],
                         [lc.CLOSED_TP])
        self.assertAlmostEqual(store.closed_records()[0]["payload"]["r"],
                               1.8625, delta=0.002)
        self.assertEqual(engine.advance("T", q("2026-09-28T16:30:00",
                                               bid=1.13300, ask=1.13311)), "")

    def test_timeout_close_after_horizon(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        engine.process(sell_sig("TO"), [
            q("2026-09-28T16:01:00", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:02:00", bid=1.13640, ask=1.13651),
        ])
        engine.advance("TO", q("2026-09-28T17:00:00", bid=1.13610, ask=1.13621))
        self.assertEqual(engine.close_timeout("TO", u("2026-09-28T21:59:00")), "")
        out = engine.close_timeout("TO", u("2026-09-28T22:00:01"))
        self.assertEqual(out, lc.CLOSED_TIMEOUT)
        rec = store.closed_records()[0]
        self.assertEqual(rec["payload"]["exit_price"], 1.13610)

    def test_sl_first_precedence_on_degenerate_geometry(self):
        _, _, store, engine = make_env("2026-09-28T16:01:00")
        sig = buy_sig("DEG", entry=1.13600, sl=1.13620, tp=1.13620)
        engine.process(sig, [q("2026-09-28T16:01:00", bid=1.13599, ask=1.13600)])
        self.assertEqual(engine.advance("DEG", q("2026-09-28T16:10:00",
                                                 bid=1.13619, ask=1.13620)),
                         lc.CLOSED_SL)


class TestExternalConflict(unittest.TestCase):
    def test_external_conflict_excludes_and_never_closes_manual(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("X"), [q("2026-09-28T16:00:05", bid=1.13630,
                                         ask=1.13641)])
        out = engine.record_external_conflict("X", "manual close observed at terminal")
        self.assertEqual(out, lc.EXTERNAL_STATE_CONFLICT)
        self.assertIsNone(store.open_position("X"))
        self.assertIn("X", store.excluded_signal_ids())
        self.assertEqual([c["event_type"] for c in store.closed_records()], [])
        self.assertNotIn("CLOSED_MANUAL", event_types(store))


class TestMigrationManifest(unittest.TestCase):
    INVALID_IDS = ["EURUSD_H1_SELL_2026-09-28T16:00:00Z",
                   "EURUSD_H1_SELL_2026-09-28T17:00:00Z"]

    def test_manifest_contains_both_records(self):
        m = inv.load_manifest()
        self.assertEqual(len(m), 2)
        for sid in self.INVALID_IDS:
            self.assertIn(sid, m)
            self.assertEqual(m[sid]["state"], inv.INVALID_STATE)

    def test_exclusion_from_metrics(self):
        m = inv.load_manifest()
        records = [
            {"signal_id": self.INVALID_IDS[0], "event_type": "CLOSED_TP"},
            {"signal_id": self.INVALID_IDS[1], "event_type": "CLOSED_SL"},
            {"signal_id": "EURUSD_H1_SELL_VALID", "event_type": "CLOSED_TP"},
        ]
        valid, excluded = inv.partition(records, m)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(excluded), 2)
        self.assertTrue(inv.is_excluded(self.INVALID_IDS[0], m))
        self.assertFalse(inv.is_excluded("EURUSD_H1_SELL_VALID", m))

    def test_assert_no_reconstruction(self):
        m = inv.load_manifest()
        bad = [{"signal_id": self.INVALID_IDS[0], "event_type": "CLOSED_TP"}]
        with self.assertRaises(AssertionError):
            inv.assert_no_reconstruction(bad, m)
        inv.assert_no_reconstruction([], m)

    def test_manifest_required_for_metrics(self):
        with self.assertRaises(FileNotFoundError):
            inv.load_manifest("/nonexistent/nope.json")


class TestBrokerGate(unittest.TestCase):
    REAL = {"trade_stops_level": 3.0, "trade_freeze_level": 50.0,
            "filling_mode": 1, "expiration_mode": 1, "order_mode": 15}

    def _si(self, **overrides):
        base = dict(self.REAL, **overrides)
        return SimpleNamespace(**base)

    def _gate(self, enabled=True, si=None, freeze_provider=None):
        return BrokerConstraintGate(
            enabled=enabled,
            symbol_info_provider=(lambda s: si),
            freeze_level_provider=freeze_provider)

    def test_demo_disabled_skips(self):
        gate = BrokerConstraintGate(enabled=False)
        ev = gate.evaluate(order_type="SELL_STOP", trigger_level=1.13648,
                           executable_quote=1.13661, symbol="EURUSD")
        self.assertTrue(ev.ok)
        self.assertEqual(ev.mode, "demo_skipped")

    def test_enabled_no_provider_fails_closed(self):
        gate = BrokerConstraintGate(enabled=True, symbol_info_provider=None,
                                    freeze_level_provider=lambda: 30)
        ev = gate.evaluate(order_type="SELL_STOP", trigger_level=1.13648,
                           executable_quote=1.13661, symbol="EURUSD")
        self.assertFalse(ev.ok)
        self.assertEqual(ev.code, BROKER_CONSTRAINT_UNVERIFIED)

    def test_enabled_missing_trade_stops_level_fails_closed(self):
        si = self._si(trade_stops_level=None)
        ev = self._gate(si=si).evaluate(order_type="SELL_STOP",
                                        trigger_level=1.13648,
                                        executable_quote=1.13661,
                                        symbol="EURUSD")
        self.assertFalse(ev.ok)
        self.assertEqual(ev.code, BROKER_CONSTRAINT_UNVERIFIED)

    def test_enabled_missing_freeze_level_fails_closed(self):
        si = self._si(trade_freeze_level=None)
        ev = self._gate(si=si).evaluate(order_type="SELL_STOP",
                                        trigger_level=1.13648,
                                        executable_quote=1.13661,
                                        symbol="EURUSD")
        self.assertFalse(ev.ok)
        self.assertEqual(ev.code, FREEZE_UNVERIFIED)

    def test_malformed_metadata_fails_closed(self):
        for bad in (self._si(trade_stops_level="abc"),
                    self._si(trade_stops_level=-2.0),
                    self._si(trade_freeze_level="nope")):
            ev = self._gate(si=bad).evaluate(order_type="SELL_STOP",
                                             trigger_level=1.13648,
                                             executable_quote=1.13661,
                                             symbol="EURUSD")
            self.assertFalse(ev.ok, f"must block malformed: {bad}")
            self.assertEqual(ev.code, BROKER_CONSTRAINT_MALFORMED)

    def test_enabled_min_stop_violation_blocks(self):
        si = self._si(trade_stops_level=3.0)
        gate = self._gate(si=si)
        ev = gate.evaluate(order_type="SELL_STOP", trigger_level=1.13648,
                           executable_quote=1.13650, symbol="EURUSD")
        self.assertFalse(ev.ok)
        self.assertEqual(ev.code, MIN_STOP_VIOLATION)
        ok = gate.evaluate(order_type="SELL_STOP", trigger_level=1.13648,
                           executable_quote=1.13661, symbol="EURUSD")
        self.assertTrue(ok.ok)

    def test_introspect_none_reports_unavailable(self):
        fields = introspect_symbol_info_fields(None)
        self.assertEqual(fields["trade_stops_level"], "UNAVAILABLE")

    def test_mt5_not_importable_in_this_environment(self):
        status = mt5_import_status()
        self.assertTrue(status.startswith("UNAVAILABLE"))


class TestBrokerRealFieldMap(unittest.TestCase):
    """Fix-5 corrected: REAL MT5 names per the documented/verified interface
    (synthetic SymbolInfo-like fixtures only; no broker runtime semantics are
    claimed by synthetic tests)."""

    def test_field_classification_audit(self):
        self.assertEqual(field_classification("trade_stops_level"), "REAL_SYMBOL_FIELD")
        self.assertEqual(field_classification("trade_freeze_level"), "REAL_SYMBOL_FIELD")
        self.assertEqual(field_classification("filling_mode"), "REAL_SYMBOL_FIELD")
        self.assertEqual(field_classification("expiration_mode"), "REAL_SYMBOL_FIELD")
        self.assertEqual(field_classification("order_mode"), "REAL_SYMBOL_FIELD")
        for name in ("margin_stop", "margin_freeze", "fill_mode"):
            self.assertEqual(field_classification(name), "NOT_AN_MT5_FIELD")
        self.assertIn("trade_stops_level", bc.REAL_SYMBOL_FIELDS)
        self.assertNotIn("margin_stop", bc.REAL_SYMBOL_FIELDS)
        self.assertEqual(bc.documented_property_map()["margin_freeze"]["classification"],
                         "NOT_AN_MT5_FIELD")
        self.assertEqual(bc.documented_property_map()["filling_mode"]["classification"],
                         "REAL_SYMBOL_FIELD")

    def test_gate_never_reads_invalid_assumed_names(self):
        # Fixture that ONLY tolerates reads of real, correct names: any access
        # to margin_stop / margin_freeze / fill_mode raises — proving the gate
        # never touches them.
        class StrictSymbolInfo:
            trade_stops_level = 3.0
            trade_freeze_level = 50.0
            filling_mode = 1
            expiration_mode = 1
            order_mode = 15

            def __getattr__(self, name):
                if name in ("margin_stop", "margin_freeze", "fill_mode"):
                    raise AttributeError(f"{name} must never be read")
                raise AttributeError(name)

        gate = BrokerConstraintGate(enabled=True,
                                    symbol_info_provider=lambda s: StrictSymbolInfo())
        ok = gate.evaluate(order_type="SELL_STOP", trigger_level=1.13648,
                           executable_quote=1.13661, symbol="EURUSD")
        self.assertTrue(ok.ok)

    def test_synthetic_symbol_info_introspection(self):
        from collections import namedtuple
        Mini = namedtuple("MiniSymbolInfo", ("trade_stops_level",
                                             "trade_freeze_level"))
        si = Mini(3.0, 50.0)
        fields = introspect_symbol_info_fields(si)
        self.assertEqual(fields["trade_stops_level"], "AVAILABLE")
        self.assertEqual(fields["trade_freeze_level"], "AVAILABLE")
        self.assertEqual(introspect_symbol_info_fields(None)["trade_stops_level"],
                         "UNAVAILABLE")
        self.assertEqual(introspect_symbol_info_fields(SimpleNamespace())["trade_stops_level"],
                         "UNVERIFIED")

    def test_missing_metadata_still_fails_closed(self):
        gate = BrokerConstraintGate(enabled=True,
                                    symbol_info_provider=lambda s: None,
                                    freeze_level_provider=lambda: 30)
        ev = gate.evaluate(order_type="SELL_STOP", trigger_level=1.13648,
                           executable_quote=1.13650, symbol="EURUSD")
        self.assertFalse(ev.ok)
        self.assertEqual(ev.code, BROKER_CONSTRAINT_UNVERIFIED)


class TestProbeResolver(unittest.TestCase):
    """Fix-5 corrected: the probe uses mt5.symbol_info — verified WITHOUT
    connecting (module-level introspection only; no runtime MT5 call)."""

    def test_resolver_prefers_symbol_info_and_never_falls_back(self):
        class FakeModule:
            symbol_info = "the-callable"

        self.assertEqual(bc.symbol_api_name(FakeModule()), "symbol_info")

        class FakeModuleWithout:
            symbol_info_get = "the-callable"

        self.assertNotEqual(
            bc.symbol_api_name(FakeModuleWithout()), "symbol_info_get")
        self.assertTrue(bc.symbol_api_name(FakeModuleWithout()).startswith("<absent"))

    def test_probe_module_requires_symbol_info_without_connecting(self):
        # Run the probe's module-level introspection path only (imports are
        # stubbed); we assert the template references the corrected API call,
        # never the invalid `symbol_info_get(...)` call pattern, and validates
        # configuration BEFORE any initialization call.
        import tools.mt5_metadata_validate as probe  # noqa: F401  (module import only)
        import inspect as _inspect
        src = _inspect.getsource(probe)
        self.assertIn("mt5.symbol_info(symbol)", src)
        self.assertNotIn(".symbol_info_get(", src)
        # The config validation precedes the actual initialize CALL SITE (the
        # first docstring mention of mt5.initialize earlier in the source is
        # not the call; compare against the LAST occurrence).
        self.assertLess(src.index("build_initialize_args(env)"),
                        src.rindex("mt5.initialize("))
        # The call itself is PATH-ONLY: no credentials are passed to the SDK.
        self.assertIn("mt5.initialize(path=terminal)", src)
        for bad_pattern in ("login=login,", "password=password,",
                            "server=server,", "login=login)"):
            self.assertNotIn(bad_pattern, src)


class TestConfigParsing(unittest.TestCase):
    """Authorized path-only fix: build_initialize_args returns ONLY {"path"}
    (credentials never passed to the SDK); credential validators remain as
    optional environment-structure verification utilities."""

    def setUp(self):
        from tools import mt5_config as cfg
        self.cfg = cfg
        self.tmpdir = tempfile.mkdtemp(prefix="exec_d1_cfg_")
        self.term = Path(self.tmpdir) / "terminal64.exe"
        self.term.write_text("", encoding="utf-8")

    def _env(self, **overrides):
        base = {
            "MT5_LOGIN": "740000623",
            "MT5_PASSWORD": "x-secret-x",
            "MT5_SERVER": "FPMarketsSC-Demo",
            "MT5_PATH": str(self.term),
            "MT5_TERMINAL_PATH": "",
        }
        base.update(overrides)
        return base

    # ── path-only builder contract ───────────────────────────────────────────
    def test_build_initialize_args_is_path_only(self):
        args = self.cfg.build_initialize_args(self._env())
        self.assertIsInstance(args, dict)
        self.assertEqual(sorted(args.keys()), ["path"])
        self.assertIsInstance(args["path"], str)
        self.assertTrue(args["path"].endswith("terminal64.exe"))

    def test_builder_ignores_credentials_for_sdk_call(self):
        # login/password/server may be missing or garbage: the PATH-ONLY
        # build must still succeed and must never include them.
        env = {"MT5_PATH": str(self.term)}
        args = self.cfg.build_initialize_args(env)
        self.assertEqual(sorted(args.keys()), ["path"])
        args2 = self.cfg.build_initialize_args(
            {"MT5_PATH": str(self.term), "MT5_LOGIN": "not-a-number",
             "MT5_PASSWORD": "", "MT5_SERVER": ""})
        self.assertEqual(sorted(args2.keys()), ["path"])

    def test_missing_path_rejected(self):
        env = self._env(); del env["MT5_PATH"]; env["MT5_TERMINAL_PATH"] = ""
        with self.assertRaises(self.cfg.ConfigError):
            self.cfg.build_initialize_args(env)

    def test_nonexistent_path_rejected(self):
        with self.assertRaises(self.cfg.ConfigError):
            self.cfg.build_initialize_args(
                self._env(MT5_PATH=str(Path(self.tmpdir) / "missing.exe")))

    def test_unexpected_binary_name_rejected(self):
        other = Path(self.tmpdir) / "noterminal.exe"
        other.write_text("", encoding="utf-8")
        with self.assertRaises(self.cfg.ConfigError):
            self.cfg.build_initialize_args(self._env(MT5_PATH=str(other)))

    def test_quoted_windows_path_with_spaces_ok_when_file_exists(self):
        dir_with_space = Path(self.tmpdir) / "dir with space"
        dir_with_space.mkdir(exist_ok=True)
        exe = dir_with_space / "terminal64.exe"
        exe.write_text("", encoding="utf-8")
        args = self.cfg.build_initialize_args(self._env(MT5_PATH=f'"{exe}"'))
        self.assertTrue(args["path"].endswith("terminal64.exe"))

    # ── credential validators (verification utilities, never SDK inputs) ─────
    def test_valid_numeric_login_becomes_int(self):
        self.assertIsInstance(self.cfg.validate_login("740000623"), int)
        self.assertEqual(self.cfg.validate_login("740000623"), 740000623)

    def test_whitespace_is_normalized(self):
        self.assertEqual(self.cfg.validate_login("  740000623  "), 740000623)

    def test_quoted_login_rejected(self):
        for quoted in ("'740000623'", '"740000623"'):
            with self.assertRaises(self.cfg.ConfigError):
                self.cfg.validate_login(quoted)

    def test_blank_login_rejected(self):
        for blank in ("", "   ", "\t"):
            with self.assertRaises(self.cfg.ConfigError):
                self.cfg.validate_login(blank)

    def test_non_numeric_login_rejected(self):
        for bad in ("abc", "74-623", "12a34", "+7"):
            with self.assertRaises(self.cfg.ConfigError):
                self.cfg.validate_login(bad)

    def test_zero_and_negative_login_rejected(self):
        with self.assertRaises(self.cfg.ConfigError):
            self.cfg.validate_login("0")
        with self.assertRaises(self.cfg.ConfigError):
            self.cfg.validate_login("-5")

    def test_blank_password_rejected(self):
        with self.assertRaises(self.cfg.ConfigError):
            self.cfg.validate_password("   ")

    def test_blank_server_rejected(self):
        with self.assertRaises(self.cfg.ConfigError):
            self.cfg.validate_server("")

    def test_config_errors_do_not_contain_secrets(self):
        secret = "S3CR3T-VALUE"
        with self.assertRaises(self.cfg.ConfigError) as ctx:
            self.cfg.validate_login("not-a-number" + secret)
            self.cfg.validate_password(secret)
        self.assertNotIn(secret, str(ctx.exception))
        self.assertNotIn("740000623", str(ctx.exception))
        with self.assertRaises(self.cfg.ConfigError) as ctx:
            self.cfg.build_initialize_args({"MT5_PATH": secret,
                                            "MT5_TERMINAL_PATH": ""})
        self.assertNotIn(secret, str(ctx.exception))


class TestStoreIntegrity(unittest.TestCase):
    def test_corrupt_tail_recovered(self):
        tmp, clock, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("A"), [q("2026-09-28T16:00:05", bid=1.13630,
                                         ask=1.13641)])
        engine.process(sell_sig("B", symbol="GBPUSD"),
                       [q("2026-09-28T16:00:06", bid=1.13630, ask=1.13641)])
        n_before = store.event_count()
        with open(store.events_path, "a", encoding="utf-8") as f:
            f.write('{"event_id": "x"')   # truncated JSON line (crash mid-append)
        store2 = LifecycleStore(tmp, now_fn=lambda: u("2026-09-28T16:00:10"))
        self.assertEqual(store2.corrupt_tail, 1)
        self.assertEqual(store2.corrupt_mid, 0)
        self.assertEqual(store2.event_count(), n_before)
        self.assertIn("B", store2.open_positions())

    def test_snapshots_written_atomically(self):
        tmp, clock, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("P"), [
            q("2026-09-28T16:00:05", bid=1.13661, ask=1.13672),
            q("2026-09-28T16:08:00", bid=1.13660, ask=1.13671)])
        self.assertTrue(store.pending_snapshot.exists())
        with open(store.pending_snapshot, encoding="utf-8") as f:
            row = json.loads(f.readline())
        self.assertEqual(row["signal_id"], "P")
        self.assertEqual(row["pending_type"], "SELL_STOP")
        clock.advance(seconds=5)
        engine.process(sell_sig("O", symbol="GBPUSD"),
                       [q("2026-09-28T16:00:10", bid=1.13630, ask=1.13641)])
        self.assertTrue(store.open_snapshot.exists())
        with open(store.open_snapshot, encoding="utf-8") as f:
            row = json.loads(f.readline())
        self.assertEqual(row["signal_id"], "O")

    def test_integrity_summary(self):
        _, _, store, engine = make_env("2026-09-28T16:00:05")
        engine.process(sell_sig("A"), [q("2026-09-28T16:00:05", bid=1.13630,
                                         ask=1.13641)])
        summary = store.integrity_summary()
        self.assertEqual(summary["open_active"], 1)
        self.assertEqual(summary["schema_version"], 2)


class TestSignalValidation(unittest.TestCase):
    def test_from_signal_dict_real_record(self):
        sig = {
            "signal_id": "EURUSD_H1_SELL_2026-09-28T16:00:00Z",
            "symbol": "EURUSD", "direction": "SELL", "pip_multiplier": 10000,
            "timestamp_utc": "2026-09-28T16:00:00",
            "trade": {"entry": 1.13628, "entry_zone": [1.13648, 1.13608],
                      "stop_loss": 1.13720, "take_profit": 1.13491,
                      "rr_ratio": 1.5, "expires_at_utc": "2026-09-28T22:00:00"},
        }
        esig = lc.from_signal_dict(sig)
        self.assertEqual(esig.entry, 1.13628)
        self.assertEqual((esig.zone_lo, esig.zone_hi), (1.13608, 1.13648))
        self.assertEqual(esig.texp, u(TEXP))
        self.assertEqual(esig.t_horizon, u("2026-09-28T22:00:00"))
        self.assertEqual(esig.executable_side, "bid")

    def test_signal_requires_trade_levels(self):
        with self.assertRaises(ValueError):
            lc.from_signal_dict({"signal_id": "X", "symbol": "EURUSD",
                                 "direction": "SELL", "timestamp_utc": T0})


if __name__ == "__main__":
    unittest.main(verbosity=2)