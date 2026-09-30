# Data-Source Provenance Template

**Status:** Stage 1A governance standard  
**Date:** 2026-09-25

---

## Purpose

Every data field used in research must have a documented origin so that: (a) costs are not silently assumed, (b) revisions are traceable, and (c) the difference between measured, quoted, derived, and assumed values is explicit.

## Provenance Fields

For each instrument and each cost/price field, record:

| Field | Definition | Example |
|---|---|---|
| `field` | Which field this provenance describes | `spread` |
| `instrument` | Instrument or universe | `EURUSD` |
| `source` | Vendor / broker / derived / assumed | `mt5_symbol_info` |
| `source_date` | When the value was obtained | `2026-09-24` |
| `measurement_type` | `measured` / `quoted` / `derived` / `assumed` / `unresolved` | `measured` |
| `method` | How it was measured or derived | `live tick bid/ask spread × point` |
| `confidence` | `high` / `medium` / `low` | `high` |
| `timestamp` | UTC timestamp of the observation | `2026-09-24T18:00:00Z` |
| `missing_status` | `available` / `partial` / `unavailable` | `available` |
| `revision_policy` | How this value may change (e.g., daily, on broker update) | `per-session` |
| `notes` | Caveats | `points convention; price = pts × point` |

## Classification of Measurement Type

| Type | Meaning | Use |
|---|---|---|
| `measured` | Observed from a source (e.g., live tick bid/ask) | Decision-grade if source is authoritative |
| `quoted` | Reported by broker/vendor without independent verification | Provisional; mark `confidence` accordingly |
| `derived` | Computed from other measured values (e.g., spread_price = pts × point) | Document the formula |
| `assumed` | Placeholder or conservative estimate | **Never decision-grade**; mark `unresolved` until replaced |
| `unresolved` | Not obtainable from current sources | **Do not populate with arbitrary values** |

## Rules

1. **No arbitrary estimates.** A field with `missing_status: unavailable` or `measurement_type: unresolved` stays unresolved. It is never filled with a guess.
2. **FRED-class macro data is not carry data.** Policy rates / OIS may explain macro conditions; they do not provide executable FX forward/carry returns.
3. **Current values are not historical.** A current swap or spread does not establish a historical series. Historical series require their own provenance.
4. **Every cost field in the cost model carries a provenance block.** See the cost-model schema.

## Template File

Place one provenance record per instrument per field in:

```
data/reference/provenance/{instrument}_{field}.yaml
```

or as inline blocks in `config/cost_model.yaml` / dataset manifests where the field lives.