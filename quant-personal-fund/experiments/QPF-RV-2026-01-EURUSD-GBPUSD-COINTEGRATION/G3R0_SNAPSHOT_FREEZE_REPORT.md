# G3-R0 — Snapshot Freeze Report

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Stage:** `G3R0_IMMUTABLE_INPUT_SNAPSHOT_FREEZE`
**Date:** 2026-09-29
**Result:** `SNAPSHOT_FROZEN_PENDING_G3_V2`

---

## 1. Scope and prohibition statement

Narrow, deterministic freeze of an **immutable internal-clock** input snapshot from the two local H1
CSVs, following the `PAUSE_STATISTICAL_VIABILITY` of the first G3 attempt. Internal clock only —
labels are **ordinal (`NOT_UTC`)**. No MT5, broker, credentials, network, external data, or
execution code. No statistical calculation was performed (no log prices, returns, spreads, ADF,
Johansen, AR(1), half-life, variance ratio, bootstrap, hedge ratio, correlation, cointegration,
costs, PnL, signals, ML, backtests, or trading).

## 2. Reason v2 is required

The G3-v1 runner **failed closed at SHA256 verification** because the two source CSVs are mutable
outputs of an incremental MT5 downloader and had changed after the G1 audit. A stable, immutable
input must be frozen before any (separately authorized) G3-v2 statistical run.

## 3. Statement that G3-v1 failed before parsing

G3-v1 returned **before** `pandas.read_csv` on either CSV — no panel was built and **no statistical
result was observed**. Consequently the V2 protocol-integrity corrections are **not** result-driven.

## 4. Raw source paths, schema, current hashes, row counts, label ranges

| Instrument | Path | Current SHA256 | Rows | Label range |
|---|---|---|---|---|
| EURUSD | `ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv` | `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` | 48,185 | 2019-01-02 00:00:00 → 2026-09-29 20:00:00 |
| GBPUSD | `ml-signal-service/data/raw/mt5/H1/GBPUSD_H1.csv` | `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` | 48,190 | 2019-01-02 00:00:00 → 2026-09-29 20:00:00 |

Source schema used: `datetime, close` only. Validation: monotonicity **PASS**, duplicates **PASS**,
nulls **PASS**, positivity **PASS**.

## 5. Strict intersection count

Raw intersection of EURUSD/GBPUSD timestamp labels: **48,185**.

## 6. Exact exclusions and counts

| Exclusion | Count |
|---|---|
| Final label `2026-09-29 19:00:00` (present → removed) | 1 |
| Unmatched **GBPUSD-only** observations (removed by intersection) | 5 |
| Unmatched **EURUSD-only** observations | 0 |
| Duplicate/missing validation outcome | PASS (no duplicates; monotonic) |

No forward-fill, interpolation, resampling, or repair was applied.

**Observation for the future G3-v2 run (documented, not adjusted):** the frozen exclusion rule names
the exact label `2026-09-29 19:00:00`; the sources now end at `2026-09-29 20:00:00`, which is
therefore retained in the snapshot. Whether `20:00:00` is a completed bar is unproven; the G3-v2
runner may apply an explicit completed-bar rule, but this snapshot was frozen per the stated rule and
is **not** re-cut here.

## 7. Snapshot path, schema, row count, SHA256

| Field | Value |
|---|---|
| Path | `g3_internal_clock_snapshot_v2.csv` |
| Header comment | `# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; NO_COSTS; NO_TRADING_USE` |
| Columns | `internal_index_k, timestamp_label_internal, eurusd_close, gbpusd_close` |
| Rows (T) | **48,184** |
| First / last label | `2019-01-02 00:00:00` / `2026-09-29 20:00:00` |
| SHA256 | `159BE4F9F1A3AD7F1F0B19675C6EB11DC4CFFDED95101898F147D041BEB0BA5D` |
| Hash file | `g3_internal_clock_snapshot_v2.sha256` (format: `<HASH>  g3_internal_clock_snapshot_v2.csv`) |

## 8. Internal-clock-only declaration

`internal_index_k = 1..T` is an **ordinal** clock. Timestamp labels are **NOT_UTC**; nothing was
converted, localized, or interpreted as UTC/broker/session/event time. No external data was joined.

## 9. Explicit statement

No log prices, returns, changes, spreads, correlations, covariance, cointegration, ADF, Johansen,
hedge ratios, AR(1), half-life, variance ratio, Hurst, bootstrap, costs, PnL, EV, signals, sizing,
portfolio, ML, LLM, backtests, or trading actions occurred. The script wrote only the snapshot CSV
and its hash file.

## 10. Recommendation

**`SNAPSHOT_FROZEN_PENDING_G3_V2`** — an immutable input snapshot is frozen and hash-verified,
pending a separately authorized single G3-v2 statistical run using the snapshot exactly.

## Artifacts

- `G3_INTERNAL_STATISTICAL_PROTOCOL_V2.md`
- `g3r0_snapshot_freeze.py`
- `g3_internal_clock_snapshot_v2.csv`
- `g3_internal_clock_snapshot_v2.sha256`
- `G3R0_SNAPSHOT_FREEZE_REPORT.md`
- `G3R0_DECISION.md`
- `data_manifest_v2.yaml`
- `RUN_LOG.md` (appended)
