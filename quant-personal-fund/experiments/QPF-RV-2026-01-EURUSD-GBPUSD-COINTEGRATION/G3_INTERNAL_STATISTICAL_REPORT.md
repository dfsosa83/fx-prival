# G3-Internal Statistical Report

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Stage:** `G3_INTERNAL_STATISTICAL_VIABILITY_SCREENING` (internal clock only)
**Date:** 2026-09-29
**Result:** `PAUSE_STATISTICAL_VIABILITY` — **input hash verification failed (fail-closed; no statistics executed).**

---

## 1. Scope, clock limitation, and prohibition statement

Internal-clock-only statistical viability screening, authorized by
`INTERNAL_CLOCK_ONLY_RESEARCH_AMENDMENT.md`. Timestamp labels are **ordinal only (`NOT_UTC`)** and
are never interpreted as UTC/broker/session/event time. No costs, PnL, EV, signals,
entries/exits, sizing, portfolio, ML/LLM, backtests, shadow/demo/live, or execution. Only the two
local H1 CSVs were to be read; the run **failed closed before parsing any data**.

## 2. Hash verification result

The frozen protocol mandates SHA256 verification of both inputs before loading. Verification
**failed** — the current files differ from the hashes recorded in `data_manifest_v1.yaml`:

| Input | Expected (manifest) | Actual (current) | Match |
|---|---|---|---|
| `EURUSD_H1.csv` | `AFC3109108AE64E59800F99D4B87A11B58B26EDE5185DCBD3B132422E4F3DA5F` | `56E72E231DF53BAD0743940D2F21C5FA678EAE2CC47B02D82C7152DCE73A67FE` | **NO** |
| `GBPUSD_H1.csv` | `11D9D435C1DDBC4A797BDF236ED3F3F13765338D2AD21870268016F76FD24CB7` | `D175138CFA33F377071FAF2C9DC84F8D7FD35383D3778829476015A99F4DE6D2` | **NO** |

The script returned **before** `pandas.read_csv`; no price data was parsed, transformed, or tested.

## 3. Dataset construction, exclusions, raw internal-label boundaries

`NOT_RUN` — blocked by §2. The intended panel was the strict EURUSD/GBPUSD H1 timestamp
intersection after excluding the five unmatched GBPUSD Friday-evening observations (by
intersection) and the final label `2026-09-29 19:00:00`.

**Observed cause (documentation only):** the two CSVs have been updated since the G1 audit
(the incremental MT5 downloader appends new bars), which changes their file hashes. Current
metadata (read-only listing): `EURUSD_H1.csv` (2,863,583 bytes) and `GBPUSD_H1.csv` (2,869,091
bytes), last write 2026-09-29 15:19:43 / 15:18:26 local. Per the frozen protocol, a hash mismatch
**fails closed** and is **not** remediated by re-baselining hashes inside this phase.

## 4. Train/validation/test/embargo split counts and boundaries

`NOT_RUN` — not computed (blocked by §2).

## 5. Fixed train OLS α, β

`NOT_RUN`.

## 6. Residual ADF results

`NOT_RUN`.

## 7. Johansen results

`NOT_RUN`.

## 8. Rolling ADF stability results

`NOT_RUN`.

## 9. AR(1)/OU and half-life results

`NOT_RUN`.

## 10. Variance-ratio results

`NOT_RUN`.

## 11. Subperiod robustness results

`NOT_RUN`.

## 12. Bootstrap results

`NOT_RUN`.

## 13. Parameter sensitivity results

`NOT_RUN`.

## 14. Frozen decision-gate evaluation

| Check | Result |
|---|---|
| C1 hash verification passes | **FAIL** |
| C2 intersection/exclusion rules followed | NOT_EVALUATED |
| C3 validation & sealed residual ADF p<0.05 | NOT_RUN |
| C4 Johansen rank ≥1 at 5% | NOT_RUN |
| C5 ≥60% rolling ADF blocks pass | NOT_RUN |
| C6 AR(1) b<0, p<0.05, finite half-life (val & sealed) | NOT_RUN |
| C7 ≥2 of 4 VR horizons mean-reversion-compatible (val & sealed) | NOT_RUN |
| C8 ≥2 of 3 subperiods pass ADF & b<0 (val & sealed) | NOT_RUN |
| C9 bootstrap b CI below 0 (val & sealed) | NOT_RUN |
| C10 no prohibited feature/calculation | PASS |

The frozen REJECT rule is triggered by "hash failure or violation of intersection/exclusion rules";
the frozen PAUSE rule covers "a remediable artifact/hash/data-integrity problem". The hash mismatch
is a remediable **precondition** failure (the inputs must be re-frozen/re-manifested and re-verified
before the frozen statistical protocol can run), so this phase records **PAUSE** rather than REJECT
of the statistical hypothesis itself (no statistical test was executed, so the hypothesis is neither
approved nor rejected).

## 15. Final statistical-viability recommendation

**`PAUSE_STATISTICAL_VIABILITY`.** The frozen precondition #5 ("dataset hashes must be re-verified
before use") failed; no statistical test ran. Per the Execution Rule, the first frozen run is
recorded as final for this phase and no parameters were changed or retried.

## 16. Explicit statement

No economic or trading conclusion exists. No cost, PnL, spread/slippage/commission/swap, EV, signal,
entry/exit, sizing, portfolio, ML/LLM, backtest, shadow/demo/live, or order action occurred. No
price data was parsed. Internal clock only; **no absolute UTC/session/event alignment**.

## Artifacts

- `G3_INTERNAL_STATISTICAL_PROTOCOL.md` (frozen before run)
- `G3_INTERNAL_RESULTS.json` (fail-closed result)
- `G3_INTERNAL_DECISION.md`
- `data_manifest_v1.yaml` (updated: `g3_internal_screening`)
- `RUN_LOG.md` (appended)
