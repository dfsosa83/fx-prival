"""
Data acquisition pipelines for the quant fund platform.

Downloads market data from external sources (Yahoo Finance, FRED, etc.)
and stores raw data with versioned manifests.
"""
from .download import download_yahoo_daily
from .validate import validate_ohlcv

__all__ = ["download_yahoo_daily", "validate_ohlcv"]