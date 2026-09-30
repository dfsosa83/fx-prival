"""Stage 1B v1.2 — determine valid-observation counts and first eligible rebalance."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.fx import convert_cross_eurjpy, convert_local_to_usd  # noqa: E402
from core.instruments import InstrumentMaster  # noqa: E402
from data.pipelines.dataset import load_and_validate  # noqa: E402
from portfolio.accounting_v2 import _rebalance_dates  # noqa: E402

DATA_START = "2020-02-28"
DATA_END = "2026-09-23"
MIN_HIST = 60
LOOKBACK = 200

master = InstrumentMaster()
master.load_from_yaml("quant-personal-fund/config/universe.yaml")
prices, meta = load_and_validate("quant-personal-fund/data/raw/yahoo/daily", master)
local = np.log(prices / prices.shift(1))
fx_prices = pd.DataFrame({t: prices[t] for t in ["EURUSD", "USDJPY"] if t in prices.columns})
for t, ccy in [("SX5E", "EUR"), ("NKY", "JPY")]:
    if t in local.columns:
        local[t] = convert_local_to_usd(local[t], fx_prices, ccy, max_ffill_days=5)
if "EURJPY" in local.columns and "USDJPY" in fx_prices.columns:
    local["EURJPY"] = convert_cross_eurjpy(local["EURJPY"], fx_prices["USDJPY"], max_ffill_days=5)

# Use RAW returns (pre-fillna) to count VALID observations per instrument
rets_raw = local.loc[DATA_START:DATA_END]
tickers = sorted(master.tickers(active_only=True))
tickers = [t for t in tickers if t in rets_raw.columns]

# Valid-observation count per instrument from data_start
print("=== Valid (non-NaN) observations per instrument, 2020-02-28 onward ===")
for t in tickers:
    n = int(rets_raw[t].notna().sum())
    first_valid = rets_raw[t].dropna().index.min().date()
    print(f"  {t}: {n} valid, first valid {first_valid}")

# First rebalance date where ALL instruments have >=60 valid observations
# in their 200-day lookback (from data_start)
reb_dates = _rebalance_dates(rets_raw.index, "M")
print("\n=== First eligible rebalance (all instruments >=60 valid obs in lookback) ===")
first_eligible = None
for dt in reb_dates:
    # lookback from data_start to dt (max 200 rows)
    window = rets_raw.loc[DATA_START:dt]
    if len(window) > LOOKBACK:
        window = window.iloc[-LOOKBACK:]
    counts = window.notna().sum()
    if (counts >= MIN_HIST).all():
        first_eligible = dt
        break
print(f"First eligible rebalance: {first_eligible}")
if first_eligible is not None:
    min_count = rets_raw.loc[DATA_START:first_eligible].notna().min().min()
    print(f"Minimum valid obs across instruments at that date: {min_count}")
    # Performance window
    print(f"Performance window: {first_eligible.date()} to {DATA_END}")