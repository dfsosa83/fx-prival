# Quant Personal Fund — Systematic Multi-Asset Research Platform

**Status:** Phase 1 — Foundation (2026-09-22)  
**Purpose:** A disciplined, research-driven quantitative investment platform for multi-asset portfolio construction, risk management, and systematic strategy evaluation.

---

## Platform Overview

This platform is designed to answer one question honestly:

> Can a diversified multi-asset systematic portfolio generate returns that are positive after realistic costs, statistically credible, diversified, explainable, operationally executable, and robust across time and market regimes?

It is **not** a collection of trading bots. It is a portfolio-level research and construction platform built from first principles: economic hypothesis before model complexity, portfolio evaluation before individual-trade enthusiasm, and net-of-cost performance before gross backtests.

## Architecture

```
quant-personal-fund/
├── docs/            Governance, ADRs, falsification ledger, data dictionary
├── config/          Instrument universe, cost model, risk limits (YAML)
├── core/            Shared library: instruments, returns, volatility, costs, bootstrap, metrics
├── data/            Data ingestion, validation, raw/processed/reference, quality
├── notebooks/       Exploratory notebooks only (no production logic)
├── experiments/     Pre-registered experiments with immutable artifacts
├── signals/         Strategy signal generation (trend, carry, value)
├── portfolio/       Position sizing, exposure decomposition, constraints
├── risk/            VaR, stress tests, drawdown governance
├── backtest/        Portfolio-level backtesting, execution simulation, attribution
├── execution/       Abstract broker interface, paper trading (Phase 6)
├── monitoring/      Portfolio and risk monitoring (Phase 6)
├── tests/           Integration and system-level tests
└── llm_tools/       LLM-assisted research operations (outside trading path)
```

## Closed Research Families

The following research families were tested and falsified in the prior project (Q4 2026). They must not be reopened through incremental parameter variation:

1. **Directional H1 FX ML** with triple-barrier hit/miss labels — costs + irreducible precision floor.
2. **FX crosses** as diversification under the same label — arithmetic handicap (0.53–0.56R spread per trade).
3. **Manual gold trading + mechanical exit optimization** — entries have no edge; exits do not create one.
4. **Cross-sectional momentum** (weekly relative strength) — effect ≈ 0 in recent regimes.
5. **Macro-event reaction** (scheduled surprise → price) — FX prices-in surprises within 1 hour.

See `docs/falsification_ledger/no_edge_map.md` for the complete evidence.

## Phase Status

| Phase | Description | Status |
|---|---|---|
| Phase 0 | Audit and architecture decision | Complete |
| Phase 1 | Data foundation, instrument master, core library, governance | In progress |
| Phase 2 | Portfolio analytics and baseline backtesting engine | Planned |
| Phase 3 | Transparent baseline strategies (multi-asset trend first) | Planned |
| Phase 4 | FX carry, FX value, dynamic hedging research | Planned |
| Phase 5 | ML overlays (only if justified by baseline) | Planned |
| Phase 6 | Shadow portfolio, execution measurement, paper operation | Planned |

## Setup

```bash
# Create conda environment
conda env create -f environment.yaml
conda activate quant-fund

# Or with pip
pip install -r requirements.txt

# Run tests
make test
```

## Governance

- Every experiment requires a pre-registered manifest with sealed test period.
- GO/HOLD/STOP verdicts are pre-defined before scoring.
- No strategy may be evaluated only gross of cost.
- ML is used only for risk/policy problems (regime, volatility, correlation, sizing), not next-candle prediction.
- LLMs operate outside the trading decision path: research, QA, reporting, governance.

## Research Traceability

- Experiment identifiers and the future QPF namespace: [`experiments/REGISTRY.md`](experiments/REGISTRY.md)
- Pointer index to preserved legacy research artifacts: [`docs/falsification_ledger/LEGACY_INDEX.md`](docs/falsification_ledger/LEGACY_INDEX.md)
- Append-only research decision log: [`docs/decisions/DECISION_LOG.md`](docs/decisions/DECISION_LOG.md)

## License

Proprietary. All rights reserved.