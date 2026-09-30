# Experiment Registry — Identifier Governance

**Status:** Governance reference (Phase 0.5 — Traceability and Execution Isolation)
**Scope:** `quant-personal-fund/` (QPF) and the referenced legacy programs `frival/` and `ml-signal-service/`
**Nature:** Documentation only. This file reserves nothing and creates no experiment folder.

This registry exists to make every experiment — past and future — unambiguous. It records the
known identifiers, their owning program, their documented status/decision, and the canonical
evidence path, so that no future experiment can silently reuse a historical identifier or
repeat a closed hypothesis.

---

## 1. Identifier collision hazard (read first)

Two research programs share the same historical `EXP-2026-xx` label scheme:

- **Legacy program** — `frival/` + `ml-signal-service/` (the Q4 2026 research program).
- **QPF platform** — `quant-personal-fund/` (the current, independent platform).

Because both programs were numbered independently, the *same* number can denote two different
experiments. Known overlaps:

| Label | Legacy meaning | QPF meaning |
|---|---|---|
| `EXP-2026-01` | (not registered in the preserved legacy record) | `EXP-2026-01-VOL-FORECAST-OVERLAY` |
| `EXP-2026-03` | `EXP-2026-03-RULEENGINE` (gold rules engine) | `EXP-2026-03-SELECTIVE-DERISK-OVERLAY` |
| `EXP-2026-05` | `EXP-2026-05-EURUSD-SELL-COSTLABEL` | `EXP-2026-05-INVALIDATION-REVERSAL` |

**Rule:** a bare `EXP-2026-xx` identifier is ambiguous on its own. Always qualify it with its
program scope (see §4) and never treat one program's number as pointing at the other's artifact.

---

## 2. Legacy identifiers are immutable

- Historical experiment IDs are **frozen**. They may not be renamed, renumbered, re-scoped, or
  reused for a different hypothesis.
- A legacy artifact may be *referenced* (pointer only) but must never be moved, copied over,
  rewritten, or re-scored. See `docs/falsification_ledger/LEGACY_INDEX.md`.
- A materially different future hypothesis gets a **new** identifier under the Future QPF
  namespace (§3) and a new pre-registration. It never inherits a historical ID.

---

## 3. Future QPF namespace (reserved format)

Future QPF experiments use the collision-proof format:

```
QPF-<FAMILY>-<YEAR>-<SEQUENCE>-<SLUG>
```

- `<FAMILY>` — short family code (e.g. `RV`, `MR`, `CRYPTO`, `TREND`, `CARRY`).
- `<YEAR>` — four-digit year.
- `<SEQUENCE>` — two-digit sequence within the family and year (`01`, `02`, …).
- `<SLUG>` — upper-case hyphenated descriptor.

Illustrative examples (**NOT reserved, NOT created** — documentation only):

