# H6 — Screen Orchestration Specification

**Stage:** `H6_SCREEN_ORCHESTRATION_DESIGN`
**Experiment:** `QPF-RV-2027-04-H6-SCREEN-ORCHESTRATION-DESIGN`
**Parent design:** `QPF-RV-2026-11-H6-FAILED-BREAKOUT-INVALIDATION`
**Snapshot source:** `QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE`
**Clock:** internal ordinal only (`NOT_UTC`)

> Documentation + pseudocode only. This does **not** run H6, does not create a runnable screen, and does
> not modify the frozen H6 protocol.

---

## 1. Snapshot binding

A later execution must:

- read **only** the seven snapshot paths and exact hashes recorded in
  `experiments/QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE/data_manifest_h6.yaml`;
- verify every snapshot **SHA256 before `pandas.read_csv`**;
- load each with `pd.read_csv(..., comment="#")` (the banner line is skipped);
- validate each individual schema. The canonical contract is
  `internal_index_k, timestamp_label_internal, <instrument>_close` — the third column is
  **instrument-specific** (e.g. `eurusd_close`, `xauusd_close`), matching the manifest;
- validate its own index sequence (`1..T`), row count, monotonic labels, and positive finite closes;
- treat labels as **`NOT_UTC`** opaque ordinals;
- **never** align, join, intersect, pool, resample, or compare timestamps **across** instruments.

## 2. Instrument strata

```text
FX stratum:
EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD

XAUUSD stratum:
XAUUSD only
```

- Each instrument is screened **independently**.
- **FX and XAUUSD are never pooled.**
- No instrument may be **ranked against another using raw performance statistics**.
- Per-instrument validation selection is permitted only under the frozen H6 survivor rules.
- Stratum-level summary counts are **descriptive, not a pooled statistical test**.

## 3. Fixed H6 grid (unchanged)

```text
N ∈ {12, 24, 48}
M ∈ {2, 4, 8}
H ∈ {4, 8, 24}
Event classes: FAILED_UPWARD_BREAKOUT, FAILED_DOWNWARD_BREAKOUT
```

Each instrument has \(3 \times 3 \times 3 \times 2 = 54\) validation tests.

## 4. Splits (per snapshot, independently)

\[
n_{\mathrm{train}}=\lfloor0.60T\rfloor,\quad n_{\mathrm{validation}}=\lfloor0.20T\rfloor,\quad
n_{\mathrm{sealed}}=T-n_{\mathrm{train}}-n_{\mathrm{validation}}.
\]

Frozen **30-bar embargo** after train and after validation.

- The event start, the whole invalidation interval, the confirmation event, and the entire outcome
  through \(e+H\) must stay **inside the assigned segment**.
- Embargo bars cannot participate in any feature, event, control, or outcome.
- **Train is descriptive only.**
- **Validation is the only selection segment.**
- **Sealed is evaluated only for selected configurations.**

## 5. Multiplicity families (separate)

```text
FX validation family:     6 instruments × 3 N × 3 M × 3 H × 2 classes = 324 tests
XAUUSD validation family: 1 instrument  × 3 N × 3 M × 3 H × 2 classes = 54 tests
```

For each family:

- report **every** test, including insufficient-event records;
- apply BH only across **numeric** validation HAC p-values **in that family**;
- use BH FDR **\(q=0.10\)**;
- **do not combine families**;
- do not use target/instrument filtering after seeing results;
- **null p-values remain in the complete result table but are excluded from the numeric BH ranking**
  (rank/`q` are `null` for those rows).

## 6. Validation selection (frozen H6 survivor rule)

For a bound configuration `instrument, N, M, H`, **both** event classes must independently have:

- ≥30 valid events;
- ≥200 valid controls;
- favorable unaligned difference sign;
- positive aligned event mean;
- positive aligned difference;
- HAC two-sided p < 0.05;
- BH q ≤ 0.10;
- favorable non-overlap aligned-difference sign.

Selection rules:

- Select **at most three** configurations **within FX**.
- Select **at most three** configurations **within XAUUSD**.
- Rank **only within stratum** using the frozen order: 1. lower max BH q across classes; 2. lower max raw
  p; 3. larger min |aligned difference|; 4. larger min valid-event count; 5. lexicographically smaller
  instrument; 6. smaller \(N\), then \(M\), then \(H\).
- No survivor in a stratum ⇒ that stratum's sealed outcomes are not evaluated.
- A failure in FX does **not** prevent XAUUSD from being evaluated, and vice versa.

## 7. Sealed confirmation and decision scope

For selected configurations only:

- evaluate exactly the same instrument, \(N,M,H\), control definition and event rules;
- **no BH reranking on sealed**;
- apply the frozen seven criteria independently to **both** event classes;
- record one decision per selected configuration: `APPROVE_FAILED_BREAKOUT_STATISTICAL_VIABILITY` or
  `REJECT_FAILED_BREAKOUT_STATISTICAL_VIABILITY`.

Stratum-level status:

```text
APPROVE_H6_FX_STATISTICAL_VIABILITY / REJECT_H6_FX_STATISTICAL_VIABILITY / PAUSE_H6_FX_STATISTICAL_VIABILITY
APPROVE_H6_XAUUSD_STATISTICAL_VIABILITY / REJECT_H6_XAUUSD_STATISTICAL_VIABILITY / PAUSE_H6_XAUUSD_STATISTICAL_VIABILITY
```

A stratum is **approved** only if at least one selected configuration passes sealed. If no validation
survivors exist, it is **rejected**. Any integrity/technical failure affecting a snapshot makes **only
the affected stratum** pause; it does **not** silently remove the instrument.

A statistical approval may support later design of a **cost-aware economic test for that individual
configuration only**. It does **not** establish PnL, profitability, execution feasibility, or trading
authorization.

## 8. Execution order

1. Verify all snapshot hashes and schemas.
2. Independently construct splits per snapshot.
3. Compute train descriptive summaries only if the execution protocol requires it; **never** use train
   for selection.
4. Evaluate all validation tests per stratum (324 FX; 54 XAUUSD).
5. Apply BH **independently per stratum**.
6. Identify/rank/select up to three configurations **per stratum**.
7. Evaluate sealed only for selected configurations in each stratum.
8. Produce per-instrument, per-configuration, and per-stratum decisions.
9. **Stop** — do not continue to costs/PnL/backtest/trading.
10. Update research-control files only after a successful/paused **execution** stage, never during design.
