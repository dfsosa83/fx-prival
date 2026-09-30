# Final Recommendations and Next Steps

## Q4 2026 Research Close-Out and Framework for Future Work

**Date:** September 22, 2026
**Recommended status:** Formally close the tested strategy families, preserve the research infrastructure, and only resume research under genuinely new mechanisms and stricter governance.

------

## 1. Executive Summary

The research conducted during this quarter leads to a clear operational conclusion: **no statistically robust, economically positive, and executable edge has been demonstrated within the tested signal families**.

This includes:

- Directional H1 FX machine-learning models using triple-barrier-style labels.
- EURUSD BUY and SELL variants.
- Expansion to FX crosses.
- Applying the same framework to US30.
- Automated gold rule systems.
- Mechanical exit management applied to manual gold entries.
- Weekly cross-sectional momentum.
- Scheduled macroeconomic-event reaction signals.

The appropriate recommendation is to **stop optimizing, retraining, or deploying capital** on these lines through small parameter changes. Changing the TP/SL ratio, threshold, currency pair, related asset, learning algorithm, or training window is not a genuinely new hypothesis; it is an extension of an already explored search surface.

The correct conclusion is not that “markets have no opportunities.” It is more specific:

> Given the data, time horizon, cost structure, features, labels, and market mechanisms tested, no edge has been demonstrated that survives realistic costs, out-of-sample validation, serial dependence, and robustness checks.

This is still a valuable outcome. It avoids the most expensive mistake in quantitative research: confusing in-sample fit, partial predictive metrics, or a small number of exceptional trades with an investable strategy.

The methodology and infrastructure built during this work are durable assets:

- Cost-adjusted labels.
- Chronological and purged validation.
- Moving-block bootstrap confidence intervals for serially dependent trades.
- Sealed, one-shot test scoring.
- Experiment manifests.
- GO / HOLD / STOP decision gates.
- Cost, friction, concentration, and robustness auditing.
- Execution diagnostics for spread, slippage, latency, and fill quality.

The project should no longer operate as an incremental edge search. It should move into a phase of **preservation, observability, execution measurement, and discovery of genuinely new market mechanisms**.

------

## 2. Conclusion by Research Family

| Research family               | Result               | Primary evidence                                             | Recommended decision                                   |
| :---------------------------- | :------------------- | :----------------------------------------------------------- | :----------------------------------------------------- |
| Directional H1 FX ML          | Negative             | Costs around 0.4R on small stops; results do not survive net-cost evaluation | Close                                                  |
| EURUSD SELL                   | HOLD, not GO         | Precision 0.387 vs. 0.40 gross break-even; EV/R −0.03; 95% CI [−0.52, +0.45] | Do not deploy or extend                                |
| EURUSD BUY                    | STOP                 | Precision 0.355; AUC 0.504; EV/R −0.111; entirely negative CI | Close                                                  |
| FX majors after cost retrofit | STOP                 | All four backtest pairs became negative after costs and block CIs | Close                                                  |
| FX crosses                    | Aborted on economics | 0.53–0.56R cost per trade; approximately 62% break-even precision required | Do not reopen unless cost structure materially changes |
| US30 with TP 1.5 / SL 1.0     | STOP                 | AUC 0.660 but precision 0.329 and EV/R −0.178                | Close this family                                      |
| US30 with TP 2.0 / SL 1.0     | STOP                 | AUC rose to 0.687, but precision fell to 0.268 and EV/R to −0.197 | Do not continue geometry optimization                  |
| Manual gold trading           | Net negative         | 139 trades, −$815 PnL, PF 0.94, 107% maximum drawdown        | Do not scale or automate current logic                 |
| Gold rules engine             | No usable evidence   | Demo-mode loop closes simulated trades almost immediately at zero PnL | Fix only for observability                             |
| Gold exit management          | Not robust           | Positive candidate dominated by three trades and one week    | Close                                                  |
| Cross-sectional momentum      | Not supported        | Net-negative recent cells; effect concentrated in 2022       | Close                                                  |
| Macro-event FX/XAUUSD         | Not persistent       | FX reacts too quickly; gold effect was a 2025 regime artifact | Close                                                  |

The important distinction is between a **rejected hypothesis**, an **inconclusive hypothesis**, and an **unmeasurable hypothesis**:

- EURUSD SELL is statistically inconclusive, but not strong enough to justify further budget inside the same family.
- The gold engine cannot yet be evaluated correctly because the demo environment fails to produce a coherent PnL record.
- EURUSD BUY, US30, and the gold exit-management line have sufficient negative evidence to be closed under their current conceptual design.

