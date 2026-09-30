# Quant Fund Blueprint
## Strategic Recommendations, Research Agenda, and Implementation Framework

**Date:** September 22, 2026  
**Purpose:** Provide a practical blueprint for building a disciplined quantitative investment platform using systematic strategies, machine learning, LLM-enabled research operations, and institutional-grade portfolio-risk controls.

---

## 1. Executive Summary

If the objective is to build an independent quantitative fund with a realistic chance of producing positive long-run returns, the starting point should **not** be another short-horizon FX direction-prediction model based primarily on OHLC, ATR, and technical indicators.

The recommended direction is to build a **systematic multi-asset portfolio platform** that combines several economically distinct return sources:

- Time-series trend following.
- FX carry.
- FX value.
- Equity-index trend.
- Rates and bond trend.
- Commodity trend.
- Volatility targeting.
- Portfolio-level risk management.
- Machine-learning overlays for regimes, volatility, correlations, and position sizing.
- LLM-enabled research, monitoring, documentation, and governance.

The central principle is:

> Do not build a fund around predicting the next price move. Build a diversified portfolio of imperfect but economically distinct signals, then manage risk, concentration, execution, and drawdowns better than average.

The completed FX H1 research should be treated as a valuable falsification record. It showed that, under the tested data, labels, costs, and horizons, no robust net edge survived realistic friction, out-of-sample evaluation, and robustness tests. The correct response is not to abandon quantitative research; it is to move to a more fund-like structure: lower turnover, broader diversification, stronger economic hypotheses, and portfolio-level risk control.

---

## 2. Strategic Positioning

### 2.1 Recommended fund identity

The most suitable initial identity is:

> **Diversified Systematic Macro / Multi-Asset Alternative Risk Premia Platform**

This does not require institutional scale on day one. It means designing the research and portfolio process around liquid markets, transparent signals, robust risk management, and reproducible evidence.

The initial objective should be to demonstrate a high-quality investment process rather than maximize early returns.

### 2.2 What not to build first

Avoid making the first product any of the following:

- A retail-style FX scalping bot.
- A high-frequency or market-making system.
- A short-horizon H1 direction classifier using only technical indicators.
- A deep-learning model trained only on OHLC data.
- A fully autonomous LLM trader.
- A volatility-selling strategy without deep options expertise.
- A broker-arbitrage or latency-arbitrage concept.
- A single-asset strategy dependent on one currency pair, one market regime, or one technical signal.

These approaches are usually highly competitive, fragile, expensive to execute, or vulnerable to overfitting.

---

## 3. How Professional FX and Macro Funds Differ

FX funds are not one homogeneous category. Different approaches require very different data, time horizons, execution capabilities, and controls.

| Fund style | Main objective | Typical horizon | Key inputs | Difficulty for a small fund |
|---|---|---:|---|---|
| Discretionary macro | Express views on policy, inflation, growth, and capital flows | Weeks to months | Macro, rates, central banks, positioning | Medium |
| Systematic macro | Trade rules across liquid global markets | Days to months | Prices, rates, macro, volatility | Medium |
| CTA / managed futures | Capture persistent trends across assets | Weeks to months | Liquid futures or reliable proxies | Medium |
| FX carry / value / momentum | Capture cross-sectional currency style premia | Weeks to months | Spot, forwards, rates, valuation measures | Medium |
| Relative value | Trade spreads, curves, basis, and linked instruments | Days to months | Curves, forwards, swaps, basis | High |
| Volatility / options | Trade implied-vs-realized volatility and skew | Days to months | Option surfaces and risk models | High |
| Market making / HFT | Capture microstructure and liquidity provision | Milliseconds to minutes | Tick data, order books, colocation | Very high |
| Event-driven macro | Trade price response to surprises | Minutes to days | Consensus, releases, timestamps | High |
| Dynamic hedging | Reduce portfolio risk while preserving expected return | Daily to weeks | Exposures, correlations, factor models | Medium |

For an independent quantitative platform, the most realistic starting points are:

- Systematic macro with low-to-medium turnover.
- Multi-asset trend following.
- FX carry, value, and trend portfolios.
- Dynamic hedging and portfolio-risk overlays.
- Execution-cost measurement and quality control.

