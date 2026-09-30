# Notebooks

Exploratory notebooks for ad-hoc analysis, data visualization, and signal prototyping.

## Rules

1. **Exploration only.** Notebooks are for investigation and reporting. Production logic lives in tested `.py` modules.
2. **Location.** All notebooks go in `exploratory/`. No notebooks in `core/`, `signals/`, `experiments/`, or other source directories.
3. **Imports.** Notebooks may import from any `quant-personal-fund` module. Modules must never import from notebooks.
4. **Reproducibility.** `Kernel > Restart & Run All` must produce the same result as interactive execution.
5. **No credentials.** Never hardcode account numbers, API keys, or passwords in notebooks.

See `docs/governance/NOTEBOOK_POLICY.md` for the full policy.