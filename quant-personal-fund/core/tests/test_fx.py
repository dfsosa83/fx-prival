"""Unit tests for core.fx USD conversion module."""
import numpy as np
import pandas as pd
import pytest

from core.fx import (
    convert_cross_eurjpy,
    convert_local_to_usd,
    convert_panel_to_usd,
    fx_leg_log_return,
)


@pytest.fixture
def fx_prices():
    """Synthetic FX price levels with known moves."""
    dates = pd.date_range("2024-01-02", periods=6, freq="B")
    # EURUSD: 1.00 -> 1.05 over 5 days (rising USD per EUR)
    eurusd = pd.Series([1.00, 1.01, 1.02, 1.03, 1.04, 1.05], index=dates)
    # USDJPY: 100 -> 110 (JPY per USD rising = JPY weakening vs USD)
    usdjpy = pd.Series([100.0, 102.0, 104.0, 106.0, 108.0, 110.0], index=dates)
    return pd.DataFrame({"EURUSD": eurusd, "USDJPY": usdjpy})


class TestFxLegLogReturn:
    def test_direct_pair(self, fx_prices):
        """EUR leg log return equals ln(EURUSD_t / EURUSD_{t-1})."""
        leg = fx_leg_log_return(fx_prices, "EUR")
        expected = np.log(1.05 / 1.04)
        assert leg.iloc[-1] == pytest.approx(expected)

    def test_inverse_pair(self, fx_prices):
        """JPY leg log return = -ln(USDJPY_t / USDJPY_{t-1})."""
        leg = fx_leg_log_return(fx_prices, "JPY")
        expected = -np.log(110.0 / 108.0)
        assert leg.iloc[-1] == pytest.approx(expected)

    def test_unknown_currency(self, fx_prices):
        """Unknown currency raises ValueError."""
        with pytest.raises(ValueError, match="No USD conversion"):
            fx_leg_log_return(fx_prices, "XYZ")

    def test_missing_pair(self, fx_prices):
        """Missing required pair raises KeyError."""
        with pytest.raises(KeyError, match="GBPUSD"):
            fx_leg_log_return(fx_prices, "GBP")


class TestConvertLocalToUsd:
    def test_constant_fx_identity(self, fx_prices):
        """If FX is constant, R_usd == R_local."""
        dates = fx_prices.index
        local = pd.Series([0.01, 0.02, -0.01, 0.005, 0.0], index=dates[1:])
        fx_flat = fx_prices.copy()
        fx_flat["EURUSD"] = 1.10  # constant
        conv = convert_local_to_usd(local, fx_flat, "EUR")
        np.testing.assert_allclose(conv.values, local.values, rtol=1e-10)

    def test_inverse_sign(self, fx_prices):
        """JPY weakening (USDJPY up) reduces the USD return of a JPY asset."""
        dates = fx_prices.index
        local = pd.Series(0.0, index=dates[1:])  # flat local returns
        conv = convert_local_to_usd(local, fx_prices, "JPY")
        # USDJPY rising -> leg negative -> USD return negative
        assert conv.iloc[-1] < 0
        assert conv.iloc[-1] == pytest.approx(-np.log(110.0 / 108.0))

    def test_missing_fx_ffill(self):
        """Missing FX in the MIDDLE is forward-filled up to limit."""
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        local = pd.Series([0.01] * 5, index=dates)
        # FX observed at 0,1,2; missing at 3,4 -> ffill from 2
        eurusd = pd.Series([1.05, 1.06, 1.07, np.nan, np.nan], index=dates)
        fx = pd.DataFrame({"EURUSD": eurusd})
        conv = convert_local_to_usd(local, fx, "EUR", max_ffill_days=5)
        # Day 0: no prior FX level -> NaN leg
        assert np.isnan(conv.iloc[0])
        # Day 1: leg = ln(1.06/1.05)
        assert conv.iloc[1] == pytest.approx(0.01 + np.log(1.06 / 1.05))
        # Day 2: leg = ln(1.07/1.06)
        assert conv.iloc[2] == pytest.approx(0.01 + np.log(1.07 / 1.06))
        # Day 3: FX missing -> ffill leg (level 1.07 -> leg 0)
        assert conv.iloc[3] == pytest.approx(0.01)
        # Day 4: FX missing -> ffill leg (level 1.07 -> leg 0)
        assert conv.iloc[4] == pytest.approx(0.01)

    def test_missing_fx_beyond_limit(self):
        """FX missing beyond ffill limit -> NaN (never zero-filled)."""
        dates = pd.date_range("2024-01-02", periods=6, freq="B")
        local = pd.Series([0.01] * 6, index=dates)
        # FX observed at 0,1; missing 2,3,4; observed 5
        eurusd = pd.Series([1.05, 1.06, np.nan, np.nan, np.nan, 1.07], index=dates)
        fx = pd.DataFrame({"EURUSD": eurusd})
        conv = convert_local_to_usd(local, fx, "EUR", max_ffill_days=2)
        # Day 2: within 2-day limit (level 1.06 filled, leg 0)
        assert conv.iloc[2] == pytest.approx(0.01)
        # Day 3: still within 2-day limit (level 1.06 filled, leg 0)
        assert conv.iloc[3] == pytest.approx(0.01)
        # Day 4: beyond 2-day limit -> NaN
        assert np.isnan(conv.iloc[4])
        # Day 5: level present but prior level NaN (gap never filled) -> leg NaN
        assert np.isnan(conv.iloc[5])

    def test_no_lookahead(self, fx_prices):
        """A jump at t+1 does not affect the conversion at t."""
        dates = pd.date_range("2024-01-02", periods=4, freq="B")
        local = pd.Series(0.0, index=dates)
        # EURUSD constant 1.00 for t0-t2, then jumps to 1.50 at t3
        eurusd = pd.Series([1.00, 1.00, 1.00, 1.50], index=dates)
        fx = pd.DataFrame({"EURUSD": eurusd})
        conv = convert_local_to_usd(local, fx, "EUR")
        # t2 return uses EURUSD[t2]/EURUSD[t1] = 1.0/1.0 -> 0
        assert conv.iloc[2] == pytest.approx(0.0)
        # t3 return uses EURUSD[t3]/EURUSD[t2] = 1.50 -> +ln(1.5)
        assert conv.iloc[3] == pytest.approx(np.log(1.5))

    def test_synthetic_known_value(self):
        """Hand-computed exact conversion."""
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        # Local price: 100 -> 102 (2% local return at day 1)
        local = pd.Series([np.nan, np.log(102 / 100), 0.0], index=dates)
        # EURUSD: 1.00 -> 1.01 (~0.995% USD-per-EUR rise at day 1)
        eurusd = pd.Series([1.00, 1.01, 1.01], index=dates)
        fx = pd.DataFrame({"EURUSD": eurusd})
        conv = convert_local_to_usd(local, fx, "EUR")
        expected = np.log(102 / 100) + np.log(1.01 / 1.00)
        assert conv.iloc[1] == pytest.approx(expected)


