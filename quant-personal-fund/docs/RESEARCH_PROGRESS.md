# Research Progress Record

**Platform:** Quant Personal Fund (`quant-personal-fund/`)  
**Maintained from:** 2026-09-22  
**Purpose:** Chronological record of research hypotheses, experiments, results, verdicts, and methodology decisions. This is the platform's institutional memory — it must never be deleted.

---

## 1. Program Context

### Origin

This platform was built after the legacy H1 directional FX ML project ("frival") completed Q4 2026 research with **zero demonstrated edge** across 8+ experiments. The legacy program's strengths were methodological (block-bootstrap CI, pre-registration, sealed tests, GO/HOLD/STOP gates, audit reflex). Its failures were structural (triple-barrier hit/miss labels at H1 on technical features cannot convert ranking skill into breakeven precision).

### Governing Constraint

The new platform is **portfolio-level, multi-asset, risk-first**. It is not a collection of trading bots. Closed research families must not be reopened through incremental parameter variation. See `docs/falsification_ledger/no_edge_map.md` for the authoritative list.

### The Benchmark

The equal-weight portfolio across 18 global assets (8 FX, 4 equity indices, 3 bond proxies, 3 commodities) is the null hypothesis and the benchmark:

| Metric | Value (2015-01-05 to 2026-09-18) |
|---|---|
| Annualized Return | +2.40% |
| Annualized Volatility | 6.13% |
| Sharpe Ratio | 0.53 (full), 1.06 (2024-01-01 onward) |
| Max Drawdown | −16.7% |
| Annualized Turnover | 0.0× |
| Cost / Gross PnL | 29.6% |

**Every active strategy tested has failed to beat this net of costs.** That is the central finding of Phase 3–5, confirmed across 10 pre-registered experiments. As of EXP-2026-03 (2026-09-23), the entire tested active-strategy space — trend, FX carry/value, and ML volatility overlays across two information sources and three mechanisms — is closed. Any future research requires a new economic mechanism, not a new parameterization.

---

## 2. Infrastructure Delivered

| Phase | Deliverable | Status |
|---|---|---|
| **Phase 0** | Architecture decision (ADR-001), legacy audit, falsification ledger | Complete |
| **Phase 1** | Instrument master (18 instruments), core library (returns, volatility, bootstrap, costs, hashing), governance docs, data contracts | Complete — 101 tests |
| **Phase 2** | Portfolio accounting engine, exposure decomposition, risk metrics, backtest engine, reporting | Complete — 174 tests |
| **Phase 3** | Multi-asset trend signal, scaling, builder, rebalancing | Complete — 189 tests |
| **Phase 4** | FX carry + value signals | Complete — 198 tests |
| **Phase 5** | ML overlays: features, noise-voting selection, vol forecast, sizing, FRED macro | Complete — 225 tests |

**Current test count: 225 passing.**

---

## 3. Experiment Log

### EXP-2026-01 — ML Volatility-Forecast Overlay (price features)

| Field | Value |
|---|---|
| **Date** | 2026-09-23 |
| **Hypothesis** | Lagged price features predict forward 30-day vol; de-risking on the forecast beats passive |
| **Setup** | LightGBM, noise-voting selection, train 2015–22 / val 2023 / test 2024–26 |
| **Result** | Sharpe 0.27 full / 0.69 test (baseline 0.53 / 1.06). Max DD −19.1%. Cost/gross 60.5% |
| **Verdict** | **STOP** — reactive features, cost dominance |
| **Falsification entry** | Family 7 (closed) |

### EXP-2026-02 — ML Volatility-Forecast Overlay (FRED macro features)