------

## 3. What the Results Actually Mean

## 3.1 In FX, the main problem is economics, not model sophistication

A model may exhibit some predictive skill, but that is not enough for a profitable strategy. The strategy must consistently overcome:

- Spread.
- Slippage.
- Entry and exit costs.
- Opportunity cost.
- Dependence across nearby trades.
- Short-horizon market noise.
- Execution error.
- Financing costs when trades cross rollover.

In the tested FX majors, effective friction was approximately 0.4R for trades using stops around 3 pips. With a nominal risk-reward structure of 1:1.5, the required win rate rises from 40% to roughly 56%.

The net expectancy is:

EV=p(1.5−c)−(1−p)(1+c)*E**V*=*p*(1.5−*c*)−(1−*p*)(1+*c*)

Where:

- p*p* is the win probability.
- 1.5R1.5*R* is the gross profit when the take-profit is reached.
- 1R1*R* is the baseline loss when the stop-loss is reached.
- c*c* is total trading cost expressed in risk units R*R*.

The break-even win rate is:

pBE=1+c2.5*p**BE*=2.51+*c*

With c=0.4*c*=0.4:

pBE=1.42.5=56%*p**BE*=2.51.4=56%

Therefore, a precision level in the 35%–39% range is not marginally below the required level. It is structurally far from what the strategy needs to be economically viable.

The practical implication is straightforward: no amount of minor model refinement is likely to close a gap of that size. A modest increase in AUC or precision would not solve the underlying economics.

## 3.2 FX crosses were correctly rejected before spending more research budget

EURGBP, GBPJPY, and EURJPY showed spreads of approximately 4.7, 13.6, and 10.6 pips. Under the tested setup, that translated into approximately 0.53–0.56R of cost per trade.

At that level of friction, the break-even precision is around 62%. The observed model family produced precision levels well below that threshold, leaving no credible path to rescue the design merely by changing ATR multipliers or threshold settings.

Aborting this branch before spending a sealed-test evaluation was the correct scientific and economic decision. Not every idea deserves a complete backtest; some can be rejected by cost arithmetic before consuming time, compute, and multiple-testing budget.

## 3.3 US30 shows why a high AUC is not an investable strategy

US30 is the most instructive result in the entire program.

The model showed meaningful ranking skill:

- AUC of 0.660 under the first geometry.
- AUC of 0.687 after widening the target to TP 2.0 / SL 1.0.

However, operational performance remained negative:

- At TP 1.5 / SL 1.0: precision 0.329 and EV/R −0.178.
- At TP 2.0 / SL 1.0: precision 0.268 and EV/R −0.197.

The audit of fired signals showed that, inside the subset of trades the system had already decided were actionable, the predicted probability had almost no useful relationship with realized return. The model’s skill appeared mostly between vetoed and non-vetoed bars, not within the opportunities it would actually trade.

In other words:

> The model may have some ability to identify conditions to avoid, but it does not have enough ability to select profitable trades among the signals it already regards as good.

This rules out several tempting but unsupported extensions:

- Raising the threshold.
- Trading only the top-k signals.
- Replacing the objective with ranking loss.
- Applying further calibration.
- Moving the same design to a different index.
- Testing more TP/SL geometries.

Those changes may generate additional backtest outputs, but they do not test a new hypothesis or address the observed failure: a lack of economically useful discrimination inside the tradable region.

------

## 4. Final Recommendations

## 4.1 Formally close the directional H1 ML line

The following research directions should be declared closed:

- EURUSD BUY and SELL using the current label family.
- Extensions to GBPUSD, USDCHF, USDCAD, AUDUSD, or NZDUSD using the same framework.
- FX crosses using similar target structures.
- Index CFDs using the same directional H1 approach.
- Small variations in TP, SL, forward window, threshold, or class weighting.
- New models trained on the same technical feature set.
- Meta-labeling on the same signals.
- Additional ensembles, hyperparameter searches, or feature-selection cycles intended to rescue the same thesis.

The reason is not dogma. It is protection against multiple testing. After many attempts, every additional parameter combination has an increasingly high probability of producing an apparently attractive result by chance.

The governance rule should be:

> No future experiment may reuse the same economic mechanism, information source, and horizon while presenting itself as a new research hypothesis.

## 4.2 Do not deploy real capital

No real capital should be allocated to any of the tested strategy families.

This applies even when a dashboard, model, or real-time signal looks attractive. A visually compelling trade idea does not invalidate sealed, net-of-cost research that failed to demonstrate a robust edge.

