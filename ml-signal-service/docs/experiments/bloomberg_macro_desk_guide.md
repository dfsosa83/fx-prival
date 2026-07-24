# Bloomberg Macro Insights — Operational Guide for Desk Personnel

*Document version: 1.0 · Date: 2026-07-15 · Owner: Desk Operations*

---

## 1. What You're Building

You are producing a daily-updated CSV file that feeds economic context into the EURUSD machine learning pipeline. The file contains 15 macro indicators pulled from Bloomberg, formatted so the training notebook can read them without manual intervention.

**One file, one process, run once per day.** Takes approximately 5 minutes on a Bloomberg terminal.

---

## 2. Bloomberg Tickers to Export

Open Bloomberg terminal. In Excel/Batch mode, pull `PX_LAST` (Last Price) for the following tickers:

### Section A — Market-Traded Rates (high priority)

| Order | Ticker | Field | Description |
|---|---|---|---|
| 1 | `EURR002W Index` | PX_LAST | ECB Main Refinancing Operation Rate |
| 2 | `FDTR Index` | PX_LAST | Federal Funds Target Rate (Upper Bound) |
| 3 | `EUR3M BGN Curncy` | PX_LAST | EUR 3-Month EURIBOR |
| 4 | `EESWE1 BGN Curncy` | PX_LAST | EUR 1-Year OIS Swap Rate |
| 5 | `USOSFR1 BGN Curncy` | PX_LAST | USD 1-Year OIS Forward Rate |
| 6 | `USOSFRC BGN Curncy` | PX_LAST | USD 3-Month OIS Forward Rate |
| 7 | `CO1 Comdty` | PX_LAST | Brent Crude Oil Front Month |

### Section B — Economic Releases (context for the machine)

| Order | Ticker | Field | Description |
|---|---|---|---|
| 8 | `ECCPEMUY Index` | PX_LAST | Euro Area CPI All Items YoY |
| 9 | `CPI YOY Index` | PX_LAST | US CPI Urban Consumers YoY NSA |
| 10 | `GDP CQOQ Index` | PX_LAST | US GDP Chained Dollars QoQ SAAR |
| 11 | `UMRTEMU Index` | PX_LAST | Eurostat Unemployment Rate Eurozone |
| 12 | `USURTOT Index` | PX_LAST | US Unemployment Rate (U-3) |
| 13 | `NFP TCH Index` | PX_LAST | US Nonfarm Payrolls Monthly Change |
| 14 | `PCE DEFY Index` | PX_LAST | US PCE Deflator YoY |

**Total: 14 tickers.** If any ticker fails to return data (e.g., discontinued, renamed), note it in the audit log and proceed with the remaining 13 — do not block the file submission.

---

## 3. Step-by-Step: Building the File on a Bloomberg Terminal

### Step 1 — Create a new Excel workbook in Bloomberg

1. In Bloomberg, type `XLTP XTRA` and press `<GO>`.
2. Select **"Create New Spreadsheet"**.
3. In the wizard:
   - Data type: **Historical**
   - Securities: enter all 14 tickers from Section 2, one per row
   - Fields: `PX_LAST` for all tickers
   - Date range: `2016-01-01` to `today`
   - Periodicity: **Daily**
   - Output: new Excel workbook

### Step 2 — Export the raw data

1. Bloomberg will populate an Excel workbook with columns: `Dates | Ticker1 | Ticker2 | ... | Ticker14`
2. Note the date range the first column covers — it should start on or before `2016-01-01`.
3. Save the workbook as `Bloomberg_Raw_Export_YYYYMMDD.xlsx` where `YYYYMMDD` is today's date.

### Step 3 — Forward-fill stale macro values

Economic releases (Section B, tickers 8–14) only change on release dates. Bloomberg reports them as actual values on release days and blank on all other days. You must **forward-fill** these blanks so every calendar date has a value.

In Excel:
1. Select the columns for tickers 8–14 (CPI, GDP, Unemployment, NFP, PCE).
2. Press `Ctrl+G` → **Special** → **Blanks** → `OK`.
3. Type `=` then press the **up arrow** key.
4. Press `Ctrl+Enter` to fill all blanks with the value from the row above.
5. Select all filled cells → `Ctrl+C` → `Ctrl+Shift+V` (Paste Values) to replace formulas with values.

### Step 4 — Rename columns

Rename the Bloomberg-generated column headers to the exact names required by the pipeline:

| Bloomberg output header | Rename to | Double-check |
|---|---|---|
| `Dates` | `date` | All lowercase |
| `EURR002W Index` | `ecb_refi_rate` | |
| `FDTR Index` | `fed_funds_target` | |
| `EUR3M BGN Curncy` | `eur_3m_euribor` | Note: `euribor` not `eurbor` |
| `EESWE1 BGN Curncy` | `eur_1y_ois` | |
| `USOSFR1 BGN Curncy` | `usd_1y_ois` | |
| `USOSFRC BGN Curncy` | `usd_3m_ois` | |
| `CO1 Comdty` | `brent_price` | |
| `ECCPEMUY Index` | `eur_cpi_yoy` | |
| `CPI YOY Index` | `usd_cpi_yoy` | |
| `GDP CQOQ Index` | `usd_gdp_qoq` | |
| `UMRTEMU Index` | `eur_unemployment` | |
| `USURTOT Index` | `usd_unemployment` | |
| `NFP TCH Index` | `nfp_change` | |
| `PCE DEFY Index` | `usd_pce_yoy` | |

### Step 5 — Format dates

1. Select the `date` column.
2. Right-click → **Format Cells** → **Custom** → type `yyyy-mm-dd`.
3. Verify all dates are in `YYYY-MM-DD` format. No timestamps.

