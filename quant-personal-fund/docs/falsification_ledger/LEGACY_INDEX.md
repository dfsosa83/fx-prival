# Legacy Index — Pointer to Preserved Legacy Research

**Status:** Governance reference (Phase 0.5 — Traceability and Execution Isolation)
**Nature:** Pointer-only. This file copies, moves, rewrites, and re-scores nothing.

This index tells a reader where the legacy (pre-QPF) research artifacts live and what each
family concluded, without relocating any of them. The authoritative falsification record is
`docs/falsification_ledger/no_edge_map.md`; this file only maps families to locations.

---

## 1. Where legacy material lives

| Root | Contains | Notes |
|---|---|---|
| `frival/` | Legacy execution/research code (e.g. `frival/gold_rules/`, `frival/fx_rules_backtest/`, `frival/execution_bot/`) | Outside QPF. Do not modify from Phase 0.5. |
| `ml-signal-service/` | Legacy experiment folders (`ml-signal-service/experiments/EXP-2026-…`), notebooks, model bundles, design docs and roadmaps under `ml-signal-service/docs/experiments/` | Outside QPF. Do not modify from Phase 0.5. |
| `quant-personal-fund/docs/falsification_ledger/no_edge_map.md` | The preserved, authoritative no-edge map (Families 1–8 + cross-cutting lessons + 04A/04B supersession pointers) | Inside QPF. Reference only. |

A QPF experiment that cites legacy work must cite these paths; it must not import, execute, or
alter the legacy code.

---

## 2. Legacy experiment families (as documented)

Each family below is recorded in `docs/falsification_ledger/no_edge_map.md` with its mechanism of
failure. Identifiers are listed only to locate the evidence; they are immutable.

| Family | Theme | Documented legacy experiment IDs | Evidence location |
|---|---|---|---|
| Family 1 | Directional H1 FX/index ML (triple-barrier hit/miss labels) | `EXP-2026-05-EURUSD-SELL-COSTLABEL`, `EXP-2026-06-EURUSD-BUY-COSTLABEL`, `EXP-2026-08-EQUITY-INDEX-COSTLABEL`, `EXP-2026-09-US30-LABEL-GEOMETRY-REDESIGN`, `P0.2 retrofit` | `ml-signal-service/experiments/…`; `quant-personal-fund/docs/falsification_ledger/no_edge_map.md` (Family 1) |
| Family 2 | FX crosses as diversification (same label) | `EXP-2026-07-CROSSES-COSTLABEL` | `ml-signal-service/experiments/EXP-2026-07-CROSSES-COSTLABEL/`; `no_edge_map.md` (Family 2) |
| Family 3 | Manual gold trading + mechanical exit optimization | Manual account record; `EXP-2026-10-GOLD-EXIT-MANAGEMENT`, `EXP-2026-11-GOLD-EXIT-ATR` | `ml-signal-service/experiments/EXP-2026-10-…`, `…/EXP-2026-11-…`; `no_edge_map.md` (Family 3) |
| Family 4 | Cross-sectional momentum (weekly relative strength) | `EXP-2026-12-CROSS-SECTIONAL-MOMENTUM` | `ml-signal-service/experiments/EXP-2026-12-…`; `no_edge_map.md` (Family 4) |
| Family 5 | Macro-event reaction (scheduled surprise → price) | `EXP-2026-13-EVENT-DRIVEN` | `ml-signal-service/experiments/EXP-2026-13-…`; `no_edge_map.md` (Family 5) |
| Family 6 | Gold rules engine (automated A/B level-test) | `EXP-2026-03-RULEENGINE` | `ml-signal-service/docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md`; `frival/gold_rules/`; `no_edge_map.md` (Family 6) |
| (transfer) | Gold rules engine transferred to FX | `EXP-2026-04-RULEENGINE-FX-BACKTEST` | `ml-signal-service/docs/experiments/EXP-2026-04-RULEENGINE-FX-BACKTEST.md`; `frival/fx_rules_backtest/results/SUMMARY.md` |
| Family 7 | ML volatility-forecast sizing overlay (price features) | `EXP-2026-01-VOL-FORECAST-OVERLAY` (QPF-scoped label) | `no_edge_map.md` (Family 7) |
| Family 8 | ML volatility-forecast sizing overlay (FRED macro features) | `EXP-2026-02-MACRO-VOL-OVERLAY`, `EXP-2026-03-SELECTIVE-DERISK-OVERLAY` | `no_edge_map.md` (Family 8) |

Note: Families 7–8 use QPF-platform identifiers; they are listed here because the no-edge map
preserves them as part of the continuous research lineage.

---

## 3. Non-reopening rule — `EXP-2026-05-INVALIDATION-REVERSAL`

`EXP-2026-05-INVALIDATION-REVERSAL` is a **QPF** experiment, currently **CLOSED / STOP**
(`quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/FINAL_VERDICT.json`).

It must **not** be rerun, tuned, re-scored, deployed, demo-tested, or forward-validated, and it
must **not** be followed up under the same hypothesis. Its closure explicitly prohibits any
new hypothesis, variant, ML, or follow-up derived from it.

This rule is distinct from the similarly numbered **legacy** `EXP-2026-05-EURUSD-SELL-COSTLABEL`
(HOLD). The two share a number but are different experiments; see
`experiments/REGISTRY.md` §1.

---

## 4. Reopening requires a materially distinct, newly pre-registered hypothesis

A closed family may only be revisited by a **new** experiment that:

1. Uses a **new identifier** under the future QPF namespace
   `QPF-<FAMILY>-<YEAR>-<SEQUENCE>-<SLUG>` (see `experiments/REGISTRY.md` §3).
2. Carries a **new pre-registration** (`experiments/_template/experiment.yaml`) whose
   `hypothesis.why_existing_results_do_not_already_reject_it` field cites the relevant
   `no_edge_map.md` entry.
3. Demonstrates **material distinction** — a genuinely different economic mechanism,
   information source, and evaluation framework — not a parameter, threshold, time-frame, or
   re-scoring variation. This must be recorded in the manifest's
   `lineage.materially_distinct_from` field, which is mandatory when the new experiment is
   adjacent to a STOP/CLOSED experiment.
4. Defines its own `decision_gate` (GO/HOLD/STOP) **before** any code touches the sealed test set.

A different currency pair, threshold, classifier, or ATR multiplier is not a new hypothesis.

---

## 5. Related references

- `docs/falsification_ledger/no_edge_map.md` — authoritative family record + supersession pointers.
- `experiments/REGISTRY.md` — identifier governance and the future QPF namespace.
- `docs/decisions/DECISION_LOG.md` — append-only decision record.
- `docs/governance/EXPERIMENT_MANIFEST_SPEC.md` — manifest requirements.
