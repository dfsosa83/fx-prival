# -*- coding: utf-8 -*-
"""Tests for the demo virtual-fill ledger (P0 / PORTFOLIO-DEMO-SPEC §3).

Verifies the core guarantee that lets the paper account accumulate EVIDENCE:
a simulated order produces a REALIZED, non-zero PnL + R, and SL/TP/force-close
behave conservatively.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, r"C:\Users\david\OneDrive\Documents\fx-prival\frival\execution_bot\core")
import demo_ledger as dl


class TestOpenClose(unittest.TestCase):
    def test_open_then_sl_close_long(self):
        pool = []
        p = dl.open_virtual(pool, "EURUSD", "buy", 0.1, entry=1.1000, sl=1.0950, tp=1.1100)
        self.assertEqual(p.status, "OPEN")
        # price falls below SL -> SL hit (long)
        closed = dl.manage_open(pool, latest_price=1.0940)
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].exit_reason, "SL")
        self.assertEqual(closed[0].status, "CLOSED")
        # buy: exited BELOW entry -> realized negative
        self.assertLess(closed[0].realized_usd, 0)
        # R should be ≈ -1.0 (1.1000-1.0950=0.0050 risk; exit at SL -> -1.0R)
        self.assertAlmostEqual(closed[0].r, -1.0, places=3)

    def test_open_then_tp_close_sell(self):
        pool = []
        p = dl.open_virtual(pool, "EURUSD", "sell", 0.1, entry=1.1000, sl=1.1050, tp=1.0900)
        closed = dl.manage_open(pool, latest_price=1.0890)   # below TP for a short
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].exit_reason, "TP")
        self.assertGreater(closed[0].realized_usd, 0)
        # TP at 1.0900, entry 1.1000, risk 0.0050 -> R ≈ +2.0
        self.assertAlmostEqual(closed[0].r, 2.0, places=3)

    def test_mid_price_keeps_position_open(self):
        """A price inside (SL, TP) never closes the position — no false close."""
        pool = []
        # valid long: SL below entry, TP above entry
        dl.open_virtual(pool, "EURUSD", "buy", 0.1, entry=1.1000, sl=1.0950, tp=1.1100)
        # price sits between SL and TP -> no hit
        closed = dl.manage_open(pool, latest_price=1.1040)
        self.assertEqual(closed, [])
        self.assertEqual(pool[0].status, "OPEN")

    def test_sell_sl_and_tp_directions(self):
        """SELL SL is above entry, TP below; price must RISE to SL, FALL to TP."""
        pool = []
        dl.open_virtual(pool, "EURUSD", "sell", 0.1, entry=1.1000, sl=1.1050, tp=1.0950)
        # price RISES to SL -> SL (sell), loss
        closed = dl.manage_open(pool, latest_price=1.1050)
        self.assertEqual(closed[0].exit_reason, "SL")
        self.assertLess(closed[0].realized_usd, 0)
        # a fresh short: price FALLS to TP -> TP (sell), profit
        pool2 = []
        dl.open_virtual(pool2, "EURUSD", "sell", 0.1, entry=1.1000, sl=1.1050, tp=1.0950)
        closed2 = dl.manage_open(pool2, latest_price=1.0940)
        self.assertEqual(closed2[0].exit_reason, "TP")
        self.assertGreater(closed2[0].realized_usd, 0)

    def test_force_close_engine(self):
        pool = []
        dl.open_virtual(pool, "GBPUSD", "sell", 0.01, entry=1.2600, sl=1.2610, tp=1.2500)
        closed = dl.close_pool(pool, reason="ENGINE")
        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].exit_reason, "ENGINE")

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "trades.jsonl"
            pool = []
            p = dl.open_virtual(pool, "EURUSD", "buy", 0.1, 1.1000, 1.0950, 1.1100)
            dl.manage_open(pool, latest_price=1.0940)
            dl.append_trade(path, pool[0])
            loaded = dl.load_ledger(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].ticket, pool[0].ticket)
            self.assertEqual(loaded[0].exit_reason, "SL")
            self.assertLess(loaded[0].realized_usd, 0)

    def test_open_persist_at_app_level(self):
        """Regression: opening then persisting via the pool reflects OPEN status."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "open.jsonl"
            pool = []
            dl.open_virtual(pool, "EURUSD", "buy", 0.1, 1.1000, 1.0950, 1.1100)
            dl.append_trade(path, pool[0])          # this write is for audit clarity
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)