| Field | Value |
|---|---|
| **Date** | 2026-09-23 |
| **Hypothesis** | FRED macro conditions (rates, term spread, VIX, CPI, unemployment) contain volatility information that price features lack |
| **Setup** | Same model + FRED macro features (leakage-safe: daily lag 1d, monthly +45d publication buffer) |
| **Result** | Sharpe 0.33 full / 0.83 test. Max DD −19.2%. Cost/gross 54.5%. Macro features selected 11–18 per instrument — **information confirmed present** |
| **Verdict** | **HOLD** — information real, mechanism (continuous de-risking) too blunt |
| **Falsification entry** | Family 8 (hold) |

### EXP-2026-03 — Selective De-Risking Overlay

| Field | Value |
|---|---|
| **Date pre-registered** | 2026-09-23 |
| **Hypothesis** | De-risk ONLY in the top decile of forecast vol (confident elevated regime) instead of continuously; the information from EXP-2026-02 becomes exploitable when the mechanism is selective |
| **Change vs EXP-2026-02** | Sizing rule only: scale = 0.5 at forecast-vol ≥ 90th percentile of trailing 252d; else 1.0. Features, model, splits, costs frozen |
| **Result (sealed run)** | Full Sharpe **0.35** (gate ≥ 0.55), max DD **−19.1%** (gate > −0.167), cost/gross 50.4% (gate < 0.545). Test Sharpe 0.77 vs baseline 1.06 |
| **Verdict** | **STOP** — cost/gross PASSED, but Sharpe and drawdown FAILED the pre-registered gate |
| **Falsification entry** | Family 8 closed (supersedes HOLD) |

**Excerpt from the sealed run log (2026-09-23):**
- 16 instruments had sufficient data for training.
- De-risk days per instrument ranged 74–383 (of 881–2524 forecast days) — the top-decile rule fired ~10–15% of days as designed.
- Selective de-risking improved cost/gross vs continuous (50.4% vs 54.5%) but did not improve drawdown (−19.1% vs −19.2%) or beat the baseline Sharpe (0.35 vs 0.53).
- Pre-registered STOP gate triggered on two of three criteria.

---

## 5. Cumulative Strategy Results

All results are net-of-cost, 2015-01-05 to 2026-09-18, 18 instruments, monthly rebalancing unless noted.

| Strategy | Ann Ret | Sharpe | Max DD | Turnover | Verdict |
|---|---|---|---|---|---|
| Equal-weight (benchmark) | +2.40% | 0.53 | −16.7% | 0.0× | **Benchmark** |
| Trend long-only (daily) | −0.15% | −0.04 | −11.7% | 26.6× | HOLD |
| Trend long-only (weekly) | −0.24% | −0.07 | −13.1% | 18.4× | HOLD |
| Trend long-only (monthly) | −0.39% | −0.10 | −14.9% | 14.5× | HOLD |
| Trend long/short (monthly) | −2.67% | −0.68 | −32.3% | 25.9× | HOLD |
| FX carry/value (monthly) | −1.88% | −0.42 | −27.4% | 47.9× | HOLD |
| ML vol overlay (price) | +1.20% | 0.27 | −19.1% | — | **STOP** |
| ML vol overlay (macro, continuous) | +1.52% | 0.33 | −19.2% | — | HOLD → STOP |
| ML vol overlay (macro, selective) | +1.59% | 0.35 | −19.1% | 19.0× | **STOP** |

### Year-by-year (Trend L/S, net)

| Year | Return | Vol | Sharpe | DD |
|---|---|---|---|---|
| 2016 | +1.25% | 4.2% | +0.39 | −4.0% |
| 2017 | −3.05% | 3.8% | −1.01 | −3.4% |
| 2018 | −2.28% | 5.0% | −0.57 | −6.8% |
| 2019 | −5.88% | 3.0% | −2.62 | −7.7% |
| 2020 | −4.15% | 5.1% | −1.06 | −8.5% |
| 2021 | −1.27% | 3.5% | −0.44 | −3.4% |
| 2022 | −0.18% | 7.0% | +0.00 | −8.3% |
| 2023 | −3.64% | 4.5% | −0.99 | −7.2% |
| 2024 | −5.47% | 3.6% | −2.03 | −7.2% |
| 2025 | −4.41% | 5.4% | −1.09 | −7.0% |

