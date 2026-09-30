# Audit Report — AUDIT-2026-09-23-PHASE-5-5

**Title:** Data, Benchmark, Cost, and Accounting Audit  
**Date:** 2026-09-23  
**Type:** Analysis-only, non-invasive, append-only  
**Final Recommendation:** **REMEDIATE**

---

## 1. Executive Summary

The Phase 5.5 audit traced the equal-weight benchmark and the four active-strategy verdicts (trend HOLD, carry/value HOLD, ML vol price STOP, ML vol selective STOP) from input data through position construction, turnover, cost deduction, and final reporting.

**Headline result:** the negative verdicts are **directionally supported** by the traced accounting, but their **magnitudes are not final**. Two confirmed blocking issues — missing base-currency conversion (H9) and financing double-charge (H1) — plus a benchmark definition clarification (H5) and the complete absence of confidence intervals (S1) require a controlled remediation rerun before any verdict is relied upon.

**Crucially:** the audit did NOT find that the active strategies were mis-implemented such that their negative results are pure artifacts. The accounting chain is mechanically consistent (metrics recompute exactly; cost/turnover reconcile). The negative results are real under the current implementation — but that implementation has representation and cost-model defects that must be corrected before the results are decision-grade.

---

## 2. Findings by Area

### 2.1 Benchmark Definition (Step c)

- **VERIFIED:** `equal_weight()` emits 1/N on every date; `compute_portfolio` computes turnover on weight diffs → reported turnover 0.0000 is correct.
- **VERIFIED:** Benchmark cost/gross 0.2962 = 100% daily holding cost (0.1414 NAV units over 11 years) on 8 instruments with `financing_annual_pct > 0`. No transaction cost.
- **VERIFIED:** The benchmark is **continuously rebalanced toward 1/N**, NOT buy-and-hold. The name "equal-weight" obscures this.
- **BLOCKING (H5):** benchmark definition must be stated as rebalanced equal-weight; a buy-and-hold variant would have different drift behavior.
- **VERIFIED:** First-entry transaction cost is NOT charged (first weight-diff is NaN → 0). Costs are slightly understated.
- **VERIFIED:** Benchmark gross return +47.7% cumulative: Equity +25.4%, Commodity +19.2%, Bonds +5.8%, FX +0.19%.

### 2.2 Asset Representation (Step b, f)

- **BLOCKING (H9):** 4 of 18 instruments (SX5E, NKY, BUND, JGB) have local-currency returns with **no USD conversion** anywhere in the pipeline. For a USD-based investor they are economically incomparable.
- **VERIFIED:** The 8 FX pairs are USD-quoted (EURUSD, GBPUSD, etc.) or approximately USD-comparable for daily returns (USDJPY, EURJPY).
- **VERIFIED (H2):** All returns use Yahoo `adj_close` (dividend-adjusted for equity); closer to total-return than raw index, but not a true total-return index.
- **VERIFIED (H3):** Bond leg is heterogeneous: yield-proxy (US10Y), ETF (BUND), REIT (JGB) — three different economic objects under one "govt_bond" label.
- **REPORTED (H2b):** Orphan `2644.T_daily.parquet` exists (old JGB ticker); not loaded by current config (verified not read by `load_and_validate` since JGB now uses 1343.T).
- **VERIFIED:** Common range inner-join discards ~100–180 rows/instrument; minor sample loss.

### 2.3 Cost and Turnover (Step d, e)

- **BLOCKING (H1):** Financing double-charge confirmed — `round_trip_cost_pct` (non-FX) = `2*commission + daily_holding_cost_pct` AND `compute_portfolio` charges daily hold cost. Affects SPX, NDX, SX5E, US10Y, BUND, NKY, JGB on turnover events.
- **VERIFIED:** Benchmark NOT double-charged (zero turnover → only daily path fires).
- **VERIFIED:** Cost waterfall per sleeve: trend cost/gross 97.9% (txn 0.0846 + hold 0.0687); carry/value 703.7% (txn 0.391, FX has no hold cost).
- **VERIFIED:** Trend txn cost concentrated in EURJPY (0.043) and USDJPY (0.034) — spread-driven, not a bug.
- **VERIFIED (H4):** FX swap = 0 for all 8 pairs. Carry verdicts are net of zero swap — economically wrong for a carry strategy.
- **VERIFIED:** Costs charged only on weight changes (unlagged); positions lagged 1 day → cost timing is conservative.