Manual trading may continue only as discretionary activity, not as quantitatively validated trading. It should not be used as evidence that the existing models, rules, or automation logic have an edge.

## 4.3 Keep the infrastructure as an observability system

The demo systems can remain active, but their purpose must change:

- They are not a strategy portfolio.
- They are not experiments seeking positive PnL.
- They are not justification for real-money deployment.
- They are systems for market and execution observability.

The primary goal should be to build reliable data on:

- Spread by instrument.
- Spread by session.
- Entry slippage.
- Exit slippage.
- End-to-end execution latency.
- Difference between signal price and actual fill price.
- Rejections, requotes, and order failures.
- Swap and financing effects.
- Distribution of total cost as a share of ATR, stop, and target.
- Stability of data pipelines and scheduling.

This turns the demo environment into a data asset. If a strong future hypothesis emerges, you will already have empirical execution data for realistic evaluation.

## 4.4 Fix the gold engine only as a measurement requirement

The gold engine’s demo-mode logic should be repaired if the system will remain active:

- Demo mode must retain a genuine virtual position in internal state.
- Exit logic must read the virtual position when operating in demo mode.
- Each trade must contain entry, stop, target, exit, exit reason, and virtual PnL.
- PnL must be computed consistently with bid/ask, spread, and position size.
- The system must record equity curve, drawdown, MAE, MFE, and holding duration.
- The `--dry` path must realize and store simulated PnL instead of leaving it at zero.

However, fixing this system is **not** permission to spend more research budget searching for a new gold-rule variant. First repair measurement. Then allow it to run as an observational system. Only later, under a genuinely new hypothesis, decide whether another research program is justified.

## 4.5 Preserve negative results as a research asset

Negative results should be treated as durable knowledge, not as a failed project to be hidden.

Create a single **Falsification Ledger** containing:

- Exact hypothesis.
- Pre-registration date.
- Assets.
- Data used.
- Forecast horizon.
- Signal definition.
- Label definition.
- Model.
- Cost assumptions.
- Temporal split.
- Primary metric.
- GO / HOLD / STOP rule.
- Sealed-test result.
- Confidence interval.
- Robustness diagnostics.
- Final decision.
- Economic or statistical reason for closure.
- Hashes of data and code artifacts.

This prevents the team from accidentally retesting a previously rejected idea six months later under a different name.

------

## 5. Open Risks to Document

The following issues do not weaken the existing negative conclusions, but they are mandatory requirements before any future GO decision.

| Risk                        | Current condition              | Implication                                                  |
| :-------------------------- | :----------------------------- | :----------------------------------------------------------- |
| Slippage                    | Set to 0.0                     | A marginal future result may overstate realistic performance |
| Session-conditioned spreads | Not modeled                    | Costs may worsen during Asia, rollover, or macro-event periods |
| Swap / financing            | Not deducted in FX backtests   | Can affect trades that cross rollover                        |
| Cost measurements           | Point-in-time snapshots        | Must be refreshed before being reused for new decisions      |
| A2/A3 account isolation     | Not provisioned                | Needed only if a future strategy reaches paper-trading GO    |
| Fork traceability           | Risk of file overwrite remains | Immutable runs and hashes are required                       |
| Compute robustness          | Hardening was ad hoc           | Must be centralized before future heavy research             |
| Gold demo engine            | Virtual PnL is broken          | Must be fixed before it can generate operational evidence    |

A key principle is worth stating clearly:

> Missing costs are not a reason to reopen negative results. They are an additional reason to be conservative.

If a strategy was already unprofitable using flat spread assumptions and zero slippage, more realistic costs are unlikely to rescue it.

------

## 6. Recommended Action Plan

## Phase 1 — Formal Close and Freeze

## Time horizon: one week

1. Officially close the current directional H1 FX ML family and its immediate extensions.
2. Freeze all completed experiment artifacts.
3. Create hashes for:
   - Datasets.
   - Notebooks.
   - Scripts.
   - Configuration files.
   - Cost tables.
   - Final reports.
   - Trained models.
4. Create one index of all experiments linking the manifest, run log, and sealed report.
5. Explicitly mark prohibited incremental re-experimentation families.
6. Separate historical documents from operational documentation.
7. Remove empty scaffolding, temporary scripts, and non-reproducible artifacts.
8. Correct remaining stale references and ensure the roadmap, audit, and synthesis stay consistent.

**Expected deliverable:** a reproducible repository with immutable evidence and a consolidated ledger of closed hypotheses.

------

## Phase 2 — Instrumentation and Observability

## Time horizon: two to four weeks

