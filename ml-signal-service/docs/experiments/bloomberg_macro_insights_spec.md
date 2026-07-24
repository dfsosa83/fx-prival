# Bloomberg Macro Insights — Technical Specification for Model Training

*Document version: 1.0 · Date: 2026-07-15 · Owner: ML Engineering*

---

## 1. Purpose

This specification defines the exact file format, column schema, and validation rules for the Bloomberg Macro Insights dataset consumed by the EURUSD H1 training pipeline (`eurusd_buy.ipynb`). The dataset enriches the feature matrix with daily macro context — interest rate differentials, commodity prices, and economic release flags — that the model cannot derive from OHLCV price data alone.

---

## 2. File Specification

### 2.1 File name

```
EURUSD_H1_macro_insights.csv
```

Location: `ml-signal-service/data/raw/macro/EURUSD_H1_macro_insights.csv`

A second file containing the release calendar (produced automatically from the same source) is also required:

```
EURUSD_H1_release_calendar.csv
```

Location: `ml-signal-service/data/raw/macro/EURUSD_H1_release_calendar.csv`

### 2.2 Format

- **Encoding:** UTF-8 without BOM
- **Delimiter:** comma (`,`)
- **Line endings:** LF (`\n`)
- **Header row:** required (first row)
- **Date format:** `YYYY-MM-DD` (date only, no timestamp)
- **Numeric format:** decimal point (`.`), no thousands separator
- **Missing values:** leave cell empty (no `N/A`, `NULL`, or `-999`)
- **Row order:** chronological, oldest first

### 2.3 Columns — Insights Dataset

| # | Column name | Type | Unit | Description |
|---|---|---|---|---|
| 1 | `date` | date (YYYY-MM-DD) | — | Calendar date. One row per business day. Must be contiguous — gaps must be filled with forward-fill from last known value. |
| 2 | `ecb_refi_rate` | float | % | ECB Main Refinancing Operation rate. Source: `EURR002W Index`. Forward-filled between ECB decisions. |
| 3 | `fed_funds_target` | float | % | Federal Funds target rate (upper bound). Source: `FDTR Index`. Forward-filled between FOMC decisions. |
| 4 | `eur_3m_euribor` | float | % | EUR 3-month EURIBOR fixing. Source: `EUR3M BGN Curncy` (PX_LAST). Market rate — changes daily. |
| 5 | `eur_1y_ois` | float | % | EUR 1-year OIS swap rate. Source: `EESWE1 BGN Curncy` (PX_LAST). Market rate — changes daily. |
| 6 | `usd_1y_ois` | float | % | USD 1-year OIS forward rate. Source: `USOSFR1 BGN Curncy` (PX_LAST). Market rate — changes daily. |
| 7 | `usd_3m_ois` | float | % | USD 3-month OIS forward rate. Source: `USOSFRC BGN Curncy` (PX_LAST). Market rate — changes daily. |
| 8 | `brent_price` | float | USD/barrel | Brent crude oil front-month price. Source: `CO1 Comdty` (PX_LAST). Market price — changes daily. |
| 9 | `eur_cpi_yoy` | float | % | Euro Area MUICP All Items YoY. Source: `ECCPEMUY Index`. Forward-filled between monthly releases. |
| 10 | `usd_cpi_yoy` | float | % | US CPI Urban Consumers YoY NSA. Source: `CPI YOY Index`. Forward-filled between monthly releases. |
| 11 | `usd_gdp_qoq` | float | % | US GDP Chained Dollars QoQ SAAR. Source: `GDP CQOQ Index`. Forward-filled between quarterly releases. |
| 12 | `eur_unemployment` | float | % | Eurostat Unemployment Rate Eurozone. Source: `UMRTEMU Index`. Forward-filled between monthly releases. |
| 13 | `usd_unemployment` | float | % | U-3 US Unemployment Rate. Source: `USURTOT Index`. Forward-filled between monthly releases. |
| 14 | `nfp_change` | float | thousands | US Nonfarm Payrolls monthly change. Source: `NFP TCH Index`. Forward-filled between monthly releases. |
| 15 | `usd_pce_yoy` | float | % | US PCE Deflator YoY. Source: `PCE DEFY Index`. Forward-filled between monthly releases. |
| 16 | `event_flag` | int | — | Binary flag. `1` if ANY column 9–15 changed value on this date (a new economic release occurred). `0` otherwise. Computed column — see Section 3.4. |

### 2.4 Columns — Release Calendar

| # | Column name | Type | Description |
|---|---|---|---|
| 1 | `date` | date (YYYY-MM-DD) | Calendar date of the release. |
| 2 | `indicator` | string | Human-readable indicator name (e.g., `US CPI YoY`, `US NFP`, `ECB Refi Rate`). |
| 3 | `currency` | string | `EUR` or `USD`. Which currency the release directly impacts. |
| 4 | `frequency` | string | `monthly`, `quarterly`, or `decision` (for central bank meetings). |
| 5 | `previous_value` | float | The value of the indicator BEFORE the release. |
| 6 | `new_value` | float | The value of the indicator AFTER the release. |
| 7 | `change_direction` | string | `increase`, `decrease`, or `unchanged`. |

### 2.5 Data types and validation rules

