# Practical Evaluation Overview — Existing Assets (A1 / A3 / A8)

**Stage:** `A1_A3_A8_REPLAY_AND_FORWARD_DEMO_EVALUATION_DESIGN`
**Experiment:** `QPF-RV-2027-07-A1-A3-A8-PRACTICAL-EVALUATION-DESIGN`
**Date:** 2026-09-30

---

## Scope and why the program is pivoting

After several generic H1 statistical hypotheses were evaluated and rejected, the program pivots to
**concrete, already-implemented assets** that are reconstructible, timestamped, isolated from live
execution, and objectively measurable. This is a design stage only — nothing is executed here.

**H3 (`G3-v3`), H4 (`G3-AUDNZD`, `H4-C2`), H5 (`H5-v2`) and H6 remain rejected in their frozen
formulations. They are not reopened, retested, or retuned.**

## Asset roles

- **A1 `GOLD_RULES_ENGINE`** — deterministic signal/rule engine (XAUUSD; M15/M30/H1); no ML/LLM.
- **A3 `EXEC_D1_TERMINAL`** — pending-entry **lifecycle/state persistence and event-recording adapter**
  (not a rule source here).
- **A8 `FX_RULES_BACKTEST`** — replay **support harness** (`frival/fx_rules_backtest/`), used only to
  support replay mechanics where the exact existing A1 logic can be applied **without changing the rule**.

## Two separate evaluation tracks

1. **Controlled offline replay design** — primary A1; harness A8. Verifies reproducible rule behavior,
   state transitions, pending/retest/breakout logic, risk-field generation, and journal completeness
   from **local controlled inputs**.
2. **Forward-demo observation design** — primary rule A1; recording adapter A3. Defines how future
   live-market observations will be collected with **orders disabled by default**.

**Neither track is PnL, performance optimization, or trading.**

## Instrument scope

- A1 primary: **XAUUSD**.
- A8 FX replay support only, and only if the exact existing A1 logic can be applied unchanged.
- **FX and XAUUSD results remain separate** and are never pooled.

## Event-recording principle

**Every candidate evaluation must be traceable even if no entry occurs.** Each evaluation cycle emits
a complete event record (or an explicit error), with `null` used where no signal/setup exists — never a
fabricated fill/order field.

## Exact next steps after this design

1. **First, a separate authorization** for a controlled **offline reproducibility check** of frozen A1
   using existing local fixtures.
2. **Then, separately, a forward-observation stage** with **orders disabled**.

No step here authorizes connecting to a broker, observing MT5, placing demo orders, simulating fills,
or trading.

## Related documents

- `A1_CONTROLLED_REPLAY_DESIGN.md`
- `A1_A3_FORWARD_OBSERVATION_DESIGN.md`
- `EVALUATION_EVENT_SCHEMA.yaml`
- `SAFETY_AND_PROMOTION_GATES.md`
