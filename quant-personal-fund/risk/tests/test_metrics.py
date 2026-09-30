"""Unit tests for risk.metrics module."""
import numpy as np
import pandas as pd
import pytest

from risk.metrics import (
    annualized_return,
    annualized_volatility,
    calmar_ratio,
    cost_to_gross_pnl,
    expected_shortfall,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    var_historical,
    performance_summary,
)


@pytest.fixture
def flat_nav():
    """NAV that never changes."""
    dates = pd.date_range("2026-01-05", periods=100, freq="B")
    return pd.Series(1.0, index=dates, name="nav")


@pytest.fixture
def rising_nav():
    """NAV with 10bp/day growth."""
    dates = pd.date_range("2026-01-05", periods=252, freq="B")
    returns = np.full(252, 0.001)
    nav = (1 + pd.Series(returns, index=dates)).cumprod()
    nav.name = "nav"
    return nav


@pytest.fixture
def volatile_returns():
    """Returns with known properties."""
    rng = np.random.RandomState(99)
    dates = pd.date_range("2020-01-01", periods=500, freq="B")
    return pd.Series(rng.randn(500) * 0.01, index=dates, name="ret")


class TestAnnualizedReturn:
    def test_no_change(self, flat_nav):
        assert annualized_return(flat_nav) == pytest.approx(0.0)

    def test_positive_growth(self, rising_nav):
        ann_ret = annualized_return(rising_nav)
        assert ann_ret > 0.0

    def test_short_series(self):
        nav = pd.Series([1.0], index=[pd.Timestamp("2026-01-05")])
        assert annualized_return(nav) == 0.0


class TestSharpeRatio:
    def test_constant_positive(self):
        """Constant positive returns → high Sharpe."""
        returns = pd.Series([0.001] * 200)
        sr = sharpe_ratio(returns)
        assert sr > 5.0

    def test_zero_excess(self):
        """Returns = 0 → Sharpe ≈ 0."""
        returns = pd.Series([0.0] * 200)
        sr = sharpe_ratio(returns)
        assert sr == pytest.approx(0.0, abs=0.01)

    def test_with_risk_free_rate(self):
        """Positive rf reduces Sharpe for positive mean returns."""
        rng = np.random.RandomState(99)
        returns = pd.Series(0.001 + rng.randn(200) * 0.002)
        sr_no_rf = sharpe_ratio(returns, rf_annual=0.0)
        sr_with_rf = sharpe_ratio(returns, rf_annual=0.03)
        assert sr_with_rf < sr_no_rf


class TestMaxDrawdown:
    def test_no_loss(self, rising_nav):
        dd, peak, trough = max_drawdown(rising_nav)
        assert dd == pytest.approx(0.0)

    def test_known_drawdown(self):
        """NAV with known peak, trough, recovery."""
        nav = pd.Series(
            [100, 110, 105, 95, 100, 105, 120],
            index=pd.date_range("2026-01-05", periods=7),
        )
        dd, peak, trough = max_drawdown(nav)
        # Peak = day 1 (110), trough = day 3 (95), dd = (95-110)/110 = -0.1364
        assert dd == pytest.approx(-15.0 / 110.0, rel=0.01)
        assert trough == nav.index[3]


class TestVaRandES:
    def test_var_95(self, volatile_returns):
        """VaR at 95% is the 5th percentile."""
        var = var_historical(volatile_returns, 0.95)
        expected = np.percentile(volatile_returns, 5.0)
        assert var == pytest.approx(expected)

    def test_es_greater_than_var(self, volatile_returns):
        """Expected shortfall >= |VaR| for the same confidence."""
        var = var_historical(volatile_returns, 0.95)
        es = expected_shortfall(volatile_returns, 0.95)
        # ES is the average of returns <= VaR, so ES <= VaR (more negative or equal)
        assert es <= var + 1e-10


class TestSortinoRatio:
    def test_only_positive_returns(self):
        """Sortino is inf when there are no negative returns."""
        returns = pd.Series([0.001] * 100)
        sr = sortino_ratio(returns)
        assert sr == float("inf") or sr > 100


class TestCalmarRatio:
    def test_rising_nav(self, rising_nav):
        cr = calmar_ratio(rising_nav.pct_change().dropna(), rising_nav)
        assert cr > 0


class TestCostToGrossPnl:
    def test_no_costs(self):
        assert cost_to_gross_pnl(0.0, 1.0) == 0.0

    def test_cost_dominance(self):
        assert cost_to_gross_pnl(2.0, 1.0) == 2.0

    def test_zero_gross_pnl(self):
        result = cost_to_gross_pnl(1.0, 0.0)
        assert result == float("inf")


class TestAnnualizedVolatility:
    def test_zero_vol(self, flat_nav):
        returns = flat_nav.pct_change().dropna()
        assert annualized_volatility(returns) == pytest.approx(0.0)