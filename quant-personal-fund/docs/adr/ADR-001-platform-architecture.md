# ADR-001: Platform Architecture Decision

**Status:** Accepted  
**Date:** 2026-09-22  
**Deciders:** Quantitative research lead

## Context

A prior H1 FX directional ML project (codename "frival") completed a quarter of hypothesis-driven research (Q4 2026) with the following outcome: **zero demonstrated edge across 8+ experiments.** The tested families — directional H1 FX ML, crosses, equity indices, momentum, event-driven macro, manual gold trading, and mechanical gold exit management — were all falsified for specific, documented reasons.

The prior project also produced durable methodological assets: block-bootstrap CI infrastructure, an instrument cost table, pre-registration experiment manifests, sealed one-shot testing, GO/HOLD/STOP gates, and an audit reflex that caught three false GOs before acceptance.

The strategic decision is to **close the H1 directional ML program** and build a new platform with a structurally different approach: portfolio-level, multi-asset, daily-to-monthly horizons, transparent baselines before ML, and risk-first construction.

## Decision

We will build a new self-contained quantitative research platform under `quant-personal-fund/` with the following architectural principles:

1. **Self-contained root.** All new architecture, code, configs, data contracts, experiments, and documentation live under `quant-personal-fund/`. Legacy code is referenced but not modified or imported.

2. **Modular separation.** Clear boundaries between: documentation/governance, data layer, core library, signals, portfolio construction, risk management, backtesting, execution, monitoring, and LLM tools.

3. **Research-first, not trading-first.** The platform is a research and portfolio-construction system. Execution and live trading are deferred to Phase 6 and are gated on research evidence.

4. **Configuration-driven.** Instrument universes, cost models, risk limits, and strategy parameters live in version-controlled YAML files, not hardcoded in source.

5. **Test-first core.** Every core module has unit tests before any strategy code depends on it.

6. **Pre-registration governance.** Every experiment requires a manifest filed before any code touches the test set. GO/HOLD/STOP gates are pre-defined.

7. **Net-of-cost by default.** No backtest or performance metric may be reported without cost accounting.

8. **ML is for risk/policy, not price prediction.** ML is reserved for regime classification, volatility/correlation forecasting, and conditional sizing. It is not used for next-candle direction prediction.

9. **LLMs are outside the trading path.** LLMs assist with research, QA, reporting, and governance. They do not place orders, modify risk limits, or generate trading signals autonomously.

## Consequences

### Positive
- Clean separation from legacy code prevents accidental reintroduction of falsified approaches.
- Modular architecture supports independent development and testing of each layer.
- Pre-registration discipline makes null results as trustworthy as positive results.
- Daily-frequency, multi-asset scope is more aligned with institutional systematic macro approaches and less vulnerable to microstructure costs.

### Negative
- Requires building foundational infrastructure (instrument master, data pipelines, core library) before any strategy can be evaluated — a 2-phase delay before the first backtest.
- Daily-frequency data for some instruments (bonds, commodities) may require different sources than the legacy MT5 H1 pipeline.
- Multi-asset scope increases data acquisition and validation complexity relative to the legacy 4-pair FX setup.

### Risks
- Data availability risk: free daily data sources may have gaps, survivorship bias, or adjustment inconsistencies for non-FX instruments.
- Cost model incompleteness: swap, financing, and roll costs may be unavailable until a broker is selected.
- Compute constraints: the single-machine Windows environment may limit backtest scope across 12–20 instruments.

## Alternatives Considered

### Alternative A: Extend the legacy H1 FX ML platform
**Rejected.** Six experiments with zero GO, including a diagnostic showing no usable operating point exists in the tradeable region. The triple-barrier hit/miss label family is structurally incapable of converting ranking skill into breakeven precision.

### Alternative B: Build a new FX-only platform at daily frequency
**Rejected.** A single-asset-class portfolio is insufficiently diversified. Multi-asset trend following is the strongest structural improvement available to a small systematic manager.

### Alternative C: Start with ML-driven regime detection as the first module
**Rejected.** Simple transparent baselines must exist before ML can demonstrate incremental value. Building ML first inverts the burden of proof.

## References

- `PROJECT-CONTEXT.md` — Legacy system overview and state.
- `quant_fund_blueprint_recommendations.md` — Strategic blueprint for the new platform.
- `ROADMAP-2026-Q4-SYNTHESIS.md` — Falsification ledger and no-edge map.
- `docs/governance/RESEARCH_STANDARDS.md` — Research methodology and standards.
- `docs/governance/EXPERIMENT_MANIFEST_SPEC.md` — Experiment manifest specification.
- `docs/falsification_ledger/no_edge_map.md` — Preserved legacy no-edge map.