- `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
- `QPF-MR-2026-01-FX-INTRADAY-OVEREXTENSION`
- `QPF-CRYPTO-2026-01-PERP-BASIS-FUNDING`

A `QPF-*` identifier is distinct from any historical `EXP-2026-xx` identifier and must never be
mapped back onto one.

---

## 4. Program scope legend

| program_scope | Meaning |
|---|---|
| `LEGACY_FRIVAL_ML` | Legacy `frival/` + `ml-signal-service/` Q4 2026 research program. Immutable. |
| `QPF_PLATFORM` | Current `quant-personal-fund/` platform experiments (historical `EXP-2026-xx` IDs). |
| `FUTURE_QPF` | New experiments under the `QPF-<FAMILY>-<YEAR>-<SEQUENCE>-<SLUG>` namespace. |

---

## 5. Known experiments

Statuses, decisions, evidence paths, and traceability grades below reproduce only what is
explicitly documented in the repository (the falsification ledger, experiment manifests,
RUN_LOGs, and the prior static audit). Nothing is inferred. Missing information is left blank.

### 5a. QPF platform (`program_scope: QPF_PLATFORM`)

| historical_id | title | status / decision | canonical evidence path | traceability |
|---|---|---|---|---|
| `EXP-2026-01-VOL-FORECAST-OVERLAY` | ML volatility-forecast sizing overlay (price features) | closed; historical STOP superseded to **HOLD** by 04B | `quant-personal-fund/experiments/EXP-2026-01-VOL-FORECAST-OVERLAY/experiment.yaml` | MEDIUM |
| `EXP-2026-02-MACRO-VOL-OVERLAY` | ML volatility overlay (FRED macro features, continuous de-risk) | HOLD, superseded by `EXP-2026-03` | `quant-personal-fund/docs/RESEARCH_PROGRESS.md` (no artifact folder) | LOW |
| `EXP-2026-03-SELECTIVE-DERISK-OVERLAY` | Selective top-decile de-risk overlay (macro features) | closed; **STOP** | `quant-personal-fund/experiments/EXP-2026-03-SELECTIVE-DERISK-OVERLAY/` | HIGH |
| `EXP-2026-04A-BENCHMARK-FOUNDATION` | Benchmark remediation (USD conversion, financing single-charge, Benchmark A/B) | complete; **PASS** (foundation stage) | `quant-personal-fund/experiments/EXP-2026-04A-BENCHMARK-FOUNDATION/` | HIGH |
| `EXP-2026-04B-STRATEGY-RERUNS` | Verdict-validity reruns on Benchmark B | complete (awaiting review); Trend HOLD, EXP-01 HOLD, EXP-03 STOP; none beats Benchmark B | `quant-personal-fund/experiments/EXP-2026-04B-STRATEGY-RERUNS/` | HIGH |
| `EXP-2026-05-INVALIDATION-REVERSAL` | Exit-and-reverse vs exit-and-flat after M15 invalidation (XAUUSD) | closed; **STOP** | `quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/` | HIGH |

### 5b. Legacy program (`program_scope: LEGACY_FRIVAL_ML`)

| historical_id | title | status / decision | canonical evidence path | traceability |
|---|---|---|---|---|
| `EXP-2026-03-RULEENGINE` | Gold rules engine (automated A/B level-test, Claim C) | closed — measurement failure; REJECTED (never traded) | `ml-signal-service/docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md` | MEDIUM |
| `EXP-2026-04-RULEENGINE-FX-BACKTEST` | Gold A/B rules transferred to FX | closed; REJECTED (negative EV/R on all pairs) | `ml-signal-service/docs/experiments/EXP-2026-04-RULEENGINE-FX-BACKTEST.md`; `frival/fx_rules_backtest/results/SUMMARY.md` | MEDIUM |
| `EXP-2026-05-EURUSD-SELL-COSTLABEL` | Directional H1 ML, EURUSD SELL, cost-adjusted label | resolved; **HOLD** | `ml-signal-service/experiments/EXP-2026-05-EURUSD-SELL-COSTLABEL/RUN_LOG.md` | HIGH |
| `EXP-2026-06-EURUSD-BUY-COSTLABEL` | Directional H1 ML, EURUSD BUY, cost-adjusted label | closed; **STOP** | `ml-signal-service/experiments/EXP-2026-06-EURUSD-BUY-COSTLABEL/RUN_LOG.md` | HIGH |
| `EXP-2026-07-CROSSES-COSTLABEL` | FX crosses as diversification (same label) | aborted; REJECTED (arithmetic handicap) | `ml-signal-service/experiments/EXP-2026-07-CROSSES-COSTLABEL/RUN_LOG.md` | HIGH |
| `EXP-2026-08-EQUITY-INDEX-COSTLABEL` | Directional ML on equity index (US30) | closed; **STOP** | `ml-signal-service/experiments/EXP-2026-08-EQUITY-INDEX-COSTLABEL/RUN_LOG.md` | HIGH |
| `EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN` | US30 label-geometry redesign (TP2.0/SL1.0) | closed — hypothesis falsified; **STOP** | `ml-signal-service/experiments/EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN/RUN_LOG.md` | HIGH |
| `EXP-2026-10-GOLD-EXIT-MANAGEMENT` | Mechanical exits on manual gold entries (operator-SL-anchored) | closed; **STOP** (confounded) | `ml-signal-service/experiments/EXP-2026-10-GOLD-EXIT-MANAGEMENT/experiment.yaml` | HIGH |
| `EXP-2026-11-GOLD-EXIT-ATR` | ATR-anchored mechanical exits on the same entries | closed; **STOP** (robustness) | `ml-signal-service/experiments/EXP-2026-11-GOLD-EXIT-ATR/` | HIGH |
| `EXP-2026-12-CROSS-SECTIONAL-MOMENTUM` | Weekly cross-sectional relative-strength momentum | closed; REJECTED (effect ≈ 0 in recent regimes) | `ml-signal-service/experiments/EXP-2026-12-CROSS-SECTIONAL-MOMENTUM/RUN_LOG.md` | HIGH |
| `EXP-2026-13-EVENT-DRIVEN` | Scheduled macro surprise → 1/4/24h price response | closed; **HOLD** (FX null; XAUUSD regime-only) | `ml-signal-service/experiments/EXP-2026-13-EVENT-DRIVEN/RUN_LOG.md` | HIGH |
| `EXP-2026-14-VOLATILITY-TIMING` | CALM vs VOLATILE regime trade-EV | closed; REJECTED | `ml-signal-service/experiments/EXP-2026-14-VOLATILITY-TIMING/RUN_LOG.md` | MEDIUM |

> Legacy evidence paths live outside `quant-personal-fund/`. They are recorded here for
> identification only; see `docs/falsification_ledger/LEGACY_INDEX.md` for how to locate them.

---

### 5c. Future QPF (`program_scope: FUTURE_QPF`)

| future_id | family | title | status / decision | canonical evidence path | traceability |
|---|---|---|---|---|---|
| `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION` | `RV` | EURUSD–GBPUSD Cointegration Viability Falsification | `preregistered`; decision `NONE` — viability falsification only, no results available, no execution authorized | `experiments/QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION/experiment.yaml` | pre-registered / no data accessed |

> This is the only reserved future-QPF identifier. It is a pre-registration only; it is not an
> approved strategy and authorizes no data work, computation, or execution.

---

## 6. Adding a new experiment (summary)

1. Choose a `QPF-<FAMILY>-<YEAR>-<SEQUENCE>-<SLUG>` identifier and confirm it is not already
   present in this registry.
2. Pre-register `experiments/<id>/experiment.yaml` from `experiments/_template/experiment.yaml`
   with `program_scope: FUTURE_QPF` and a completed `lineage` block.
3. Follow the lifecycle and status taxonomy in `experiments/README.md` and
   `docs/governance/EXPERIMENT_MANIFEST_SPEC.md`.
4. Record the verdict in `docs/decisions/DECISION_LOG.md`.

Machine-readable companion: `experiments/REGISTRY.yaml` (same records, list form).