---

## 5. Methodology Decisions (Recorded)

| # | Decision | Rationale | Date |
|---|---|---|---|
| M1 | Naive dates interpreted as UTC; per-instrument session close not modeled | Multi-week horizons make intraday timezone mismatch immaterial | 2026-09-22 |
| M2 | Bond instruments use constant-duration zero-coupon proxy (Option b) | Simple, transparent, directionally correct for trend | 2026-09-22 |
| M3 | Costs are centralized in `config/cost_model.yaml`; always non-negative; 1.5× conservative spread multipliers | Prevent sign errors; cost stress is explicit | 2026-09-22 |
| M4 | Lag = 1 trading day between weight signal and execution | Conservative; no same-day close leakage | 2026-09-22 |
| M5 | Equal-weight is the null hypothesis and benchmark | No active strategy may be accepted without beating it net of costs | 2026-09-23 |
| M6 | ML is restricted to risk-management targets (vol, correlation, drawdown, sizing) | Price-direction prediction is a closed family | 2026-09-23 |
| M7 | Noise-voting feature selection (3-model, 5 strategies) applies to regression targets via linear-regression importances | Preserves the legacy methodology's overfitting guard | 2026-09-23 |
| M8 | FRED monthly series shifted by 45-day publication buffer before use | Guarantees no look-ahead on CPI/unemployment | 2026-09-23 |
| M9 | Every experiment requires a pre-registered GO/HOLD/STOP gate, set before running | Prevents threshold-walking after results | 2026-09-23 |

---

## 6. Data Provenance

| Dataset | Source | Coverage | Notes |
|---|---|---|---|
| Daily OHLCV (18 instruments) | Yahoo Finance | 2015-01-05 to 2026-09-18 | Adjusted close; FX has bid/ask OHL artifacts (warnings, not errors) |
| DGS3MO, DGS10, T10Y3M, VIXCLS | FRED | 2014-01-01 to present | Daily; lagged 1 day |
| CPIAUCSL, UNRATE | FRED | 2014-01-01 to present | Monthly; shifted 45 days |
| JGB proxy | Yahoo `1343.T` | 2015-01-05 to present | Japanese ETF proxy (REIT), not pure JGB |
| BUND proxy | Yahoo `IGLT.L` | 2015-01-02 to present | iShares Euro Govt Bond ETF |

### Known Data Issues

1. **WTI negative prices** (April 2020): produce NaN log returns; handled gracefully.
2. **FX OHL inconsistencies**: Yahoo bid/ask artifacts; OHL checks downgraded to warnings.
3. **JGB/BUND are ETF proxies**, not pure government bond yield series. The `data_type: yield` flag only applies to US10Y (`^TNX`).
4. **Common date range** limited by JGB (2015+) and BUND (2015+); all instruments have ≥2,600 trading days.

---

## 7. Next Steps (Decision Pending)

| Option | Description | Trigger |
|---|---|---|
| **Proceed to Phase 6** | Accept passive equal-weight as the operating portfolio; shadow portfolio with execution measurement | Recommended — all active-strategy families now closed (Family 9) |
| **Defensive-rotation overlay** | De-risk into bonds/USD instead of cash (new mechanism) | New hypothesis; requires user decision to pre-register |
| **Correlation/drawdown target** | New risk quantity for the ML overlay | New hypothesis; requires user decision to pre-register |
| **Risk-parity base portfolio** | Different base than equal-weight | New hypothesis; requires user decision to pre-register |

---

## 8. Repository Map (Key Files)

