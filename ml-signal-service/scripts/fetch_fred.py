"""
Fetch FRED macro data (TIPS 10Y real yield + VIX) for XAUUSD fundamental features.

Series:
  DFII10  - 10-Year Treasury Inflation-Indexed Security (TIPS) Constant Maturity
  VIXCLS  - CBOE Volatility Index

Downloads via the FRED CSV endpoint (no API key needed for public data).
Saves to ml-signal-service/data/macro/ as daily CSVs:
  tips10y_daily.csv
  vix_daily.csv

These are merged into the XAUUSD training notebooks as D1 context features.
"""
import pandas as pd
from pathlib import Path
import urllib.request

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "macro"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SERIES = {
    "DFII10": "tips10y_daily.csv",   # 10Y TIPS real yield (%)
    "VIXCLS": "vix_daily.csv",       # CBOE VIX
}


def fetch_series(series_id: str, out_name: str):
    url = FRED_CSV.format(series=series_id)
    tmp = OUT_DIR / f"_{series_id}.raw.csv"
    print(f"Fetching {series_id} from {url}")
    urllib.request.urlretrieve(url, tmp)

    df = pd.read_csv(tmp)
    # FRED CSV format: date, series_name
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values, keep date + value
    df = df.dropna(subset=["value"]).sort_values("date")
    df = df.rename(columns={"value": series_id})

    out_path = OUT_DIR / out_name
    df.to_csv(out_path, index=False)
    print(f"  Saved {len(df):,} rows -> {out_path}")
    print(f"  Range: {df['date'].min()} -> {df['date'].max()}")
    print(f"  Latest: {df.iloc[-1]['date'].date()} = {df.iloc[-1][series_id]:.4f}")
    tmp.unlink()
    return df


if __name__ == "__main__":
    print(f"Saving to: {OUT_DIR}\n")
    for sid, name in SERIES.items():
        try:
            fetch_series(sid, name)
        except Exception as e:
            print(f"  FAILED {sid}: {e}\n")
    print("\nDone.")