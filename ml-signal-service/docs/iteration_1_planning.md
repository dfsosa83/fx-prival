# EURUSD H1 Signal System — Preliminary Scope & Planning

*Internal planning document · July 13, 2026 · Status: Iteration 1 in progress*

---

## 1. Y₁ Target Definition & Success Criteria

**What the model predicts:** At every hourly bar close, the model answers a single binary question:

> *If we entered long right now with a 1:1.5 risk-to-reward trade (TP = 1.5× ATR above entry, SL = 1.0× ATR below entry), would price hit Take Profit before Stop Loss within the next 6 hours?*

- **Label = 1:** TP hit first — historically favorable entry.
- **Label = 0:** SL hit first, or timeout with no resolution — unfavorable entry.

ATR (14-period Average True Range) is used as a volatility ruler rather than fixed pip targets, ensuring TP/SL adapt to current market conditions.

**Success criteria for Iteration 1:**

| Criterion | Threshold | Measurement |
|---|---|---|
| Signal precision on sealed test set | ≥ 0.400 (breakeven at R:R 1:1.5) | Precision = TP hits ÷ total signals |
| Signal frequency | ≥ 0.15 signals/day | Total signals ÷ trading days |
| Decision traceability | Every signal logged with gate-by-gate reason | Decision log CSV audit trail |

## 2. Project Timeline

| Phase | Deliverable | Target |
|---|---|---|
| **Iteration 1** (current) | BUY-only signal model validated on sealed test set | Jul 14–18 |
| **Iteration 2** | Multi-agent validation layer (Perplexity + GPT-4o) | Jul 21–25 |
| **Iteration 3** | Production alert emitter + scheduling | Jul 28–Aug 1 |
| **Iteration 4** | Live paper trading (no real capital) | Aug 4+ |

Iteration 1 is in its final validation week. Preliminary results are below breakeven on the test set; configuration tuning and optional feature/model refinement are in progress before the iteration closes.

## 3. Planned Components

### Completed (Iteration 1 core)

| Component | Description |
|---|---|
| BUY LightGBM model | 22 selected features, trained on 2019–Jun 2025 data |
| SELL LightGBM model | 19 features, used only as cross-filter (not for standalone signals) |
| Signal combiner pipeline | BUY-only mode with 4 decision gates: threshold → cross-filter → session → cooldown |
| Decision log | Full trace CSV (46K bars): buy_proba, sell_proba, TP, SL, gate reason per bar |

### In Design / Planned

| Component | Iteration | Description |
|---|---|---|
| Perplexity validation agent | 2 | Web-enabled LLM: confirms/rejects signals via multi-pillar analysis (technical, fundamental, sentiment, news, correlation) |
| GPT-4o evaluation agent | 2 | Independent LLM evaluation from a different provider — eliminates single-vendor bias |
| Rules engine | 2 | Combines base model, Perplexity, and GPT decisions → final action with confidence tier |
| Senior agent validator | 2 | GPT-4o risk review layer: validates logic, risk/reward, stop placement before any execution decision |
| Alert emitter | 3 | Structured JSON alert files with entry/TP/SL/confidence, dedup tracking, alert history |
| Hourly scheduler | 3 | Windows Task Scheduler trigger at :01 past each hour |
| Paper trading executor | 4 | Simulated execution with PnL tracking, no real capital at risk |

## 4. Analytical Methodology

**Data pipeline:**
```
MT5 H1 CSV (2019–Jul 2026)
    → 86 engineered features (technical indicators, D1 context, session flags)
    → Feature selection via noise-injection voting (RF + LightGBM + Logistic Regression consensus)
    → Nested cross-validation (GroupKFold by year, TimeSeriesSplit inner loop)
    → LightGBM classifier optimized for PR-AUC
    → Threshold calibration at precision-recall breakeven
```

**Validation discipline:**
- Train/Val/Test split: 2019–Jun 2025 / Jul 2025–Jan 2026 / Feb 2026–Jul 2026
- Feature selection fit on training set only (no leakage)
- Test set is sealed — only opened once for final evaluation per iteration
- All signals logged with per-gate reason for full auditability

**Decision gates (applied post-inference, no retraining needed):**
1. **Threshold:** buy_proba ≥ 0.678 (model-calibrated)
2. **Cross-filter:** suppress if sell_proba ≥ 0.60 (ambiguous bar)
3. **Session filter:** London (07:00–15:59 UTC) + NY (13:00–21:59 UTC) only
4. **Cooldown:** max 1 signal per 4 bars (prevents clustering)

## 5. Iteration Targets

| Iteration | Target | Success metric |
|---|---|---|
| 1 | BUY-only model clears breakeven on sealed test | Precision ≥ 0.400 |
| 2 | Multi-agent validation reduces false positive rate by ≥ 10% | % of base model signals rejected by agents with correct reasoning |
| 3 | Alert system runs autonomously for 1 week with zero missed/silent failures | 100% scheduled run success rate |
| 4 | Paper trading PnL trends positive over a 2-week window | Sharpe > 0, max drawdown < 5% |

---

*This document is a planning artifact. Final Iteration 1 results will be shared upon completion of ongoing configuration testing.*