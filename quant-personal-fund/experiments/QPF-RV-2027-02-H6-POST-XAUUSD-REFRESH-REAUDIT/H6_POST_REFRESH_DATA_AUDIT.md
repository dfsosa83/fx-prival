# H6 — Post-XAUUSD-Refresh Data Availability & Integrity Re-Audit

**Stage:** `H6_POST_XAUUSD_REFRESH_DATA_REAUDIT`
**Parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Date:** 2026-09-30 · **Clock:** internal ordinal only (`NOT_UTC`)

---

## 1. Scope

Availability/integrity re-audit of the seven H6 H1 instruments after the successful XAUUSD refresh.
No price-derived analytics, no snapshot, no H6 screen, no costs/PnL/trading. No raw source was
modified in this stage.

## 2. Per-instrument re-audit

| Symbol | Raw path | SHA256 | Schema | Rows | First label | Final label | Validation | Status |
|---|---|---|---|---|---|---|---|---|
| EURUSD | `…/H1/EURUSD_H1.csv` | `2F7B0630EDCD6CE0D162992393996E0248E51280EB58798C1313A91D0FFAA7AE` | legacy | 48,204 | `2019-01-02 00:00:00` | `2026-09-30 15:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| USDJPY | `…/H1/USDJPY_H1.csv` | `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858` | canonical | 48,191 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| USDCHF | `…/H1/USDCHF_H1.csv` | `E87554BC919CED237E62B993AC612DD53FA9F583A07CCE81797CFB6B455DC9EB` | legacy | 48,209 | `2019-01-02 00:00:00` | `2026-09-30 15:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| USDCAD | `…/H1/USDCAD_H1.csv` | `8AECF7FE947BBB340469BC739AB7B93ED0EEA44E89984A31D3ED6178A8C39B53` | legacy | 48,179 | `2019-01-02 07:00:00` | `2026-09-30 14:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| AUDUSD | `…/H1/AUDUSD_H1.csv` | `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` | canonical | 48,116 | `2019-01-02 00:00:00` | `2026-09-24 18:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| NZDUSD | `…/H1/NZDUSD_H1.csv` | `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` | canonical | 48,087 | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| XAUUSD | `…/H1/XAUUSD_H1.csv` | `6DB76DE379FCF0EF65E60597B1A14AC3DD5E3466E01216D7386702CB14FB7F36` | canonical | 45,809 | `2019-01-02 01:00:00` | `2026-09-30 14:00:00` | PASS | **H6_DATA_ELIGIBLE** |

Validation (all PASS): recognized canonical or legacy schema; `datetime`/`close` present; ≥30,000 rows;
no null/duplicate labels; strictly ascending lexical order; close finite & strictly positive; final
label ≥ `2026-09-24 18:00:00`. `…/H1/` denotes `ml-signal-service/data/raw/mt5/H1/`.

## 3. XAUUSD-specific assertion

| Condition | Required | Observed | Result |
|---|---|---|---|
| SHA256 | `6DB76DE379FCF0EF65E60597B1A14AC3DD5E3466E01216D7386702CB14FB7F36` | same | **PASS** |
| Schema | `datetime,open,high,low,close,volume` | canonical | **PASS** |
| Rows | 45,809 | 45,809 | **PASS** |
| First label | `2019-01-02 01:00:00` | same | **PASS** |
| Final label | `2026-09-30 14:00:00` | same | **PASS** |

XAUUSD was **not** modified in this stage.

## 4. Overall decision

**`H6_ALL_INSTRUMENTS_DATA_READY`** — all seven instruments are `H6_DATA_ELIGIBLE`.

- Availability/integrity only, **not** an H6 result.
- **FX and XAUUSD stay separate snapshots and separate statistical strata.**
- **No H6 snapshot exists yet.**
- **No H6 screen is authorized.**
- **No instrument was selected based on performance.**
- The H6 primary family remains `7 instruments × 3 N × 3 M × 3 H × 2 event classes = 378 tests`.

## 5. No-computation statement

No prices, log prices, returns, volatility, ranges, breakout events, invalidations, correlations,
regressions, ADF, AR/OU, variance ratios, bootstrap, outcomes, costs, PnL, backtests, signals,
strategies, ML, or trading metrics were computed. No MT5/downloader/broker/network/calendar/external
access occurred. Datetime labels are opaque ordinals (`NOT_UTC`).