| Column | Expected range | Validation rule |
|---|---|---|
| `date` | 2016-01-01 to present | Must be a valid ISO date. No duplicates. No gaps longer than 5 business days (if longer, forward-fill required). |
| `ecb_refi_rate` | −0.75 to 10.0 | Non-negative in Eurozone context. Must match known ECB decision dates. |
| `fed_funds_target` | 0.0 to 10.0 | Non-negative. Must match known FOMC decision dates. |
| `eur_3m_euribor` | −1.0 to 10.0 | Must change at least once per week (trades daily). |
| `eur_1y_ois` / `usd_1y_ois` / `usd_3m_ois` | −2.0 to 10.0 | Must change at least once per week. |
| `brent_price` | 10.0 to 200.0 | Must change on >80% of business days. |
| `eur_cpi_yoy` | −5.0 to 20.0 | Changes monthly only. Max one change per 15+ business days. |
| `usd_cpi_yoy` | −5.0 to 20.0 | Changes monthly only. |
| `usd_gdp_qoq` | −20.0 to 20.0 | Changes quarterly only. Max one change per 40+ business days. |
| `eur_unemployment` | 3.0 to 25.0 | Changes monthly only. |
| `usd_unemployment` | 2.0 to 15.0 | Changes monthly only. |
| `nfp_change` | −1000 to 1000 | Changes monthly only. |
| `usd_pce_yoy` | −5.0 to 20.0 | Changes monthly only. |
| `event_flag` | 0 or 1 | Must equal 1 on exactly the rows where any of columns 9–15 changed. |

### 2.6 Naming conventions

- **File names:** `{PAIR}_{TIMEFRAME}_{dataset_type}.csv` where `dataset_type` = `macro_insights` or `release_calendar`
- **Column names:** lowercase, snake_case. Abbreviations used consistently: `eur`/`usd`, `yoy`/`qoq`/`mom`, `ois`/`euribor`
- **Versioning:** if multiple versions of the file are produced (e.g., after a Bloomberg data correction), append `_v{N}` before `.csv`: `EURUSD_H1_macro_insights_v2.csv`

---

## 3. Integration with Training Pipeline

### 3.1 When the merge happens

The notebook currently follows this sequence:

```
Cell 5:  Load raw OHLCV data (EURUSD_H1.csv)
Cell 12: compute_features(df) → 86 technical features + D1 context
Cell 20: generate labels → train/val/test split → model training
```

The macro insights file is merged **after Cell 12 and before Cell 20**:

```
Cell 5:  Load raw OHLCV data
Cell 12: compute_features(df) → df_features
Cell 12b: [NEW] Load macro_insights.csv → merge on date → df_features
Cell 20: generate labels → train/val/test split → model training
```

### 3.2 Merge logic

The macro file has **daily** granularity (one row per calendar date). The H1 feature matrix has **hourly** granularity (one row per H1 bar). The merge works as follows:

1. Extract calendar date from each H1 bar's `datetime`: `df_features["_date"] = df_features["datetime"].dt.date`
2. Left-join the macro file on `_date` (H1 bars match to their calendar date's macro row)
3. Drop the helper column `_date`
4. All daily-frequency columns from the macro file now appear on every H1 bar for that day

This is identical to how existing D1 context features (`d1_trend`, `d1_rsi`) are merged — the macro values are carried forward across all 24 H1 bars within the same calendar day.

### 3.3 Late-arriving data handling

If the macro file's latest date is behind the H1 data's latest date (e.g., today's EURIBOR hasn't fixed yet), the merge will produce NaN for those future H1 rows. The notebook will:
- Print a warning showing the gap: `Macro data ends at {last_macro_date}, H1 data has {N} bars beyond`
- Drop the trailing NaN rows (they can't be used for training)

### 3.4 How `event_flag` is derived

The `event_flag` column is NOT populated by the desk team. It is computed automatically by the notebook at merge time:

```python
# Detect release dates by comparing each macro column to its prior row
for col in ["eur_cpi_yoy", "usd_cpi_yoy", "usd_gdp_qoq", ...]:
    changed = df_macro[col] != df_macro[col].shift(1)
    df_macro["event_flag"] = df_macro.get("event_flag", 0) | changed.astype(int)
```

This means the desk team does not need to populate `event_flag` — they only need to forward-fill the raw Bloomberg values. The notebook derives the calendar automatically.

### 3.5 Feature selection treatment

Macro columns are treated identically to the 86 technical features during feature selection. They enter the noise-injection voting pipeline alongside all other features. If the feature selector drops them, the model was not helped by macro data for this training cycle. This ensures macro features are never added on assumption — they must earn their place.

---

## 4. Release Calendar Usage

The `EURUSD_H1_release_calendar.csv` file is **not consumed by the model**. It is consumed by the **agent layer** (Perplexity/GPT) to determine whether a given signal occurred near a high-impact economic release, and to provide the agent with the context it needs to evaluate that signal.

The file can be derived automatically from the insights dataset (see Section 3.4) and saved alongside it.

---

## 5. Validation Checklist (for pipeline ingestion)

Before training begins, the notebook will validate the macro file against the following rules. Any failure stops the pipeline with an error message.

| # | Check | Error message |
|---|---|---|
| 1 | File exists at expected path | `Macro insights file not found: {path}` |
| 2 | All required columns present | `Missing columns: {list}` |
| 3 | `date` column has no duplicates | `Duplicate dates found: {list}` |
| 4 | `date` column is sorted ascending | `Dates not in chronological order` |
| 5 | `brent_price` changes on >50% of rows | `Brent appears stale — check data` |
| 6 | `eur_3m_euribor` changes at least weekly | `EURIBOR appears stale — check data` |
| 7 | All rate columns within expected ranges | `{column} has {N} values outside range [{min}, {max}]` |
| 8 | Date range covers training data window | `Macro data starts at {start}, training starts at {train_start} — gap of {N} days` |
| 9 | No negative values in unemployment columns | `{column} has {N} negative values` |

---

## 6. Revision History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-07-15 | ML Engineering | Initial specification |