# H6 — H1 Data Availability & Quality Audit

**Stage:** `H6_H1_DATA_AVAILABILITY_AUDIT`
**Parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Date:** 2026-09-30 · **Clock:** internal ordinal only (`NOT_UTC`)

---

## 1. Scope and prohibitions

Availability/integrity audit of the seven H6 H1 instruments (existence, schema, hash provenance,
coverage, integrity). **No** market statistics, log prices, returns, ranges, highs/lows,
breakout/invalidation events, outcomes, correlations, regressions, PnL, costs, backtests, ML, or
trading were computed. No snapshot was created. No valid existing source was modified or updated.

## 2. Universe and strata

- H6 universe: `EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD, XAUUSD`.
- **FX instruments and XAUUSD remain separate snapshots and separate result strata**; XAUUSD is never
  pooled with FX, never used as a confirmation feature, and never used to rank FX candidates.
- Frozen H6 primary multiplicity family: **7 instruments × 3 N × 3 M × 3 H × 2 event classes = 378**.
- **Correction note:** any malformed larger product in prior rendered text (e.g. an inflated
  instrument×N×M×H product) was a **display artifact only** and does **not** modify the frozen
  protocol. The family is exactly **378** tests.

## 3. Per-instrument audit

| Symbol | Expected path | Existed before | Downloaded | SHA256 | Schema | Rows | First label | Final label | Validation | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| EURUSD | `…/H1/EURUSD_H1.csv` | true | false | `18F6135044EA42D81D575122B63F614F47BEF0EC100E68970096A7FE8204A507` | legacy | 48,203 | `2019-01-02 00:00:00` | `2026-09-30 14:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| USDJPY | `…/H1/USDJPY_H1.csv` | true | false | `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858` | canonical | 48,191 | `2019-01-02 00:00:00` | `2026-09-29 21:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| USDCHF | `…/H1/USDCHF_H1.csv` | true | false | `3DF2043951102C70DF97661C28A76715C291FF6121C8144A719CF5E6BAE5C715` | legacy | 48,208 | `2019-01-02 00:00:00` | `2026-09-30 14:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| USDCAD | `…/H1/USDCAD_H1.csv` | true | false | `8AECF7FE947BBB340469BC739AB7B93ED0EEA44E89984A31D3ED6178A8C39B53` | legacy | 48,179 | `2019-01-02 07:00:00` | `2026-09-30 14:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| AUDUSD | `…/H1/AUDUSD_H1.csv` | true | false | `0BF89F684D31DA032EB3B7D93713E45C7D8D1E8ADBF9A033D53311AE8A110A66` | canonical | 48,116 | `2019-01-02 00:00:00` | `2026-09-24 18:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| NZDUSD | `…/H1/NZDUSD_H1.csv` | true | false | `9707F4D0066248440A97FD93B4CFAACE9D5A3F9D350171298F7EC695A97A85E9` | canonical | 48,087 | `2019-01-02 07:00:00` | `2026-09-24 18:00:00` | PASS | **H6_DATA_ELIGIBLE** |
| XAUUSD | `…/H1/XAUUSD_H1.csv` | true | false | `A36F2E2331B38E72A6D2874B625DB981AED92220499204D18E8CE58D71332CFA` | legacy | 45,077 | `2019-01-02 01:00:00` | `2026-08-17 16:00:00` | PASS | **H6_DATA_STALE** |

Validation (all PASS): `datetime`/`close` present; ≥2 rows; no null/duplicate labels; strict lexical
ascending order; close finite & strictly positive. `…/H1/` denotes
`ml-signal-service/data/raw/mt5/H1/`.

## 4. Eligibility rule applied

`H6_DATA_ELIGIBLE` requires: raw CSV exists; recognized canonical or legacy schema; integrity PASS;
≥30,000 rows; final label ≥ `2026-09-24 18:00:00`. Otherwise one of `H6_DATA_MISSING`,
`H6_DATA_INVALID`, `H6_DATA_INSUFFICIENT_HISTORY`, `H6_DATA_STALE`,
`BLOCKED_SCHEMA_REPAIR_REQUIRED`.

- **All six FX instruments are `H6_DATA_ELIGIBLE`.**
- **XAUUSD is `H6_DATA_STALE`** (final label `2026-08-17 16:00:00` < threshold). Because XAUUSD exists
  and is structurally valid, it was **not** downloaded or updated in this stage (only missing/invalid
  files may be acquired; valid files must not be updated).

## 5. Downloads in this stage

**None.** No H6 instrument was missing or invalid, so no acquisition was performed and the downloader
was not invoked.

## 6. No-price-statement

No raw-price statistics, breakout/invalidation, outcome, PnL, cost, execution, or trading conclusion
appears in this audit. Datetime labels are opaque ordinals (`NOT_UTC`) and were not parsed.