---

## 4. Recommended Portfolio Architecture

The portfolio should be built as a set of sleeves, each with a distinct economic rationale and a defined risk budget.

| Sleeve | Economic mechanism | Typical horizon | Portfolio role | Initial priority |
|---|---|---:|---|---|
| Multi-asset time-series trend | Trend persistence and slow-moving macro flows | Weeks to months | Core return engine and diversifier | Very high |
| FX carry | Compensation for holding higher-yielding currencies | Weeks to months | Carry return source with crash controls | High |
| FX value | Mean reversion from long-run valuation dislocations | Months | Slow diversifier to trend and carry | High |
| Equity-index trend | Persistent directional equity-index moves | Weeks to months | Growth and risk-cycle exposure | High |
| Rates / bond trend | Monetary-policy, inflation, and growth trends | Weeks to months | Diversification and risk-off potential | High |
| Commodity trend | Inflation, supply-demand, and geopolitical trends | Weeks to months | Inflation and shock diversification | High |
| Volatility targeting | Dynamic scaling of portfolio exposure | Daily / weekly | Drawdown and leverage control | Mandatory |
| Portfolio risk overlay | Control of correlation, concentration, and tail risk | Daily | Capital preservation | Mandatory |
| ML regime overlay | Forecast regimes, volatility, and conditional risk | Daily / weekly | Improve sizing and allocation | Medium |
| LLM operations layer | Research, QA, reporting, and governance | Continuous | Operational scalability | Medium |

Do not launch all sleeves at once. Begin with three:

1. Multi-asset time-series trend.
2. FX carry/value at low frequency.
3. A robust risk engine for volatility, correlation, drawdown, and exposure control.

---

## 5. Recommended Initial Investment Universe

Start with 12 to 20 liquid instruments. The aim is genuine diversification without overwhelming the data, execution, and research process.

| Asset class | Example instruments | Why include them |
|---|---|---|
| G10 FX | EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, USDCHF, NZDUSD, EURJPY | Macro, rates, carry, and global risk exposure |
| Equity indices | S&P 500, Nasdaq 100, Euro Stoxx 50, Nikkei 225, FTSE 100 | Global growth and risk-on/risk-off exposure |
| Rates / government bonds | U.S. Treasury, Bund, Gilt, JGB futures or robust ETF proxies | Policy, inflation, growth, and defensive diversification |
| Commodities | Gold, crude oil, copper, broad commodity exposure | Inflation, supply shocks, global demand |
| Defensive exposures | USD, gold, duration proxies | Crisis and macro-risk diversification |

A practical first universe could include:

- 6 to 8 G10 FX pairs.
- 4 major equity indices.
- 3 government-bond or rate instruments.
- 3 liquid commodities.
- 1 to 2 global-risk or defensive proxies.

The final instruments depend on account access, legal structure, execution venue, financing, and data quality. The research architecture should remain instrument-agnostic where possible.

---

## 6. Core Strategy 1: Multi-Asset Time-Series Trend

### 6.1 Strategic rationale

Time-series trend following should be the first core sleeve because it is interpretable, broadly applicable, low-turnover relative to intraday trading, and naturally diversifiable across asset classes.

The basic hypothesis is that price trends can persist over medium horizons because of gradual information diffusion, policy repricing, institutional rebalancing, slow-moving macroeconomic conditions, and persistent investor flows.

### 6.2 Simple initial signal

For each asset \(i\):

\[
s_{i,t} = \operatorname{sign}(r_{i,t-L:t})
\]

Where:

- \(s_{i,t}\) is the direction signal.
- \(r_{i,t-L:t}\) is the cumulative return over a lookback window \(L\).

Use a small, economically defensible group of horizons rather than optimizing dozens of windows:

- 1 month.
- 3 months.
- 6 months.
- 9 months.
- 12 months.

A blended trend score can be formed using equal or fixed robust weights across these horizons.

### 6.3 Volatility scaling

Position sizing should be adjusted by estimated volatility:

\[
w_{i,t} \propto \frac{s_{i,t}}{\hat{\sigma}_{i,t}}
\]

Where \(\hat{\sigma}_{i,t}\) is an estimate of the asset’s recent volatility.

