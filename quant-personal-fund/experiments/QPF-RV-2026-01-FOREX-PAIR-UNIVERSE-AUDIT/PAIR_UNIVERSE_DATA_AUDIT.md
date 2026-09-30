# Pair-Universe H1 Data-Availability Audit

**Stage:** `PAIR_UNIVERSE_DATA_AVAILABILITY_AUDIT`
**Date:** 2026-09-29
**Nature:** data preparation / quality control only. No statistical, cost, PnL, signal, model, or
trading analysis. No candidate was selected on performance.

Candidate universe (fixed): `AUDUSD, NZDUSD, EURUSD, USDCHF, USDCAD, EURGBP`.
Raw directory: `ml-signal-service/data/raw/mt5/H1/` (canonical filename `<SYMBOL>_H1.csv`).
Downloader (used only for missing symbols): `ml-signal-service/steps/01_download/mt5_downloader.py`.

---

## 1. Per-symbol audit

| Symbol | Path | Existed before | Downloaded now | Tool | Schema | Rows | First label (as stored) | Last label (as stored) | SHA256 | Validation | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| AUDUSD | `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv` | false | **true** | `mt5_downloader.py` | `datetime,open,high,low,close,volume` | 48,116 | `2019-01-02 00:00:00` | `2026-09-24 18:00:00` | `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` | all pass | **DOWNLOADED_VALID** |
| NZDUSD | `ml-signal-service/data/raw/mt5/H1/NZDUSD_H1.csv` | false | **true** | `mt5_downloader.py` | `datetime,open,high,low,close,volume` | 48,087 | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` | `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` | all pass | **DOWNLOADED_VALID** |
| EURUSD | `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` | true | false | — | `open,high,low,close,volume,datetime` | 48,186 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | `8161B866D6CFE233B5361A51DE09ACFE9E9B8926D400EE09751DA8E65CA6550B` | all pass | **AVAILABLE_VALID** |
| USDCHF | `ml-signal-service/data/raw/mt5/H1/USDCHF_H1.csv` | true | false | — | `open,high,low,close,volume,datetime` | 48,191 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | `A25CBF3D0BF96C0A16FF41E9B157BBFFB1F94D8F268A16E5DD797D98F7134DFB` | all pass | **AVAILABLE_VALID** |
| USDCAD | `ml-signal-service/data/raw/mt5/H1/USDCAD_H1.csv` | true | false | — | `open,high,low,close,volume,datetime` | 48,161 | `2019-01-02 07:00:00` | `2026-09-29 20:00:00` | `B21F200A9EA8F8AE0468658EC2D65266F56FFE2604FEBF321CAF1BD0B39C5F11` | all pass | **AVAILABLE_VALID** |
| EURGBP | `ml-signal-service/data/raw/mt5/H1/EURGBP_H1.csv` | true | false | — | `datetime,open,high,low,close,volume` | 48,020 | `2019-01-02 06:00:00` | `2026-09-21 20:00:00` | `8B3E101797AFCBF1DEBCADA8B9474CB121609716AFADC6290351E774F5AAF9BA` | all pass | **AVAILABLE_VALID** |

Validation per symbol: required columns present (`datetime`, `close`); no nulls; no duplicate labels;
monotonic ascending; finite values; `close` strictly positive. **All six pass.**

## 2. Candidate-pair matrix (fixed order)

| ID | Ordered symbols | Both valid | Left label range | Right label range | Common labels | First common | Last common | Left-only | Right-only | ≥30,000 common | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | AUDUSD / NZDUSD | true | `2019-01-02 00:00:00` → `2026-09-24 18:00:00` | `2019-01-02 07:00:00` → `2026-09-24 18:00:00` | **48,030** | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` | 86 | 57 | true | **ELIGIBLE_FOR_FUTURE_G3_FREEZE** |
| C2 | EURUSD / USDCHF | true | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | 48,186 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | 0 | 5 | true | ELIGIBLE_FOR_FUTURE_G3_FREEZE |
| C3 | AUDUSD / USDCAD | true | `2019-01-02 00:00:00` → `2026-09-24 18:00:00` | `2019-01-02 07:00:00` → `2026-09-29 20:00:00` | 48,030 | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` | 86 | 131 | true | ELIGIBLE_FOR_FUTURE_G3_FREEZE |
| C4 | EURGBP / EURUSD | true | `2019-01-02 06:00:00` → `2026-09-21 20:00:00` | `2019-01-02 00:00:00` → `2026-09-29 21:00:00` | 48,020 | `2019-01-02 06:00:00` | `2026-09-21 20:00:00` | 0 | 166 | true | ELIGIBLE_FOR_FUTURE_G3_FREEZE |
| C5 | NZDUSD / USDCAD | true | `2019-01-02 07:00:00` → `2026-09-24 18:00:00` | `2019-01-02 07:00:00` → `2026-09-29 20:00:00` | 48,086 | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` | 1 | 75 | true | ELIGIBLE_FOR_FUTURE_G3_FREEZE |

Counts are **strict timestamp-label intersections** (ordinal internal labels, `NOT_UTC`); no
maximum-common-label exclusion has been applied yet. No log prices, changes, returns, correlations,
spreads, ratios, cointegration, or statistical tests were computed.

## 3. Data-quality notes

- The two downloaded files (AUDUSD, NZDUSD) use the downloader's canonical schema
  (`datetime,open,high,low,close,volume`); pre-existing files use the same columns in a different
  order. Both contain the required `datetime` and `close`.
- Downloaded files end at `2026-09-24 18:00:00` (today's later bars were unavailable to the downloader
  at run time); pre-existing files extend further. This does not affect eligibility.
- No existing raw CSV was overwritten, rewritten, re-sorted, repaired, filled, resampled, or altered.

## 4. Artifacts

- `pair_universe_data_audit.py`
- `pair_universe_data_audit.json`
- `PAIR_UNIVERSE_DATA_AUDIT.md`
- `PAIR_UNIVERSE_ACQUISITION_DECISION.md`
- New raw files: `ml-signal-service/data/raw/mt5/H1/AUDUSD_H1.csv`, `.../NZDUSD_H1.csv`
