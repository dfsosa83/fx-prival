# LLM Tools

LLM-assisted research operations — outside the trading decision path.

## Permitted Uses

- Research copilot: summarize papers, structure hypotheses, generate research notes.
- Event extraction: extract central-bank decisions, guidance, and language changes.
- Research governance: verify manifests, sealed tests, and GO/HOLD/STOP documentation.
- Portfolio monitoring: explain changes in PnL, volatility, exposures, and correlations.
- Data QA: flag missing data, inconsistencies, and instrument anomalies.
- Risk reporting: generate daily and weekly risk reports.
- Code review: review strategy changes, tests, and risk-control logic.
- Knowledge base: maintain rejected hypotheses and avoid repeating failed experiments.

## Prohibited Uses

- Autonomous order placement or execution.
- Autonomous risk-limit changes or parameter modification.
- Rewriting strategy logic without human review.
- Trading directly from unstructured news sentiment.
- Declaring a strategy profitable without quantitative evidence.
- Overriding portfolio risk controls.

## Architecture Principle

```
Data → Signals → Risk Engine → Execution Rules → Broker
                                          ↑
                                    Human Review
                                          
LLM → Research, Monitoring, QA, Reporting, Governance
```

LLMs operate around the trading process, not inside it. All LLM outputs affecting research, risk, or production must be logged, reviewable, and attributable.

## Implementation

This directory is a placeholder. LLM tools are optional and will be implemented only after deterministic foundations (core, portfolio, risk, backtest) are built and tested. No LLM tool may modify strategy parameters, place orders, or alter risk limits.