# H6 — Screen Decision Matrix

**Stage:** `H6_SCREEN_ORCHESTRATION_DESIGN`

An approved configuration does **not** authorize economic testing automatically; it only permits a
**separately authorized economic-test design**. FX and XAUUSD are always separate strata.

| Condition | Per-configuration result | Stratum effect |
|---|---|---|
| Hash/schema/input failure (one snapshot) | n/a (not evaluated) | That stratum → `PAUSE_H6_<STRATUM>_STATISTICAL_VIABILITY`; other stratum proceeds |
| Numerical/technical failure during evaluation | n/a (not evaluated) | That stratum → PAUSE; other stratum proceeds |
| Insufficient events/controls | `NOT_TESTABLE_INSUFFICIENT_EVENTS` (retained; null p/rank/q) | Still counted in that family's completeness; no effect on the other stratum |
| No validation survivor | n/a | Stratum → `REJECT_H6_<STRATUM>_STATISTICAL_VIABILITY`; sealed not evaluated for it |
| Survivor(s), sealed failure (any class fails) | `REJECT_FAILED_BREAKOUT_STATISTICAL_VIABILITY` | Contributes to REJECT unless another selected config passes |
| Sealed pass (both classes, all criteria) | `APPROVE_FAILED_BREAKOUT_STATISTICAL_VIABILITY` | Stratum → `APPROVE_H6_<STRATUM>_STATISTICAL_VIABILITY` (≥1 pass) |
| FX approved, XAUUSD rejected | FX config APPROVE; XAUUSD config REJECT | FX APPROVE; XAUUSD REJECT (independent) |
| XAUUSD approved, FX rejected | XAUUSD config APPROVE; FX config REJECT | XAUUSD APPROVE; FX REJECT (independent) |
| Both rejected | REJECT each | FX REJECT; XAUUSD REJECT |
| Both approved | APPROVE each | FX APPROVE; XAUUSD APPROVE |

Notes:

- One decision is recorded **per selected configuration** (≤3 per stratum).
- A stratum is **approved** only if ≥1 selected configuration passes sealed.
- Any integrity/technical failure pauses **only the affected stratum** — it never silently removes an
  instrument.
- Approval permits only a **later cost-aware economic-test design** for that individual configuration.
  It establishes **no** PnL, profitability, execution feasibility, or trading authorization.
