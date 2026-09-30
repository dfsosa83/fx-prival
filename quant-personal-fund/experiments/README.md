# Experiments

Pre-registered research experiments with immutable artifacts.

## Lifecycle

```
preregistered → in_progress → completed → closed
```

1. **PRE-REGISTER:** File `experiment.yaml` with hypothesis, universe, signal, cost model, validation design, metrics, decision gate, and robustness checks. Compute `inputs_hash`. No code touches the test set.
2. **IMPLEMENT:** Write signal/portfolio code in the appropriate module. Build the experiment runner.
3. **SCORE ONCE:** Run against the sealed test period. Record results in `RUN_LOG.md`.
4. **ROBUSTNESS:** Apply all mandatory checks. A positive result that fails any check is non-robust.
5. **DECIDE:** Apply pre-registered GO/HOLD/STOP gate. Do not re-score. Do not adjust thresholds post-hoc.
6. **CLOSE:** Document the verdict, failure mechanism, or next steps.

## Folder Structure

```
experiments/EXP-YYYY-NN-NAME/
├── experiment.yaml          # Pre-registration manifest
├── RUN_LOG.md               # Chronological execution log
├── inputs.hash              # SHA256 of frozen inputs
└── reports/                 # Generated outputs (gitignored)
    ├── test_metrics.json
    ├── test_signals.csv
    ├── robustness_report.json
    └── attribution.html
```

## Hard Rules

- **No re-scoring.** If a bug is found, supersede with a new experiment ID and new sealed window.
- **No threshold-walking.** The decision gate is defined before scoring.
- **No GO without robustness.** All mandatory checks must pass.
- **Inputs are immutable.** `inputs_hash` is verified before scoring; mismatch aborts.

See `docs/governance/EXPERIMENT_MANIFEST_SPEC.md` for the full manifest specification.

## Status Taxonomy

Historical statuses are unchanged. The lifecycle below applies to every experiment.

**QPF lifecycle (historical and continuing):**

```
preregistered -> in_progress -> completed -> closed
```

**Future-QPF research decision states:** `GO`, `HOLD`, `STOP`, `PAUSE`.

- **`STOP` + `closed`** freezes the hypothesis and its sealed result. It cannot be re-opened by
  parameter changes, threshold changes, time-frame changes, or re-scoring. A new hypothesis must
  be materially distinct and separately pre-registered (see
  `docs/falsification_ledger/LEGACY_INDEX.md` §4).
- **`HOLD`** means the evidence is inconclusive. It is not evidence of approval and not a license
  to trade.
- **`PAUSE`** means insufficient data, a missing capability, or unresolved governance.
- **`GO`** does not authorize execution. It authorizes only the next explicitly pre-registered
  research phase.
- A future live/shadow/demo workflow requires separate, explicit governance and must not be
  inferred from these states.

Identifiers, the future QPF namespace, and the program-scope legend are defined in
`experiments/REGISTRY.md`. Decisions are recorded in `docs/decisions/DECISION_LOG.md`.