# Internal Clock Only Research Amendment

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Decision:** `APPROVED_FOR_STATISTICAL_SCREENING_ONLY`

---

## Purpose

This amendment creates a limited, conditional research path that allows **future** statistical tests
based only on the **common internal ordering** of synchronized EURUSD and GBPUSD H1 bars.

It does **not** resolve absolute UTC, broker-server offset, DST, session, or cross-vendor
alignment. It does not claim that timestamps are UTC, and it does not change, erase, weaken, or
reinterpret any prior G1, G1-R, G1-R2, or G1-R3 evidence. It authorizes **no** statistical
computation in this task; it documents only the strictly limited scope that may be separately
authorized in the future.

## Evidence Basis

Source artifacts (unchanged by this amendment):

- `data_audit_report.md`
- `data_manifest_v1.yaml`
- `G1_DECISION.md`
- `G1R_MT5_METADATA_REPORT.md`
- `G1R_DECISION.md`
- `G1R2_TIMEZONE_PROVENANCE_REPORT.md`
- `G1R2_DECISION.md`
- `G1R3_CONTROLLED_EPOCH_PROBE_REPORT.md`
- `G1R3_DECISION.md`
- `RUN_LOG.md`

Only the following facts are asserted here:

- EURUSD and GBPUSD H1 CSVs come from the **same exporter / pipeline**.
- The two series share a **common internally synchronized timestamp-label basis**.
- Both series are **structurally clean** (no duplicates, strictly monotonic, valid OHLC).
- Cross-instrument alignment is **near-perfect** (structural intersection ≈ 99.99%).
- The **absolute timezone remains unresolved**.
- There is **no claim of UTC alignment**.

## Internal Clock Definition

The admissible research index is the ordinal

\[
k = 1, 2, \ldots, T
\]

where each \(k\) denotes one observation in the **strict chronological intersection** of EURUSD and
GBPUSD completed H1 bars. The future candidate pair is

\[
(P_k^{EURUSD}, P_k^{GBPUSD}).
\]

Rules:

- \(k\) is an **ordinal internal clock** — **not** UTC, not broker-local, not event time, not
  session time.
- **Only intersecting timestamps** may be used.
- **Unmatched timestamps must be excluded** — never forward-filled, interpolated, or repaired.
- **Chronological order must be preserved.**
- Any future split is chronological **in \(k\)**, not in assumed UTC.
- **No external data may be joined on \(k\)**.

## Conditionally Authorized Future Statistical Scope

A future, separately approved **G3-Internal** task may be allowed to:

- build a synchronized intersection dataset from the two existing local CSVs;
- preserve only common completed-bar observations;
- create chronological train / validation / sealed-test partitions based on observation order \(k\);
- estimate a hedge ratio using **training-past observations only**;
- test Engle-Granger/ADF, Johansen where appropriate, variance ratio, half-life, and rolling
  stability;
- calculate only research-statistical quantities necessary for these tests;
- use block bootstrap and subperiod robustness checks;
- produce an explicit `APPROVE`, `REJECT`, or `PAUSE` recommendation for **statistical viability
  only**.

This authorization is **conditional**: no data processing or calculation is authorized by the
amendment itself; a future explicit task-level prompt is required.

## Absolute-Time and External-Alignment Prohibitions

Internal-clock research may **not**:

- interpret timestamps as UTC, broker-local, London, New York, Asia, or any named session;
- join macro calendars, news, MERG, FRED, economic releases, event datasets, public sources, or
  external vendors;
- create time-of-day, day-of-week, session, calendar, or event features;
- use swaps by calendar day, rollover-day labels, session-sensitive spreads, or intraday execution
  timing;
- compare or align to a non-MT5 provider;
- assert absolute event timing, session timing, or UTC conversion.

## Cost and Execution Limitations

- This amendment does **not** advance G2.
- Current MT5 metadata may describe **contemporary** symbol conditions but **cannot** establish
  **historical** execution costs.
- No economic viability, spread/slippage/commission/swap calculation, EV, PnL, order simulation,
  trade sizing, or executable-strategy conclusion is allowed.
- **G6 remains blocked.**
- Any future cost research requires a separate G2 authorization and a new decision about how to
  handle historical time-dependent costs.

## Gate Interpretation

```text
Original G1 status: PAUSE.
Conditional internal-clock authorization: APPROVED_FOR_STATISTICAL_SCREENING_ONLY.
```

This is **not** `G1_PASS` under the original absolute-time contract. The only future candidate
phase enabled by this amendment is:

```text
G3-Internal Statistical Viability Screening
```

and only after a separate explicit task-level authorization.

## Required Future Preconditions

Before any G3-Internal work:

1. A new task-level prompt explicitly authorizes data parsing and computation.
2. The synchronized dataset must use the **strict EURUSD/GBPUSD timestamp intersection only**.
3. Any **current/final forming bar** must be excluded under the documented completed-bar rule.
4. The **five unmatched GBPUSD Friday-evening observations** identified in G1 must be excluded
   without imputation.
5. Dataset hashes from `data_manifest_v1.yaml` must be **re-verified** before use.
6. **No external data joins or absolute-time features** may be introduced.
7. Split design, embargo rule, and statistical acceptance/rejection thresholds must be **fixed
   before** the sealed test is inspected.
8. The output must state **statistical viability only** and must **not** claim tradability,
   economic viability, or deployment readiness.

## Non-Authorization Statement

This amendment does **not** authorize:

- data access or processing today;
- G2 cost evidence;
- G4 mean-reversion follow-up;
- G5 economic viability;
- G6 cost-aware backtesting;
- ML, LLM, signals, execution, shadow, demo, or live trading.

## Amendment Decision

```text
Decision: APPROVED_FOR_STATISTICAL_SCREENING_ONLY
Date: 2026-09-29
```

This is an **owner-approved governance amendment**, not a result of market analysis.
