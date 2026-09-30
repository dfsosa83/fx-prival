# DECISION — AUDIT-2026-09-23-PHASE-5-5

**Date:** 2026-09-23
**Status:** COMPLETE
**Recommendation:** **REMEDIATE**

---

## Final Recommendation

### REMEDIATE

Confirmed blocking implementation and representation issues require a controlled rerun before the negative active-strategy verdicts and the equal-weight benchmark can be relied upon.

**Rationale (see findings below):**
- H9 (base-currency conversion) is confirmed as a blocking representation issue: 4 of 18 instruments (SX5E, NKY, BUND, JGB) have local-currency returns with no USD conversion, making them economically incomparable for a USD-based investor. This affects the benchmark's Equity and Bond legs and every sleeve that includes them.
- H1 (financing double-charge) is confirmed: financing is charged inside `round_trip_cost_pct` AND daily in `compute_portfolio` for the 7 financed instruments. This overstates costs on turnover-heavy sleeves.
- H5 (benchmark cost/gross reconciliation) is verified as mechanically correct (100% holding cost, zero txn), but the benchmark is REBALANCED equal-weight, not buy-and-hold — and its Sharpe CI includes zero.

These are implementation/representation issues requiring a controlled remediation rerun under new hashes, not evidence that the active-strategy families are definitively dead or alive.

---

## Blocking Findings

| ID | Finding | Classification | Evidence |
|---|---|---|---|
| H9 | **No base-currency conversion for SX5E, NKY, BUND, JGB** — local-currency returns enter the portfolio unconverted | VERIFIED (source: `backtest/engine.py::_compute_returns_panel`, `portfolio/accounting.py`) | `step_b_base_currency.json`, `instrument_representation.csv` |
| H1 | **Financing double-charge** — `round_trip_cost_pct` embeds `daily_holding_cost_pct` AND `compute_portfolio` charges it daily; affects 7 financed instruments on turnover events | VERIFIED (source: `core/costs.py`, 3-day synthetic trace) | `step_d_financing_double_charge.json` |
| H5 | **Benchmark definition** — equal-weight is CONTINUOUSLY REBALANCED (1/N daily), not buy-and-hold; reported turnover 0 is correct (verified) but benchmark is a daily-rebalanced strategy, not passive | VERIFIED (source: `portfolio/builder.py::equal_weight`, `compute_portfolio`) | `step_c_benchmark_reconcile.json` |
| S1 | **No statistical CI on any verdict** — manifests declare `bootstrap_resamples` but no experiment report contains a bootstrap CI; benchmark daily-mean CI includes zero at all block lengths | VERIFIED (search of `experiments/*.yaml` + `block_bootstrap_ci`) | `step_h_stats_review.json` |

## Non-Blocking Findings

| ID | Finding | Classification | Evidence |
|---|---|---|---|
| H2 | Equity index returns use Yahoo `adj_close` (dividend-adjusted) — closer to total-return than raw index; NOT a true total-return index | VERIFIED (source: `dataset.py`, `_compute_returns_panel`) | `step_f_provenance.csv` |
| H3 | Bond leg heterogeneous: yield-proxy (US10Y), ETF (BUND), REIT (JGB) — economically inconsistent | VERIFIED (config + instrument master) | `instrument_representation.csv` |
| H4 | FX swap = 0 for all pairs — carry/value verdicts are net of zero swap, which is economically wrong for a carry trade | VERIFIED (source: `config/cost_model.yaml`) | — |
| H6 | Turnover computed on unlagged weights; positions lagged 1 day — cost timing offset is conservative | VERIFIED (source: `portfolio/accounting.py`) | — |
| H7 | Trend sleeve cash residual ~36% (gross exposure 0.64 mean) — cap + renormalize creates cash drag; handicaps sleeve vs benchmark | VERIFIED (source: `scaling.py`, trace) | `step_g_impl_trace.json` |
| H8 | Futures roll jumps in front-month series, no roll cost applied | ASSUMPTION (source of roll jumps not isolated) | — |
| H2b | `2644.T_daily.parquet` orphan file exists (old JGB ticker) — not loaded by current config | REPORTED (unverified exclusion) | `step_f_provenance.csv` |
| H2c | Common range inner-join discards ~100–180 rows/instrument | VERIFIED (row counts) | `step_f_provenance.csv` |

---

## Findings Requiring Note

- **Benchmark Sharpe is not statistically distinct from zero** (daily-mean CI includes zero at block=10: [−0.000057, +0.000304]). The +2.4%/yr is a point estimate with wide uncertainty.
- **Benchmark is robust but concentrated:** LOO shows no single asset dominates (max effect WTI +0.10); LACO shows commodity leg drives Sharpe (0.271 without commodities).
- **Benchmark cost/gross 0.2962 is 100% holding cost** — the financing rates in `config/cost_model.yaml` (SPX 5%, NDX 5%, etc.) directly produce it. These rates are ASSUMED (not broker-confirmed).

---

## What This Means

1. The **negative active-strategy verdicts** (trend HOLD, carry/value HOLD, ML overlays STOP) are **directionally supported** but their **magnitudes are not final** due to H1 (sleeve cost overstatement) and H9 (incomparable instruments).
2. The **equal-weight benchmark** is mechanically valid but: (a) is a rebalanced strategy (not buy-and-hold as the name might imply), (b) depends on assumed financing rates for its cost, (c) includes 4 local-currency instruments, and (d) has no CI — its Sharpe could be zero.
3. **No strategy recommendation, Phase 6 recommendation, or claim of reopening/closing research families is made by this audit.** The only permitted output is the recommendation above.

## Remediation Scope (for a controlled rerun, if approved)

1. **Base-currency conversion (H9):** convert SX5E, NKY, BUND, JGB returns to USD via a USD cross-rate series before portfolio accounting; timestamp-align to local-market close.
2. **Financing single-charge (H1):** remove `daily_holding_cost_pct` from `round_trip_cost_pct` (transaction cost = commissions only); keep daily hold cost in `compute_portfolio`.
3. **Decision-grade financing (H4):** populate FX swap with broker data or mark carry verdicts explicitly as "net of zero swap."
4. **Bond homogeneity (H3):** implement ADR-002 (all-ETF, all-yield-proxy, or remove bond leg).
5. **Statistical reporting (S1):** add block-bootstrap CIs to all verdict reports.
6. Re-run the benchmark and affected sleeves end-to-end under NEW hashes; re-evaluate against the SAME pre-registered gates; preserve prior results as append-only.

*No changes to strategy parameters, signals, or model architecture are in scope for remediation.*

---

## Remediation Pointer (append-only, 2026-09-23)

EXP-2026-04A-BENCHMARK-FOUNDATION was implemented per this audit's REMEDIATE recommendation and the approved constrained remediation plan (with user amendments). Verdict: **PASS (foundation stage)**. See:

`experiments/EXP-2026-04A-BENCHMARK-FOUNDATION/reports/FINAL_REVIEW_REPORT.md`

Confirmed blocking findings from this audit (H9, H1, H5) are addressed and tested. EXP-2026-04B (strategy reruns) is gated on user approval of the 04A report. This audit's decision is REMEDIATE → resolved for the foundation scope; no strategy verdict change is implied.