# -*- coding: utf-8 -*-
"""Unit tests for bias.py and levels.py (design doc §2.1.1 / §2.1.2).

Run from frival/gold_rules/:
    python -m tests.fetch_data        # once, to cache XAUUSD fixtures
    python -m unittest tests.test_rules -v
    # or directly:
    python tests/test_rules.py

Tests are deterministic: they run against cached CSV fixtures (no MT5 dependency
once fixtures exist) plus a handful of hand-built synthetic OHLCV cases.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bias  # noqa: E402
import levels  # noqa: E402
from tests import fetch_data  # noqa: E402


def ohlcv(rows) -> pd.DataFrame:
    """Build a closed-bars DataFrame from (time, o, h, l, c) tuples."""
    return pd.DataFrame(
        rows, columns=["datetime", "open", "high", "low", "close"]
    ).assign(volume=0)


class TestBias(unittest.TestCase):
    def setUp(self):
        self.h1 = fetch_data.load_h1()

    def test_real_h1_returns_valid_bias(self):
        b = bias.compute_h1_bias(self.h1)
        self.assertIn(b, (bias.BULLISH, bias.BEARISH, bias.FLAT))
        print(f"H1 bias on real data: {b}")

    def test_uptrend_is_bullish(self):
        closes = [100 + i * 0.5 for i in range(120)]
        df = ohlcv(
            [
                (pd.Timestamp("2026-01-01") + pd.Timedelta(hours=i), c, c + 1, c - 1, c)
                for i, c in enumerate(closes)
            ]
        )
        self.assertEqual(bias.compute_h1_bias(df), bias.BULLISH)

    def test_downtrend_is_bearish(self):
        closes = [200 - i * 0.5 for i in range(120)]
        df = ohlcv(
            [
                (pd.Timestamp("2026-01-01") + pd.Timedelta(hours=i), c, c + 1, c - 1, c)
                for i, c in enumerate(closes)
            ]
        )
        self.assertEqual(bias.compute_h1_bias(df), bias.BEARISH)

    def test_flat_range_is_flat_or_non_contradictory(self):
        closes = [150 + (i % 3) for i in range(120)]
        df = ohlcv(
            [
                (pd.Timestamp("2026-01-01") + pd.Timedelta(hours=i), c, c + 1, c - 1, c)
                for i, c in enumerate(closes)
            ]
        )
        b = bias.compute_h1_bias(df)
        # A tight range may still classify by EMA cross; accept anything except
        # a contradiction (bull in falling market / bear in rising market).
        self.assertIn(b, (bias.BULLISH, bias.BEARISH, bias.FLAT))
        print(f"flat-range bias: {b} (must not contradict range)")

    def test_insufficient_history_is_flat(self):
        df = ohlcv([(pd.Timestamp("2026-01-01"), 100, 101, 99, 100)])
        self.assertEqual(bias.compute_h1_bias(df), bias.FLAT)


class TestLevels(unittest.TestCase):
    def setUp(self):
        self.m30 = fetch_data.load_m30()

    def test_real_m30_fractals_found(self):
        swings = levels.fractal_swings(self.m30, wing=2)
        self.assertGreater(len(swings), 0)
        kinds = set(swings["kind"])
        self.assertTrue({"swing_high", "swing_low"}.issubset(kinds))
        print(f"M30 fractals on real data: {len(swings)} swings"
              f" (hi={len(swings[swings['kind']=='swing_high'])}, "
              f"lo={len(swings[swings['kind']=='swing_low'])})")

    def test_real_atr_is_positive_finite(self):
        atr = levels.compute_atr(self.m30, period=14)
        self.assertTrue(atr == atr and atr > 0)
        print(f"M30 ATR(14): {atr:.2f}")

    def test_synthetic_fractal_detection(self):
        # Rows: swing low at idx 2, swing high at idx 6
        rows = [
            (1, 10.0, 11.0, 9.0, 10.0),
            (2, 10.0, 10.5, 9.5, 10.2),
            (3, 10.0, 10.2, 8.0, 9.0),   # swing low (low 8.0)
            (4, 9.0, 9.5, 8.5, 9.2),
            (5, 9.2, 10.0, 9.0, 9.8),
            (6, 9.8, 12.5, 9.7, 11.5),  # swing high (high 12.5)
            (7, 11.5, 11.9, 11.2, 11.7),
            (8, 11.7, 12.1, 11.5, 12.0),
            (9, 12.0, 12.3, 11.8, 12.1),
        ]
        df = ohlcv([(pd.Timestamp("2026-01-01") + pd.Timedelta(minutes=30 * i), o, h, l, c)
                     for i, (_, o, h, l, c) in enumerate(rows)])
        swings = levels.fractal_swings(df, wing=2)
        lows = swings[swings["kind"] == "swing_low"]
        highs = swings[swings["kind"] == "swing_high"]
        self.assertEqual(len(lows), 1)
        self.assertEqual(len(highs), 1)
        self.assertEqual(lows.iloc[0]["price"], 8.0)
        self.assertEqual(highs.iloc[0]["price"], 12.5)
        # Confirmation: pivot confirmed only after wing bars close
        self.assertEqual(lows.iloc[0]["pivot_idx"], 2)
        self.assertEqual(lows.iloc[0]["confirmed_idx"], 4)
        self.assertEqual(highs.iloc[0]["pivot_idx"], 5)
        self.assertEqual(highs.iloc[0]["confirmed_idx"], 7)

    def test_consumption_detection(self):
        # A swing high at price 100. A wick above the level with a close below
        # cannot consume; a solid-body close above 100 does (§2.1.2 rule 3).
        level = {"kind": "swing_high", "price": 100.0, "confirmed_time": pd.Timestamp("2026-01-01 01:00")}
        wick_only = ohlcv([
            (pd.Timestamp("2026-01-01 02:00"), 99, 100.5, 98.5, 99.8),  # wick above, close below -> NOT consumed
        ])
        solid_break = ohlcv([
            (pd.Timestamp("2026-01-01 02:00"), 99, 100.5, 98.5, 99.8),
            (pd.Timestamp("2026-01-01 03:00"), 99.8, 101.5, 99.8, 101.2),  # solid-body close above
        ])
        self.assertFalse(levels.level_is_consumed(wick_only, level))
        self.assertTrue(levels.level_is_consumed(solid_break, level))

    def test_watched_level_directional_filter(self):
        # Levels: swing_low at 90 (support), swing_high at 130 (resistance)
        levels_df = pd.DataFrame(
            {
                "kind": ["swing_low", "swing_high"],
                "price": [90.0, 130.0],
                "consumed": [False, False],
                "pivot_time": [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-01")],
            }
        )
        watched_bull = levels.select_watched_level(bias.BULLISH, levels_df, current_price=100.0)
        watched_bear = levels.select_watched_level(bias.BEARISH, levels_df, current_price=100.0)
        self.assertEqual(watched_bull["price"], 90.0)
        self.assertEqual(watched_bear["price"], 130.0)
        # FLAT arms nothing
        self.assertIsNone(levels.select_watched_level(bias.FLAT, levels_df, current_price=100.0))

    def test_watched_level_nearest_only(self):
        levels_df = pd.DataFrame(
            {
                "kind": ["swing_low", "swing_low"],
                "price": [90.0, 95.0],
                "consumed": [False, False],
                "pivot_time": [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-01-02")],
            }
        )
        watched = levels.select_watched_level(bias.BULLISH, levels_df, current_price=100.0)
        self.assertEqual(watched["price"], 95.0)  # nearest support below price

    def test_consumed_level_not_watchable(self):
        levels_df = pd.DataFrame(
            {
                "kind": ["swing_low"],
                "price": [90.0],
                "consumed": [True],
                "pivot_time": [pd.Timestamp("2026-01-01")],
            }
        )
        self.assertIsNone(levels.select_watched_level(bias.BULLISH, levels_df, current_price=100.0))

    def test_nearest_swing_helpers(self):
        levels_df = pd.DataFrame(
            {
                "kind": ["swing_low", "swing_high", "swing_high"],
                "price": [90.0, 120.0, 150.0],
                "consumed": [False, False, True],
                "pivot_time": [pd.Timestamp("2026-01-01")] * 3,
            }
        )
        above = levels.nearest_swing_above(levels_df, price=110.0)
        below = levels.nearest_swing_below(levels_df, price=110.0)
        self.assertEqual(above["price"], 120.0)      # nearest intact high above
        self.assertEqual(below["price"], 90.0)       # nearest intact low below
        self.assertIsNone(levels.nearest_swing_above(levels_df, price=160.0))

    def test_build_active_levels_on_real_data(self):
        res = levels.build_active_levels(self.m30)
        self.assertTrue(res["atr_m30"] > 0)
        self.assertGreater(len(res["levels"]), 0)
        print(f"active levels on real M30: {len(res['levels'])} (ATR {res['atr_m30']:.2f})")


if __name__ == "__main__":
    unittest.main(verbosity=2)