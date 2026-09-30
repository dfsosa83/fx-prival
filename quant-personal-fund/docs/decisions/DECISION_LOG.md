# Decision Log

**Status:** Governance reference (Phase 0.5 — Traceability and Execution Isolation)
**Nature:** Append-only. Entries are never edited or deleted; corrections are new entries that
reference the superseded one.

This log records research decisions (GO / HOLD / STOP / PAUSE) for QPF experiments. It is the
decision counterpart to the pre-registration manifest and the RUN_LOG: the manifest states what
was intended, the RUN_LOG records what happened, this log records the governing decision and its
follow-up constraints.

---

## Entry fields

| Field | Meaning |
|---|---|
| `date` | Decision date (`YYYY-MM-DD`). |
| `decision_id` | Unique decision identifier (e.g. `DEC-0001`). |
| `experiment_id` | The experiment the decision applies to (historical `EXP-…` or future `QPF-…`). |
| `program_scope` | `LEGACY_FRIVAL_ML` \| `QPF_PLATFORM` \| `FUTURE_QPF`. |
| `status_before` | Lifecycle status before the decision (`preregistered` \| `in_progress` \| `completed` \| `closed`). |
| `decision` | One of `GO` \| `HOLD` \| `STOP` \| `PAUSE`. |
| `evidence_paths` | Paths to the manifest, RUN_LOG, reports, and any sealed results. |
| `rationale` | Concise reason, tied to the pre-registered gate. |
| `owner` | Decision owner (person or role). |
| `immutable_artifacts` | Artifacts frozen by this decision (paths and any hashes). |
| `follow_up_constraints` | What is prohibited and what (if anything) is authorized next. |

---

## Decision semantics (governing)

- **`STOP` + `closed`** freezes the hypothesis and its sealed result. It cannot be re-opened by
  parameter changes, threshold changes, time-frame changes, or re-scoring. A new hypothesis must
  demonstrate material distinction and be separately pre-registered (see
  `docs/falsification_ledger/LEGACY_INDEX.md` §4).
- **`HOLD`** means the evidence is inconclusive. It is **not** an approval and **not** a license
  to trade, deploy, or forward-validate.
- **`PAUSE`** means insufficient data, a missing capability, or unresolved governance. It is a
  waiting state, not a result.
- **`GO`** does **not** authorize execution. It authorizes only the next explicitly
  pre-registered research phase.
- A future live/shadow/demo workflow requires separate, explicit governance and must never be
  inferred from any of these states.

---

## Entries

<!-- Append new entries below this line. Do not modify existing entries. -->

### Template (do not remove) — `DEC-0000`

```yaml
date: "YYYY-MM-DD"
decision_id: "DEC-0000"
experiment_id: "QPF-<FAMILY>-<YEAR>-<SEQUENCE>-<SLUG>"
program_scope: "FUTURE_QPF"
status_before: "completed"
decision: "HOLD"            # GO | HOLD | STOP | PAUSE
evidence_paths:
  - "experiments/<id>/experiment.yaml"
  - "experiments/<id>/RUN_LOG.md"
  - "experiments/<id>/reports/"
rationale: "<reason, tied to the pre-registered decision_gate>"
owner: "<owner>"
immutable_artifacts:
  - "experiments/<id>/experiment.yaml"
follow_up_constraints: "<what is prohibited / what is authorized next>"
```

_No real decisions are recorded in this Phase 0.5 file. This template entry is illustrative only
and corresponds to no experiment._
