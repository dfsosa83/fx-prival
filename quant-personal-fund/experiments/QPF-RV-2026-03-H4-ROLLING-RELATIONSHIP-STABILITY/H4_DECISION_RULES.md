# H4 — Decision Rules

**Stage:** `H4_ROLLING_RELATIONSHIP_STABILITY_DESIGN`

---

## Decision tree

```text
Hash/input failure                                  → PAUSE_ROLLING_STATISTICAL_VIABILITY
No validation W meets pre-registered selection gate → REJECT_ROLLING_STATISTICAL_VIABILITY
Validation-selected W fails sealed confirmation     → REJECT_ROLLING_STATISTICAL_VIABILITY
Selected W passes both validation and sealed gates  → APPROVE_ROLLING_STATISTICAL_VIABILITY (statistical viability only)
```

## Definitions

- **PAUSE** — a technical data/integrity failure (e.g. snapshot hash/schema/row validation). No
  statistical conclusion is drawn; the candidate is not rejected.
- **REJECT** — the candidate fails validation selection (no W meets the gate) or the selected W fails
  sealed confirmation.
- **APPROVE** — the selected W passes **both** validation selection and sealed confirmation.

## Statements

- **Approval permits only a separate future design of a cost-aware economic test.**
- It does **not** mean the pair is profitable or tradable.
- It does **not** authorize G2, G4, G5, G6, execution, or capital allocation.
- **Rejection applies only to the tested pair / orientation / H1 / H4 design.**
- A rejection does not reject pairs trading generally, and does not allow retuning W, E, the
  eligibility gate, thresholds, orientation, or the split.
- The next candidate proceeds only under the identical frozen protocol; the sealed segment is never
  used to choose parameters.
