"""Unit and integration tests for portfolio.benchmark (A and B)."""
import numpy as np
import pandas as pd
import pytest

from core.costs import CostModel
from portfolio.benchmark import build_benchmarks, equal_weights_for
from portfolio.accounting_v2 import _rebalance_dates


def make_cost_model() -> CostModel:
    cm = CostModel()
    cm.defaults = {"slippage_pips_fx": 0.0}
    # Two financed instruments to exercise holding costs
    cm.costs = {
        "SPX": {"spread_pips": 0.0, "commission_pct": 0.0005, "financing_annual_pct": 0.0252},
        "EURUSD": {"spread_pips": 1.8, "commission_per_lot": 0.0, "financing_annual_pct": 0.0},
        "XAUUSD": {"spread_pips": 0.0, "commission_pct": 0.0005, "financing_annual_pct": 0.0},
    }
    return cm


@pytest.fixture
def returns15():
    """Deterministic 15-ticker panel for benchmark construction."""
    rng = np.random.RandomState(42)
    dates = pd.date_range("2024-01-02", periods=120, freq="B")
    tickers = [f"T{i:02d}" for i in range(15)]
    return pd.DataFrame(rng.randn(len(dates), 15) * 0.005, index=dates, columns=tickers)


@pytest.fixture
def costs15():
    cm = CostModel()
    cm.defaults = {"slippage_pips_fx": 0.5}
    cm.costs = {f"T{i:02d}": {"spread_pips": 0.0, "commission_pct": 0.001, "financing_annual_pct": 0.0}
                for i in range(15)}
    return cm


class TestEqualWeights:
    def test_sum_to_one(self):
        w = equal_weights_for(["A", "B", "C"])
        assert w.sum() == pytest.approx(1.0)
        assert len(w) == 3

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty universe"):
            equal_weights_for([])


class TestBuildBenchmarks:
    def test_both_built(self, returns15, costs15):
        tickers = returns15.columns.tolist()
        a, b = build_benchmarks(returns15, costs15, tickers)
        assert a is not None and b is not None
        assert set(a.nav.columns) == {"nav_gross", "nav_net"}
        assert set(b.nav.columns) == {"nav_gross", "nav_net"}

    def test_a_no_trades_after_entry(self, returns15, costs15):
        tickers = returns15.columns.tolist()
        a, _ = build_benchmarks(returns15, costs15, tickers)
        n_trades = (a.trade_w.abs().sum(axis=1) > 1e-10).sum()
        assert n_trades == 1  # entry only

    def test_b_has_monthly_trades(self, returns15, costs15):
        tickers = returns15.columns.tolist()
        _, b = build_benchmarks(returns15, costs15, tickers)
        n_trades = (b.trade_w.abs().sum(axis=1) > 1e-10).sum()
        reb_dates = _rebalance_dates(returns15.index, "M")
        assert n_trades >= 1 + len(reb_dates)  # entry + monthly

    def test_a_b_start_equal_after_entry(self, returns15, costs15):
        """Both benchmarks start at initial_nav after entry (day 0)."""
        tickers = returns15.columns.tolist()
        a, b = build_benchmarks(returns15, costs15, tickers)
        assert a.nav["nav_net"].iloc[0] == pytest.approx(1.0)
        assert b.nav["nav_net"].iloc[0] == pytest.approx(1.0)

    def test_net_le_gross_both(self, returns15, costs15):
        tickers = returns15.columns.tolist()
        a, b = build_benchmarks(returns15, costs15, tickers)
        assert (a.nav["nav_net"] <= a.nav["nav_gross"] + 1e-10).all()
        assert (b.nav["nav_net"] <= b.nav["nav_gross"] + 1e-10).all()

    def test_cash_zero_both(self, returns15, costs15):
        tickers = returns15.columns.tolist()
        a, b = build_benchmarks(returns15, costs15, tickers)
        assert (a.exposures["cash_weight"] == 0.0).all()
        assert (b.exposures["cash_weight"] == 0.0).all()


