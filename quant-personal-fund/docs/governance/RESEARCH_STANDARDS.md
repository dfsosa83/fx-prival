# Research Standards

## Core Principles

1. **Economic hypothesis before modeling.** Every strategy begins with a stated economic mechanism, a falsifiable claim, and a reason why the market may not fully arbitrage it away.

2. **Simple, transparent baseline before ML.** Transparent rule-based strategies are the benchmark. ML is introduced only when it provides measurable incremental value.

3. **Portfolio-level evaluation before individual-trade enthusiasm.** A strategy is judged by its contribution to the portfolio, not by its standalone win rate.

4. **Net-of-cost performance before gross performance.** No strategy may be evaluated or reported without realistic cost accounting.

5. **Sealed chronological out-of-sample testing.** The test period is touched exactly once. No threshold-walking, no post-hoc optimization.

6. **Dependence-aware statistics.** Positions and labels that overlap in time must be evaluated with methods that respect serial dependence (block bootstrap, not IID).

7. **Pre-registration before implementation.** Every experiment has a manifest filed before any code is written against the test set.

8. **No repeated tuning on the same final test set.** Re-scoring a sealed test with changed parameters requires a new experiment ID and a new sealed window.

9. **Robustness testing before accepting positive results.** Every apparent positive must survive: top-trade removal, year/quarter splits, regime splits, cost stress, parameter perturbation, concentration analysis, and unconditional baseline comparison.

10. **Code, data, configurations, and outputs must be reproducible and traceable.** Inputs are hashed. Data is versioned. Outputs are generated from known inputs.

11. **Preserve legacy evidence.** The falsification ledger is a permanent record. Do not overwrite or delete prior negative findings.

12. **No deployment of real capital based on research alone.** A strategy must pass: research GO → shadow portfolio → paper trading → operational validation before any real capital is considered.

13. **No autonomous LLM-driven trading or risk-limit modification.** LLMs operate outside the decision path.

14. **Prefer conservative, explainable, liquid, lower-turnover designs.** During early phases, favor robustness over optimization.

## Decision Gates

Every experiment uses pre-registered GO/HOLD/STOP criteria:

- **GO:** Primary metric meets the pre-defined threshold with statistical confidence. All robustness checks pass. Proceed to shadow portfolio planning.

- **HOLD:** Result is inconclusive. Confidence interval straddles zero or sample size is insufficient. Do not proceed. Do not kill. Accumulate more data or re-evaluate with a new mechanism.

- **STOP:** Primary metric is negative with statistical confidence, or robustness checks destroy the positive result. Close the experiment. Document the specific failure mechanism. Do not re-test this family with incremental changes.

**Rule:** A HOLD is not a tradeable result. It cannot become a GO through threshold adjustment, parameter tuning, or narrative reinterpretation.

**Rule:** A STOP verdict on a research family means the mechanism is falsified. A new experiment on the same family requires a genuinely different economic mechanism, information source, horizon, and evaluation framework — not a different pair, window, multiplier, or classifier.

## Metrics Hierarchy

1. **Primary:** Net EV/R (expected value per unit of risk, after all costs), with 95% block-bootstrap CI.
2. **Secondary:** Sharpe ratio, Sortino ratio, Calmar ratio, maximum drawdown, drawdown duration, expected shortfall.
3. **Diagnostic:** Win rate, profit factor, turnover, cost-to-gross-PnL ratio, PnL concentration, benchmark correlation, factor exposures.

Win rate is a diagnostic, not a decision metric. A high-quality systematic portfolio can have a win rate below 50% and still be excellent.

## Cost Model Requirements

Every strategy must account for, at minimum:

- Bid-ask spread (per instrument, per session where measurable).
- Slippage (conservative estimate until fills provide empirical data).
- Commissions (per broker, per instrument class).
- Swap/financing (for multi-day holds).
- Roll costs (for futures or CFD instruments).
- Dividend adjustments (for equity index instruments).

The cost model is specified in the experiment manifest before any backtest is run. Cost assumptions are documented with their source and date of measurement.

## Reproducibility Requirements

- Environment is pinned (`environment.yaml`).
- Raw data is versioned with SHA256 hashes and acquisition-date manifests.
- Experiment inputs are hashed (`inputs_hash` in manifest).
- Experiment outputs are generated deterministically from known inputs.
- All code used in an experiment is committed before scoring.
- The sealed test period is recorded in the manifest before scoring.