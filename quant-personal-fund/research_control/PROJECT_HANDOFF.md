# Quant Research Project Handoff

## Project Objective

The program seeks statistically credible FX/XAUUSD hypotheses first, then separately evaluates economic
viability with realistic costs, and only later considers execution. An early statistical effect is
**not** proof of profitability, and no stage of this program treats it as such.

## Current State

- Active research family: `H6_FAILED_BREAKOUT_INVALIDATION`.
- H6 design is complete.
- All seven H6 instruments are H1 data eligible: `EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`, plus
  the separate `XAUUSD`.
- XAUUSD was safely refreshed, canonicalized and is no longer blocked.
- H6 uses FX and XAUUSD as **separate strata** and never pools their outcomes.
- All seven independent H6 H1 close-only snapshots are frozen and hash-verified.
- The frozen H6 failed-breakout screen has run once: **both strata were REJECTED**
  (no BH-corrected paired survivor in the FX 324-test family or the XAUUSD 54-test family).
- FX and XAUUSD remain separate research strata. No H6 economic test, cost/PnL analysis,
  backtest or trading task has run.
- Existing-asset inventory (`QPF-RV-2027-06`) selected two forward-demo candidates (readiness
  `READY_FOR_FORWARD_DEMO_DESIGN`, next design stage `FORWARD_DEMO_DESIGN`):
  A1 `GOLD_RULES_ENGINE` (XAUUSD) and A3 `EXEC_D1_TERMINAL` (pending-entry lifecycle).
  Supporting offline replay harness: A8 `FX_RULES_BACKTEST` (`READY_FOR_OFFLINE_REPLAY_DESIGN`).
- A practical evaluation design (`QPF-RV-2027-07`) now exists for A1 / A3 / A8 (two tracks: offline
  replay reproducibility; orders-disabled forward observation). H3/H4/H5/H6 remain rejected.
- A1 formal offline reproducibility passed using the frozen rule version, isolated runner and local
  XAUUSD fixtures. Forward observation is not run; orders remain disabled.
- A1 formal offline reproducibility and orders-disabled forward-observation setup passed
  (`QPF-RV-2027-10`). A DEMO-only, orders-disabled observation environment was then built and validated
  read-only on the FP Markets MT5 demo terminal (`QPF-RV-2027-11`): `demo_verified=true`, XAUUSD
  available, 0 positions / 0 orders, H1/M30/M15 + tick read OK; connection shut down immediately.
- A1 orders-disabled XAUUSD forward observation is **ACTIVE** (`QPF-RV-2027-12`, session
  `a1_xauusd_observ_20260930`, decision `A1_ORDERS_DISABLED_FORWARD_OBSERVATION_STARTED`): preflight
  static scan clean, demo verified read-only, 0 positions / 0 orders, feed H1/M30/M15 + tick OK, one
  first cycle completed (`NO_SETUP`; 1 event, 1 heartbeat). Orders, virtual fills, PnL and trading
  remain disabled.
- A1 XAUUSD orders-disabled forward observation is active under a bounded routine continuation policy.
  It uses verified MT5 demo read-only data, frozen A1 code, append-only records and no execution path.
  It may run at most once per newly closed M15 bar until 30 calendar days and 50 completed cycles are
  both met.

## Immediate Blocker

```text
The observation window is incomplete (0 / 30 calendar days; 2 / 50 cycles).
Observation continues under the bounded routine continuation policy
(`A1_BOUNDED_OBSERVATION_ROUTINE`): at most one cycle per newly closed M15 bar,
pre-cycle integrity checks required, and automatic expiry once 30 calendar days
and 50 completed cycles are both met. A separate observation-close review is
then required. Orders, virtual fills, PnL, cost analysis and trading remain
disabled.
```

## Non-Negotiable Rules

- Timestamp labels are internal ordinal labels only: `NOT_UTC`.
- No raw-data repair, interpolation, forward fill, resampling or external joins for research snapshots.
- Every statistical screen reads a hash-verified immutable snapshot.
- Every snapshot excludes exactly its maximum available timestamp label.
- Do not silently change a frozen protocol because of results.
- No PnL, cost model, backtest, signal execution, position sizing or trading before its hypothesis
  passes statistical validation **and** a separate stage explicitly authorizes the next task.
