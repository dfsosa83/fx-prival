"""Unit tests for portfolio.accounting_v2 economic engine."""
import numpy as np
import pandas as pd
import pytest

from core.costs import CostModel
from portfolio.accounting_v2 import (
    PortfolioResultV2,
    compute_buy_and_hold,
    compute_monthly_rebalanced,
    _drift_weights,
    _exposures,
    _rebalance_dates,
)


def make_cost_model(with_financing: bool = True) -> CostModel:
    """Cost model: A/B symmetric commission, optional financing."""
    cm = CostModel()
    cm.defaults = {"slippage_pips_fx": 0.0}
    cm.costs = {
        "A": {"spread_pips": 0.0, "commission_pct": 0.001,
              "financing_annual_pct": 0.0252 if with_financing else 0.0},
        "B": {"spread_pips": 0.0, "commission_pct": 0.001,
              "financing_annual_pct": 0.0252 if with_financing else 0.0},
    }
    return cm


def two_asset_returns(n=30, seed=7):
    """Deterministic 2-asset returns."""
    rng = np.random.RandomState(seed)
    dates = pd.date_range("2024-01-02", periods=n, freq="B")
    ret = pd.DataFrame({
        "A": rng.randn(n) * 0.005,
        "B": rng.randn(n) * 0.005,
    }, index=dates)
    return ret


@pytest.fixture
def returns2():
    return two_asset_returns()


@pytest.fixture
def weights2():
    return pd.Series({"A": 0.5, "B": 0.5})


class TestDriftWeights:
    def test_conservation(self):
        """Drift preserves sum = 1."""
        w = pd.Series({"A": 0.6, "B": 0.4})
        r = pd.Series({"A": 0.05, "B": -0.01})
        drifted = _drift_weights(w, r)
        assert drifted.sum() == pytest.approx(1.0)
        # A outperformed -> A weight grows
        assert drifted["A"] > 0.6

    def test_zero_returns_no_drift(self):
        w = pd.Series({"A": 0.5, "B": 0.5})
        r = pd.Series({"A": 0.0, "B": 0.0})
        drifted = _drift_weights(w, r)
        np.testing.assert_allclose(drifted.values, w.values)


class TestRebalanceDates:
    def test_month_end(self):
        """Rebalance dates are last trading day of each month."""
        dates = pd.date_range("2024-01-02", periods=40, freq="B")
        reb = _rebalance_dates(dates, "M")
        # 40 business days ~ Jan+Feb => 2 month-ends
        assert len(reb) >= 2
        for d in reb:
            # last business day of its month in the series
            month = pd.Timestamp(d).to_period("M")
            month_days = dates[dates.to_period("M") == month]
            assert d == month_days[-1]


