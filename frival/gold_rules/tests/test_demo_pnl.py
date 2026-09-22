# -*- coding: utf-8 -*-
"""P0 acceptance test for the demo PnL fix (PORTFOLIO-DEMO-SPEC §3).

Verifies the exact guarantee the paper-account needs: a simulated (demo)
trade that goes SL/TP produces a NON-ZERO realized PnL + R appended to the
shared ledger — the condition that was previously `ticket=0, pnl=0` forever.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, r"C:\Users\david\OneDrive\Documents\fx-prival\frival\gold_rules")

import run_gold_rules as ggr
from execution_bot.core import demo_ledger as dl


class _FakeCM:
    def is_demo_mode(self):
        return True


class _FakeRunner(ggr.GoldRunner):
    """Minimal driver: same PnL realization, no MT5/live loop."""

    def __init__(self, led_path: Path):
        self.cfg = {"symbol": "XAUUSD", "risk": {"fixed_lot": 0.01, "contract_size": 100.0}}
        self.dry = False
        self.cm = _FakeCM()
        self._led = led_path
        self.state = SimpleNamespace(direction="sell")

    @property
    def cfg(self):
        return self._cfg

    @cfg.setter
    def cfg(self, v):
        self._cfg = v


class TestDemoPnlAcceptance(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.led = Path(self._td.name) / "demo_trades_ledger.jsonl"
        self._patcher = patch.object(ggr, "DEMO_LEDGER_FILE", self.led)
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._td.cleanup()

    def test_demo_trade_realizes_nonzero_pnl_on_sl(self):
        r = _FakeRunner(self.led)
        trade = {"entry": 4300.0, "sl": 4305.0, "tp1": 4285.0}  # sell, R=5
        r._realize_trade(trade, bid=4306.0, reason="SL")
        rows = dl.load_ledger(self.led)
        self.assertEqual(len(rows), 1, "exactly one closed trade must land in the ledger")
        row = rows[0]
        self.assertEqual(row.exit_reason, "SL")
        self.assertNotEqual(row.realized_usd, 0.0, "PnL must be non-zero (was pnl=0 before)")
        self.assertLess(row.realized_usd, 0)          # SL on a sell = loss
        self.assertAlmostEqual(row.r, -1.0, places=3)  # exit at SL = -1R

    def test_demo_trade_realizes_tp(self):
        r = _FakeRunner(self.led)
        trade = {"entry": 4300.0, "sl": 4305.0, "tp1": 4290.0}  # sell, TP 10 pts off
        r._realize_trade(trade, bid=4289.0, reason="TP")
        rows = dl.load_ledger(self.led)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].exit_reason, "TP")
        self.assertGreater(rows[0].realized_usd, 0)

    def test_no_ledger_write_in_live_mode(self):
        r = _FakeRunner(self.led)
        r.cm = SimpleNamespace(is_demo_mode=lambda: False)   # LIVE
        r._realize_trade({"entry": 4300.0, "sl": 4305.0, "tp1": 4285.0}, 4306.0, "SL")
        self.assertFalse(self.led.exists(), "live mode must never write the demo ledger")


if __name__ == "__main__":
    unittest.main(verbosity=2)