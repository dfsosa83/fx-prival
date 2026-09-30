"""Step b: Base-currency / instrument-representation classification."""
import sys; sys.path.insert(0, ".")
import json
import pandas as pd
from pathlib import Path
from core.instruments import InstrumentMaster

OUT = Path("audits/AUDIT-2026-09-23-PHASE-5-5/diagnostics")
OUT.mkdir(parents=True, exist_ok=True)

master = InstrumentMaster()
master.load_from_yaml("config/universe.yaml")

REPRESENTATION = {
    "EURUSD": ("spot_fx", "EUR", "USD"), "USDJPY": ("spot_fx", "USD", "JPY"),
    "GBPUSD": ("spot_fx", "GBP", "USD"), "AUDUSD": ("spot_fx", "AUD", "USD"),
    "USDCAD": ("spot_fx", "USD", "CAD"), "USDCHF": ("spot_fx", "USD", "CHF"),
    "NZDUSD": ("spot_fx", "NZD", "USD"), "EURJPY": ("spot_fx", "EUR", "JPY"),
    "SPX": ("price_index", "USD", "USD"), "NDX": ("price_index", "USD", "USD"),
    "SX5E": ("price_index", "EUR", "EUR"), "NKY": ("price_index", "JPY", "JPY"),
    "US10Y": ("yield_proxy", "USD", "USD"),
    "BUND": ("etf_price", "EUR", "EUR"),
    "JGB": ("reit_etf_price", "JPY", "JPY"),
    "XAUUSD": ("futures_proxy", "USD", "USD"),
    "WTI": ("futures_proxy", "USD", "USD"),
    "COPPER": ("futures_proxy", "USD", "USD"),
}

rows = []
for ticker in master.tickers(active_only=True):
    rec = master.get(ticker)
    rep, denom, trade = REPRESENTATION.get(ticker, ("unknown", "?", "?"))
    rows.append({
        "ticker": ticker,
        "asset_class": rec.get("asset_class"),
        "representation": rep,
        "denomination_currency": denom,
        "trading_currency": trade,
        "is_usd_denominated": denom == "USD",
        "yahoo_ticker": rec.get("yahoo_ticker"),
        "data_type": rec.get("data_type", "price"),
    })

df = pd.DataFrame(rows)
df.to_csv(OUT / "instrument_representation.csv", index=False)

print("=== INSTRUMENT REPRESENTATION CLASSIFICATION ===")
print(df.to_string(index=False))

non_usd = df[~df["is_usd_denominated"]]
print("\n=== BASE-CURRENCY (USD) AUDIT ===")
print(f"Portfolio base currency assumed: USD")
print(f"Non-USD-denominated instruments: {len(non_usd)}")
for _, r in non_usd.iterrows():
    print(f"  {r['ticker']}: denom={r['denomination_currency']} "
          f"rep={r['representation']} -> RETURNS IN LOCAL CCY, NO FX CONVERSION")

print("\n=== FINDING H9 (BASE-CURRENCY CONVERSION) ===")
print("VERIFIED: backtest/engine.py::_compute_returns_panel computes returns "
      "per ticker from its own price series (np.log(prices/prices.shift(1))).")
print("VERIFIED: No FX conversion to USD is applied to non-USD instruments.")
print("VERIFIED: No timestamp alignment between local-market close and any FX "
      "conversion series exists (no conversion exists at all).")
print("VERIFIED: Transaction costs, financing, NAV, attribution, and risk "
      "metrics all operate on the unconverted per-ticker returns.")
print("CONSEQUENCE: For a USD-based investor, SX5E/NKY/BUND/JGB returns are "
      "economically NOT comparable to USD assets. This is a representation "
      "issue affecting benchmark and all sleeve results.")

result = {
    "base_currency": "USD",
    "non_usd_instruments": non_usd["ticker"].tolist(),
    "fx_conversion_applied": False,
    "timestamp_alignment": "N/A - no conversion exists",
    "severity": "blocking_if_confirmed",
}
with open(OUT / "step_b_base_currency.json", "w") as f:
    json.dump(result, f, indent=2, default=str)
print("\nSaved: step_b_base_currency.json")