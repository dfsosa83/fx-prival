"""
Instrument master for the quantitative fund platform.

Provides InstrumentMaster — the single source of truth for every instrument
in the research universe. Loads from config/universe.yaml and/or
data/reference/instrument_master.csv and validates all instrument records.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml


class InstrumentMaster:
    """
    Central registry of all instruments in the research universe.

    Loads instrument definitions from YAML configuration and/or CSV files,
    validates required fields, and provides lookup methods by ticker, asset
    class, currency, and other attributes.

    Attributes:
        instruments: Dict mapping ticker to instrument record dict.
    """

    REQUIRED_FIELDS_FX = [
        "ticker", "asset_class", "base_currency", "quote_currency",
        "pip_value", "lot_size", "tick_size", "yahoo_ticker", "is_active",
    ]

    REQUIRED_FIELDS_OTHER = [
        "ticker", "asset_class", "currency", "tick_size", "yahoo_ticker", "is_active",
    ]

    def __init__(self):
        self.instruments: Dict[str, Dict[str, Any]] = {}
        self._active_tickers: List[str] = []

    def load_from_yaml(self, path: str) -> "InstrumentMaster":
        """
        Load instrument universe from a YAML configuration file.

        Expected structure:
            universe:
              fx:
                - ticker: EURUSD
                  base_currency: EUR
                  ...

        Args:
            path: Path to config/universe.yaml or equivalent.

        Returns:
            self (for method chaining).

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If an instrument is missing required fields.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Universe config not found: {path}")

        with open(path, "r") as f:
            config = yaml.safe_load(f)

        universe = config.get("universe", {})
        for asset_class, instruments_list in universe.items():
            for record in instruments_list:
                ticker = record["ticker"]
                record["asset_class"] = asset_class
                self._validate_record(ticker, record, asset_class)
                self.instruments[ticker] = record

        self._refresh_active()
        return self

    def load_from_csv(self, path: str) -> "InstrumentMaster":
        """
        Load instrument master from CSV file.

        Expected columns: ticker, asset_class, base_currency, quote_currency,
        pip_value, lot_size, tick_size, session_hours, holiday_calendar,
        data_source, yahoo_ticker, is_active.

        Args:
            path: Path to data/reference/instrument_master.csv.

        Returns:
            self (for method chaining).
        """
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            record = row.to_dict()
            # Convert boolean fields
            if "is_active" in record:
                record["is_active"] = bool(record["is_active"])
            ticker = record["ticker"]
            asset_class = record.get("asset_class", "unknown")
            self._validate_record(ticker, record, asset_class)
            self.instruments[ticker] = record

        self._refresh_active()
        return self

    def _validate_record(
        self, ticker: str, record: Dict[str, Any], asset_class: str
    ) -> None:
        """Validate that a record has all required fields."""
        if asset_class == "fx":
            required = self.REQUIRED_FIELDS_FX
        else:
            required = self.REQUIRED_FIELDS_OTHER

        missing = [f for f in required if f not in record or record[f] is None]
        if missing:
            raise ValueError(
                f"Instrument '{ticker}' ({asset_class}) missing required fields: {missing}"
            )

    def _refresh_active(self) -> None:
        """Rebuild the active ticker list."""
        self._active_tickers = [
            t for t, r in self.instruments.items() if r.get("is_active", False)
        ]

    # ---- Lookup Methods ----

    def get(self, ticker: str) -> Dict[str, Any]:
        """
        Get the full instrument record for a ticker.

        Args:
            ticker: Standardized ticker symbol.

        Returns:
            Instrument record dict.

        Raises:
            KeyError: If ticker is not in the master.
        """
        if ticker not in self.instruments:
            raise KeyError(f"Instrument '{ticker}' not found in master")
        return self.instruments[ticker]

    def is_active(self, ticker: str) -> bool:
        """Check if an instrument is active in the current universe."""
        rec = self.get(ticker)
        return bool(rec.get("is_active", False))

    def tickers(self, active_only: bool = True) -> List[str]:
        """
        Return a list of ticker symbols.

        Args:
            active_only: If True, return only active instruments.

        Returns:
            Sorted list of tickers.
        """
        if active_only:
            return sorted(self._active_tickers)
        return sorted(self.instruments.keys())

    def by_asset_class(
        self, asset_class: str, active_only: bool = True
    ) -> List[str]:
        """
        Return tickers belonging to a specific asset class.

        Args:
            asset_class: One of 'fx', 'equity_index', 'govt_bond', 'commodity'.
            active_only: If True, return only active instruments.

        Returns:
            Sorted list of tickers.
        """
        tickers = self.tickers(active_only=active_only)
        return [
            t for t in tickers
            if self.instruments[t].get("asset_class") == asset_class
        ]

    def by_base_currency(
        self, currency: str, active_only: bool = True
    ) -> List[str]:
        """
        Return tickers with a specific base currency.

        Args:
            currency: ISO 4217 currency code.
            active_only: If True, return only active instruments.

        Returns:
            Sorted list of tickers.
        """
        tickers = self.tickers(active_only=active_only)
        return [
            t for t in tickers
            if self.instruments[t].get("base_currency") == currency
        ]

    def by_quote_currency(
        self, currency: str, active_only: bool = True
    ) -> List[str]:
        """
        Return tickers with a specific quote currency.

        Args:
            currency: ISO 4217 currency code.
            active_only: If True, return only active instruments.

        Returns:
            Sorted list of tickers.
        """
        tickers = self.tickers(active_only=active_only)
        return [
            t for t in tickers
            if self.instruments[t].get("quote_currency") == currency
        ]

    def yahoo_ticker(self, ticker: str) -> str:
        """Get the Yahoo Finance ticker for an instrument."""
        rec = self.get(ticker)
        return rec.get("yahoo_ticker", ticker)

    def asset_class(self, ticker: str) -> str:
        """Get the asset class of an instrument."""
        rec = self.get(ticker)
        return rec.get("asset_class", "unknown")

    def pip_value(self, ticker: str) -> float:
        """Get the pip value for an FX instrument."""
        rec = self.get(ticker)
        return float(rec.get("pip_value", 0.0))

    def to_dataframe(self, active_only: bool = True) -> pd.DataFrame:
        """
        Export instrument master to a pandas DataFrame.

        Args:
            active_only: If True, include only active instruments.

        Returns:
            DataFrame with ticker as index.
        """
        tickers = self.tickers(active_only=active_only)
        records = [self.instruments[t] for t in tickers]
        df = pd.DataFrame(records)
        df.set_index("ticker", inplace=True)
        return df

    def __len__(self) -> int:
        return len(self.instruments)

    def __contains__(self, ticker: str) -> bool:
        return ticker in self.instruments

    def __repr__(self) -> str:
        n_total = len(self.instruments)
        n_active = len(self._active_tickers)
        return (
            f"InstrumentMaster(total={n_total}, active={n_active}, "
            f"classes={self._class_summary()})"
        )

    def _class_summary(self) -> Dict[str, int]:
        """Count instruments per asset class."""
        counts: Dict[str, int] = {}
        for rec in self.instruments.values():
            ac = rec.get("asset_class", "unknown")
            counts[ac] = counts.get(ac, 0) + 1
        return counts