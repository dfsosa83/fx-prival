# -*- coding: utf-8 -*-
"""EXEC-D1 → DEMO terminal executor tests (offline; fake MT5, no connection)."""

import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

EXEC_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXEC_DIR))
sys.path.insert(0, str(EXEC_DIR / "core"))   # flat: core/__init__ needs pytz/mt5

import exec_d1_terminal as et
import lifecycle as lc
from lifecycle_store import LifecycleStore

TRADE_ACTION_DEAL = 1
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
ORDER_TIME_GTC = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_FOK = 0
SYMBOL_FILLING_FOK = 1
SYMBOL_FILLING_IOC = 2
TRADE_RETCODE_DONE = 10009


class FakeMT5:
    """Recorded-call fake of the MetaTrader5 surface used by the executor."""

    TRADE_ACTION_DEAL = TRADE_ACTION_DEAL
    ORDER_TYPE_BUY = ORDER_TYPE_BUY
    ORDER_TYPE_SELL = ORDER_TYPE_SELL
    ORDER_TIME_GTC = ORDER_TIME_GTC
    ORDER_FILLING_IOC = ORDER_FILLING_IOC
    ORDER_FILLING_FOK = ORDER_FILLING_FOK
    SYMBOL_FILLING_FOK = SYMBOL_FILLING_FOK
    SYMBOL_FILLING_IOC = SYMBOL_FILLING_IOC
    TRADE_RETCODE_DONE = TRADE_RETCODE_DONE

    def __init__(self):
        self.sent = []
        self._positions = []
        self._day_pnl = [0.0]
        self.tick_price = {"bid": 1.1355, "ask": 1.1356}
        self.login = "7409623"
        self.server = "FPMarketsSC-Demo"
        self.filling_mode = SYMBOL_FILLING_IOC

    def initialize(self, path=""):
        return True

    def shutdown(self):
        return True

    def last_error(self):
        return None

    def account_info(self):
        return SimpleNamespace(login=self.login, server=self.server,
                               trade_mode=0, balance=5000.0)

    def symbol_info(self, symbol):
        return SimpleNamespace(filling_mode=self.filling_mode)

    def symbol_info_tick(self, symbol):
        return SimpleNamespace(bid=self.tick_price["bid"],
                               ask=self.tick_price["ask"],
                               time=datetime.now(timezone.utc))

    def positions_get(self, symbol=None):
        return self._positions

    def history_deals_get(self, start, end):
        return self._deals()

    def _deals(self):
        return [SimpleNamespace(profit=float(p)) for p in self._day_pnl]

    def order_send(self, request):
        self.sent.append(dict(request))
        return SimpleNamespace(retcode=TRADE_RETCODE_DONE, order=123456,
                               deal=654321)


class FakeMT5Reject(FakeMT5):
    """Broker/wrapper rejects every send (e.g. the 2026-09-30 comment bug)."""

    def __init__(self, last_error=(-2, 'Invalid "comment" argument')):
        super().__init__()
        self._last_error = last_error

    def order_send(self, request):
        self.sent.append(dict(request))
        return None

    def last_error(self):
        return self._last_error


def u(ts):
    d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return d.replace(tzinfo=timezone.utc)


class FakeClock:
    def __init__(self, ts):
        self._now = u(ts)

    def now(self):
        return self._now


def make_executor(*, fake=None, emergency=False):
    fake = fake or FakeMT5()
    gateway = et.Mt5Gateway(fake)
    tmp = tempfile.mkdtemp(prefix="exec_d1_term_")
    executions = Path(tmp) / "exec_d1_executions.jsonl"
    executor = et.TerminalExecutor(
        gateway, login_expected=fake.login,
        executions_path=executions,
        lots={"EURUSD": 0.08, "GBPUSD": 0.08, "USDCHF": 0.04, "USDCAD": 0.08})
    if emergency:
        et.EMERGENCY_STOP.write_text("stop", encoding="utf-8")
    return fake, executor, tmp


def sell_sig(sid="EURUSD_H1_SELL_D1T"):
    return {
        "signal_id": sid, "symbol": "EURUSD", "direction": "SELL",
        "pip_multiplier": 10000, "timestamp_utc": "2026-09-29T11:00:00",
        "trade": {"entry": 1.13466,
                  "entry_zone": [1.13486, 1.13446],
                  "stop_loss": 1.13543, "take_profit": 1.13350,
                  "rr_ratio": 1.5},
    }