### 2.4 Trend and Carry/Value Implementation (Step g)

- **VERIFIED:** No look-ahead — signals use rolling windows through date t; positions lag 1 day; ML labels shifted forward.
- **VERIFIED (H7):** Trend sleeve gross exposure mean 0.644 → ~36% cash residual from cap (0.15) + renormalize. Handicaps trend vs benchmark.
- **VERIFIED:** Cap respected (max weight 0.1500, 12 float-boundary rows at 0.15).
- **VERIFIED:** 2,503 signal sign-flips drive daily turnover; carry signal is near non-directional (45% long / 47% short of days) — a weak signal, verified, not an accounting artifact.

### 2.5 Data Quality and Provenance (Step f)

- **VERIFIED:** All 19 parquet files load; completeness ≥ 99.96% per instrument.
- **VERIFIED:** Dates normalized to naive (tz_localize(None)) at load.
- **VERIFIED:** WTI has exactly 1 non-positive close (Apr 2020) → NaN returns, handled.
- **ASSUMPTION (H8):** Futures roll jumps in front-month series (GC=F, CL=F, HG=F) not isolated; no roll cost applied.

### 2.6 Statistical / Reporting (Step h, i)

- **VERIFIED:** Metrics recomputation matches reported values exactly (annualized return, vol, Sharpe, max DD).
- **VERIFIED:** 252-period annualization, rf=0, consistent sample dates across all sleeves.
- **BLOCKING (S1):** No bootstrap CI on any verdict. Benchmark daily-mean 95% CI includes zero at all block lengths ([−0.000057, +0.000304] at block=10). Serial dependence confirmed (CI widens with block).
- **VERIFIED:** LOO — no single asset dominates (max effect WTI +0.10 Sharpe). LACO — commodity leg drives Sharpe (0.271 without commodities); dropping FX or Bonds improves it.

---

## 3. Classification Summary

| Classification | Count | IDs |
|---|---|---|
| VERIFIED (directly from source/artifact) | 16 | H1, H2, H3, H4, H5, H6, H7, H2c, all Step c/e/f/g/h/i trace items |
| REPORTED (in docs, not independently verified) | 1 | H2b (2644.T exclusion) |
| ASSUMPTION (unresolved) | 1 | H8 (futures roll jumps) |

---

## 4. Recommendation

**REMEDIATE**

The equal-weight benchmark and the negative active-strategy verdicts are **mechanically valid under the current implementation** but **not decision-grade** because of:
1. Missing base-currency conversion (H9) — 4 instruments economically incomparable for a USD investor.
2. Financing double-charge (H1) — sleeve costs overstated.
3. Benchmark definition clarification (H5) — rebalanced, not buy-and-hold.
4. No confidence intervals (S1) — point estimates only.

A controlled remediation rerun (new hashes, same pre-registered gates, append-only history) is required before any verdict is relied upon. No strategy recommendation, Phase 6 recommendation, or claim of reopening/closing research families is made by this audit.

---

## 5. Artifacts

| Artifact | Path |
|---|---|
| Manifest | `audits/AUDIT-2026-09-23-PHASE-5-5/audit_manifest.yaml` |
| Run log | `audits/AUDIT-2026-09-23-PHASE-5-5/RUN_LOG.md` |
| Inputs hash | `audits/AUDIT-2026-09-23-PHASE-5-5/inputs_hash.json` |
| Decision | `audits/AUDIT-2026-09-23-PHASE-5-5/DECISION.md` |
| Diagnostics | `audits/AUDIT-2026-09-23-PHASE-5-5/diagnostics/*.json` and `*.csv` |
| Reports | `audits/AUDIT-2026-09-23-PHASE-5-5/reports/` (this file) |