class TestMonthEndLagIntegration:
    """
    MANDATED integration test (Amendment 2 / Revision 2 §2.2):

    A month-end target decision does NOT receive the same day's return and
    becomes effective only on the next trading day.
    """

    def _make_spike_scenario(self):
        dates = pd.date_range("2024-01-02", periods=45, freq="B")
        reb = _rebalance_dates(dates, "M")
        K = reb[0]
        ret = pd.DataFrame({"T00": 0.0, "T01": 0.0}, index=dates)
        return dates, K, ret

    def test_month_end_target_does_not_get_same_day_return(self):
        """
        Spike placed ON the month-end day K.
        Day-K gross return must reflect the PRE-trade drifted holdings
        (50/50 from prior days of zero returns), NOT the new target.
        """
        dates, K, ret = self._make_spike_scenario()
        ret.loc[K, "T00"] = 0.05  # +5% spike ON month-end

        cm = CostModel()
        cm.defaults = {"slippage_pips_fx": 0.0}
        cm.costs = {
            "T00": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
            "T01": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
        }
        w = pd.Series({"T00": 0.5, "T01": 0.5})
        from portfolio.accounting_v2 import compute_monthly_rebalanced
        res = compute_monthly_rebalanced(ret, cm, w)

        # Day-K gross return = old 50/50 position earns the spike
        assert res.returns["gross_return"].loc[K] == pytest.approx(0.5 * 0.05, abs=1e-10)

    def test_month_end_target_effective_next_day(self):
        """
        Spike placed on the day AFTER month-end K.
        The new target (set at close[K]) MUST capture the spike at K+1.
        """
        dates, K, ret = self._make_spike_scenario()
        Knext = dates[dates.get_loc(K) + 1]
        ret.loc[Knext, "T01"] = 0.04  # +4% spike on day after month-end

        cm = CostModel()
        cm.defaults = {"slippage_pips_fx": 0.0}
        cm.costs = {
            "T00": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
            "T01": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
        }
        w = pd.Series({"T00": 0.5, "T01": 0.5})
        from portfolio.accounting_v2 import compute_monthly_rebalanced
        res = compute_monthly_rebalanced(ret, cm, w)

        # Position at K+1 is the post-rebalance target (50/50)
        assert res.returns["gross_return"].loc[Knext] == pytest.approx(0.5 * 0.04, abs=1e-10)


class TestHandComputed:
    def test_buy_and_hold_nav_hand_computed(self):
        """
        Benchmark A NAV matches hand computation on 2 assets, 3 days.

        Convention: position decided at close[0] earns return interval [0,1]
        (row 1 of returns). Row 0 precedes the backtest start and is unearned.
        """
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        ret = pd.DataFrame({
            "A": [0.00, 0.10, 0.00],   # A moves +10% in interval [0,1]
            "B": [0.00, 0.00, 0.00],
        }, index=dates)
        cm = CostModel()
        cm.defaults = {"slippage_pips_fx": 0.0}
        cm.costs = {
            "A": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
            "B": {"spread_pips": 0.0, "commission_pct": 0.0, "financing_annual_pct": 0.0},
        }
        w = pd.Series({"A": 0.5, "B": 0.5})

        from portfolio.accounting_v2 import compute_buy_and_hold
        res = compute_buy_and_hold(ret, cm, w, initial_nav=100.0)

        # Day 0: NAV = 100 (no return yet)
        assert res.nav["nav_net"].iloc[0] == pytest.approx(100.0, abs=1e-8)
        # Day 1: earns 0.5 * 0.10 = 0.05 -> NAV = 105
        assert res.nav["nav_net"].iloc[1] == pytest.approx(105.0, abs=1e-8)
        # Day 2: returns zero -> NAV unchanged
        assert res.nav["nav_net"].iloc[2] == pytest.approx(105.0, abs=1e-8)

    def test_monthly_rebalanced_trades_explicit(self):
        """Benchmark B trades reconcile to target-drifted at month-end."""
        dates = pd.date_range("2024-01-02", periods=45, freq="B")
        rng = np.random.RandomState(3)
        ret = pd.DataFrame({"A": rng.randn(45) * 0.01, "B": rng.randn(45) * 0.01}, index=dates)
        cm = CostModel()
        cm.defaults = {"slippage_pips_fx": 0.0}
        cm.costs = {
            "A": {"spread_pips": 0.0, "commission_pct": 0.001, "financing_annual_pct": 0.0},
            "B": {"spread_pips": 0.0, "commission_pct": 0.001, "financing_annual_pct": 0.0},
        }
        w = pd.Series({"A": 0.5, "B": 0.5})
        from portfolio.accounting_v2 import compute_monthly_rebalanced
        res = compute_monthly_rebalanced(ret, cm, w)
        reb = _rebalance_dates(dates, "M")
        for d in reb:
            trade = res.trade_w.loc[d]
            # After trade, holdings == target (50/50)
            np.testing.assert_allclose(res.holdings_w.loc[d].values, [0.5, 0.5], atol=1e-8)