class TestConvertPanelToUsd:
    def test_panel_conversion(self, fx_prices):
        """Only mapped non-FX tickers are converted."""
        dates = fx_prices.index[1:]
        panel = pd.DataFrame({
            "SPX": pd.Series([0.01, 0.02, 0.01, 0.0, 0.01], index=dates),   # USD asset
            "SX5E": pd.Series([0.01, 0.01, 0.01, 0.01, 0.01], index=dates),  # EUR asset
        })
        ccy_map = {"SX5E": "EUR"}
        out = convert_panel_to_usd(panel, fx_prices, ccy_map)
        # SPX unchanged
        np.testing.assert_allclose(out["SPX"].values, panel["SPX"].values)
        # SX5E converted
        expected = panel["SX5E"] + fx_leg_log_return(fx_prices, "EUR").reindex(dates).values
        np.testing.assert_allclose(out["SX5E"].values, expected.values)


class TestConvertCrossEurjpy:
    def test_cross_conversion(self):
        """R_usd(EURJPY) = r_EURJPY - r_USDJPY."""
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        eurjpy = pd.Series([0.0, np.log(160 / 150), 0.0], index=dates)
        usdjpy = pd.Series([150.0, 155.0, 160.0], index=dates)
        conv = convert_cross_eurjpy(eurjpy, usdjpy)
        expected = np.log(160 / 150) - np.log(155 / 150)
        assert conv.iloc[1] == pytest.approx(expected)

    def test_cross_missing_fx(self):
        """Missing USDJPY leg (level-ffill semantics) -> NaN beyond limit."""
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        eurjpy = pd.Series([0.0, 0.01, 0.02, 0.03, 0.04], index=dates)
        # USDJPY observed at 0,1; missing 2,3; observed 4
        usdjpy = pd.Series([150.0, 155.0, np.nan, np.nan, 160.0], index=dates)
        conv = convert_cross_eurjpy(eurjpy, usdjpy, max_ffill_days=1)
        # Day 1: leg = -ln(155/150) applied
        assert conv.iloc[1] == pytest.approx(0.01 - np.log(155 / 150))
        # Day 2: FX missing -> ffill level (155) -> leg 0 -> conv = 0.02
        assert conv.iloc[2] == pytest.approx(0.02)
        # Day 3: FX missing, gap beyond 1-day limit -> NaN
        assert np.isnan(conv.iloc[3])
        # Day 4: leg = -ln(160/155) from new observation pair? No prior fill:
        # levels_ff[4]=160, levels_ff[3]=NaN -> leg NaN
        assert np.isnan(conv.iloc[4])