This prevents the most volatile instruments from dominating the portfolio merely because their nominal returns fluctuate more.

### 6.4 Main risks

Trend following can suffer during:

- Sideways or range-bound markets.
- Sharp reversals.
- Whipsaw regimes.
- Sudden policy shocks.
- Correlation spikes across risk assets.

The solution is not to use excessively tight stops. The solution is a portfolio-level framework that includes volatility targeting, diversification, concentration limits, and conditional de-risking during stress.

---

## 7. Core Strategy 2: FX Carry with Crash-Risk Protection

### 7.1 Strategic rationale

FX carry seeks compensation for holding higher-yielding currencies relative to lower-yielding currencies. In practice, the relevant measure should use forward-implied carry, forward points, or rate differentials rather than simplistic spot assumptions.

### 7.2 Initial construction

A basic carry sleeve can be constructed by:

1. Ranking currencies by forward-implied carry.
2. Going long the highest-carry basket.
3. Going short the lowest-carry basket.
4. Weighting positions by inverse volatility.
5. Controlling net USD exposure where appropriate.
6. Applying a risk-off or crash-risk filter.
7. Reducing gross exposure when market stress rises.

### 7.3 Carry risks

Carry can generate persistent returns during calm risk-on periods, but it is vulnerable to sudden losses when leveraged positions unwind. Key stress conditions include:

- Rapid increases in FX volatility.
- Equity-market drawdowns.
- Liquidity shocks.
- Credit-stress episodes.
- Sudden central-bank repricing.
- Sharp declines in high-carry currencies.

### 7.4 Recommended crash filters

Possible filters include:

- Elevated realized FX volatility.
- Elevated implied volatility.
- Large equity-index drawdowns.
- VIX or credit-spread stress.
- Rising cross-asset correlations.
- Sharp recent loss in the carry basket.
- Event-risk or central-bank-risk calendars.

Initially, use transparent rule-based filters. Only after the baseline is established should ML be tested as a conditional risk-scaling layer.

---

## 8. Core Strategy 3: FX Value

### 8.1 Strategic rationale

FX value is a long-horizon strategy based on the idea that currencies can deviate materially from longer-term economic anchors such as purchasing-power parity, real effective exchange rates, inflation differentials, or external-balance conditions.

It is not suitable for H1 or short daily holding periods. It should be evaluated on monthly or multi-week horizons.

### 8.2 Conceptual signal

\[
\text{FXValue}_{i,t} =
\frac{\log(S_{i,t}) - \log(FV_{i,t})}
{\hat{\sigma}_{\text{misalignment},i,t}}
\]

Where:

- \(S_{i,t}\) is observed spot.
- \(FV_{i,t}\) is an estimate of fair value.
- The signal measures the deviation between spot and fair value in standardized units.

### 8.3 Candidate inputs

- Purchasing-power parity measures.
- Real effective exchange rates.
- Relative inflation.
- Terms of trade.
- Current-account or external-balance proxies.
- Productivity and growth differentials.
- Long-run exchange-rate trend deviations.
- Positioning extremes.

### 8.4 Practical rules

- Rebalance monthly, not intraday.
- Treat value as a slow signal.
- Combine it with carry and trend.
- Do not assume cheap currencies immediately appreciate.
- Require long historical samples and stable data definitions.

---

## 9. Trend in Indices, Rates, and Commodities

A portfolio that only trades FX is exposed to a narrow set of risk drivers. Multi-asset diversification is one of the strongest structural improvements available to a small systematic manager.

| Asset class | Main economic drivers | Portfolio benefit |
|---|---|---|
| Equity indices | Growth, earnings, liquidity, risk appetite | Captures global growth cycles |
| Bonds / rates | Inflation, policy expectations, growth | Can diversify equity and FX risk |
| Commodities | Supply-demand, inventories, inflation, geopolitics | Adds inflation and shock sensitivity |
| FX | Relative rates, capital flows, risk sentiment | Global macro transmission channel |

The goal is not that each sleeve performs every year. The goal is that they are not all dependent on one market regime.

---

## 10. Portfolio Construction Framework

### 10.1 Think in risk budgets, not capital weights

A portfolio should not assign equal dollar amounts to each instrument. It should assign exposure based on expected volatility, correlation, liquidity, and marginal contribution to risk.

