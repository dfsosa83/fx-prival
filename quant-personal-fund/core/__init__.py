"""
Core library for the Quant Personal Fund platform.

Shared foundational modules used across all layers:
- instruments: Instrument master and universe management
- calendar: Trading calendar with holidays and session logic
- returns: Return computation (simple, log, excess, yield-to-price)
- volatility: Volatility estimation (EWMA, realized, Parkinson)
- correlation: Correlation matrix estimation (Pearson, EWMA, shrinkage)
- bootstrap: Block bootstrap confidence intervals for time series
- costs: Multi-asset cost model
- hashing: SHA256 hashing for data versioning and reproducibility
"""