class TestTerminalExecutor(unittest.TestCase):
    def setUp(self):
        et.EMERGENCY_STOP.unlink(missing_ok=True)

    def test_market_fill_executes_one_order_with_proven_shape(self):
        fake, executor, _ = make_executor()
        res = executor.execute_fill(
            signal_id="EURUSD_H1_SELL_D1T", symbol="EURUSD", direction="SELL",
            fill_price=1.13466, sl=1.13543, tp=1.13350)
        self.assertEqual(res["decision"], "EXECUTED")
        self.assertEqual(len(fake.sent), 1)
        req = fake.sent[0]
        self.assertEqual(req["action"], TRADE_ACTION_DEAL)
        self.assertEqual(req["type"], ORDER_TYPE_SELL)
        self.assertEqual(req["volume"], 0.08)
        self.assertEqual(req["price"], 1.13466)
        self.assertEqual(req["sl"], 1.13543)
        self.assertEqual(req["tp"], 1.13350)
        self.assertIn("D1-", req["comment"])
        self.assertEqual(req["type_filling"], ORDER_FILLING_IOC)
        # idempotent: second attempt is skipped
        res2 = executor.execute_fill(
            signal_id="EURUSD_H1_SELL_D1T", symbol="EURUSD", direction="SELL",
            fill_price=1.13466, sl=1.13543, tp=1.13350)
        self.assertEqual(res2["decision"], "SKIP")
        self.assertEqual(res2["reason"], "already_executed")
        self.assertEqual(len(fake.sent), 1)

    def test_position_exists_blocks_send(self):
        fake, executor, _ = make_executor()
        fake._positions = [SimpleNamespace(ticket=1, symbol="EURUSD",
                                           type=1)]  # POSITION_TYPE_SELL
        res = executor.execute_fill(
            signal_id="S", symbol="EURUSD", direction="SELL",
            fill_price=1.13466, sl=1.13543, tp=1.13350)
        self.assertEqual(res["decision"], "SKIP")
        self.assertEqual(res["reason"], "position_exists_sell")
        self.assertEqual(len(fake.sent), 0)

    def test_daily_loss_cap_blocks_send(self):
        fake, executor, _ = make_executor()
        fake._day_pnl = [-101.0]
        res = executor.execute_fill(
            signal_id="S", symbol="EURUSD", direction="SELL",
            fill_price=1.13466, sl=1.13543, tp=1.13350)
        self.assertEqual(res["reason"], "daily_loss_cap")
        self.assertEqual(len(fake.sent), 0)

    def test_demo_env_mismatch_blocks_send(self):
        fake, executor, _ = make_executor()
        fake.login = "9999999"
        res = executor.execute_fill(
            signal_id="S", symbol="EURUSD", direction="SELL",
            fill_price=1.13466, sl=1.13543, tp=1.13350)
        self.assertEqual(res["reason"], "demo_env_mismatch")
        self.assertEqual(len(fake.sent), 0)

    def test_emergency_stop_blocks_send(self):
        fake, executor, _ = make_executor(emergency=True)
        try:
            res = executor.execute_fill(
                signal_id="S", symbol="EURUSD", direction="SELL",
                fill_price=1.13466, sl=1.13543, tp=1.13350)
            self.assertEqual(res["reason"], "emergency_stop")
            self.assertEqual(len(fake.sent), 0)
        finally:
            et.EMERGENCY_STOP.unlink(missing_ok=True)

    def test_expired_unfilled_sends_nothing(self):
        fake, executor, _ = make_executor()
        clock = FakeClock("2026-09-29T11:00:05")
        store = LifecycleStore(tempfile.mkdtemp(), now_fn=clock.now)
        engine = lc.LifecycleEngine(store, now_fn=clock.now)
        out = engine.process(sell_sig("T"), [
            {"ts": "2026-09-29T11:00:05", "bid": 1.13661, "ask": 1.13672},
            {"ts": "2026-09-29T11:10:30", "bid": 1.13620, "ask": 1.13631},
        ])
        self.assertEqual(out, lc.EXPIRED_UNFILLED)
        self.assertEqual(len(fake.sent), 0)
        self.assertEqual(len(store.open_positions()), 0)

    def test_no_valid_pending_sends_nothing(self):
        fake, executor, _ = make_executor()
        clock = FakeClock("2026-09-29T11:00:05")
        store = LifecycleStore(tempfile.mkdtemp(), now_fn=clock.now)
        engine = lc.LifecycleEngine(store, now_fn=clock.now)
        out = engine.process(sell_sig("N"), [
            {"ts": "2026-09-29T11:00:05", "bid": 1.13440, "ask": 1.13451}])
        self.assertEqual(out, lc.NO_VALID_PENDING)
        self.assertEqual(len(fake.sent), 0)

    def test_pending_touch_fills_at_qualifying_quote_via_adapter(self):
        fake, executor, _ = make_executor()
        clock = FakeClock("2026-09-29T11:00:05")
        store = LifecycleStore(tempfile.mkdtemp(), now_fn=clock.now)
        engine = lc.LifecycleEngine(store, now_fn=clock.now)
        out = engine.process(sell_sig("P"), [
            {"ts": "2026-09-29T11:00:05", "bid": 1.13661, "ask": 1.13672}])
        self.assertEqual(out, lc.ENTRY_PENDING)
        # later touch at the zone boundary
        trig = engine.advance_pending("P", {
            "ts": "2026-09-29T11:03:00", "bid": 1.13486, "ask": 1.13497})
        self.assertEqual(trig, lc.PENDING_TRIGGERED)
        pos = store.open_position("P")
        # the CONSERVATIVE fill quote is what the executor must send
        res = executor.execute_fill(
            signal_id="P", symbol="EURUSD", direction="SELL",
            fill_price=float(pos["entry_used"]),
            sl=float(pos["stop_loss"]), tp=float(pos["take_profit"]))
        self.assertEqual(res["decision"], "EXECUTED")
        self.assertEqual(fake.sent[0]["price"], float(pos["entry_used"]))

    def test_close_position_sends_offset_without_sl_tp(self):
        fake, executor, _ = make_executor()
        res = executor.close_position(symbol="EURUSD", volume=0.08,
                                      side_open="SELL",
                                      comment="D1-CLOSE-X")
        self.assertTrue(res["success"])
        self.assertEqual(fake.sent[0]["type"], ORDER_TYPE_BUY)
        self.assertNotIn("sl", fake.sent[0])
        self.assertNotIn("tp", fake.sent[0])