A possible initial risk-budget structure is:

| Sleeve | Initial risk budget | Function |
|---|---:|---|
| Multi-asset trend | 35% | Core diversified return engine |
| FX carry | 15% | Structural carry with risk filters |
| FX value | 10% | Slow macro diversifier |
| Equity-index trend | 15% | Growth and risk-cycle exposure |
| Rates / bond trend | 15% | Policy and risk-off diversification |
| Commodity trend | 10% | Inflation and supply-shock diversification |

These are risk budgets, not fixed capital allocations.

### 10.2 Portfolio volatility targeting

Scale total exposure toward a predefined annualized volatility target:

\[
\text{Leverage}_t =
\frac{\sigma_{\text{target}}}
{\hat{\sigma}_{\text{portfolio},t}}
\]

For an initial platform, a target annualized volatility of approximately 8% to 12% is more defensible than aggressive leverage.

### 10.3 Risk parity and concentration limits

Avoid allocating based only on historical Sharpe ratios. That tends to overfit.

Use:

- Equal-risk or capped-risk allocation across sleeves.
- Maximum risk by instrument.
- Maximum risk by asset class.
- Maximum net exposure by currency.
- Limits on contribution to Value-at-Risk or expected shortfall.
- Correlation monitoring.
- Liquidity and leverage constraints.

### 10.4 Currency exposure decomposition

Each FX pair should be decomposed into its base and quote currency exposures.

Examples:

- Long EURUSD = long EUR and short USD.
- Long USDJPY = long USD and short JPY.
- Short GBPUSD = short GBP and long USD.

This enables portfolio-level currency exposure measurement:

\[
E_{\text{USD}} = \sum_j w_j \cdot \beta_{j,\text{USD}}
\]

The main risk is hidden concentration. Long EURUSD, long GBPUSD, long AUDUSD, and short USDCHF may look like four positions but can represent one large short-USD thesis.

### 10.5 Initial limits

Possible starting limits include:

- Maximum risk per instrument: 5% to 10% of total risk budget.
- Maximum risk per asset class: 30% to 40%.
- Maximum contribution of one instrument to portfolio VaR: 10% to 15%.
- Maximum net currency exposure: defined in volatility-adjusted terms.
- Conservative gross leverage cap.
- Explicit liquidity limits by instrument and venue.

---

## 11. Drawdown Governance

Drawdown responses should be specified before deployment.

| Portfolio drawdown | Suggested action |
|---:|---|
| 0% to −5% | Normal operation |
| −5% to −8% | Reduce risk to 75% |
| −8% to −12% | Reduce risk to 50%; review exposures and correlations |
| −12% to −15% | Reduce risk to 25%; pause any scaling decisions |
| Below −15% | Halt scaling; perform full hypothesis, data, and execution review |

These thresholds should be calibrated to the eventual volatility target and expected strategy profile, but the response structure should always be predetermined.

---

## 12. Dynamic Hedging as an Institutional Strategy

Dynamic hedging is especially relevant for a portfolio-oriented FX platform.

The objective is not to predict whether one hedge pair will rise or fall. The objective is to reduce portfolio risk while preserving as much expected return as possible.

### 12.1 Example

Suppose the portfolio accumulates long EURUSD, long GBPUSD, long AUDUSD, and short USDCHF. Although these positions use different pairs, they may collectively create a large short-USD exposure.

A dynamic hedging engine should:

1. Identify net exposures by currency and macro factor.
2. Estimate current volatility and correlation risk.
3. Identify instruments capable of reducing concentrated exposure.
4. Compare expected risk reduction against hedge cost and return drag.
5. Apply a partial hedge only when the portfolio-level benefit is meaningful.

### 12.2 Correct target variable

The target should not be:

> Will USDJPY go up or down?

The target should be closer to:

> What hedge size minimizes expected shortfall, drawdown risk, or factor concentration while preserving an acceptable level of expected return?

This is a more institutional, more defensible, and potentially more valuable use of quantitative modeling than isolated pair prediction.

---

## 13. Where Machine Learning Should Be Used

Machine learning should primarily improve **risk decisions, conditional allocation, and operational quality**, not act as a generic next-candle predictor.

