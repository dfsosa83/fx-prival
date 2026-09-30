# Notebook Usage Policy

## Permitted Uses

Notebooks (`.ipynb` files) in this project are restricted to:

1. **Exploratory data analysis** — initial investigation of data quality, distributions, correlations, and visual patterns.
2. **Visualization and prototyping** — quick charts, signal prototyping, metric exploration before committing to a module.
3. **Research reporting** — generating formatted reports (tables, charts, commentary) from experiment outputs.
4. **Ad-hoc one-off analysis** — answering a specific question that will not be repeated.

## Prohibited Uses

Notebooks must NOT serve as:

1. **The canonical implementation of any reusable function.** If a computation will be used more than once, it belongs in a `.py` module under `core/`, `signals/`, `portfolio/`, `risk/`, or `backtest/`.
2. **The production backtest or experiment runner.** Experiments are executed by `experiments/` modules with manifest-driven execution, not notebooks.
3. **A container for credentials, account numbers, or API keys.**
4. **The sole location of a critical computation** with no equivalent tested module.

## Location

All notebooks live under `notebooks/exploratory/`. They may be organized by topic or date. Notebooks are never placed in `experiments/`, `signals/`, `core/`, or any other source-code directory.

## Import Rules

- Notebooks may import from any `quant-personal-fund` module (`core`, `signals`, `portfolio`, etc.).
- Modules must never import from notebooks.
- Notebook-to-notebook imports are prohibited.

## Reproducibility

- Cell execution order must be linear. `Kernel > Restart & Run All` must produce the same result as interactive execution.
- No hidden state from out-of-order cell execution.
- Data dependencies should be loaded from versioned paths in `data/raw/` or `data/processed/`, not from hardcoded absolute paths.

## Transition to Module

When a computation prototyped in a notebook proves useful:

1. Extract the logic into a function in the appropriate module (`core/`, `signals/`, etc.).
2. Write a docstring and type hints.
3. Write unit tests in the corresponding `tests/` directory.
4. Update the notebook to import from the module instead of containing the inline code.
5. Delete or archive the original notebook if it is no longer needed for exploration.