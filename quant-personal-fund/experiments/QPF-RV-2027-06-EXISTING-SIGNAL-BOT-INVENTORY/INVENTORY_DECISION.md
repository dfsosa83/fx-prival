# Inventory Decision

**Stage:** `EXISTING_SIGNAL_AND_BOT_EVIDENCE_INVENTORY`
**Experiment:** `QPF-RV-2027-06-EXISTING-SIGNAL-BOT-INVENTORY`
**Date:** 2026-09-30
**Mode:** read-only inspection; no execution of any kind.

```text
decision: EXISTING_RULE_READY_FOR_FORWARD_DEMO_DESIGN
```

---

## Selection basis

Candidates were assessed **only** on technical measurability:

1. clarity of rule definition;
2. availability of local inputs/logs/test evidence;
3. isolation from execution;
4. feasibility of objective measurement.

Performance, PnL and inferred profitability were **not** used.

## Selected candidates (at most two)

1. **A1 `GOLD_RULES_ENGINE`** (XAUUSD, M15/M30/H1) — deterministic rules, `--dry` mode, local tests/fixtures,
   per-evaluation journal and demo virtual-PnL realization; adapter-isolated on a demo guard.
   Readiness: `READY_FOR_FORWARD_DEMO_DESIGN`. Next design stage: **`FORWARD_DEMO_DESIGN`**.
2. **A3 `EXEC_D1_TERMINAL`** (pending-entry lifecycle, configurable instruments) — deterministic lifecycle,
   unit-tested append-only event log, demo-env guard, dedicated adapter.
   Readiness: `READY_FOR_FORWARD_DEMO_DESIGN`. Next design stage: **`FORWARD_DEMO_DESIGN`**.

**Supporting (not selected as a standalone candidate):** **A8 `FX_RULES_BACKTEST`** is an existing offline
replay harness (`READY_FOR_OFFLINE_REPLAY_DESIGN`) relevant to A1's rule.

FX ML/LLM signal generation (A2/A6) and the prior hypothesis families (G3-v3, G3-AUDNZD, H4-C2, H5-v2)
remain rejected in their frozen formulations.

## Required statements

- **H6 remains rejected and closed** — both strata (`REJECT_H6_FX_STATISTICAL_VIABILITY`,
  `REJECT_H6_XAUUSD_STATISTICAL_VIABILITY`) — as do G3-v3, G3-AUDNZD, H4-C2 and H5-v2 in their frozen
  formulations. This inventory does not reopen, retest or retune them.
- This inventory **does not grant** demo, paper, shadow or live trading.
- Any next stage **requires separate explicit authorization**.
- **No claim of profitability** follows from asset existence; no PnL/cost/performance was computed.
- **FX and XAUUSD remain separate strata**; their results must never be pooled.

## Next authorization consequence (requires separate authorization)

```text
A separate stage may design a controlled forward-demo evaluation for A1 and/or A3,
with explicit measurement, logging and isolation requirements. No live execution,
costs, PnL, backtest or trading is authorized. The next action remains
REQUIRES_SEPARATE_AUTHORIZATION. H6 remains rejected.
```