| ML application | Question answered | Potential value |
|---|---|---|
| Regime classification | Are markets in risk-on, risk-off, inflation, recession, or liquidity stress? | Conditional exposure control |
| Volatility forecasting | How much risk may the asset or portfolio have next week? | Better position sizing |
| Correlation forecasting | Which assets may stop diversifying under stress? | Avoid false diversification |
| Drawdown probability | Which sleeves have elevated downside risk? | Gross-exposure reduction |
| Signal combination | When do trend, carry, and value agree or conflict? | Better allocation |
| Feature stability | Which variables remain useful out of sample? | Lower overfitting risk |
| Transaction-cost prediction | When will spread/slippage make trading unattractive? | Better execution |
| Anomaly detection | Have market data, broker conditions, or model distributions changed? | Operational resilience |
| Conditional sizing | How should exposure vary by regime? | Improved risk-adjusted returns |

### 13.1 ML uses to avoid initially

Avoid beginning with:

- Next-candle prediction.
- BUY/SELL classification from many overlapping technical indicators.
- Deep learning on OHLC alone.
- Reinforcement learning for execution with limited realistic data.
- Autonomous LLM trade decision-making.
- Daily parameter optimization.
- Complex ensembles without an economic mechanism.

The most useful question for ML is:

> How much risk should the portfolio take, in which assets, under which regime, and when should risk be reduced?

---

## 14. Where LLMs Should Be Used

LLMs should support research operations, governance, reporting, and data quality. They should not sit at the center of autonomous order generation.

| LLM application | Practical use |
|---|---|
| Research copilot | Summarize papers, structure hypotheses, generate research notes |
| Event extraction | Extract central-bank decisions, guidance, risks, and language changes |
| Research governance | Verify manifests, sealed tests, and GO/HOLD/STOP documentation |
| Portfolio monitoring | Explain changes in PnL, volatility, exposures, and correlations |
| Trade journal | Produce a structured decision and execution journal |
| Data QA | Flag missing data, inconsistencies, and instrument anomalies |
| Risk reporting | Generate daily and weekly risk reports |
| Code review | Review strategy changes, tests, and risk-control logic |
| Knowledge base | Maintain rejected hypotheses and avoid repeating failed experiments |

### 14.1 Architecture principle

The trading decision architecture should remain deterministic and auditable:

\[
\text{Data} \rightarrow \text{Signals} \rightarrow \text{Risk Engine}
\rightarrow \text{Execution Rules} \rightarrow \text{Broker}
\]

LLMs should operate around that process:

\[
\text{LLM} \rightarrow \text{Research, Monitoring, QA, Reporting, Governance}
\]

LLMs should not autonomously place orders, alter risk parameters, or override pre-defined controls.

---

## 15. Data Requirements

| Data category | Minimum inputs | Primary use |
|---|---|---|
| Market prices | Daily OHLCV, adjusted closes, reliable futures series | Trend, volatility, portfolio backtests |
| FX carry | Spot, forwards, forward points, implied rates | Carry estimation |
| Macro | Inflation, employment, PMIs, policy rates, yield curves, surprises | Regime and macro research |
| FX value | PPP, REER, relative inflation, external-balance proxies | Long-horizon value |
| Derivatives | Implied volatility, skew, risk reversals | Regime and crash-risk controls |
| Positioning | COT, ETF flows, futures positioning where relevant | Crowding and reversal diagnostics |
| Execution | Bid/ask, slippage, latency, fills, fees, swap | Cost model and real-world implementation |
| Reference data | Calendars, roll dates, contract specs, corporate actions | Data quality and reproducibility |

For the first research version, focus on high-quality daily prices, rates/forward data, public macro sources, positioning where available, a reliable macro calendar, and a proprietary execution ledger.

---

## 16. Twelve-Month Implementation Roadmap

## Months 1–2: Research foundation

- Build a reproducible market-data warehouse.
- Define a 12–20 instrument liquid universe.
- Create pipelines for prices, rates, carry, volatility, and macro data.
- Implement returns, volatility, correlation, and exposure decomposition.
- Build a portfolio-level backtester rather than only a trade-level backtester.
- Model trading costs, roll, financing, and contract specifications.
- Implement a Falsification Ledger and experiment-manifest template.

