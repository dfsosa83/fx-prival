"""Tests for the A1 MT5-demo observation-environment setup module.

Mocks + synthetic payloads only. No MT5, no broker, no market data, no orders.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_mt5_demo_observation_environment as env  # noqa: E402

CFG = {"mode": "OBSERVATION_DEMO", "ORDERS_DISABLED": True}


class MockGateway:
    def __init__(self, trade_mode=0, symbol_ok=True, bars=True):
        self.trade_mode = trade_mode
        self.symbol_ok = symbol_ok
        self.bars = bars
        self.shutdown_called = False
        self.order_send_called = False

    def initialize(self):
        return True

    def shutdown(self):
        self.shutdown_called = True

    def account_info(self):
        return {"trade_mode": self.trade_mode}

    def symbol_info(self, s):
        return {"visible": True} if self.symbol_ok else None

    def symbol_select(self, s, enable=True):
        return self.symbol_ok

    def symbol_info_tick(self, s):
        return {"bid": 1.0, "ask": 2.0}

    def copy_rates_from_pos(self, s, tf, start, count):
        return [(i, 1.0, 2.0, 0.5, 1.5) for i in range(count)] if self.bars else None

    def positions_get(self):
        return []

    def orders_get(self):
        return []


class TestDemoObservationEnvironment(unittest.TestCase):
    def test_01_live_unverified_account_rejected(self):
        g = MockGateway(trade_mode=2)  # live
        with self.assertRaises(RuntimeError):
            env.run_setup(g, CFG)
        self.assertTrue(g.shutdown_called)

    def test_02_demo_account_accepted(self):
        g = MockGateway(trade_mode=0)
        att = env.run_setup(g, CFG)
        self.assertTrue(att["demo_verified"])

    def test_03_orders_disabled_guard(self):
        with self.assertRaises(ValueError):
            env.orders_disabled_guard({"mode": "OBSERVATION_DEMO"})

    def test_04_rejects_forbidden_order_method(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "bad.py"
            p.write_text("def f():\n    return " + "order_" + "send()\n", encoding="utf-8")
            hits = env.static_scan_forbidden([p])
            self.assertNotEqual(hits, [])

    def test_05_xauusd_only(self):
        self.assertEqual(env.SYMBOL, "XAUUSD")
        g = MockGateway(symbol_ok=False)
        self.assertFalse(env.xauusd_available(g))

    def test_06_only_h1_m30_m15(self):
        g = MockGateway()
        env.read_symbol_bars(g, "H1")
        with self.assertRaises(ValueError):
            env.read_symbol_bars(g, "D1")

    def test_07_redaction_of_account_server_fields(self):
        att = env.build_attestation(True, True, {"positions_count": 0, "orders_count": 0},
                                    {"H1": True, "M30": True, "M15": True}, True)
        for forbidden in ("login", "server", "balance", "equity", "margin", "leverage", "account_id"):
            self.assertNotIn(forbidden, att)
        # gateway account accessor returns only trade_mode
        self.assertEqual(set(MockGateway().account_info().keys()), {"trade_mode"})

    def test_08_count_only_reconciliation(self):
        self.assertEqual(env.reconcile_counts([1, 2, 3], [9]), {"positions_count": 3, "orders_count": 1})

    def test_09_bar_and_tick_payload_validation(self):
        env.validate_bar_payload([{"time": 1, "open": 1, "high": 2, "low": 0, "close": 1}])
        with self.assertRaises(ValueError):
            env.validate_bar_payload([{"time": 1, "open": 1, "high": 2, "low": 0}])

    def test_10_immediate_shutdown_after_validation(self):
        g = MockGateway()
        env.run_setup(g, CFG)
        self.assertTrue(g.shutdown_called)

    def test_11_no_persistent_price_or_account_storage(self):
        g = MockGateway()
        att = env.run_setup(g, CFG)
        # attestation carries no raw bars and no account fields
        self.assertNotIn("bars", att)
        self.assertNotIn("login", att)
        self.assertNotIn("balance", att)

    def test_12_no_order_method_invoked(self):
        g = MockGateway()
        env.run_setup(g, CFG)
        self.assertFalse(g.order_send_called)


if __name__ == "__main__":
    unittest.main(verbosity=2)
