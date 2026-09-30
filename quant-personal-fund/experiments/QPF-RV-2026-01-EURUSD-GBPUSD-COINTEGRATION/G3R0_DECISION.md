# G3-R0 Decision — Immutable Input Snapshot Freeze

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G3R0_IMMUTABLE_INPUT_SNAPSHOT_FREEZE`
**Decision:** `SNAPSHOT_FROZEN_PENDING_G3_V2`

---

## Reason

The mutable incremental-downloader source CSVs changed after the G1 audit, which caused G3-v1 to fail
closed at hash verification. An immutable, strict-intersection input version is now frozen **before**
any future G3-v2 parsing.

## Protocol integrity repair summary

Executed via `G3_INTERNAL_STATISTICAL_PROTOCOL_V2.md` (supersedes V1 only for the snapshot-v2 run):
- **Correction 1 — rolling stability isolation:** pre-sealed (train+validation) 5,000/1,000 rolling
  is the **only** gate input; sealed rolling is confirmatory (`NOT_APPLICABLE_INSUFFICIENT_BARS` if
  too short); sensitivity windows 4,000/6,000 are pre-sealed only. Rolling thresholds updated
  (≥60% approve; <40% reject; 40–<60% may contribute to PAUSE).
- **Correction 2 — bootstrap terminology:** the AR(1) bootstrap is described as
  "stationary-bootstrap resampling of aligned AR(1) observations" (aligned-pairs, uncertainty
  diagnostic only; not an OU-trajectory simulation). No numerical change.

These corrections came from **static review**, not from any observed statistical result.

## Source / snapshot hashes

| Item | SHA256 |
|---|---|
| EURUSD source (current) | `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` |
| GBPUSD source (current) | `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` |
| Snapshot `g3_internal_clock_snapshot_v2.csv` | `159BE4F9F1A3AD7F1F0B19675C6EB11DC4CFFDED95101898F147D041BEB0BA5D` |

## Snapshot row count

**T = 48,184** (strict intersection 48,185; minus the final label `2026-09-29 19:00:00`; 5
GBPUSD-only unmatched labels excluded by intersection).

## Status statement

G3-v1 remains **`PAUSE_STATISTICAL_VIABILITY`**. No statistical result was observed in G3-v1, and
**no hypothesis conclusion was changed**. The V2 protocol repairs are integrity corrections only.

## Authorization consequence

Only a **separately authorized single G3-v2 run using the snapshot exactly**
(`g3_internal_clock_snapshot_v2.csv`, hash-verified, comment line skipped) may proceed. No G2/G4/G5/G6
work is authorized.

## Declaration

No log-price transformation, returns, spread, correlation, covariance, cointegration, ADF, Johansen,
hedge ratio, AR(1), half-life, variance ratio, Hurst, bootstrap, cost, PnL, EV, signal, sizing,
portfolio, ML, LLM, backtest, MT5/broker/credential/network, order, or execution/demo/shadow/live
activity occurred. No external joins; internal clock only (`NOT_UTC`).