**Deliverable:** A platform that can answer what returns, risks, costs, and exposures a portfolio would have generated, with full traceability.

## Months 3–4: First simple portfolio

Implement:

- Multi-asset trend following.
- Basic FX carry with volatility filters.
- Slow FX value.
- Portfolio volatility targeting.
- Risk parity across sleeves.
- Concentration and currency-exposure limits.

**Goal:** Measure stability, turnover, costs, drawdown, and correlations. Do not optimize for headline returns.

## Months 5–6: Robustness and stress testing

- Walk-forward testing.
- Multiple historical subperiods.
- Crisis and stress-period analysis.
- Cost sensitivity analysis.
- Leverage simulations.
- Expected shortfall and drawdown-duration analysis.
- PnL attribution by asset class, factor, and sleeve.

**Goal:** Identify which sleeves survive across regimes and which are artifacts of a limited historical period.

## Months 7–9: ML risk overlays

- Regime classification.
- Volatility and correlation forecasts.
- Dynamic risk budgeting.
- Carry crash-risk filtering.
- Conditional exposure scaling.
- Data and execution anomaly detection.

**Goal:** Demonstrate incremental value versus simple, transparent baseline rules.

## Months 10–12: Shadow portfolio and paper operation

- Run the portfolio in shadow or paper mode.
- Use simulated or very small exposure.
- Measure fills and realized costs.
- Produce daily and weekly risk reports.
- Validate that realized PnL behavior resembles modeled PnL.
- Test operational resilience.
- Write a formal investment-process document.

**Goal:** Demonstrate an operational investment process, not merely a collection of notebooks.

---

## 17. Metrics That Matter

Do not judge a fund mainly by win rate or a single monthly return.

| Metric | Why it matters |
|---|---|
| CAGR | Long-term compounded return |
| Annualized volatility | Total risk taken |
| Sharpe ratio | Return per unit of volatility |
| Sortino ratio | Return relative to downside risk |
| Calmar ratio | Return relative to maximum drawdown |
| Maximum drawdown | Largest peak-to-trough loss |
| Drawdown duration | Time required to recover from losses |
| Expected shortfall | Average loss in severe scenarios |
| Skewness | Exposure to extreme outcomes |
| Turnover | Trading-cost and capacity implication |
| Cost-to-gross-PnL | Dependence on execution quality |
| Hit rate | Diagnostic only, not a central decision metric |
| Profit factor | Payoff-shape diagnostic |
| Benchmark correlation | True diversification measurement |
| Factor exposures | Detection of hidden bets |
| Contribution to risk | Concentration measurement |
| PnL concentration | Dependence on a few trades or periods |

A high-quality systematic portfolio can have a win rate below 50% and still be excellent. The important properties are the return distribution, drawdown behavior, diversification, net-of-cost persistence, and protection from concentration.

---

## 18. Research Governance Requirements

Every future experiment should begin with a pre-registered manifest.

```yaml
experiment_id: EXP-YYYY-NN-NAME
status: preregistered

hypothesis:
  economic_mechanism: ""
  falsifiable_claim: ""
  why_existing_results_do_not_already_reject_it: ""

universe:
  instruments: []
  broker_or_data_source: ""
  timeframe: ""
  date_range: ""

signal:
  definition: ""
  directionality: ""
  holding_horizon: ""
  entry_rule: ""
  exit_rule: ""

cost_model:
  spread_source: ""
  slippage_assumption: ""
  commission: ""
  financing_swap: ""
  session_conditioning: ""

validation:
  train_window: ""
  validation_window: ""
  sealed_test_window: ""
  embargo_rule: ""
  bootstrap_method: "moving_block"
  bootstrap_resamples: 1000

metrics:
  primary_metric: "net EV/R"
  secondary_metrics:
    - sharpe_ratio
    - max_drawdown
    - expected_shortfall
    - turnover
    - cost_to_gross_pnl
    - calibration
  minimum_sample_size: ""

decision_gate:
  go: ""
  hold: ""
  stop: ""

robustness_checks:
  - remove_top_trades
  - year_by_year
  - regime_split
  - cost_stress_test
  - parameter_stability
  - concentration_analysis

non_goals:
  - ""
```