class TestTickToQuote(unittest.TestCase):
    """Regression for the 2026-09-29 no_quote race: the quote timestamp must be
    the local UTC wall clock, never the broker `tick.time` epoch (server time),
    and a tick with no usable price must not fabricate a quote."""

    def test_stamps_utc_now_and_preserves_prices(self):
        before = datetime.now(timezone.utc)
        quote = et.tick_to_quote({"bid": 1.13550, "ask": 1.13561,
                                  "time": 1234567890})
        after = datetime.now(timezone.utc)
        ts = lc.parse_utc(quote["ts"])
        self.assertLessEqual(before - timedelta(seconds=1), ts)
        self.assertLessEqual(ts, after + timedelta(seconds=1))
        self.assertEqual(quote["bid"], 1.13550)
        self.assertEqual(quote["ask"], 1.13561)

    def test_missing_price_returns_none(self):
        self.assertIsNone(et.tick_to_quote({"bid": None, "ask": 1.1}))
        self.assertIsNone(et.tick_to_quote({"bid": 1.1}))
        self.assertIsNone(et.tick_to_quote(None))

    def test_carries_broker_time_for_audit(self):
        quote = et.tick_to_quote({"bid": 1.1, "ask": 1.2, "time": 1234567890})
        self.assertEqual(quote["broker_time"], 1234567890)


class TestTickFreshness(unittest.TestCase):
    """Offset-free staleness guard: broker tick time must advance over wall time."""

    def setUp(self):
        self._now = datetime(2026, 9, 29, 12, 0, 0, tzinfo=timezone.utc)

    def _now_fn(self):
        return self._now

    def _advance(self, seconds):
        self._now += timedelta(seconds=seconds)

    def test_advancing_ticks_are_fresh(self):
        f = et.TickFreshness(max_stale_seconds=90, now_fn=self._now_fn)
        self.assertTrue(f.observe("EURUSD", 1000))    # first sight
        self._advance(1)
        self.assertTrue(f.observe("EURUSD", 1001))
        self._advance(1)
        self.assertTrue(f.observe("EURUSD", 1002))

    def test_quiet_moment_within_grace_is_fresh(self):
        f = et.TickFreshness(max_stale_seconds=90, now_fn=self._now_fn)
        f.observe("EURUSD", 1000)
        self._advance(30)
        self.assertTrue(f.observe("EURUSD", 1000))

    def test_frozen_feed_goes_stale(self):
        f = et.TickFreshness(max_stale_seconds=90, now_fn=self._now_fn)
        self.assertTrue(f.observe("EURUSD", 1000))    # first sight
        self._advance(91)
        self.assertFalse(f.observe("EURUSD", 1000))   # no advance past grace

    def test_recovery_after_advance_is_fresh(self):
        f = et.TickFreshness(max_stale_seconds=90, now_fn=self._now_fn)
        f.observe("EURUSD", 1000)
        self._advance(120)
        self.assertFalse(f.observe("EURUSD", 1000))
        self._advance(1)
        self.assertTrue(f.observe("EURUSD", 1001))


