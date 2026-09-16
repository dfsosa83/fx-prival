# -*- coding: utf-8 -*-
"""Unit tests for Claim C — breakout-continuation trigger (design v1.4).

Run from frival/gold_rules/:
    python tests/test_breakout.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine as eng  # noqa: E402
from engine import EngineState  # noqa: E402
from tests.test_engine import mmk15, run  # noqa: E402


def bull_h1(base=100.0):
    closes = [base - 20 + i * 0.25 for i in range(80)]   # ASCENDING = bullish
    return pd.DataFrame(
        {"datetime": [pd.Timestamp("2026-08-01") + pd.Timedelta(hours=i) for i in range(80)],
         "open": closes, "high": [c + 0.5 for c in closes],
         "low": [c - 0.5 for c in closes], "close": closes, "volume": 0}
    )


def bear_h1(base=100.0):
    closes = [base + 20 - i * 0.25 for i in range(80)]  # DESCENDING = bearish
    return pd.DataFrame(
        {"datetime": [pd.Timestamp("2026-08-01") + pd.Timedelta(hours=i) for i in range(80)],
         "open": closes, "high": [c + 0.5 for c in closes],
         "low": [c - 0.5 for c in closes], "close": closes, "volume": 0}
    )


def m30_resistance(resistance=100.5):
    """M30 with swing_high at `resistance` (idx 2) AND a higher swing_high at
    resistance+2 (idx 20) so TP1 resolves after the first break."""
    rows = []
    n = 60
    for i in range(n):
        if i == 2:
            hi, lo, cl = resistance, 97.5, 99.0
        elif i in (0, 1, 3, 4, 5):
            hi, lo, cl = resistance - 1.0, 97.5, 99.0
        elif i == 20:
            hi, lo, cl = resistance + 2.0, 98.0, resistance + 1.0
        elif i in (18, 19, 21, 22, 23):
            hi, lo, cl = resistance + 1.0, 98.0, resistance
        else:
            hi, lo, cl = resistance - 0.5, 98.0, resistance - 0.3
        rows.append((i * 30, cl, hi, lo, cl))
    return mmk15(rows)


def m30_support(support=95.0):
    """M30 with swing_low at `support` (idx 2) AND a lower swing_low at
    support-2.8 (idx 20) — wide enough to clear the 0.5×ATR merge rule so
    TP1 resolves after the first break."""
    rows = []
    n = 60
    for i in range(n):
        if i == 2:
            hi, lo, cl = 100.5, support, 99.0
        elif i in (0, 1, 3, 4, 5):
            hi, lo, cl = 100.5, support + 1.0, 99.0
        elif i == 22:
            hi, lo, cl = support + 1.0, support - 2.8, support - 1.5
        elif i in (20, 21, 23, 24, 25):
            hi, lo, cl = support + 1.5, support - 1.0, support
        else:
            hi, lo, cl = 100.0, support + 1.5, support + 0.5
        rows.append((i * 30, cl, hi, lo, cl))
    return mmk15(rows)


def flat_h1():
    closes = [100.0] * 80   # constant price => no trend => FLAT bias
    return pd.DataFrame(
        {"datetime": [pd.Timestamp("2026-08-01") + pd.Timedelta(hours=i) for i in range(80)],
         "open": closes, "high": [c + 0.5 for c in closes],
         "low": [c - 0.5 for c in closes], "close": closes, "volume": 0}
    )


class TestBreakout(unittest.TestCase):
    def setUp(self):
        self.eng = eng.default_engine()
        self.eng.breakout_enabled = True

    def test_bullish_breakout_fires(self):
        """BULLISH bias, resistance 100.5 above price, solid close through it
        -> ENTRY with comment GOLD_RULES_C."""
        m30 = m30_resistance(100.5)
        h1 = bull_h1()
        warm = [(t, 99.0, 99.9, 98.6, 99.3) for t in range(0, 240, 15)]
        action = [(240, 99.3, 100.9, 99.2, 100.7)]  # solid close above 100.5
        m15 = mmk15(warm + action)

        state, out = run(self.eng, m15, m30=m30, h1=h1, positions=0)
        entries = [(a, r) for _, a, r in out if a == eng.ENTRY]
        self.assertGreaterEqual(len(entries), 1, f"no ENTRY; out={out}")
        self.assertIn("CLAIM-C", entries[0][1])
        self.assertEqual(state.state, eng.IN_TRADE)
        self.assertEqual(state.active_trade["comment"], "GOLD_RULES_C")
        self.assertEqual(state.active_trade["variant"], "C")
        # SL must be BELOW the broken level (invalidation = broken level)
        self.assertLess(state.active_trade["sl"], 100.5)

    def test_bearish_breakout_fires(self):
        """BEARISH bias, support 95.0 below price, solid close through it
        -> SELL ENTRY with SL above the broken support."""
        m30 = m30_support(95.0)
        h1 = bear_h1()
        warm = [(t, 99.0, 99.8, 98.7, 99.2) for t in range(0, 240, 15)]
        action = [(240, 99.2, 99.5, 94.6, 94.8)]  # solid close below 95.0
        m15 = mmk15(warm + action)

        state, out = run(self.eng, m15, m30=m30, h1=h1, positions=0)
        entries = [(a, r) for _, a, r in out if a == eng.ENTRY]
        self.assertGreaterEqual(len(entries), 1, f"no ENTRY; out={out}")
        self.assertIn("CLAIM-C", entries[0][1])
        self.assertEqual(state.active_trade["variant"], "C")
        self.assertGreater(state.active_trade["sl"], 95.0)  # SL above broken support

    def test_flat_bias_no_breakout(self):
        """FLAT bias -> C must not fire even on a strong close."""
        m30 = m30_resistance(100.5)
        h1 = flat_h1()
        warm = [(t, 99.0, 99.9, 98.6, 99.3) for t in range(0, 240, 15)]
        action = [(240, 99.3, 100.9, 99.2, 100.7)]
        m15 = mmk15(warm + action)
        _, out = run(self.eng, m15, m30=m30, h1=h1, positions=0)
        self.assertNotIn(eng.ENTRY, [a for _, a, _ in out])

    def test_disabled_no_breakout(self):
        """breakout_enabled=False -> classic behavior only."""
        self.eng.breakout_enabled = False
        m30 = m30_resistance(100.5)
        h1 = bull_h1()
        warm = [(t, 99.0, 99.9, 98.6, 99.3) for t in range(0, 240, 15)]
        action = [(240, 99.3, 100.9, 99.2, 100.7)]
        m15 = mmk15(warm + action)
        _, out = run(self.eng, m15, m30=m30, h1=h1, positions=0)
        self.assertNotIn(eng.ENTRY, [a for _, a, _ in out])

    def test_concurrency_blocks_breakout(self):
        """If a position is already open, C must not add a second."""
        m30 = m30_resistance(100.5)
        h1 = bull_h1()
        warm = [(t, 99.0, 99.9, 98.6, 99.3) for t in range(0, 240, 15)]
        action = [(240, 99.3, 100.9, 99.2, 100.7)]
        m15 = mmk15(warm + action)
        _, out = run(self.eng, m15, m30=m30, h1=h1, positions=1)
        self.assertNotIn(eng.ENTRY, [a for _, a, _ in out])

    def test_low_rr_breakout_rejected(self):
        """Impossible R:R requirement blocks the breakout entry."""
        self.eng.breakout_min_rr = 5.0
        m30 = m30_resistance(100.5)
        h1 = bull_h1()
        warm = [(t, 99.0, 99.9, 98.6, 99.3) for t in range(0, 240, 15)]
        action = [(240, 99.3, 100.9, 99.2, 100.7)]
        m15 = mmk15(warm + action)
        _, out = run(self.eng, m15, m30=m30, h1=h1, positions=0)
        self.assertNotIn(eng.ENTRY, [a for _, a, _ in out])


if __name__ == "__main__":
    unittest.main(verbosity=2)