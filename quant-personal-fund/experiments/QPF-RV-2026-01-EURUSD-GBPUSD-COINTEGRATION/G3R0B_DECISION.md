# G3-R0b Decision — Completed-Label Boundary Repair

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Date:** 2026-09-29
**Stage:** `G3R0B_COMPLETED_LABEL_BOUNDARY_REPAIR`
**Decision:** `SNAPSHOT_V3_FROZEN_PENDING_G3_V3`

---

## Summary

- **G3-v2 is not authorized.**
- **G3-v3 is not yet executed** and requires separate one-time authorization.
- Only `g3_internal_clock_snapshot_v3.csv`, **hash-verified** and read with its **comment line
  skipped**, may be used by a future G3-v3 runner.
- The boundary repair changed **no statistical setting and no decision threshold** — only the input
  exclusion rule (fixed named label → deterministic maximum common label).
- No statistical, economic, trading, or external activity was performed.
- **v1 and v2 artifacts remain intact and immutable.**

## Boundary rule

```text
Form the strict sorted intersection of internal timestamp labels, then exclude
exactly the maximum common label.
```

- Raw strict intersection: **48,185**
- Excluded maximum common label: **`2026-09-29 20:00:00`** (count = 1)
- Snapshot v3 rows: **48,184**; first label `2019-01-02 00:00:00`; last retained `2026-09-29 19:00:00`

## Hashes

| Item | SHA256 |
|---|---|
| EURUSD source (current) | `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` |
| GBPUSD source (current) | `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` |
| Snapshot v3 `g3_internal_clock_snapshot_v3.csv` | `B372EF5B508E11A244B521C9BD7D475D05682ABEFA8A383C3372D7F56AC81448` |

## Authorization consequence

```text
Only a separately authorized, one-time G3-v3 statistical run using the
hash-verified g3_internal_clock_snapshot_v3.csv exactly, with its comment line
skipped, may proceed. No G2, G4, G5, or G6 work is authorized.
```

## Declaration

No log-price transformation, returns, spread, correlation, covariance, cointegration, ADF, Johansen,
hedge ratio, AR(1), half-life, variance ratio, Hurst, bootstrap, cost, PnL, EV, Sharpe, signal,
sizing, portfolio, ML, LLM, backtest, MT5/broker/credential/network, order, or
execution/demo/shadow/live activity occurred. Internal clock only (`NOT_UTC`).
