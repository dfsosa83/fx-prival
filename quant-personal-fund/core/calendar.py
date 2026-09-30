"""
Calendar utilities for trading days, sessions, holidays, and roll schedules.

Provides TradingCalendar for date filtering, session-hour logic, and
holiday-aware date range generation.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

import pandas as pd


class TradingCalendar:
    """
    Trading calendar with holiday awareness and session-hour logic.

    Loads holiday data from a CSV file and provides methods for filtering
    dates, generating trading-day ranges, and checking session membership.

    Attributes:
        holidays: Dict mapping calendar name to set of holiday dates.
        weekends: Set of weekend weekdays (default: Saturday=5, Sunday=6).
    """

    WEEKEND_DAYS: Set[int] = {5, 6}  # Saturday, Sunday

    def __init__(
        self,
        holidays_path: Optional[str] = None,
        weekend_days: Optional[Set[int]] = None,
    ):
        """
        Initialize the trading calendar.

        Args:
            holidays_path: Path to holidays CSV. If None, no holidays loaded.
            weekend_days: Set of weekday integers treated as weekends.
                          Defaults to {5, 6} (Saturday, Sunday).
        """
        self.weekends = weekend_days if weekend_days is not None else self.WEEKEND_DAYS
        self._holidays: Dict[str, Set[date]] = {}

        if holidays_path:
            self.load_holidays(holidays_path)

    def load_holidays(self, path: str) -> None:
        """
        Load holiday calendar from CSV.

        Expected CSV columns: date, calendar, description.
        The 'calendar' column controls which calendar name a date belongs to.

        Args:
            path: Path to holidays CSV file.
        """
        df = pd.read_csv(path, parse_dates=["date"])
        for calendar_name in df["calendar"].unique():
            cal_df = df[df["calendar"] == calendar_name]
            self._holidays[calendar_name] = set(
                cal_df["date"].dt.date.tolist()
            )

    def get_holidays(self, calendar: str) -> Set[date]:
        """
        Return the set of holiday dates for a given calendar.

        Args:
            calendar: Calendar name (e.g. 'FX_global', 'NYSE').

        Returns:
            Set of date objects. Empty set if calendar not found.
        """
        return self._holidays.get(calendar, set())

    def is_weekend(self, d: date) -> bool:
        """Check if a date falls on a weekend."""
        return d.weekday() in self.weekends

    def is_holiday(self, d: date, calendar: str) -> bool:
        """Check if a date is a holiday for the given calendar."""
        return d in self.get_holidays(calendar)

    def is_trading_day(self, d: date, calendar: str) -> bool:
        """
        Check if a date is a valid trading day.

        A trading day is a weekday that is not a holiday for the given calendar.

        Args:
            d: Date to check.
            calendar: Calendar name.

        Returns:
            True if the date is a trading day.
        """
        return not self.is_weekend(d) and not self.is_holiday(d, calendar)

    def trading_days(
        self,
        start: date,
        end: date,
        calendar: str,
    ) -> List[date]:
        """
        Generate a list of trading days within a date range.

        Args:
            start: Start date (inclusive).
            end: End date (inclusive).
            calendar: Calendar name.

        Returns:
            Sorted list of trading-day dates.
        """
        days: List[date] = []
        current = start
        while current <= end:
            if self.is_trading_day(current, calendar):
                days.append(current)
            current += timedelta(days=1)
        return days

    def previous_trading_day(self, d: date, calendar: str, offset: int = 1) -> date:
        """
        Find the Nth previous trading day.

        Args:
            d: Reference date.
            calendar: Calendar name.
            offset: How many trading days back (default 1).

        Returns:
            The Nth previous trading day.
        """
        count = 0
        current = d - timedelta(days=1)
        while count < offset:
            if self.is_trading_day(current, calendar):
                count += 1
            if count < offset:
                current -= timedelta(days=1)
        return current