class TestComputeEconomicBenchmark:
    def test_buy_and_hold_no_trades_after_entry(self, returns2, weights2):
        """Benchmark A: only the initial trade; no rebalance trades."""
        cm = make_cost_model()
        res = compute_buy_and_hold(returns2, cm, weights2)
        n_nonzero_trades = (res.trade_w.abs().sum(axis=1) > 1e-10).sum()
        assert n_nonzero_trades == 1  # day 0 entry only
        # Entry cost booked at day 1
        assert res.costs["txn_cost"].iloc[1] == pytest.approx(
            0.5 * 0.001 + 0.5 * 0.001, abs=1e-10
        )

    def test_entry_cost_once(self, returns2, weights2):
        """Entry transaction cost appears exactly once (at day 1)."""
        cm = make_cost_model(with_financing=False)
        res = compute_buy_and_hold(returns2, cm, weights2)
        txn_days = (res.costs["txn_cost"].abs() > 1e-12).sum()
        assert txn_days == 1
        assert res.costs["txn_cost"].iloc[1] == pytest.approx(0.001, abs=1e-10)

    def test_monthly_trades_generated(self, returns2, weights2):
        """Benchmark B generates trades on month-end dates."""
        cm = make_cost_model(with_financing=False)
        res = compute_monthly_rebalanced(returns2, cm, weights2)
        trade_days = (res.trade_w.abs().sum(axis=1) > 1e-10).sum()
        assert trade_days > 1  # entry + monthly rebalances
        # Trade amounts reconcile: trade = target - drifted
        reb = _rebalance_dates(returns2.index, "M")
        for d in reb:
            if d in returns2.index:
                assert res.trade_w.loc[d].abs().sum() > 1e-10

    def test_net_nav_le_gross_nav(self, returns2, weights2):
        """Net NAV <= Gross NAV always (costs reduce)."""
        cm = make_cost_model(with_financing=True)
        for builder in [compute_buy_and_hold, compute_monthly_rebalanced]:
            res = builder(returns2, cm, weights2)
            assert (res.nav["nav_net"] <= res.nav["nav_gross"] + 1e-10).all()

    def test_financing_single_charge(self):
        """H1 regression: financing appears ONLY in hold cost, never in txn."""
        cm = make_cost_model(with_financing=True)
        # Scenario: all-in on A for 3 days then out
        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        ret = pd.DataFrame({"A": [0.0, 0.01, -0.005], "B": [0.0, 0.0, 0.0]}, index=dates)
        w = pd.Series({"A": 1.0, "B": 0.0})
        res = compute_buy_and_hold(ret, cm, w)
        # Day 1 entry txn = commission only (no financing)
        assert res.costs["txn_cost"].iloc[1] == pytest.approx(0.001, abs=1e-12)
        # Hold cost positive for the days the position is held (days 1 and 2)
        assert (res.costs["hold_cost"] > 0).any()
        # Total financing charged = daily_rate * 2 held days (once each)
        daily_rate = 0.0252 / 252.0
        assert res.costs["hold_cost"].sum() == pytest.approx(daily_rate * 2.0, abs=1e-10)

    def test_lag_month_end_no_same_day_return(self):
        """
        Mandated integration test: a month-end target decision does NOT
        receive the same day's return and becomes effective only on the
        next trading day.

        Construct returns with a large spike ON the month-end date K.
        The portfolio's day-K gross return must reflect ONLY the pre-trade
        drifted holdings (which do not include the new target), and the
        new target's first market exposure must be r[K+1].
        """
        dates = pd.date_range("2024-01-02", periods=45, freq="B")
        reb = _rebalance_dates(dates, "M")
        K = reb[0]  # first month-end

        ret = pd.DataFrame({"A": 0.0, "B": 0.0}, index=dates)
        # Spike ON the month-end day K: A returns +5%
        ret.loc[K, "A"] = 0.05

        cm = make_cost_model(with_financing=False)
        w = pd.Series({"A": 0.5, "B": 0.5})
        res = compute_monthly_rebalanced(ret, cm, w)

        # Day-K gross return: position decided at close[K-1] = 50/50
        # drift only from prior days (all 0 returns) -> 50/50
        # The spike at K is earned by the OLD position, NOT the new target.
        expected_gross_K = 0.5 * 0.05
        assert res.returns["gross_return"].loc[K] == pytest.approx(expected_gross_K, abs=1e-10)

        # After rebalance at close[K], holdings = target 50/50 for interval K+1.
        # The NEXT spike is placed at K+1 on B to prove the new target captures it.
        Knext = dates[dates.get_loc(K) + 1]
        ret.loc[Knext, "B"] = 0.04
        res2 = compute_monthly_rebalanced(ret, cm, w)
        # Position at K+1 = post-rebalance target (50/50), NOT drifted old weights
        assert res2.returns["gross_return"].loc[Knext] == pytest.approx(
            0.5 * 0.00 + 0.5 * 0.04, abs=1e-10
        )

    def test_exposure_cash_semantics(self, returns2, weights2):
        """net/gross/cash are separate; A/B have cash=0 and net=gross=1 after entry."""
        cm = make_cost_model(with_financing=False)
        for builder in [compute_buy_and_hold, compute_monthly_rebalanced]:
            res = builder(returns2, cm, weights2)
            expo = res.exposures
            assert "net_exposure" in expo.columns
            assert "gross_exposure" in expo.columns
            assert "cash_weight" in expo.columns
            # After entry (day>=1), net=gross=1 and cash=0 (within float tol)
            tail = expo.iloc[1:]
            assert (tail["cash_weight"] == 0.0).all()
            np.testing.assert_allclose(tail["net_exposure"].values, 1.0, atol=1e-9)
            np.testing.assert_allclose(tail["gross_exposure"].values, 1.0, atol=1e-9)

    def test_collateral_reserved(self, returns2, weights2):
        """collateral_margin is reserved and None in 04A."""
        cm = make_cost_model()
        res = compute_buy_and_hold(returns2, cm, weights2)
        assert res.collateral_margin is None

    def test_result_type(self, returns2, weights2):
        cm = make_cost_model()
        res = compute_monthly_rebalanced(returns2, cm, weights2)
        assert isinstance(res, PortfolioResultV2)
        assert set(res.nav.columns) == {"nav_gross", "nav_net"}
        assert set(res.returns.columns) == {"gross_return", "net_return"}
        assert set(res.costs.columns) == {"txn_cost", "hold_cost"}

    def test_turnover_formula(self, returns2, weights2):
        """Turnover = 0.5 * sum|trade_w|, with entry turnover booked at day 1."""
        cm = make_cost_model(with_financing=False)
        res = compute_monthly_rebalanced(returns2, cm, weights2)
        # Day 0: entry trade exists in trade_w but its turnover is booked at day 1
        assert res.turnover.iloc[0] == pytest.approx(0.0, abs=1e-12)
        assert res.turnover.iloc[1] == pytest.approx(0.5 * res.trade_w.iloc[0].abs().sum(), abs=1e-10)
        # Days 2+ : turnover matches 0.5*sum|trade_w|
        np.testing.assert_allclose(
            res.turnover.iloc[2:].values,
            (0.5 * res.trade_w.iloc[2:].abs().sum(axis=1)).values,
            atol=1e-10,
        )