# QPF-RV-2026-02 — G0/G1 Design Specification

**Experiment ID:** `QPF-RV-2026-02-AUDUSD-NZDUSD-COINTEGRATION`
**Candidate ID:** `C1` · **Instruments:** AUDUSD / NZDUSD · **Timeframe:** H1
**Clock:** `INTERNAL_ORDINAL_NOT_UTC` · **Status:** `G1_SNAPSHOT_FROZEN_PENDING_G3`

---

## 1. Primary hypothesis and ordering

The primary candidate is **AUDUSD/NZDUSD**, preordered as C1 by the prior pair-universe data-availability
audit (data availability only — **not** selected on performance).

## 2. Future G3 design (NOT executed in this stage)

If separately authorized, the future G3 statistical screen will follow the same core design used for
the prior EURUSD/GBPUSD study:

- 60 / 20 / 20 chronological split (train / validation / sealed);
- 30-bar embargoes between train→validation and validation→sealed;
- **train-only** OLS hedge ratio (fixed for all out-of-sample residual spreads);
- ADF (`regression="c"`, `autolag="AIC"`), Johansen (`det_order=0`, `k_ar_diff=1`), AR(1)/OU
  half-life, variance ratio (q = 2, 4, 8, 16), subperiod and bootstrap diagnostics;
- pre-sealed rolling **primary** stability check at **5,000 / 1,000**;
- rolling **sensitivity** at 4,000 / 1,000 and 6,000 / 1,000;
- **sealed rolling** confirmatory only;
- random **seed 42**;
- **stationary bootstrap of aligned AR(1) observations**, 1,000 resamples, average block length 24;
- differences of the residual spread used only for AR(1), variance-ratio, and bootstrap diagnostics
  (not asset/strategy returns);
- internal ordinal clock only (`NOT_UTC`); no absolute-time/session/event/external alignment.

**These tests are not executed in this stage.** The future G3 is permitted only after a separate
explicit authorization, and only against the frozen, hash-verified snapshot
`audnzd_h1_internal_snapshot_v1.csv` (comment line skipped).

## 3. Meaning of a future G3 approval

Approval of a future G3 would mean **only** that a **cost-aware economic test may be designed**. It
does **not** establish profitability and does **not** authorize trading.

## 4. G0/G1 status

- **G0** (execution isolation): PASS (research library remains isolated from execution/broker code).
- **G1** (data audit): PASS for the frozen internal-clock snapshot (see `G1_DATA_AUDIT.md`).
- **G3 onward:** NOT_RUN.
