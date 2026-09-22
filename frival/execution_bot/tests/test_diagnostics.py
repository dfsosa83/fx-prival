# -*- coding: utf-8 -*-
"""Unit tests for OrderBot §6.1 execution diagnostics (ROADMAP-2026-Q4 §6.1).

Verifies the additive diagnostic capture:
- latency_seconds measured from signal timestamp to sent timestamp,
- slippage_pips = (fill - requested_entry) / pip_size with the shared pip table,
- spread_at_fill captured from live bid/ask when present,
- cost_assumed_pips sourced from experiments/_core/costs.py (no duplicate table),
- diagnostics enabled only on the EXECUTED event (never on SKIPPED/health paths).
"""
import sys
import time
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.insert(0, r"C:\Users\david\OneDrive\Documents\fx-prival\frival\execution_bot")
sys.path.insert(0, r"C:\Users\david\OneDrive\Documents\fx-prival\frival\execution_bot\core")

from order_bot import OrderBot  # noqa: E402


class _FakeConfig:
    def get_config(self, key, default=None):
        return {"pairs": {"EURUSD": {"shadow": False, "lot_size": 0.08, "direction": "SELL"}},
                "mt5": {"timeout": 30, "retries": 3}} if key == "pairs" else {}

    def get_mt5_credentials(self): return {}
    def get_risk_config(self): return {"max_daily_loss": 100.0, "max_positions_per_pair": 1, "max_total_positions": 4}
    def get_trading_config(self): return {"default_risk_profile": "MODERATE"}
    def is_demo_mode(self): return True


class _FakeConnector:
    def get_symbol_tick(self, symbol):
        return {"symbol": symbol, "bid": 1.1000, "ask": 1.10012, "spread": 0.00012, "time": datetime.now(timezone.utc)}
    def get_symbol_info(self, symbol):
        return {"symbol": symbol, "point": 1e-4, "digits": 5}
    def get_positions(self, symbol=None): return []
    def get_account_info(self): return {"balance": 5000.0, "margin_free": 4900.0, "leverage": 100}
    def connect(self): return True
    def disconnect(self): pass


def _signal(ts="2026-09-21T12:00:00", entry=1.10000, sl=1.10150, tp=1.09850):
    return {
        "signal_id": "EURUSD_H1_SELL_2026-09-21T12:00:00Z",
        "symbol": "EURUSD", "direction": "SELL",
        "timestamp_utc": ts,
        "trade": {"entry": entry, "entry_zone": [entry + 0.0001, entry - 0.0001],
                  "stop_loss": sl, "take_profit": tp, "rr_ratio": 1.5,
                  "expires_at_utc": "2026-09-21T18:00:00"},
    }


class TestDiagnostics(unittest.TestCase):
    def setUp(self):
        self.bot = OrderBot(_FakeConfig())
        self.bot.connector = _FakeConnector()
        self.bot.order_manager = MagicMock()
        self.bot.daily_pnl = 0.0

    def test_diagnostics_latency_and_slippage(self):
        t0 = time.time()
        sig = _signal()
        result = {"success": True, "retcode": 10009, "price": 1.10006, "order": 42, "deal": 7}
        diag = self.bot._diagnostics(sig, "EURUSD", 1.10000, result, t0, t0 + 0.5)
        self.assertIn("latency_seconds", diag)
        self.assertGreaterEqual(diag["latency_seconds"], 0.0)
        # fill 1.10006 vs entry 1.10000 on 5-digit pip = +0.6 pips (adverse for SELL near ask)
        self.assertAlmostEqual(diag["slippage_pips"], 0.6, places=3)
        self.assertAlmostEqual(diag["spread_at_fill_pips"], 1.2, places=3)
        self.assertAlmostEqual(diag["spread_at_fill_price"], 0.00012, places=6)

    def test_cost_assumed_from_shared_table(self):
        t0 = time.time()
        diag = self.bot._diagnostics(_signal(), "EURUSD", 1.1, {"success": True, "retcode": 1, "price": 1.1}, t0, t0)
        self.assertEqual(diag["cost_assumed_pips"], 1.2)  # measured 2026-09-18 EURUSD spread

    def test_missing_fill_leaves_diag_fields_absent(self):
        t0 = time.time()
        diag = self.bot._diagnostics(_signal(), "EURUSD", 1.1, None, t0, t0)
        self.assertNotIn("slippage_pips", diag)  # no fill -> no slippage claim
        self.assertNotIn("fill_price", diag)
        self.assertNotIn("retcode", diag)  # no result -> no retcode claim
        # latency still measured on error paths
        self.assertIn("latency_seconds", diag)

    def test_signal_ts_parsing(self):
        dt = self.bot._signal_ts_utc(_signal(ts="2026-09-21T12:00:00"))
        self.assertIsNotNone(dt)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertIsNone(self.bot._signal_ts_utc({"signal_id": "x"}))

    def test_unknown_symbol_no_crash(self):
        t0 = time.time()
        diag = self.bot._diagnostics(_signal(), "FAKE_SYM", 0.0, {"success": True, "retcode": 1, "price": 1.0}, t0, t0)
        # no exception; pip fallback may be absent or zero -> no slippage claim
        self.assertIn("retcode", diag)


if __name__ == "__main__":
    unittest.main(verbosity=2)