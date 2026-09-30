# A1 — Controlled Offline Replay Design

**Asset:** A1 `GOLD_RULES_ENGINE` (`frival/gold_rules/{run_gold_rules.py,engine.py,bias.py,levels.py,config.yaml}`)
**Supporting harness:** A8 `FX_RULES_BACKTEST` (`frival/fx_rules_backtest/{run_backtest.py,report.py}`)
**Stage:** `A1_A3_A8_REPLAY_AND_FORWARD_DEMO_EVALUATION_DESIGN`

> This design **does not change A1 rules**. It is not a profitability backtest, parameter optimization,
> or performance study.

---

## Version pinning

- The A1 rule version must be pinned **by source path and commit/hash at execution time**.
- **This stage does not calculate that hash** (no execution).

## Inputs

- Inputs must be **local controlled fixtures or archived local inputs already identified by the
  inventory** (e.g. `frival/gold_rules/tests/fixtures/XAUUSD_{M15,M30,H1}.csv` and, if applicable to
  unchanged A1 logic, `frival/fx_rules_backtest/data/*_M15.csv` / `*_M30.csv`).
- **Do not download or use new market data.**

## What the replay measures (only)

- deterministic repeatability;
- signal/state transitions;
- rule inputs and derived **structural levels already emitted by A1**;
- signal acceptance/rejection reasons;
- pending/retest/breakout classifications;
- expiry and lifecycle closure;
- completeness of journal/event fields.

## What the replay must NOT calculate

PnL; profitability; trade returns; optimization; costs; performance ranking; strategy comparison.

## Reproducibility criterion

- A later authorized stage must run **two independent repeat runs over the same fixture inputs**.
- The success criterion is **exact event-record equality** between the two runs (after normalizing
  non-deterministic metadata such as wall-clock `run_id`, which must be excluded from the comparison).

## Outcomes

- **Fail-closed** → `REPLAY_REPRODUCIBILITY_PAUSE` if identical inputs produce different event records,
  missing required fields, inconsistent state transitions, or if any external dependency is required.
- **Success** → `REPLAY_REPRODUCIBILITY_PASS` if event records are deterministic and complete.

Success allows **only** the later forward-observation **design/execution**, not demo orders or trading.

## Artifacts of the future check (not created now)

- pinned rule version record;
- input fixture identity/hashes;
- two run event-record sets;
- equality comparison report;
- the `REPLAY_REPRODUCIBILITY_PASS`/`PAUSE` decision.