| Path | Content |
|---|---|
| `docs/falsification_ledger/no_edge_map.md` | Authoritative falsification ledger (Families 1–8 + cross-cutting lessons) |
| `docs/adr/ADR-001-platform-architecture.md` | Architecture decision record |
| `experiments/EXP-2026-01-VOL-FORECAST-OVERLAY/experiment.yaml` | Pre-registration: price-only vol overlay |
| `experiments/EXP-2026-03-SELECTIVE-DERISK-OVERLAY/experiment.yaml` | Pre-registration: selective de-risking (pending) |
| `config/universe.yaml` | 18-instrument universe definition |
| `config/cost_model.yaml` | Centralized cost assumptions |
| `scripts/phase3_analysis.py` | Phase 3 analysis (baseline, trend, lookback sweep) |
| `scripts/phase5_ml_overlay.py` | Phase 5 price-only overlay |
| `scripts/phase5b_macro_overlay.py` | Phase 5b macro overlay |
| `scripts/download_fred_macro.py` | FRED macro downloader |

---

*This document is maintained as the program's institutional memory. Never delete. Add new entries, never rewrite history.*

---

## Addendum — EXP-2026-04A (2026-09-23)

### What happened

The Phase 5.5 audit returned REMEDIATE with confirmed blocking issues (H9 base-currency, H1 financing double-charge, H5 benchmark convention). User approved EXP-2026-04A (foundation) with mandatory amendments (one-way cost API, explicit event timeline, exposure/cash semantics, two-stage 04A/04B gate).

### Result

- **Verdict: PASS** (foundation stage only). 273 tests pass.
- Active universe corrected to **15 instruments** (US10Y, BUND, JGB excluded, raw data archived).
- **USD conversion implemented** with material impact: NKY −370 bps, EURJPY −238 bps annualized vs local returns.
- **Benchmark B (monthly rebalanced, PRIMARY):** annualized return +3.20%, vol 6.72%, Sharpe 0.503, max DD −20.6%.
- **Benchmark A (buy-and-hold):** +3.82%, 9.68%, 0.435, −23.4%.
- **Financing double-charge fixed** — costs now >98% daily-holding (H1 corrected, verified by test).
- Supplementary moving-block CIs added; max drawdown reported as observed episodes only.
- EXP-2026-04B (strategy reruns) is **gated on user approval** of the 04A report.

### Files

`experiments/EXP-2026-04A-BENCHMARK-FOUNDATION/reports/{FINAL_REVIEW_REPORT.md, EXECUTION_SUMMARY.md, stats.json, benchmark_*_nav.csv, trades_B.csv, cost_waterfall.csv, attribution*.csv, loo_laco.json, usd_conversion_impact.json, reproducibility_hashes.json}`

---

## Addendum — EXP-2026-04B (2026-09-23)

### What happened

Verdict-validity rerun of the frozen trend, EXP-2026-01, and EXP-2026-03 sleeves under the corrected 15-instrument USD accounting and Benchmark B (04A foundation). Frozen parameters, historical gates, and splits unchanged.

### Result

- **294 tests pass** (273 + 21 new).
- **Trend:** Sharpe 0.259 vs B 0.503 — prior underperformance **confirmed**; selection-driven (analytical exposure-matched reference shows exposure is not the cause).
- **EXP-2026-01:** Sharpe 0.502 at parity with B → corrected-accounting relative gate **HOLD** (prior STOP **superseded**).
- **EXP-2026-03:** literal historical gate → **STOP** (max DD −25.9% ≤ −0.167); corrected comparison reported separately and does not alter the verdict.
- **No sleeve beats Benchmark B.** Financing sensitivity (A 0× / B 1× / C 0.5× / D 1.5×) reported; verdicts from Scenario B only.
- All 04B stop conditions passed; no blocking issues.

### Files

`experiments/EXP-2026-04B-STRATEGY-RERUNS/reports/{FINAL_REVIEW_REPORT.md, EXECUTION_SUMMARY.md, VERDICT_MATRIX.md, REPRODUCIBILITY_MANIFEST.json, stats.json, *_nav.csv, attribution.csv, year_by_year.csv, financing_sensitivity.json}`