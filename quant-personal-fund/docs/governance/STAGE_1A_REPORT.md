# Stage 1A Report — Foundation and Data Governance

**Project:** quant-personal-fund  
**Milestone:** Stage 1A (limited foundation-and-data-governance)  
**Date:** 2026-09-25  
**Scope:** minimum auditable foundation to determine whether later portfolio research and a real FX carry data-feasibility audit are possible.

---

## 1. Executive Summary

Stage 1A verified and formalized the existing foundation rather than rebuilding it. The platform already contained Phases 1–2 core infrastructure (instrument master, data dictionary, returns/volatility/bootstrap/costs/hashing, governance docs) with **273 passing tests**. Stage 1A added the missing formalization: dataset versioning + SHA-256 convention, data-source provenance template, enhanced cost-model schema, an FX carry data-feasibility matrix, and data-quality/bootstrap verification on existing local datasets.

**Key conclusions:**
- The portfolio baseline foundation is **valid and reusable** — 15 active instruments, 19 validated daily datasets, 89 Stage-1A-relevant core tests passing.
- **The FX carry data gate is NOT met** — forwards are unavailable, historical swap is unavailable, and FRED rates are explicitly not a substitute. The FX carry candidate receives **HOLD/STOP** until adequate data is obtained.
- **Recommendation: GO for Stage 1B portfolio baseline; HOLD for drafting an FX carry experiment design** (data unavailable).

---

## 2. Initial Universe and Specification Status

| Asset class | Instruments | Active | Spec status |
|---|---|---|---|
| FX | EURUSD, USDJPY, GBPUSD, AUDUSD, NZDUSD, USDCAD, USDCHF, EURJPY | 8 | Price specs confirmed; **contract sizes unconfirmed** (terminal returned null) |
| Equity index | SPX, NDX, SX5E, NKY | 4 | Price specs confirmed |
| Govt bond | US10Y, BUND, JGB | **0 (excluded)** | Deactivated per ADR-003 (heterogeneous bond leg) |
| Commodity | XAUUSD, WTI, COPPER | 3 | XAUUSD contract verified (100 oz/lot); futures roll conventions pending |

**Active universe: 15.** Excluded: US10Y, BUND, JGB (bond leg excluded pending ADR-003 resolution). Full spec details in `data/reference/instrument_master.csv` and `docs/instrument_master.md`.

## 3. Data Dictionary and Source-Provenance Framework

- **Data dictionary:** `docs/data_dictionary.md` — schema, units, validation rules for OHLCV, returns, costs, instrument reference, holidays, roll schedules, experiment outputs. **Verified present and internally consistent.**
- **New (Stage 1A):**
  - `docs/governance/DATASET_VERSIONING_CONVENTION.md` — dataset identity, storage, manifest format, hashing rules, verification, status fields.
  - `docs/governance/DATA_SOURCE_PROVENANCE_TEMPLATE.md` — provenance fields, measurement-type classification (`measured/quoted/derived/assumed/unresolved`), rules (no arbitrary estimates; current ≠ historical; FRED ≠ carry).

## 4. Dataset Hash/Versioning Convention

Defined in `docs/governance/DATASET_VERSIONING_CONVENTION.md`. Key elements:
- `dataset_id = {source}_{instrument}_{frequency}_{snapshot_date}`
- SHA-256 full digest per file; raw files immutable; changes produce new files.
- Per-dataset YAML manifest with source, date range, rows, columns, missing%, hash, validation results, provenance.
- Status: `validated / unverified / superseded / rejected`.

**Verified on existing local data:** all 19 Yahoo daily parquet files hash-verified; see `stage1a_data_quality.csv`.

## 5. Data-Quality Validation Results (existing local datasets)

| Metric | Result |
|---|---|
| Files validated | 19 (all Yahoo daily parquet) |
| Valid | 19/19 (all `valid=True`, 0 errors) |
| Warnings | 1–5 per file (FX bid/ask OHL artifacts; expected and documented) |
| Missing pct | 0.0000–0.0005 |
| Date ranges | 2015–2026 (varies by instrument; FX 3,051 rows, equity/commodity ~2,947) |
| Duplicates | 0 (deduped at load) |
| UTC alignment | confirmed |

Results in `docs/governance/stage1a_data_quality.csv`.

## 6. Core Function and Unit-Test Results