class TestExecD1Enabled(unittest.TestCase):
    def test_enabled_true(self):
        tmp = tempfile.mkdtemp()
        p = Path(tmp) / "settings.yaml"
        p.write_text(
            "# t\n"
            "trading:\n  mode: demo\n"
            "execution:\n  enabled: true\n  scope: demo\n"
            "mt5:\n  timeout: 30\n", encoding="utf-8")
        self.assertTrue(et.exec_d1_enabled(p))

    def test_enabled_true_with_inline_comment(self):
        # Real settings.yaml writes "enabled: true   # comment"; the parser must
        # strip the inline comment or the delegation gate fails (2026-09-29).
        tmp = tempfile.mkdtemp()
        p = Path(tmp) / "settings.yaml"
        p.write_text(
            "# t\n"
            "execution:\n"
            "  enabled: true                  # EXEC-D1 terminal runner is the entry path\n"
            "  terminal_scope: demo\n"
            "mt5:\n  timeout: 30\n", encoding="utf-8")
        self.assertTrue(et.exec_d1_enabled(p))

    def test_enabled_false_when_absent(self):
        tmp = tempfile.mkdtemp()
        p = Path(tmp) / "settings.yaml"
        p.write_text("trading:\n  mode: demo\n", encoding="utf-8")
        self.assertFalse(et.exec_d1_enabled(p))

    def test_enabled_false_when_missing_file(self):
        self.assertFalse(et.exec_d1_enabled(Path(tempfile.mkdtemp()) / "nope.yaml"))


class TestOrderComment(unittest.TestCase):
    """Regression for 2026-09-30: f"D1-{signal_id}" was 38 chars and every real
    order was rejected with (-2, 'Invalid "comment" argument')."""

    def test_short_id_keeps_readable_form(self):
        self.assertEqual(et.order_comment("EURUSD_H1_SELL_D1T"),
                         "D1-EURUSD_H1_SELL_D1T")

    def test_real_long_signal_id_is_within_mt5_limit(self):
        c = et.order_comment("GBPUSD_H1_SELL_2026-09-30T07:00:00Z")
        self.assertLessEqual(len(c), et.MAX_COMMENT_LEN)
        self.assertTrue(c.startswith("D1-"))

    def test_truncated_comments_do_not_collide(self):
        a = "GBPUSD_H1_SELL_2026-09-30T07:00:00Z"
        b = "GBPUSD_H1_SELL_2026-09-30T08:00:00Z"
        self.assertNotEqual(et.order_comment(a), et.order_comment(b))
        for sid in (a, b):
            self.assertLessEqual(len(et.order_comment(sid)), et.MAX_COMMENT_LEN)


class TestRequestGuards(unittest.TestCase):
    def test_validate_levels_orientation(self):
        et.validate_levels(is_sell=True, price=1.10, sl=1.11, tp=1.09, digits=5)
        et.validate_levels(is_sell=False, price=1.10, sl=1.09, tp=1.11, digits=5)
        with self.assertRaises(et.ExecutorError):
            et.validate_levels(is_sell=True, price=1.10, sl=1.09, tp=1.09, digits=5)
        with self.assertRaises(et.ExecutorError):
            et.validate_levels(is_sell=False, price=1.10, sl=1.11, tp=1.11, digits=5)

    def test_overlong_comment_is_refused_before_send(self):
        fake, executor, _ = make_executor()
        with self.assertRaises(et.ExecutorError):
            executor.gateway.place_market(
                symbol="EURUSD", volume=0.08, mt5_type=ORDER_TYPE_SELL,
                price=1.10, sl=1.11, tp=1.09, comment="x" * 40)
        self.assertEqual(len(fake.sent), 0)

    def test_execute_fill_records_invalid_request_without_crashing(self):
        fake, executor, _ = make_executor()
        res = executor.execute_fill(          # SL equal to fill -> invalid stops
            signal_id="GBPUSD_H1_SELL_2026-09-30T07:00:00Z", symbol="GBPUSD",
            direction="SELL", fill_price=1.10, sl=1.10, tp=1.09)
        self.assertEqual(res["decision"], "FAILED")
        self.assertIn("request_invalid", res["error"])
        self.assertEqual(len(fake.sent), 0)

    def test_comment_actually_sent_is_within_limit(self):
        fake, executor, _ = make_executor()
        executor.execute_fill(
            signal_id="GBPUSD_H1_SELL_2026-09-30T07:00:00Z", symbol="GBPUSD",
            direction="SELL", fill_price=1.10, sl=1.11, tp=1.09)
        self.assertLessEqual(len(fake.sent[0]["comment"]), et.MAX_COMMENT_LEN)

    def test_filling_mode_selected_from_symbol_info(self):
        fake, executor, _ = make_executor()
        fake.filling_mode = SYMBOL_FILLING_FOK       # IOC unsupported
        res = executor.execute_fill(
            signal_id="S", symbol="EURUSD", direction="SELL",
            fill_price=1.13466, sl=1.13543, tp=1.13350)
        self.assertEqual(res["decision"], "EXECUTED")
        self.assertEqual(fake.sent[0]["type_filling"], ORDER_FILLING_FOK)


