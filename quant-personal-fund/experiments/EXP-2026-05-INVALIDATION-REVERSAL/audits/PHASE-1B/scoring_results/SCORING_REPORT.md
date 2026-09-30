# Historical Performance Scoring Report — EXP-2026-05

**Date:** 2026-09-24  
**Status:** **HOLD — SHORT-LEG ENGINE DEFECT FOUND. The scored reversal result is NOT a valid test of the frozen v3.5 Policy B short.**

---

## 1. Executive Finding

**The v3.5 engine's short-exit condition is defective: line 308 of `engine/engine_v35.py` uses `bar["low"] <= short_stop`, but for a SHORT position the stop is ABOVE entry, so the correct stop condition is `bar["high"] >= short_stop`.**

Because `low <= short_stop` is satisfied on nearly every bar (a bar's low is almost always below the stop level above it), **739 of 741 c1_triggered shorts exited on bar 1** (hold = 1 bar). The 12-bar time exit, forced-session exit, and the stop as designed were **never actually exercised** for shorts. The scored "short" is effectively an unconditional **1-bar scalp after C1** — not the frozen policy.

**This defect predates the scoring phase** (same line exists in the v3.3/v3.4/v3.5 engines) and is surfaced now only because shorts are being scored for the first time.

**Consequence:** the historical performance result computed here is **not a valid test of Policy B**. Per the authorization, I am stopping and reporting rather than fixing the engine or re-scoring a modified policy.

---

## 2. Preliminary Scores (INVALID — reported for completeness only)

These were computed on the defective short-exit behavior. **They must not be used as a verdict on the reversal hypothesis.**

### Development (1,863 eligible: 359 c1 / 1,462 no_c1 / 42 rollover)

| Scenario | mean ΔR | 6h CI | P(>0) | PF (diag) |
|---|---|---|---|---|
| Base | −0.0032 | [−0.019, +0.013] | 0.359 | 0.914 |
| 2× spread | −0.0056 | [−0.021, +0.011] | 0.261 | 0.854 |
| 2× slippage | −0.0044 | [−0.020, +0.012] | 0.309 | 0.884 |
| Combined | −0.0068 | [−0.023, +0.010] | 0.219 | 0.826 |

### Research-grade OOS (1,692 eligible: 382 c1 / 1,270 no_c1 / 40 rollover)

| Scenario | mean ΔR | 6h CI | P(>0) | PF (diag) |
|---|---|---|---|---|
| Base | −0.0113 | [−0.030, +0.008] | 0.120 | 0.741 |
| 2× spread | −0.0135 | [−0.032, +0.005] | 0.080 | 0.700 |
| 2× slippage | −0.0124 | [−0.031, +0.007] | 0.096 | 0.720 |
| Combined | −0.0146 | [−0.033, +0.004] | 0.066 | 0.680 |

**All mean ΔR are negative with CIs straddling zero** — but this reflects the 1-bar-scalp behavior, not the frozen stop/time policy. **No strategy conclusion is drawn.**

---

## 3. Defect Detail

| Item | Value |
|---|---|
| File | `engine/engine_v35.py` line 308 |
| Code | `if bar["low"] <= short_stop:` |
| Correct for short | `if bar["high"] >= short_stop:` (price must RISE to the stop above) |
| Evidence | 739/741 c1_triggered have hold == 1 bar; the other 2 hold 5 bars; **0 time-exits (12 bars)** |
| Impact | The frozen stop, 12-bar time exit, and forced-session exit were never exercised for shorts |

**The defect also exists in the v3.3 and v3.4 engines** (same `bar["low"] <= short_stop` pattern) — it is a pre-existing implementation error, not introduced by v3.5.

---

## 4. Why the Defect Changes the Result

A correct short stop (`high >= stop`) would let some shorts run to 2–12 bars and hit the time exit or the forced-session exit, producing a **materially different** PnL distribution than the 1-bar scalp. The negative mean ΔR here could become positive or more negative under the correct engine — **unknowable without a corrected re-score**, which is not authorized.

---

## 5. Integrity Checks (performed, all passed)

| Check | Result |
|---|---|
| No excluded/censored episode in scoring | ✅ (test) |
| no_c1/rollover_ineligible zero ΔR, in denominator | ✅ (test) |
| Policy A/B long exit identical | ✅ (test) |
| Cost scenarios alter only multipliers | ✅ (test) |
| Cluster keeps shared-invalidation together | ✅ (test) |
| Bootstrap deterministic | ✅ (test, seed 42) |
| No performance fields in score engine output | ✅ (test) |
| Input hashes recorded | ✅ `SCORING_REPRODUCIBILITY.json` |
| Test suite | 12/12 scoring integrity tests pass; full suite 307 + 12 = **319 passed** |

---

## 6. Required Correction (not applied — awaiting approval)

To obtain a valid test of the frozen Policy B short, a **v3.6 engine correction** is required:

1. **Fix the short-stop condition** to `bar["high"] >= short_stop` (for shorts).
2. **Re-run the v3.5 ledger episode identification** (no other changes) — the episode set should be unchanged (cost and exit don't affect episode identification).
3. **Re-score** all four scenarios with the corrected short exit.
4. **Re-run all integrity tests** (the "1-bar exit" pattern should disappear; time/forced exits should appear).

This is a **correction, not a tuning** — the frozen policy's intended short exit (stop when price rises to stop; else time exit at 12 bars; else forced pre-window) is only expressible with the corrected condition.

---

## 7. Confirmations

- ✅ **No performance metrics were used to alter rules, choose parameters, or claim a GO.**
- ✅ No MT5 retrieval, broker/account calls, login(), terminal/process/settings changes, `frival/` modifications, or orders.
- ✅ No files modified (scoring artifacts and this report are new; CSV/engine/manifests unchanged).
- ✅ The erratum for the v3.5 report was created (documentation-only).

## 8. Decision Labels

- **`development_result`:** INVALID (short-leg defect) — not reportable as a hypothesis verdict.
- **`research_grade_oos_result`:** INVALID (short-leg defect) — not reportable.
- **`HOLD`:** the reversal hypothesis cannot be evaluated until the v3.6 short-exit correction is applied and re-scored. No STOP/GO/promising label is issued because the current scores do not test the frozen policy.

---

*Stopped. Awaiting approval to implement the v3.6 short-exit correction and re-score.*