| Module | Tests | Result |
|---|---|---|
| returns (simple/log/excess/alignment) | `test_returns.py` | Pass |
| FX conversion (direct/inverse/cross) | `test_fx.py` | Pass |
| hashing (file/dict SHA-256) | `test_hashing.py` | Pass |
| bootstrap (block CI, IID reduction, AR(1) widening) | `test_bootstrap.py` | Pass |
| instruments (master load/validation/lookups) | `test_instruments.py` | Pass |
| costs (model, one-way API, financing) | `test_costs.py` | Pass |
| data validation (OHLCV schema) | `test_validate.py` | Pass |

**Stage-1A-relevant tests: 89 passed.** Full suite: **273 passed** (pre-Stage-1A baseline, unchanged).

**Bootstrap synthetic verification** (`stage1a_bootstrap_verify.json`):
- IID data, block=1 → CI ≈ IID bootstrap.
- AR(1) ρ=0.5 → block=10 CI width 0.239 > block=1 width 0.141 (correctly detects dependence).
- Fixed-seed reproducibility confirmed.

## 7. FX Carry Data-Feasibility Matrix

Full matrix in `docs/specs/FX_CARRY_DATA_FEASIBILITY_MATRIX.md`. Summary:

| Data field | Classification |
|---|---|
| Spot FX prices (daily) | **Confirmed available** |
| UTC timestamp alignment | **Confirmed available** |
| US policy rates (FRED) | **Confirmed available** |
| Non-US policy/OIS rates | **Available with limitations** |
| **FX forward points** | **Unavailable** (requires broker forward desk or paid vendor) |
| **Historical swap series** | **Unavailable** |
| Current swap values | Confirmed available (current only) |
| FX contract sizes | **Requires broker confirmation** |
| Holiday/early-close calendar | **Requires broker confirmation** |
| DST behavior | **Requires broker confirmation** |

**Critical finding:** a defensible FX carry experiment requires forward points or an equivalent forward-return construction, or a broker historical swap series. **None is available.** FRED policy rates are explicitly NOT a substitute (they may explain macro conditions; they cannot produce an executable carry return). **The carry data gate is not met.**

## 8. Unresolved Facts and Impact

| Unresolved fact | Impact |
|---|---|
| FX contract sizes unconfirmed | Any FX position-sizing/EV-R normalization is provisional until broker confirmation |
| Historical swap/financing series unavailable | FX carry cannot be tested (data gate not met) |
| Forward points unavailable | Same as above — carry requires forwards |
| Bond leg excluded (ADR-003) | Benchmark B universe is 15 (not 18); defensive exposure absent |
| Holiday/early-close calendar + DST unconfirmed | Calendar-sensitive logic (forced exits) stays conditional |
| Futures roll conventions for WTI/COPPER pending | Commodity return construction provisional |

## 9. GO / HOLD / STOP Recommendation

### 1. Building the full portfolio baseline (Stage 1B)

**GO.**

- The foundation is verified: 15-instrument universe, 19 validated datasets, 273 tests passing, cost model with provenance framework, benchmark-B accounting infrastructure in place.
- Remaining Stage 1B work is *formalization* (cost-model schema migration to full provenance blocks) and *baseline construction*, both enabled by Stage 1A.

### 2. Drafting a future FX carry experiment design

**HOLD (data gate not met).**

- The required forward/carry data is **unavailable** (no forwards; no historical swap; FRED not a substitute).
- Per the pre-agreed rule: **no zero-swap proxy, no arbitrary approximation.** The candidate stays HOLD/STOP until adequate, date-consistent carry data is obtainable.
- The moment a forward-desk or vendor source is identified, a **new data-feasibility assessment** (not strategy work) is the next action.

---

## 10. Non-Goals Confirmed

- ✅ No strategy signal, carry ranking, forecast, factor score, hedge ratio, or portfolio allocation.
- ✅ No backtest, alpha test, performance metric, or optimization.
- ✅ No timeframe/instrument selection by performance.
- ✅ No artificial demo fills; no realized-cost measurement.
- ✅ No MT5/broker/login/order/terminal/workflow changes.
- ✅ No `frival/` modifications.
- ✅ No ML/LLM in any decision path.

**Stopped after this milestone. Awaiting explicit approval before Stage 1B portfolio baseline, carry hypothesis, backtest, hedge overlay, or further research.**