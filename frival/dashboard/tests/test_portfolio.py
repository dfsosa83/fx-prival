# -*- coding: utf-8 -*-
"""Unit tests for the dashboard portfolio exposure lens.

Ground-truth expected values:
  SELL 0.08 EURUSD -> SHORT EUR 0.08, LONG USD 0.08
  SELL 0.08 GBPUSD -> SHORT GBP 0.08, LONG USD 0.08
  SELL 0.08 USDCAD -> SHORT USD 0.08, LONG CAD 0.08
  SELL 0.04 USDCHF -> SHORT USD 0.04, LONG CHF 0.04
  => USD total = +0.08 +0.08 -0.08 -0.04 = +0.04 LONG USD
  => EUR total -0.08, GBP -0.08, CAD +0.08, CHF +0.04
"""
import sys
import unittest

sys.path.insert(0, r"C:\Users\david\OneDrive\Documents\fx-prival\frival\dashboard\backend")
import portfolio


def pos(sym, typ, vol):
    return {"symbol": sym, "type": typ, "volume": vol, "ticket": 0, "profit": 0.0}


class TestExposure(unittest.TestCase):
    def test_single_buy_eurusd(self):
        expo = portfolio.compute_exposure([pos("EURUSD", "BUY", 1.0)])
        self.assertAlmostEqual(expo["currency_exposure"]["EUR"], 1.0)
        self.assertAlmostEqual(expo["currency_exposure"]["USD"], -1.0)
        self.assertAlmostEqual(expo["usd_exposure_units"], -1.0)  # long EUR = short USD

    def test_single_sell_eurusd(self):
        expo = portfolio.compute_exposure([pos("EURUSD", "SELL", 1.0)])
        self.assertAlmostEqual(expo["currency_exposure"]["EUR"], -1.0)
        self.assertAlmostEqual(expo["currency_exposure"]["USD"], 1.0)
        self.assertAlmostEqual(expo["usd_exposure_units"], 1.0)  # short EUR = long USD

    def test_sell_usdcad_has_usd_as_base(self):
        expo = portfolio.compute_exposure([pos("USDCAD", "SELL", 1.0)])
        self.assertAlmostEqual(expo["currency_exposure"]["USD"], -1.0)
        self.assertAlmostEqual(expo["currency_exposure"]["CAD"], 1.0)

    def test_four_shorts_net_usd(self):
        sim = [
            pos("EURUSD", "SELL", 0.08),
            pos("GBPUSD", "SELL", 0.08),
            pos("USDCAD", "SELL", 0.08),
            pos("USDCHF", "SELL", 0.04),
        ]
        expo = portfolio.compute_exposure(sim)
        c = expo["currency_exposure"]
        self.assertAlmostEqual(c["EUR"], -0.08)
        self.assertAlmostEqual(c["GBP"], -0.08)
        self.assertAlmostEqual(c["CAD"], 0.08)
        self.assertAlmostEqual(c["CHF"], 0.04)
        # USD: +0.08 (EURUSD) +0.08 (GBPUSD) -0.08 (USDCAD) -0.04 (USDCHF)
        self.assertAlmostEqual(expo["usd_exposure_units"], 0.04)
        self.assertAlmostEqual(c["USD"], 0.04)

    def test_gold_long_hedges_usd(self):
        sim = [pos("XAUUSD", "BUY", 0.5)]
        expo = portfolio.compute_exposure(sim)
        self.assertAlmostEqual(expo["currency_exposure"]["XAU"], 0.5)
        self.assertAlmostEqual(expo["currency_exposure"]["USD"], -0.5)
        self.assertAlmostEqual(expo["usd_exposure_units"], -0.5)

    def test_gross_and_net(self):
        sim = [
            pos("EURUSD", "SELL", 0.08),
            pos("EURUSD", "BUY", 0.03),
        ]
        expo = portfolio.compute_exposure(sim)
        self.assertAlmostEqual(expo["gross_exposure"], 0.11)
        self.assertAlmostEqual(expo["net_exposure_symbols"]["EURUSD"], -0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)