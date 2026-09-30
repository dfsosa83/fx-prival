"""Unit tests for core.calendar module."""
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from core.calendar import TradingCalendar


@pytest.fixture
def holidays_csv():
    """Create a temporary holidays CSV."""
    data = pd.DataFrame({
        "date": [
            "2026-01-01",
            "2026-01-19",
            "2026-12-25",
            "2026-12-25",
        ],
        "calendar": [
            "FX_global",
            "NYSE",
            "FX_global",
            "NYSE",
        ],
        "description": [
            "New Year's Day",
            "MLK Day",
            "Christmas",
            "Christmas",
        ],
    })
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False
    ) as f:
        data.to_csv(f, index=False)
        f.flush()
        path = f.name
    yield path
    Path(path).unlink()


@pytest.fixture
def calendar(holidays_csv):
    """Return a TradingCalendar loaded with test holidays."""
    return TradingCalendar(holidays_path=holidays_csv)


class TestTradingCalendar:
    """Tests for TradingCalendar."""

    def test_load_holidays(self, calendar):
        """Holidays are loaded correctly."""
        fx_holidays = calendar.get_holidays("FX_global")
        assert date(2026, 1, 1) in fx_holidays
        assert date(2026, 12, 25) in fx_holidays

        nyse_holidays = calendar.get_holidays("NYSE")
        assert date(2026, 1, 19) in nyse_holidays

    def test_is_weekend(self, calendar):
        """Correctly identifies weekend days."""
        sat = date(2026, 9, 19)  # Saturday
        sun = date(2026, 9, 20)  # Sunday
        mon = date(2026, 9, 21)  # Monday

        assert calendar.is_weekend(sat) is True
        assert calendar.is_weekend(sun) is True
        assert calendar.is_weekend(mon) is False

    def test_is_holiday(self, calendar):
        """Correctly identifies holidays."""
        new_years = date(2026, 1, 1)
        regular_day = date(2026, 3, 15)

        assert calendar.is_holiday(new_years, "FX_global") is True
        assert calendar.is_holiday(regular_day, "FX_global") is False

    def test_is_trading_day(self, calendar):
        """Weekdays that are not holidays are trading days."""
        # Monday 2026-09-21: weekday, no holiday → trading day
        trading = date(2026, 9, 21)  # Monday
        assert calendar.is_trading_day(trading, "FX_global") is True

        # Saturday: weekend → not a trading day
        weekend = date(2026, 9, 19)
        assert calendar.is_trading_day(weekend, "FX_global") is False

        # New Year's Day 2026-01-01 is a Thursday → holiday
        holiday = date(2026, 1, 1)
        assert calendar.is_trading_day(holiday, "FX_global") is False

    def test_trading_days(self, calendar):
        """Generates correct list of trading days."""
        days = calendar.trading_days(
            date(2026, 9, 21),  # Monday
            date(2026, 9, 25),  # Friday
            "FX_global",
        )
        # Mon-Fri of that week, all trading days (no holidays)
        assert len(days) == 5
        assert days[0] == date(2026, 9, 21)
        assert days[4] == date(2026, 9, 25)

    def test_trading_days_excludes_weekends(self, calendar):
        """Trading day range excludes weekends."""
        days = calendar.trading_days(
            date(2026, 9, 19),  # Saturday
            date(2026, 9, 21),  # Monday
            "FX_global",
        )
        assert days == [date(2026, 9, 21)]  # Only Monday

    def test_previous_trading_day(self, calendar):
        """Finds the Nth previous trading day."""
        # Monday Sep 21: previous trading day is Friday Sep 18
        mon = date(2026, 9, 21)
        prev = calendar.previous_trading_day(mon, "FX_global", offset=1)
        assert prev == date(2026, 9, 18)
        assert prev.weekday() == 4  # Friday

    def test_previous_trading_day_across_weekend(self, calendar):
        """Previous trading day skips weekends."""
        # Tuesday: offset=2 should give us the previous Friday
        tue = date(2026, 9, 22)
        prev2 = calendar.previous_trading_day(tue, "FX_global", offset=2)
        assert prev2 == date(2026, 9, 18)  # Friday

    def test_empty_calendar(self):
        """Calendar with no holidays still works for weekends."""
        cal = TradingCalendar()
        mon = date(2026, 9, 21)
        assert cal.is_trading_day(mon, "ANY") is True
        sat = date(2026, 9, 19)
        assert cal.is_trading_day(sat, "ANY") is False

    def test_unknown_calendar_returns_empty(self, calendar):
        """Unknown calendar name returns empty holiday set."""
        assert calendar.get_holidays("NONEXISTENT") == set()

    def test_custom_weekend_days(self):
        """Supports custom weekend definitions."""
        # Friday-Saturday weekend (e.g., some Middle Eastern markets)
        cal = TradingCalendar(weekend_days={4, 5})
        fri = date(2026, 9, 25)  # Friday
        sun = date(2026, 9, 27)  # Sunday
        assert cal.is_weekend(fri) is True
        assert cal.is_weekend(sun) is False