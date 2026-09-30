# G3-Internal Statistical Protocol V2 (FROZEN — snapshot-v2 execution)

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Stage context:** `G3R0_IMMUTABLE_INPUT_SNAPSHOT_FREEZE`
**Frozen:** 2026-09-29 — written **before** any snapshot-v2 parsing or statistical run.
**Supersedes:** `G3_INTERNAL_STATISTICAL_PROTOCOL.md` **only for the future snapshot-v2 execution.**

> Internal clock only. All timestamp labels are **ordinal (`NOT_UTC`)**. No costs, PnL, EV, signals,
> entries/exits, sizing, portfolio, ML/LLM, backtests, or execution.

---

## Why V2 supersedes V1 (documented, not result-driven)

1. The first G3 run **failed at SHA256 verification before parsing any data** and before observing
   any statistical result.
2. A **static code review** identified two **protocol-integrity corrections** (below) that are
   independent of any market outcome.
3. **No statistical parameter is being tuned** in response to any observed result.

## Preserved frozen choices (unchanged from V1)

Internal ordinal clock only (`NOT_UTC`); strict EURUSD/GBPUSD timestamp intersection; exclusion of
unmatched timestamps; exclusion of the final potentially-forming bar; 60% train / 20% validation /
20% sealed allocation; 30-bar embargoes; TRAIN-only OLS hedge ratio for the primary OOS spread; ADF
settings (`regression="c"`, `autolag="AIC"`); Johansen settings (`det_order=0`, `k_ar_diff=1`);
AR(1)/OU settings and half-life rule; variance-ratio horizons `q = 2,4,8,16`; the three-subperiod
design; random seed 42; stationary bootstrap with 1,000 resamples and average block length 24; and
all prohibitions against costs, PnL, signals, ML, backtest, trading, external joins, and
absolute-time interpretation.

## Correction 1 — Rolling stability isolation

V1 allowed a rolling summary over the full dataset. This is replaced by **three explicitly separate
diagnostics**:

1. **Pre-sealed rolling stability diagnostic (gate input).**
   - Input: **train + validation only**, excluding both embargo zones.
   - Primary design: trailing **5,000** bars; evaluation block: subsequent non-overlapping **1,000**
     bars.
   - **This is the only rolling pass-rate used in the statistical decision gate.**
2. **Sealed rolling diagnostic (confirmatory).**
   - Input: **sealed-test partition only**; same fixed 5,000/1,000 design.
   - Reported **separately** as confirmatory evidence; must not change parameters, thresholds, or
     protocol.
   - If the sealed test has insufficient observations for at least one 5,000+1,000 block, report
     `NOT_APPLICABLE_INSUFFICIENT_BARS`; do **not** reduce windows.
3. **Sensitivity diagnostics (pre-sealed only).**
   - Trailing windows **4,000** and **6,000** bars; evaluation block exactly **1,000** bars.
   - Report pass-rate sensitivity only; these do **not** replace or tune the 5,000-bar primary rule.

**Rolling approval/rejection update:**
- The primary decision gate uses **only** the pre-sealed 5,000/1,000 rolling pass rate.
- Approval requires pass rate **≥ 60%**.
- Pass rate **< 40%** is a rejection condition.
- **40% to <60%** is neither automatic approval nor rejection; it may contribute to
  `PAUSE_STATISTICAL_VIABILITY` unless another rejection condition applies.
- Sealed rolling is descriptive/confirmatory only; **no parameter adjustment** after observing it.

## Correction 2 — Bootstrap terminology

The same stationary-bootstrap **aligned-pairs** implementation is retained; it is described
accurately as:

```text
Stationary-bootstrap resampling of aligned AR(1) observations.
```

- It resamples paired \((s_{k-1}, \Delta s_k)\) observations while preserving local dependence through
  stationary-bootstrap indices.
- It estimates the uncertainty of the fitted AR(1) coefficient \(b\).
- It does **not** simulate a fully reconstructed OU trajectory.
- It is an **uncertainty diagnostic**, not a trading or return simulation.

The bootstrap design and numerical parameters are unchanged in this phase.

## Decision rule (V2)

Retain all original V1 approval/rejection conditions, except:
- Replace the old generic rolling condition with the **pre-sealed-only** rule (Correction 1).
- If the sealed rolling diagnostic is `NOT_APPLICABLE_INSUFFICIENT_BARS`, it must **not** itself
  trigger rejection or approval.

Clarification: spread differences \(\Delta s_k\) are allowed **only** for AR(1), variance-ratio, and
bootstrap diagnostics. They are **not** asset returns, trading returns, PnL, or strategy labels.

## Snapshot requirement for the G3-v2 run

The future G3-v2 run must consume the immutable snapshot
`g3_internal_clock_snapshot_v2.csv` (columns: `internal_index_k, timestamp_label_internal,
eurusd_close, gbpusd_close`), whose first line is the comment
`# INTERNAL_CLOCK_ONLY; NOT_UTC; STRICT_INTERSECTION; NO_COSTS; NO_TRADING_USE`. The runner must
**skip that comment line explicitly** and must verify the snapshot SHA256 in
`g3_internal_clock_snapshot_v2.sha256` before use.

## Restrictions

Only local CSVs + pandas/numpy/scipy/statsmodels; no `frival`/`ml-signal-service`/MetaTrader5/broker/
credentials/network/execution imports. Seed 42. Fail closed on hash/schema violations. No
PnL/returns/position/order objects; no cost/PnL/EV calculations; no external joins; no absolute-time
interpretation.
