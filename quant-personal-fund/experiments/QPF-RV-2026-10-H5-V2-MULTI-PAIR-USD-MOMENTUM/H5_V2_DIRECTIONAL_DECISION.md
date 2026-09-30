# H5-v2 Directional Decision

**Experiment:** `QPF-RV-2026-10-H5-V2-MULTI-PAIR-USD-MOMENTUM`
**Parent protocol:** `QPF-RV-2026-05-H5-MULTI-PAIR-USD-MOMENTUM`
**Stage:** `H5_V2_DIRECTIONAL_STATISTICAL_SCREEN`
**Date:** 2026-09-29

## Decision

```text
REJECT_DIRECTIONAL_STATISTICAL_VIABILITY
```

---

## 1. Snapshot hash and input validation

`h5_v2_multiseries_h1_internal_snapshot.csv` → SHA256 `751EE1647D54E5402C762141DB8D8B547118C9825BDCBFB988F48F2DDA8B2588`
— **match**. Input validation **PASS**: exact ordered columns; T = 48,028; `internal_index_k` = 1..48,028;
labels unique + strictly ascending (`NOT_UTC`); all seven closes finite and positive.

## 2. Splits / embargoes

T = 48,028 → **train** 28,816 [0, 28816) · **embargo_1** [28816, 28846) · **validation** 9,575
[28846, 38421) · **embargo_2** [38421, 38451) · **sealed** 9,577 [38451, 48028).
Boundary labels: val `2023-08-23 11:00:00` → `2025-03-11 11:00:00`; sealed `2025-03-12 18:00:00` →
`2026-09-24 17:00:00`. Feature windows were required to avoid all embargo bars (t ≥ segment_start + 5V);
outcomes never cross a segment boundary or embargo. Train was **not** used for selection.

## 3. Validation grid summary

Primary (target-excluded) tests: **672**; numeric p-values: **672**; not-testable: **0**. Each target
contributed 96 primary tests (4 L × 3 H × 2 V × 2 K × 2 directions).

| Target | primary tests | BH q≤0.10 | HAC p<0.05 | favorable Δ sign |
|---|---|---|---|---|
| EURUSD | 96 | **2** | 5 | 53 |
| GBPUSD | 96 | 0 | 2 | 32 |
| USDJPY | 96 | 0 | 3 | 42 |
| USDCHF | 96 | 0 | 3 | 73 |
| USDCAD | 96 | 0 | 0 | 21 |
| AUDUSD | 96 | 0 | 0 | 16 |
| NZDUSD | 96 | 0 | 0 | 32 |
| **Total** | **672** | **2** | **13** | **269** |

Secondary (target-included) diagnostics were computed for all targets (descriptive only, not in BH;
for AUDUSD/NZDUSD included ≡ excluded). Total secondary records: **672**.

## 4. Multiplicity method

Benjamini–Hochberg FDR at **q = 0.10**, applied across the **m = 672 numeric** primary-grid validation
HAC p-values (no not-testable items; all 672 kept in the grid). Only **2** tests passed BH q≤0.10 (both
EURUSD), and neither formed a qualifying **paired** (strength + weakness) survivor.

## 5. Validation survivors

**None.** A bound configuration needed **both** directions to satisfy all eight conditions
(≥50 signal events, ≥200 controls, favorable unaligned Δ, positive aligned signal mean, positive
aligned Δ, HAC p<0.05, BH q≤0.10, favorable non-overlap aligned difference). No configuration met
all of them in both directions, so **0 survivors**.

## 6. Selection / ranking

**No configurations selected** (survivor set empty). No ranking applied.

## 7. Sealed confirmation

**Intentionally not evaluated** — no validation configuration qualified, so sealed outcome statistics
were not computed.

## 8. Final decision and failed requirements

`REJECT_DIRECTIONAL_STATISTICAL_VIABILITY`. Across the frozen 672-test primary family, only 2 tests
(BH-passing, EURUSD) reached directional significance and neither cleared the **paired** survivor gate;
the other 5 targets had **zero** BH-passing tests. The frozen H5 directional-continuation hypothesis
is not supported out of sample for this snapshot.

## 9. Meaning

- Any approval would have been **statistical only** and would not imply profitability or tradability.
- **Rejection applies only to the tested target/basket/H1/H5 configuration family**; it does not
  reject FX momentum or continuation generally, and it does not authorize retuning L/H/V/K, targets,
  basket, thresholds, controls, split, or multiplicity rules.

## 10. Prohibited work not performed

No PnL, trading/strategy return, equity, drawdown, Sharpe, win rate, profit factor, costs, spreads,
commissions, slippage, swaps, financing, latency, fills, order-book data, entries, exits, stops,
position sizing, capital allocation, exposure, portfolio metrics, backtests, or trading/execution; no
new indicator/model/classifier/ML/LLM/optimization/bootstrap/cointegration test; no external, MT5,
broker, account, calendar, news, network, or API data. Internal clock only (`NOT_UTC`); no parameter
changed after results.

## Artifacts

- `h5_v2_directional_statistical_screen.py`
- `H5_V2_DIRECTIONAL_RESULTS.json`
- `H5_V2_DIRECTIONAL_DECISION.md`
- `RUN_LOG.md` (appended)
