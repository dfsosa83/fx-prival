"""
Multi-asset cost model for backtesting and portfolio evaluation.

Provides a single source of truth for trading costs across all instrument
classes. Loads from config/cost_model.yaml and provides per-instrument,
per-direction cost estimates for use in backtests, signal evaluation,
and net-of-cost performance reporting.

All costs are expressed as a fraction of notional or in absolute terms
depending on the instrument class, and are always positive (costs reduce
returns).
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class CostModel:
    """
    Multi-asset cost model with per-instrument cost estimates.

    Loads from a YAML configuration file and provides methods for computing
    round-trip costs, per-direction costs, and cost summaries for any
    instrument in the universe.

    Attributes:
        costs: Dict mapping instrument ticker to cost record.
        defaults: Dict of default cost assumptions.
    """

    def __init__(self):
        self.costs: Dict[str, Dict[str, Any]] = {}
        self.defaults: Dict[str, Any] = {}

    def load_from_yaml(self, path: str) -> "CostModel":
        """
        Load cost model from YAML configuration file.

        Expected structure:
            defaults:
              slippage_pips_fx: 0.5
              ...
            instruments:
              EURUSD:
                spread_pips: 1.8
                ...

        Args:
            path: Path to config/cost_model.yaml.

        Returns:
            self (for method chaining).

        Raises:
            FileNotFoundError: If the config file does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Cost model config not found: {path}")

        with open(path, "r") as f:
            config = yaml.safe_load(f)

        self.defaults = config.get("defaults", {})
        self.costs = config.get("instruments", {})
        return self

    def get(self, ticker: str) -> Dict[str, Any]:
        """
        Get the cost record for an instrument.

        Args:
            ticker: Instrument ticker.

        Returns:
            Cost record dict.

        Raises:
            KeyError: If ticker is not in the cost model.
        """
        if ticker not in self.costs:
            raise KeyError(f"Cost data not found for instrument '{ticker}'")
        return self.costs[ticker]

    def round_trip_cost_pct(
        self,
        ticker: str,
        notional: Optional[float] = None,
        pip_value: float = 0.0001,
    ) -> float:
        """
        Estimate round-trip cost as a fraction of notional.

        For FX instruments with spread_pips > 0:
            cost = (spread_pips + 2 * slippage_pips) * pip_value

        The pip_value should be provided by the InstrumentMaster for the
        specific instrument (0.0001 for most FX pairs, 0.01 for JPY crosses).

        For non-FX instruments:
            cost = 2 * commission_pct + daily_financing

        Args:
            ticker: Instrument ticker.
            notional: Notional value (required for FX instruments).
            pip_value: Value of one pip as a fraction of notional.
                       Default 0.0001. Use 0.01 for JPY crosses.

        Returns:
            Round-trip cost as a fraction (e.g., 0.001 = 0.1%).

        Raises:
            KeyError: If ticker not in cost model.
            ValueError: If notional is required but not provided.
        """
        rec = self.get(ticker)

        spread_pips = rec.get("spread_pips", 0.0)
        if spread_pips is not None and spread_pips > 0:
            if notional is None or notional <= 0:
                raise ValueError(
                    f"Notional required to convert pip costs to fraction for '{ticker}'"
                )
            slippage_pips = self.defaults.get("slippage_pips_fx", 0.5)
            total_pips = spread_pips + 2.0 * slippage_pips
            return float(total_pips * pip_value)

        commission_pct = rec.get("commission_pct", 0.0)
        financing_cost = self.daily_holding_cost_pct(ticker)
        return float(2.0 * commission_pct + financing_cost)

    def daily_holding_cost_pct(self, ticker: str) -> float:
        """
        Estimate daily holding/financing cost as a fraction of notional.

        For instruments with financing_annual_pct defined, returns the
        daily equivalent (annual_rate / 252). Always non-negative in
        Phase 2. Direction-dependent swap is deferred to Phase 4+.

        Args:
            ticker: Instrument ticker.

        Returns:
            Daily holding cost as a fraction (e.g., 0.0002 = 2 bp/day).
        """
        rec = self.get(ticker)
        annual_rate = rec.get("financing_annual_pct", 0.0)
        if annual_rate == 0.0:
            return 0.0
        return float(annual_rate / 252.0)

    def cost_per_trade(
        self,
        ticker: str,
        notional: float,
        holding_days: int = 1,
        pip_value: float = 0.0001,
    ) -> float:
        """
        Estimate total cost for a single trade in absolute terms.

        Includes spread, commission, slippage, and financing for the holding
        period.

        Args:
            ticker: Instrument ticker.
            notional: Notional value of the position.
            holding_days: Expected holding period in days.
            pip_value: Value of one pip as a fraction (for FX instruments).

        Returns:
            Total cost in the same units as notional (always positive).
        """
        cost_pct = self.round_trip_cost_pct(ticker, notional, pip_value=pip_value)
        annual_rate = self.get(ticker).get("financing_annual_pct", 0.0)
        daily_rate = annual_rate / 252.0
        financing_pct = daily_rate * holding_days
        total_pct = cost_pct + financing_pct
        return float(notional * total_pct)

    def spread_pips(self, ticker: str) -> float:
        """Get the spread in pips for an instrument."""
        rec = self.get(ticker)
        return float(rec.get("spread_pips", 0.0))

    # ── One-way transaction-cost interface (EXP-2026-04A) ──────────────────
    # TEMPORARY RESEARCH ASSUMPTION: the round-trip table is symmetric, so
    # one_way = 0.5 * round_trip. Financing is EXCLUDED from every one-way
    # cost — it is charged ONLY via daily_holding_cost_pct.
    # Documented in docs/REMEDIATION_NOTES.md.
    # The interface accepts asymmetric values without changing call sites.

    def one_way_transaction_cost(
        self,
        ticker: str,
        notional: Optional[float] = None,
        pip_value: float = 0.0001,
        direction: str = "either",
    ) -> float:
        """
        One-way (entry or exit) transaction cost as a fraction of notional.

        Excludes financing entirely. Derived as 0.5 * round_trip_cost_pct
        where the table is symmetric (temporary research assumption).
        For FX: one_way = 0.5 * (spread_pips + 2*slippage_pips) * pip_value.
        For non-FX: one_way = commission_pct.

        Args:
            ticker: Instrument ticker.
            notional: Notional (required for FX).
            pip_value: Pip value as fraction of notional (FX).
            direction: 'entry', 'exit', or 'either'. Symmetric in this
                       remediation; parameter reserved for future asymmetry.

        Returns:
            One-way cost as a fraction (e.g., 0.001 = 0.1%).
        """
        rec = self.get(ticker)
        spread_pips = rec.get("spread_pips", 0.0)
        if spread_pips is not None and spread_pips > 0:
            if notional is None or notional <= 0:
                raise ValueError(
                    f"Notional required for one-way cost on '{ticker}'"
                )
            slippage_pips = self.defaults.get("slippage_pips_fx", 0.5)
            total_pips = spread_pips + 2.0 * slippage_pips
            return float(0.5 * total_pips * pip_value)

        commission_pct = rec.get("commission_pct", 0.0)
        return float(commission_pct)

    def entry_transaction_cost(
        self,
        ticker: str,
        notional: Optional[float] = None,
        pip_value: float = 0.0001,
    ) -> float:
        """Entry one-way transaction cost (financing excluded)."""
        return self.one_way_transaction_cost(ticker, notional, pip_value, direction="entry")

    def exit_transaction_cost(
        self,
        ticker: str,
        notional: Optional[float] = None,
        pip_value: float = 0.0001,
    ) -> float:
        """Exit one-way transaction cost (financing excluded)."""
        return self.one_way_transaction_cost(ticker, notional, pip_value, direction="exit")

    def all_tickers(self) -> list:
        """Return all tickers with cost data."""
        return list(self.costs.keys())

    def __contains__(self, ticker: str) -> bool:
        return ticker in self.costs

    def __repr__(self) -> str:
        return f"CostModel(instruments={len(self.costs)})"