Every experiment should include:

- A genuinely sealed test period.
- Net-of-cost primary metrics.
- A dependence-aware bootstrap or equivalent inference method.
- Exposure and turnover reporting.
- Concentration analysis.
- Year-by-year and regime-by-regime results.
- Cost stress testing.
- A comparison with simple baselines.
- A pre-defined rule against repeated rescoring of the same test set.

---

## 19. Quantitative Governance Rules

### Rule 1 — AUC is not a deployment metric

A positive AUC can indicate ranking skill under a selected target, but it does not prove:

- An actionable threshold.
- Positive net expectancy.
- A monotonic score-to-PnL relationship.
- Robust out-of-sample performance.
- Survival after real execution costs.

Deployment decisions should use net payoff metrics, confidence intervals, stress tests, and concentration analysis.

### Rule 2 — A HOLD result is not a tradeable result

A HOLD verdict means uncertainty, not edge. It cannot become a GO merely because it appears promising.

### Rule 3 — Every positive result must be attacked

For every apparently positive strategy, test:

- Removing top 1, top 3, and top 5 trades.
- Year-by-year and quarter-by-quarter performance.
- Volatility and macro-regime splits.
- Session effects where relevant.
- Spread and slippage stress tests.
- Small parameter perturbations.
- PnL concentration.
- Comparison with unconditional asset drift.
- Dependency on a single event or period.

If performance disappears under basic robustness checks, classify it as non-robust.

### Rule 4 — Infrastructure must not generate hypotheses

Having models, notebooks, broker access, dashboards, or data does not justify an experiment. The economic hypothesis must exist before the tool is used.

### Rule 5 — Costs must be specified before signal search

Spread, commission, slippage, financing, and roll assumptions belong in the initial manifest, not as an optional adjustment after attractive gross results appear.

---

## 20. Immediate Next Steps

### Actions to take now

- [ ] Formally close the existing H1 FX directional ML / triple-barrier line.
- [ ] Preserve completed research as a Falsification Ledger.
- [ ] Freeze and hash code, data, configurations, and final reports.
- [ ] Repair the gold demo engine’s virtual-position and virtual-PnL accounting if it will remain active.
- [ ] Implement a normalized execution ledger with spread, slippage, latency, financing, and net PnL.
- [ ] Create the multi-asset research data warehouse.
- [ ] Define a 12–20 instrument initial universe.
- [ ] Build a portfolio-level backtester.
- [ ] Implement simple multi-asset trend before using ML.
- [ ] Add FX carry and slow FX value only after the trend framework is stable.
- [ ] Build volatility targeting, risk budgets, exposure decomposition, and drawdown rules before scaling signals.
- [ ] Use ML only after transparent baselines exist.
- [ ] Use LLMs for research operations, monitoring, quality assurance, and governance.

### Actions to avoid

- [ ] Do not launch another H1 technical-indicator FX ML model.
- [ ] Do not optimize TP/SL, thresholds, or lookbacks on existing test sets.
- [ ] Do not use high AUC as evidence for deployment.
- [ ] Do not add complexity before proving simple baseline behavior.
- [ ] Do not let an LLM place or alter orders autonomously.
- [ ] Do not allocate real capital before net-of-cost, robust, reproducible, and operationally validated evidence exists.
- [ ] Do not confuse many instruments with factor diversification.
- [ ] Do not scale a sleeve merely because of a short-term winning period.

---

## 21. Final Recommendation

The most realistic opportunity is not to become the best short-horizon FX predictor. It is to become a disciplined systematic manager with:

- Multiple imperfect but economically distinct sources of return.
- A diversified multi-asset portfolio.
- Strong volatility and drawdown management.
- Explicit factor and currency-exposure controls.
- Empirical execution-cost measurement.
- Machine learning used for regimes, risk, allocation, and anomaly detection.
- LLMs used for research productivity, quality assurance, reporting, and governance.
- An institutional-quality research process that rejects weak ideas quickly.

The first objective should be to prove the **process**: reproducible research, transparent portfolio construction, robust risk management, realistic costs, and disciplined governance. Once that exists, the portfolio can evolve strategically. Without it, even a temporarily profitable signal will be difficult to trust, scale, or explain.