1. Fix the gold engine’s demo PnL loop.
2. Create a normalized ledger for simulated and real trades.
3. Record, for every trade:
   - Instrument.
   - Direction.
   - Signal timestamp.
   - Order-send timestamp.
   - Fill timestamp.
   - Signal price.
   - Requested price.
   - Fill price.
   - Spread at entry and exit.
   - Signed slippage.
   - Latency.
   - Stop and target.
   - Gross PnL.
   - Estimated trading cost.
   - Swap.
   - Net PnL.
   - MAE.
   - MFE.
   - Holding duration.
   - Exit reason.
4. Build a cost dataset by:
   - Instrument.
   - Hour of day.
   - Trading session.
   - Day of week.
   - Volatility regime.
   - Proximity to macro events.
5. Implement alerts for:
   - Abnormal spread.
   - High latency.
   - Scheduler failure.
   - Trades with missing PnL.
   - Material deviations from research cost assumptions.

**Expected deliverable:** a demo system that produces auditable operational evidence, not merely system logs.

------

## Phase 3 — Discovery of New Hypotheses

## Time horizon: one to three months

This phase should not begin with a machine-learning model or a strategy backtest. It should begin with a specific economic question.

The recommended sequence is:

1. Identify a genuinely new information source.
2. Formulate an economic mechanism.
3. Define what observable relationship should exist if the mechanism is real.
4. Measure basic predictive or explanatory strength.
5. Test stability across years, assets, and regimes.
6. Apply realistic cost assumptions.
7. Only then design a tradable strategy.

## Conditions for accepting a new hypothesis

A hypothesis may enter the formal pipeline only if it satisfies all of the following:

- It uses information not explored by the closed families.
- It has a clear economic rationale.
- It is not simply another OHLC/ATR/technical-indicator transformation at H1.
- It defines the asset, horizon, data, costs, and key metric in advance.
- It has a plausible reason to survive real trading costs.
- It can be evaluated on a truly sealed final period.
- It includes an explicit abandonment rule.
- It does not rely on one year, one event, or one market regime.

------

## 7. Research Directions That Could Support a New Hypothesis

These are not trading recommendations and do not imply that an edge exists. They are research families that would represent mechanisms meaningfully different from those already rejected.

## 7.1 Medium-horizon macro-financial factors

Instead of forecasting the next H1 candle, investigate whether macro and positioning variables explain returns over several days or weeks.

Potential inputs include:

- Expected interest-rate differentials.
- OIS curves.
- Changes in central-bank expectations.
- Inflation-expectation differentials.
- Interest-rate futures curves.
- COT and speculative positioning.
- FX option risk reversals and skew.
- Implied-volatility term structures.
- Real-yield differentials for XAUUSD.
- Gold ETF flows or futures positioning, if reliable data is available.

The hypothesis should not be “put everything into a model.” It should be concrete, for example:

> When expected policy-rate differentials accelerate and positioning is not extremely crowded, relative currency trends may persist for several days rather than one hour.

This would test a different mechanism: monetary-policy repricing and portfolio flows, not short-horizon technical patterns.

## 7.2 Market microstructure and execution quality

Research may also focus on identifying measurable liquidity and execution conditions that systematically damage expected performance.

Useful questions include:

- During which sessions does spread-to-ATR systematically become prohibitive?
- How much does slippage vary across London, New York, Asia, and rollover?
- Does relative transaction cost spike before or after high-impact events?
- Are broker fills materially worse at certain times or market states?
- Can expected loss be reduced simply by avoiding extreme execution conditions?

This line may not create alpha by itself, but it can materially improve future research quality and prevent misleading backtests.

## 7.3 Weekly-horizon strategies using slow-moving data

Short-horizon signals face intense competition and relatively high transaction costs compared with target size. A different path is to study weekly strategies with lower turnover.

Potential mechanisms include:

- Macro trend conditioned on volatility.
- Risk-adjusted carry with drawdown constraints.
- Cross-sectional currency value and carry.
- Reversal after extreme moves conditional on positioning.
- Global risk regimes using DXY, VIX, real yields, and cross-asset correlation.

The condition is that this must not repeat the already tested cross-sectional momentum idea. Changing a 10-week lookback to a 30-week lookback is not a new hypothesis. There must be an additional source of information or economic mechanism.

## 7.4 Gold using higher-quality exogenous variables

XAUUSD could be studied at a different horizon using factors closer to its economic drivers:

- U.S. real yields.
- DXY.
- Rate-curve shifts.
- Implied volatility.
- Futures positioning.
- Safe-haven demand under risk shocks.
- Monetary-policy events using better surprise measures.