### Step 6 — Verify the file

Run these checks before submitting:

| Check | How to verify | Pass if |
|---|---|---|
| Row count | Look at last row number | At least 2,000 rows (covers 2016–present at daily frequency) |
| Date range | First and last value in `date` column | First ≤ 2016-01-04, last = today or yesterday |
| No gaps | Scroll through `date` column quickly | No blank rows in the middle |
| Forward-fill worked | Check `usd_cpi_yoy` for a known release month (e.g., July 2025) | Every row has a value, not just release day |
| Column order | Compare to the table in Step 4 | Columns appear in the exact order listed, left to right |
| No formula cells | Press `Ctrl+~` to toggle formula view | All cells show values, not formulas |

### Step 7 — Export to CSV

1. File → **Save As** → choose location `ml-signal-service/data/raw/macro/`
2. File name: `EURUSD_H1_macro_insights.csv`
3. File type: **CSV UTF-8 (Comma delimited) (*.csv)**
4. If prompted about features lost, click **Yes** (CSV doesn't support multiple sheets or formatting — that's fine)

### Step 8 — Run the validation script

A Python validation script exists at `ml-signal-service/steps/validate_macro.py` (to be built — currently the checks in Section 5 of the technical spec serve as the manual checklist). Run it:

```bash
python ml-signal-service/steps/validate_macro.py
```

If it prints `ALL CHECKS PASSED`, the file is ready. If it prints any errors, fix the issue and re-export.

---

## 4. Production Workflow — Daily Process

### Daily submit (1–5 minutes)

Every business day by 16:00 UTC:

1. Open existing `EURUSD_H1_macro_insights.csv` from `data/raw/macro/`
2. In Bloomberg: pull the same 14 tickers but **only for today's date** (or last available trading day if today is a holiday)
3. Append today's row to the CSV (or use the Bloomberg "Append to File" feature)
4. Re-run the forward-fill on the newly added row (the last row is always a release date for some column — the forward-fill carries it forward if needed)
5. Run validation script
6. Commit the updated file to the repository

### Weekly full refresh (Fridays)

On Friday after market close:

1. Perform the full export (Step 3–7 above) — entire date range from 2016 to present
2. This catches any Bloomberg data corrections from the past week
3. Save as `EURUSD_H1_macro_insights_v{N}.csv` where N increments
4. The ML team replaces the production file with the refreshed version before the next training cycle

### Holiday handling

If today is a non-trading day (weekend or holiday):

1. No submission required
2. On the next business day, the file should have a gap of 1–3 rows — that's expected
3. The ML pipeline forward-fills gaps of up to 5 business days automatically

---

## 5. Audit Trail

Every submission must be logged. Create a file at `data/raw/macro/audit_log.csv` with these columns:

| date_submitted | submitted_by | file_name | row_count | first_date | last_date | notes |
|---|---|---|---|---|---|---|
| 2026-07-15 | D. Sosa | EURUSD_H1_macro_insights.csv | 2610 | 2016-01-04 | 2026-07-14 | Full refresh after ECB decision week |
| 2026-07-16 | D. Sosa | EURUSD_H1_macro_insights.csv | 2611 | 2016-01-04 | 2026-07-15 | Daily append |

Add one row after every submission (daily append or full refresh).

**What to include in `notes`:**
- "Daily append" for routine additions
- "Full refresh — Bloomberg data corrections" for Friday refreshes
- Any ticker that failed, e.g., "ECCPEMUY Index returned no data — skipped, used prior value"
- Any market holiday or unusual event, e.g., "US Independence Day — no US rates published"

---

## 6. Troubleshooting

| Problem | Likely cause | Solution |
|---|---|---|
| Bloomberg returns `#N/A` for all 14 tickers | Terminal not logged in or data license expired | Log in, press `<GO>` on any ticker to verify connection |
| `EUR3M BGN Curncy` returns blank rows | EURIBOR not published on weekends/holidays | Forward-fill from last business day — expected behavior |
| Date column shows timestamps (e.g., `2026-07-15 00:00:00`) | Excel auto-formatted | Re-format as `yyyy-mm-dd` (Custom format), re-export |
| CSV opens with garbled characters | Wrong encoding | Re-export as CSV UTF-8, not plain CSV |
| Row count dropped after save | Excel truncated at row 1,048,576 (old .xls limit) | Always save as .xlsx during editing, then export to .csv as final step |
| Validation script fails on `brent_price stale` | Oil market holiday (e.g., Good Friday) | Expected on ~5 days/year. Note in audit log. Fails only if >50% of recent rows are stale. |

---

## 7. Contact

| Role | Who | When to contact |
|---|---|---|
| File format questions | ML Engineering | Column names, data types, validation rules |
| Bloomberg terminal access | Desk IT | Login issues, data license expiration |
| Pipeline ingestion failures | ML Engineering | If validation script rejects a file you believe is correct |
| Ticker changes/discontinuations | Bloomberg Help (`F1 F1`) | If a ticker stops returning data permanently |

---

## 8. Quick Reference Card

**One-time setup:** Complete Section 3 (full export, steps 1–8) once.

**Daily routine:**
1. Open Bloomberg → pull 14 tickers for today → append row → forward-fill → save
2. Log in `audit_log.csv`
3. Commit file

**Friday routine:**
1. Full re-export (steps 1–8) with `_v{N}` suffix
2. Notify ML team of new version

**File path:** `ml-signal-service/data/raw/macro/EURUSD_H1_macro_insights.csv`

**Column count:** 16 (date + 15 macro columns, event_flag computed automatically)