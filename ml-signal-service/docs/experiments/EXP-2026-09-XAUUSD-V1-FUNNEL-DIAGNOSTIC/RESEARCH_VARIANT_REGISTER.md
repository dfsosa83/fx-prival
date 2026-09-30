# RESEARCH VARIANT REGISTER — EXP-2026-09

**Status:** research hypotheses only. **None of these has been applied to
production**, and none may be applied without a separate, explicit
authorization and its own walk-forward validation stage.

These variants are **pre-registered from the funnel finding** (see
`V1_FREQUENCY_DECISION.md`). Each changes **exactly one mechanism** of the
frozen V1 engine. No variant may be selected on the basis of its historical
result; selection must come from a pre-registered walk-forward protocol.

## Guardrails (unchanged across all variants)

- 0.01 lot; ≤ $25/trade; ≤ 1 concurrent position; ≤ $50/day.
- Minimum R:R gate stays at its frozen value.
- Candle-close confirmation is **not** removed.
- No new instruments, no new timeframes.
- FX and XAUUSD stay separate strata.
- No live execution in any variant stage.

## Variants

### V2_CONFIRM_WINDOW
- **Single change:** increase only `confirm_max_bars_m15` from `3` to a
  pre-declared candidate set `{6, 8}`.
- **Runtime:** the confirm-extreme must be broken within this many M15 bars.
- **Rationale reference:** `CONFIRMATION_TIMEOUT` share of `CONFIRMED` in the
  funnel result.
- **Status:** hypothesis; not applied.

### V3_RETEST_WINDOW
- **Single change:** increase only `pending_retest_max_bars_m15` from `20` to a
  pre-declared candidate set `{28, 32}`.
- **Runtime:** the retest-rejection must occur within this many M15 bars.
- **Rationale reference:** `RETEST_TIMEOUT` count in the funnel result.
- **Status:** hypothesis; not applied.

### V4_CLAIM_C_SEPARATE
- **Single change:** retain the A/B branch unchanged and test the existing
  Claim-C breakout-continuation branch as its **own** hypothesis, preserving its
  existing gates and independent attribution (comment `GOLD_RULES_C`).
- **Runtime:** no parameter change; only the experimental framing/attribution.
- **Rationale reference:** the A/B-vs-C split in the funnel result.
- **Status:** hypothesis; not applied.

## Explicitly not recommended

Changing lot size; increasing maximum risk; loosening the daily-loss cap;
lowering the minimum R:R; removing candle-close confirmation; adding instruments
or timeframes; combining multiple changes; selecting a parameter because it
looked best historically.

## Promotion rule

A variant may move to a separate walk-forward validation stage only after it is
pre-registered from the funnel finding, with its own frozen protocol and its own
explicit authorization. Until then, V1 remains the frozen production engine and
is unchanged.
