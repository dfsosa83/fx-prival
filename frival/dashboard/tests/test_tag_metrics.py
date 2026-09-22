# -*- coding: utf-8 -*-
"""Unit tests for the Stage-2 tag metrics (P0.2).

Roadmap P0.2 validation checks (ROADMAP-2026-Q4-RESEARCH.md §9 P0.2):
- the new EV/R field is always <= the zero-cost EV/R for the same trade set;
- empty / insufficient-data books degrade gracefully (no fabricated R);
- the shared _core cost+bootstrap modules are what actually compute the numbers.
"""
import sys
import unittest

sys.path.insert(0, r"C:\Users\david\OneDrive\Documents\fx-prival\frival\dashboard\backend")
import tag_metrics

from experiments._core import bootstrap as _bootstrap


def trade(symbol="EURUSD", comment="frival_abc1234567890", r=0.5, entry=1.10, sl=1.11,
          profit=5.0):
    """A closed trade; risk = |entry - sl| in price units."""
    return {
        "symbol": symbol,
        "comment": comment,
        "R": r,
        "risk_price": abs(entry - sl),
        "entry": entry,
        "sl": sl,
        "profit": profit,
    }


class TestTagClassification(unittest.TestCase):
    def test_gold_tags_recognized(self):
        self.assertEqual(tag_metrics.classify_tag("GOLD_RULES_v1"), "GOLD_RULES_v1")
        self.assertEqual(tag_metrics.classify_tag("pos GOLD_RULES_C xauusd"), "GOLD_RULES_C")

    def test_frival_comment_is_fx_ml(self):
        self.assertEqual(tag_metrics.classify_tag("frival_e9271b3f4c00a11"), "FX_ML")

    def test_empty_and_unknown(self):
        self.assertEqual(tag_metrics.classify_tag(""), "UNKNOWN")
        self.assertEqual(tag_metrics.classify_tag("manual-adhoc"), "UNKNOWN")


class TestNetEVRBelowRaw(unittest.TestCase):
    """Roadmap P0.2 check: net EV/R <= zero-cost EV/R for the same trade set."""

    def test_net_evr_strictly_below_raw_with_positive_cost(self):
        ledger = [trade(r=0.5), trade(r=0.2), trade(r=-0.5), trade(r=0.9),
                  trade(r=0.1), trade(r=-0.3)]
        res = tag_metrics.evr_series(ledger, pair="EURUSD")
        self.assertIsNotNone(res["evr_net"])
        self.assertLess(res["evr_net"], res["evr_raw"])
        # cost is strictly positive for a measured pair
        self.assertGreater(res["cost_pips_used"], 0.0)

    def test_net_evr_holds_for_buy_side_too(self):
        ledger = [trade(sl=1.09, r=0.6), trade(sl=1.09, r=-0.4), trade(sl=1.09, r=0.3)]
        res = tag_metrics.evr_series(ledger, pair="EURUSD")
        self.assertLessEqual(res["evr_net"], res["evr_raw"])

    def test_zero_cost_converts_to_zero_cost_R(self):
        # cost_pips = 0 must leave R unchanged (unit-level check of cost_in_R)
        self.assertEqual(tag_metrics.cost_in_R("EURUSD", 0.0, risk_price=0.001), 0.0)
        self.assertGreater(tag_metrics.cost_in_R("EURUSD", 1.2, risk_price=0.001), 0.0)

    def test_cost_pips_reuses_measured_table(self):
        self.assertEqual(tag_metrics.round_trip_cost_pips("EURUSD", "ALL"), 1.2)
        self.assertEqual(tag_metrics.round_trip_cost_pips("GBPUSD", "ALL"), 1.6)


class TestGracefulDegradation(unittest.TestCase):
    def test_empty_ledger_gives_none_fields(self):
        res = tag_metrics.evr_series([], pair="EURUSD")
        self.assertEqual(res["n"], 0)
        self.assertIsNone(res["evr_net"])
        self.assertIsNone(res["ev_ci_95_lo"])

    def test_aggregate_empty_gives_empty_tags(self):
        self.assertEqual(tag_metrics.aggregate_by_tag([]), {})

    def test_trades_without_risk_are_not_fabricated(self):
        # R present but no risk distance -> cannot express cost in R: net is
        # NOT fabricated (stays None), n_cost_adjusted remains 0, raw is shown
        # for audit with the CI missing rather than a made-up number.
        ledger = [{"symbol": "EURUSD", "comment": "frival_x", "R": 0.3}]
        res = tag_metrics.evr_series(ledger, pair="EURUSD")
        self.assertEqual(res["n"], 1)
        self.assertEqual(res["n_cost_adjusted"], 0)
        self.assertIsNotNone(res["evr_raw"])
        # No eligible row -> must not pretend we can cost-adjust.
        self.assertIsNone(res["evr_net"])

    def test_aggregate_groups_and_counts(self):
        ledger = [
            trade(comment="GOLD_RULES_v1", symbol="XAUUSD", r=0.8, sl=4390.0, entry=4380.0, profit=5.0),
            trade(comment="GOLD_RULES_v1", symbol="XAUUSD", r=-0.5, sl=4390.0, entry=4380.0, profit=-2.5),
            trade(comment="frival_aaa", symbol="GBPUSD", r=0.2, profit=1.0),
            trade(comment="not-a-tag", symbol="EURUSD", r=0.1, profit=0.4),
        ]
        agg = tag_metrics.aggregate_by_tag(ledger)
        self.assertEqual(set(agg.keys()), {"GOLD_RULES_v1", "FX_ML", "UNKNOWN"})
        self.assertEqual(agg["GOLD_RULES_v1"]["trade_count"], 2)
        self.assertEqual(agg["GOLD_RULES_v1"]["win_pct"], 50.0)
        self.assertEqual(agg["FX_ML"]["trade_count"], 1)


class TestSharedCoreSourced(unittest.TestCase):
    def test_metrics_use_the_shared_core_modules(self):
        # The module hooks ml-signal-service/experiments/_core — no duplicated
        # cost constants or bootstrap logic inside the dashboard backend.
        import inspect
        src = inspect.getsource(tag_metrics)
        self.assertIn("from experiments._core", src)
        self.assertIn("block_bootstrap_ci", src)

    def test_ci_is_block_bootstrap(self):
        ledger = [trade(r=0.5), trade(r=0.4), trade(r=0.55), trade(r=-0.3),
                  trade(r=0.2), trade(r=-0.1), trade(r=0.35), trade(r=0.1)]
        res = tag_metrics.evr_series(ledger, pair="EURUSD")
        lo, hi = res["ev_ci_95_lo"], res["ev_ci_95_hi"]
        self.assertIsNotNone(lo)
        self.assertGreaterEqual(hi, lo)
        self.assertLessEqual(lo, res["evr_net"])
        self.assertGreaterEqual(hi, res["evr_net"])


if __name__ == "__main__":
    unittest.main(verbosity=2)