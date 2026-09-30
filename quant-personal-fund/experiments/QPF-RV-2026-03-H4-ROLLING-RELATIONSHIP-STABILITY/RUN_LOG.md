# Run Log — QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY

Append-only. Do not edit or delete prior entries.

---

## 2026-09-29 — H4_ROLLING_RELATIONSHIP_STABILITY_DESIGN

- **date:** 2026-09-29
- **stage:** `H4_ROLLING_RELATIONSHIP_STABILITY_DESIGN`
- **status:** `preregistered`
- **action:** Froze the H4 rolling-relationship stability hypothesis, protocol, decision rules,
  candidate universe, and implementation blueprint. Design-only.
- **fixed candidate order:** `C2 → C3 → C4 → C5`
- **frozen windows / evaluation:** `W ∈ {1000, 2000, 5000}`, `E = 1000`
- **split / embargo:** 60% train / 20% validation / 20% sealed with **30-bar** embargoes; internal
  ordinal clock only (`NOT_UTC`); strict-intersection snapshots excluding exactly the maximum common
  label.
- **selection / confirmation:** validation-only W selection (highest score, tie-break to smallest W;
  gates: ≥3 eligible blocks, ≥60% pass rate, ≥2 passes, ≥20% eligibility) then a **single** sealed
  confirmation with the same gates.
- **actions explicitly NOT performed:** any market-data read/download/parse/hash; any log prices,
  returns, spreads, OLS/beta, correlations, covariance, ADF, Johansen, AR/OU, half-life, variance
  ratios, or bootstrap; costs / slippage / swaps / PnL / Sharpe / drawdown; signals / entries /
  exits / sizing / portfolios; ML / LLM; backtests; MT5 / broker / credentials / network / API /
  calendar / external data; order / execution / demo / shadow / live; modification of any existing
  experiment, snapshot, manifest, audit, registry, template, or run log.
- **authorization consequence:** future action = create an immutable snapshot for **C2** and, only
  after **separate authorization**, run **exactly one** H4-C2 statistical screen under this protocol.
- **artifact references:**
  - `quant-personal-fund/experiments/QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY/H4_RESEARCH_QUESTION.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY/H4_CANDIDATE_UNIVERSE.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY/H4_ROLLING_RELATIONSHIP_PROTOCOL.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY/H4_DECISION_RULES.md`
  - `quant-personal-fund/experiments/QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY/H4_IMPLEMENTATION_BLUEPRINT.py`
  - `quant-personal-fund/experiments/QPF-RV-2026-03-H4-ROLLING-RELATIONSHIP-STABILITY/RUN_LOG.md`