However, discipline must be especially strict: the gold event signal observed in 2025 disappeared in 2026. Any future gold study must demand cross-regime stability before it is treated as meaningful.

------

## 8. Mandatory Template for Future Experiments

Every future experiment should have a complete manifest before implementation begins.

```
textexperiment_id: EXP-YYYY-NN-NAME
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
    - precision
    - profit_factor
    - max_drawdown
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

In addition, every experiment should require:

- A sealed test period never used for model or threshold selection.
- A net-of-cost primary metric.
- Moving-block bootstrap or an equivalent method that respects temporal dependence.
- Trade count and exposure reporting.
- PnL concentration analysis.
- Year-by-year and regime-by-regime analysis.
- Moderate cost sensitivity tests.
- Comparison against a simple baseline.
- A ban on rescoring the same test without a predefined protocol.

------

## 9. Quantitative Governance Rules

To prevent the project from drifting back into incremental optimization, the following permanent rules are recommended.

## Rule 1 — AUC is not a deployment metric

A positive AUC only indicates some ranking ability under the selected target. It does not prove:

- An actionable threshold.
- Positive net expectancy.
- A monotonic relationship between score and PnL.
- Robust out-of-sample performance.
- Survival after realistic trading costs.

The primary deployment metric must always be a net payoff measure, such as net EV/R, accompanied by a confidence interval and concentration controls.

## Rule 2 — Do not trade a HOLD result

A HOLD result means uncertainty, not edge. It cannot become a GO merely because “it may work.” It can only be revisited if new uncontaminated information appears, a genuinely unseen period becomes available, or a structurally different hypothesis is proposed.

## Rule 3 — Every positive result must be attacked before acceptance

Whenever a result appears positive, run all of the following:

- Remove top 1, top 3, and top 5 trades.
- Split results by year.
- Split results by quarter.
- Analyze volatility regimes.
- Analyze sessions.
- Stress-test spread and slippage.
- Test small parameter perturbations.
- Analyze PnL concentration.
- Compare to unconditional trend or drift in the asset.
- Verify that the result is not driven by one period or one event.

If the result disappears under these basic tests, classify it as non-robust.

## Rule 4 — Infrastructure must not generate experiments

Having a dashboard, models, MT5, notebooks, or downloaded data is not a reason to create another experiment. The hypothesis must come before the tool, not the reverse.

## Rule 5 — Costs are specified before signal search

Do not build a gross backtest and treat costs as an optional adjustment afterward. Spread, commission, slippage, and financing must be specified in the initial experiment manifest.

------

## 10. Recommended Strategic Decision

The recommended decision at this point is:

> Formally close research on the tested signal families, avoid real-capital deployment, preserve the falsification ledger, and convert the demo environment into an execution-quality and observability platform.

If research resumes later, it should do so only under a hypothesis with:

- A different economic mechanism.
- A different information source.
- Potentially a different time horizon.
- Costs modeled from the beginning.
- Full pre-registration.
- A sealed test period.
- A high robustness standard.
- A clear STOP rule.

The most important outcome of this quarter is not a trading strategy. It is a process that prevented weak results from turning into real-money losses. The research showed that rigorous methodology can produce a negative result and still create substantial value: it eliminates unproductive paths, protects capital, and raises the standard for every future trading decision.

------

## 11. Final Checklist

## Actions recommended now

- Formally close the current H1 FX ML / triple-barrier research line.
- Block incremental experiments on current pairs, thresholds, TP/SL combinations, and models.
- Freeze and hash all artifacts from finalized experiments.
- Consolidate a single Falsification Ledger.
- Correct stale and duplicate documentation.
- Repair the gold engine’s demo/PnL loop.
- Implement a trade ledger with spread, slippage, latency, swap, and net PnL.
- Keep demo systems as observability tools, not investment strategies.
- Centralize compute and execution hardening.
- Add protection against fork overwrites and sealed-result modification.
- Enforce the experiment-manifest standard for any future research.

## Actions not recommended

- Do not test another TP/SL combination on US30.
- Do not test more FX pairs using the same label family.
- Do not reopen FX crosses for diversification.
- Do not optimize thresholds using the existing test set.
- Do not treat a high AUC as deployment evidence.
- Do not scale manual gold trading because of its win rate.
- Do not automate the current manual-entry logic under the assumption that exits will repair it.
- Do not launch another H1 technical-ML project simply by adding features or algorithms.
- Do not provision isolated demo accounts until a future hypothesis earns a genuine GO decision.
- Do not commit real capital until net, robust, and replicable evidence exists.