class TestExecutionReconciliation(unittest.TestCase):
    """A VIRTUAL_OPEN whose real send failed must not remain a phantom open."""

    def _engine(self, tmp):
        clock = FakeClock("2026-09-29T11:00:05")
        store = LifecycleStore(tmp, now_fn=clock.now)
        engine = lc.LifecycleEngine(store, now_fn=clock.now,
                                    entry_mode=lc.ENTRY_MODE_REANCHOR)
        return store, engine

    def _open(self, engine, sid):
        out = engine.process(sell_sig(sid), [
            {"ts": "2026-09-29T11:00:05", "bid": 1.13550, "ask": 1.13561}])
        self.assertEqual(out, lc.MARKET_FILLED)

    def test_failed_send_retracts_phantom_open(self):
        store, engine = self._engine(tempfile.mkdtemp())
        self._open(engine, "E")
        self.assertIn("E", store.open_positions())
        engine.mark_execution_failed("E", reason="send_failed",
                                     detail="Invalid comment argument")
        self.assertNotIn("E", store.open_positions())
        self.assertEqual(len(store.closed_records()), 0)   # not a trade
        fails = store.execution_failures()
        self.assertEqual(len(fails), 1)
        self.assertEqual(fails[0]["payload"]["reason"], "send_failed")
        self.assertTrue(store.acquires("EURUSD", "SELL"))  # slot released

    def test_reconcile_keeps_open_with_real_execution(self):
        store, engine = self._engine(tempfile.mkdtemp())
        self._open(engine, "K")
        self.assertEqual(engine.reconcile_executions({"K"}, set()), [])
        self.assertIn("K", store.open_positions())

    def test_reconcile_keeps_open_when_broker_holds_symbol(self):
        store, engine = self._engine(tempfile.mkdtemp())
        self._open(engine, "H")
        self.assertEqual(engine.reconcile_executions(set(), {"EURUSD"}), [])
        self.assertIn("H", store.open_positions())

    def test_reconcile_retracts_phantom(self):
        store, engine = self._engine(tempfile.mkdtemp())
        self._open(engine, "P")
        self.assertEqual(engine.reconcile_executions(set(), set()), ["P"])
        self.assertNotIn("P", store.open_positions())
        self.assertEqual(len(store.execution_failures()), 1)

    def test_rejecting_broker_then_mark_failed(self):
        fake, executor, _ = make_executor(fake=FakeMT5Reject())
        store, engine = self._engine(tempfile.mkdtemp())
        self._open(engine, "R")
        pos = store.open_position("R")
        res = executor.execute_fill(
            signal_id="R", symbol="EURUSD", direction="SELL",
            fill_price=float(pos["entry_used"]),
            sl=float(pos["stop_loss"]), tp=float(pos["take_profit"]))
        self.assertEqual(res["decision"], "FAILED")
        self.assertIn("Invalid", res["error"])
        engine.mark_execution_failed("R", reason="send_failed",
                                     detail=str(res.get("error")))
        self.assertNotIn("R", store.open_positions())
        self.assertEqual(len(store.execution_failures()), 1)

    def test_executed_signal_ids_reads_executions_log(self):
        fake, executor, _ = make_executor()
        executor.execute_fill(
            signal_id="S", symbol="EURUSD", direction="SELL",
            fill_price=1.13466, sl=1.13543, tp=1.13350)
        self.assertEqual(executor.executed_signal_ids(), {"S"})


if __name__ == "__main__":
    unittest.main(verbosity=2)