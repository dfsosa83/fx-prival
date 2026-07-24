"""
Convert desk Bloomberg Excel file to the standardised macro insights CSV format.

Input:  ml-signal-service/data/raw/Macro_data.xlsx (desk Bloomberg export)
Output: ml-signal-service/data/raw/macro/EURUSD_H1_macro_insights.csv
        ml-signal-service/data/raw/macro/EURUSD_H1_release_calendar.csv

The input Excel has two sheets:
  - Definitions: ticker metadata
  - Data: Bloomberg historical export with 14 tickers in columns, daily freq
"""

import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path("ml-signal-service")
RAW = ROOT / "data" / "raw"
MACRO_DIR = RAW / "macro"
MACRO_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Load raw Bloomberg data ────────────────────────────────────────────
src = RAW / "Macro_data.xlsx"
df = pd.read_excel(src, sheet_name="Data", header=None)

# Row layout in Bloomberg export:
#   Row 0: empty (NaN) — Excel row padding
#   Row 1: ticker names (EURR002W Index, ECCPEMUY Index, ...)
#   Row 2: field names (Last Price, ...)
#   Row 3: field codes (PX_LAST, ...)
#   Row 4+: actual data (Dates, values...)

# Extract headers and data
tickers = df.iloc[1, 1:].values  # ticker names (skip col 0 = Dates)
data_cols = df.columns[1:]       # column indices for data (skip col 0)

# Build a clean dataframe
# Column 0 = Dates, columns 1-28 = Bloomberg data
dates = df.iloc[4:, 0].values
values = df.iloc[4:, 1:].values

# Convert to float where possible
values_float = pd.DataFrame(values, columns=tickers).apply(pd.to_numeric, errors="coerce")

# Build the output dataframe
out = pd.DataFrame()
date_series = pd.to_datetime(pd.Series(dates))
out["date"] = date_series.dt.strftime("%Y-%m-%d")

# Column mapping: Bloomberg ticker → spec column name
column_map = {
    "EURR002W Index":     "ecb_refi_rate",
    "FDTR Index":         "fed_funds_target",
    "EUR3M BGN Curncy":   "eur_3m_euribor",
    "EESWE1 BGN Curncy":  "eur_1y_ois",
    "USOSFR1 BGN Curncy": "usd_1y_ois",
    "USOSFRC BGN Curncy": "usd_3m_ois",
    "CO1 Comdty":         "brent_price",
    "ECCPEMUY Index":     "eur_cpi_yoy",
    "CPI YOY  Index":     "usd_cpi_yoy",
    "GDP CQOQ Index":     "usd_gdp_qoq",
    "UMRTEMU Index":      "eur_unemployment",
    "USURTOT Index":      "usd_unemployment",
    "NFP TCH Index":      "nfp_change",
    "PCE DEFY Index":     "usd_pce_yoy",
}

# Map columns in the specified order (see spec Section 2.3)
spec_order = [
    "ecb_refi_rate", "fed_funds_target", "eur_3m_euribor", "eur_1y_ois",
    "usd_1y_ois", "usd_3m_ois", "brent_price",
    "eur_cpi_yoy", "usd_cpi_yoy", "usd_gdp_qoq",
    "eur_unemployment", "usd_unemployment", "nfp_change", "usd_pce_yoy",
]

for bloomberg_name, spec_name in column_map.items():
    # Handle Bloomberg name with possible extra spaces
    matches = [c for c in values_float.columns if bloomberg_name.strip() in str(c).strip()]
    if matches:
        out[spec_name] = values_float[matches[0]].values
    else:
        print(f"WARNING: ticker '{bloomberg_name}' not found in data columns: {list(values_float.columns)[:5]}...")

# ── 2. Forward-fill stale macro release columns ───────────────────────────
# Market-traded rates (change daily) — leave as-is
# Economic releases (change monthly/quarterly) — forward-fill
release_cols = [
    "ecb_refi_rate", "fed_funds_target",
    "eur_cpi_yoy", "usd_cpi_yoy", "usd_gdp_qoq",
    "eur_unemployment", "usd_unemployment", "nfp_change", "usd_pce_yoy",
]

for col in release_cols:
    if col in out.columns:
        out[col] = out[col].ffill()

# ── 3. Detect release dates → event_flag ──────────────────────────────────
out["event_flag"] = 0
for col in release_cols:
    if col in out.columns:
        changed = out[col] != out[col].shift(1)
        out["event_flag"] = out["event_flag"] | changed.astype(int)

# ── 4. Build release calendar ─────────────────────────────────────────────
calendar_rows = []
for col in release_cols:
    if col not in out.columns:
        continue
    # Find rows where value changed
    changed = out[col] != out[col].shift(1)
    change_dates = out.loc[changed, "date"].values
    change_values_new = out.loc[changed, col].values
    change_values_old = out.loc[changed, col].shift(1).values

    for date, new_v, old_v in zip(change_dates, change_values_new, change_values_old):
        if pd.isna(old_v):
            continue  # skip first row (no prior value)
        if col.startswith("eur_"):
            currency = "EUR"
        else:
            currency = "USD"

        indicator_name = col.replace("_", " ").upper()

        if "gdp_qoq" in col:
            freq = "quarterly"
        elif "refi_rate" in col or "funds_target" in col:
            freq = "decision"
        else:
            freq = "monthly"

        if new_v > old_v:
            direction = "increase"
        elif new_v < old_v:
            direction = "decrease"
        else:
            direction = "unchanged"

        calendar_rows.append({
            "date": date,
            "indicator": indicator_name,
            "currency": currency,
            "frequency": freq,
            "previous_value": round(float(old_v), 2),
            "new_value": round(float(new_v), 2),
            "change_direction": direction,
        })

calendar = pd.DataFrame(calendar_rows)
calendar = calendar.sort_values(["date", "indicator"]).reset_index(drop=True)

# ── 5. Validate ────────────────────────────────────────────────────────────
print(f"Insights rows:     {len(out):,}")
print(f"Insights columns:  {list(out.columns)}")
print(f"Date range:        {out['date'].min()} to {out['date'].max()}")
print(f"Calendar events:   {len(calendar):,}")
print(f"event_flag = 1:    {out['event_flag'].sum():,} rows")

# Market-rate columns must change frequently
for col in ["eur_3m_euribor", "eur_1y_ois", "usd_1y_ois", "brent_price"]:
    if col in out.columns:
        changes = (out[col] != out[col].shift(1)).sum()
        pct = changes / len(out) * 100
        print(f"  {col}: {changes} changes ({pct:.1f}% of days)")

# ── 6. Save ────────────────────────────────────────────────────────────────
insights_path = MACRO_DIR / "EURUSD_H1_macro_insights.csv"
calendar_path = MACRO_DIR / "EURUSD_H1_release_calendar.csv"

out.to_csv(insights_path, index=False)
calendar.to_csv(calendar_path, index=False)

print(f"\nSaved: {insights_path.resolve()}")
print(f"Saved: {calendar_path.resolve()}")