- FX and XAUUSD remain separate result strata under H6.
- A rejected hypothesis stays rejected in its tested formulation; it is not quietly revived by
  parameter changes.
- The existing downloader is unsafe for direct append into legacy-schema files.
- For A1 XAUUSD forward observation, verified MT5 demo access is the approved read-only market-data
  method. It may read XAUUSD H1/M30/M15 bars and tick data, and may inspect count-only existing demo
  orders/positions for collision detection. It may not create, modify, cancel or close orders/positions,
  access live accounts, calculate PnL, or activate virtual fills unless a later stage explicitly
  authorizes those actions.

## Completed Hypotheses

| ID | Hypothesis / formulation | Status | Core reason |
|---|---|---|---|
| G3-v3 | EURUSD/GBPUSD H1 fixed-OLS residual mean reversion | REJECTED | OOS ADF, rolling stability and subperiod gates failed |
| G3-AUDNZD | AUDUSD/NZDUSD H1 fixed-OLS residual mean reversion | REJECTED | OOS ADF/Johansen/rolling stability gates failed |
| H4-C2 | EURUSD/USDCHF local rolling residual relationship | REJECTED | Insufficient eligible validation windows |
| H5-v2 | Multi-pair USD momentum plus high-volatility continuation | REJECTED | No paired strength/weakness BH-corrected validation survivor |
| H6 | Failed-breakout invalidation event study | REJECTED (frozen formulation) | No BH-corrected paired survivor in FX (324) or XAUUSD (54) validation |

## Data and Schema Status

| Item | Status / fact |
|---|---|
| Canonical raw schema | `datetime,open,high,low,close,volume` |
| Legacy raw schema | `open,high,low,close,volume,datetime` |
| Downloader behavior | Appends canonical datetime-first rows and is unsafe on legacy files |
| Safe rebuild utility | `quant-personal-fund/tools/raw_data_schema_rebuild/safe_h1_csv_rebuild.py` |
| Synthetic validation | 16/16 tests passed |
| USDJPY | Refreshed safely, canonicalized, immutable raw backup retained |
| XAUUSD | Refreshed safely, canonicalized, H6-data eligible |
| H6 FX universe | H6-data eligible |
| H6 XAUUSD | H6-data eligible |
| H6 snapshots | All seven independent close-only H1 snapshots frozen and hash-verified under `experiments/QPF-RV-2027-03-H6-SINGLE-INSTRUMENT-SNAPSHOT-FREEZE/`. |
| H6 screen | Run once; both strata rejected (0 validation survivors; sealed not evaluated). |

## H6 Frozen Design

- Instruments: `EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD`, plus separate `XAUUSD`.
- H1 only.
- Close prices only.
- Breakout lookback: `N ∈ {12,24,48}`.
- Invalidation window: `M ∈ {2,4,8}`.
- Outcome horizon: `H ∈ {4,8,24}`.
- Event classes: `FAILED_UPWARD_BREAKOUT`, `FAILED_DOWNWARD_BREAKOUT`.
- Event timestamp is the first strict re-entry into the prior range.
- Failed-up expects a negative future outcome; failed-down expects positive.
- Validation-only selection; at most three configurations per stratum reach sealed confirmation.
- BH FDR `q=0.10`.
- The primary H6 family is 378 tests: `7 instruments × 3 N × 3 M × 3 H × 2 event classes`.
- The malformed larger product seen in an earlier rendered report was a display artifact and does not
  alter H6.

## Current Authorized Next Action

```text
A1_BOUNDED_OBSERVATION_ROUTINE is an operational observation authorization only.
It permits bounded XAUUSD observations with verified MT5 demo read-only data and
orders disabled, at most once per newly closed M15 bar. No order, virtual fill,
PnL, cost analysis, performance metric or trading is authorized.
```

## Read Order for Future Agents

```text
1. quant-personal-fund/research_control/PROJECT_HANDOFF.md
2. quant-personal-fund/research_control/NEXT_ACTION.md
3. quant-personal-fund/research_control/RESEARCH_LEDGER.yaml
4. quant-personal-fund/research_control/CONTINUITY_PROTOCOL.md
5. Only the source artifacts listed in NEXT_ACTION.md
```
