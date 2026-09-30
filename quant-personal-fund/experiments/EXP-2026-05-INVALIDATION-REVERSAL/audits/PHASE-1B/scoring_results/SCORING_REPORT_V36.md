# Historical Performance Scoring Report — v3.6 (Corrected)

**Date:** 2026-09-25  
**Status:** **COMPLETE.** Prior v3.5 scoring marked INVALID; v3.6 short-stop corrected and re-scored.

---

## 1. Prior Scoring — INVALID

The prior scoring output (`SCORING_RESULTS.json`, `SCORING_REPORT.md`, `scored_*.csv`) is **INVALID — short-stop condition defect** (v3.5 line 308: `bar["low"] <= short_stop`). It is not evidence for or against the reversal hypothesis. It remains labeled invalid and is not used here.

## 2. Fix Applied (v3.6, surgical)

| Item | v3.5 (BUG) | v3.6 (FIX) |
|---|---|---|
| Short stop condition | `if bar["low"] <= short_stop` | `if bar["high"] >= short_stop` |
| Gap handling | — | open ≥ stop → exit at adverse open; else high ≥ stop → exit at stop price; cost once |

Preserved exactly: stop level, next-bar execution, 12-bar time exit, forced-session exit, cost model, episode definitions, sample, reason codes, bootstrap design, 4 scenarios.

## 3. Inputs Hashes

| Input | SHA-256 (full) |
|---|---|
| v3.5 manifest | `a1a9a990eabe4cbabc42b669e88d8486e0c1e7001794c6052e0cf3d5ac4c3f5d` |
| v3.6 manifest | `(see SCORING_REPRODUCIBILITY_V36.json)` |
| v3.5 ledger | `df7a98b6125a9097182dc192907bc2475ce7bdbe1ec642cad4cadc7f20e7d645` (unchanged) |
| engine_v36.py | `(see manifest)` |
| score_engine / bootstrap | `(see manifest)` |
| m15/h1 data | `(see manifest)` |

Full hashes in `scoring_results/SCORING_REPRODUCIBILITY_V36.json`.

## 4. Exit-Type Decomposition (C1 shorts)

| Window | Time exits (12 bars) | Stop/forced (<12) | Hold dist |
|---|---|---|---|
| Development (359 c1) | **282** | 77 | 12:282, 3:20, 9:10, 8:10, 1:7, 6:7 |
| OOS (382 c1) | **297** | 85 | 12:297, 2:24, 3:14, 5:11, 8:9, 1:9 |

**The defective 1-bar pattern (739/741) is gone.** The corrected engine now exercises the frozen stop/time/forced exits properly.

## 5. Results (Primary Endpoint: mean incremental ΔR over A-vs-B denominator)

### Development (1,863 eligible: 359 c1 / 1,462 no_c1 / 42 rollover)

| Scenario | mean ΔR | 6h CI | P(>0) | PF (diag) |
|---|---|---|---|---|
| Base | **+0.0322** | [0.0001, 0.0633] | **0.975** | 1.444 |
| 2× spread | +0.0295 | [−0.0027, 0.0606] | 0.966 | 1.398 |
| 2× slippage | +0.0308 | [−0.0014, 0.0620] | 0.970 | 1.421 |
| Combined | +0.0282 | [−0.0042, 0.0593] | 0.958 | 1.376 |

### Research-Grade OOS (1,692 eligible: 382 c1 / 1,270 no_c1 / 40 rollover)

| Scenario | mean ΔR | 6h CI | P(>0) | PF (diag) |
|---|---|---|---|---|
| Base | **−0.0208** | [−0.0499, 0.0074] | 0.083 | 0.766 |
| 2× spread | −0.0231 | [−0.0521, 0.0053] | 0.062 | 0.745 |
| 2× slippage | −0.0220 | [−0.0509, 0.0064] | 0.072 | 0.756 |
| Combined | −0.0242 | [−0.0532, 0.0043] | 0.052 | 0.735 |

**Block sensitivity (base, 6h primary):**
- Development: 3h [−0.0006, 0.0655], 12h [0.0000, 0.0611] — 6h/12h lower bound ≈ 0.
- OOS: 3h [−0.0488, 0.0078], 12h [−0.0514, 0.0056] — all negative-leaning.

## 6. Diagnostic: Top-5 Contributions (base)

From `scored_*_v36.csv` (per window per scenario).

## 7. Reconciliation (population unchanged)

| Check | Result |
|---|---|
| v3.6 episode population == v3.5 | ✅ (test: identical entry/reason/invalidation/c1/short-entry indices; reason distributions equal) |
| Denominator dev 1,863 / OOS 1,692 | ✅ |
| c1/no_c1/rollover counts unchanged | ✅ |
| Reason codes exhaustive/mutually exclusive | ✅ |
| Prior integrity tests pass | ✅ |

## 8. Decision Labels

- **`development_result`:** POSITIVE mean ΔR (+0.032 R base), CI lower bound ≈ 0 at 6h/12h, P(>0) 0.96–0.98, PF > 1.37. **Promising in-sample.**
- **`research_grade_oos_result`:** NEGATIVE mean ΔR (−0.021 R base), CI straddles 0 (upper bound +0.007), P(>0) 0.05–0.08, PF < 1. **Not supportive.**
- **`HOLD`** — the development/OOS split is **opposite in sign**, and OOS (research-grade, not sealed) is negative. Per the frozen decision rules, a GO requires forward validation and cannot be issued on these results. The correct label is **HOLD (development positive, OOS negative — unresolved)**. No STOP is issued because development shows a robust positive signal that the OOS window does not confirm; no GO is issued because OOS is negative and unsealed.

**No strategy GO, no deployment, no trading recommendation.**

## 9. Confirmations

- ✅ No MT5 retrieval, broker/account calls, login(), orders, terminal/process/settings changes, or `frival/` modifications.
- ✅ No changes to v3.5 manifest, ledger, or prior scoring artifacts.
- ✅ No new signal rules, thresholds, filters, or strategy variants; no tuning.
- ✅ v3.6 changes ONLY the short-stop condition + gap handling.

*Stopped. Awaiting explicit approval before any further research or operational step.*