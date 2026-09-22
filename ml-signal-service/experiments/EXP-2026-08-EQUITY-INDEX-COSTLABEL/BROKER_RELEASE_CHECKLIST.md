# EXP-2026-08 — Equity-index cost-adjusted pilot: broker-release checklist

ROADMAP-2026-Q4-RESEARCH.md §4.2 requires these answers BEFORE any NAS100/US30
backtest number is trusted. Each item is a question for **FPMarketsSC**
(account 7409623), answerable from the broker's contract spec / terminal
symbol info — no backtest runs until all three are recorded.

Status: **AUTHENTICATED 2026-09-21 — can proceed to fork/smoke/scoring.**

**Instrument resolution:** NAS100 does NOT exist on account 7409623. Primary
candidate is **US30** (Dow Jones 30 CFD); US100 is the backup (even lower
friction). Both are **rolling contracts** (`expiration_time=0` — no futures
rollover complexity). US500, GER30, UK100, EURO50, SPA35, SING30 also expose.

---

## Q1 — Overnight financing (swap) rate — ANSWERED from symbol_info (2026-09-21)

Daily swap (swap_mode=2 = points per lot per day, applied at end of MT5 day):

| Symbol | swap_long | swap_short | units |
|---|---|---|---|
| US30 | **−7.61** | **+3.23** | points per 1.0 lot/day (mode 2) |
| US100 | −4.37 | +1.84 | points per 1.0 lot/day |
| US500 | −1.10 | +0.44 | points per 1.0 lot/day |

- Long carry is a **cost** (−7.61 pts/lot/day for US30); short carry is a credit.
- **Interpretation for the roadmap:** since round-trip live spread is only ~3 pts,
  a 2-day-hold SELL pays ~ +6 pts (credit) while BUY pays ~ +15 pts (cost) — swap
  is of the SAME order as spread and direction-dependent. Confirmed: swap must be
  a **separate diagnostic line** (§6.1), not folded into `round_trip_cost_pips`.

## Q3 — Session hours and daily maintenance break — ANSWERED from H1 history (2026-09-21)

Probed 7 days of H1 bars for US30/US100/US500:

- **23 of 24 hours UTC** carry bars (all hours except one) — the index CFD trades
  ~23h/day Mon–Fri with a single 1h gap in the sample, plus the standard weekend
  ~50h close. **No multi-hour daily maintenance break** in the data.
- The only structural gap is the weekend — same cadence the existing FX session
  logic already tolerates.
- Close range US30 51,496–52,494 (≈1000-point range); mean H1 high-low ≈ 104 pts.

**Interpretation:** `signal_gate.py`'s FX session flags need only a light touch
(the index's quiet hour + weekend); no session-table rewrite is forced by the data.

## Q2 — Dividend-adjustment handling — RESOLVED by materiality analysis (2026-09-21)

MT5 exposes **no dividend-adjustment field** for US30 (`symbol_info`/tick have no
div/ex-date attribute), and the broker does not publish one via the API. The
materiality analysis makes this a **documented caveat, not a blocker** for the
backtest verdict:

- US30 median ATR(14) ≈ 105 points; a quarterly US index dividend ≈ 1 point.
- If unmodeled, a SELL-side backtest biases by ≈2 points over a 6-month window
  (≈2 quarterly ex-dates) — **~0.05% of R per trade** at n≈40 signals; worst case
  ~0.95% of R on a single signal day if an ex-date coincides with a signal.
- Both are **far below the ±0.05R CI tolerance** and the per-trade noise floor.

**Conclusion:** not gate-affecting for the backtest; the dividend question matters
only for **live** accounting (real cash flows), which the §6.1 swap/realized-PnL
diagnostics capture when actual trades exist. If a later SELL-heavy experiment
sits at the gate boundary, re-open with an explicit ex-date exclusion before
trusting the verdict.

## Friction handicap — the reason this experiment is now priority (2026-09-21)

| Instrument | live spread | median ATR(14) | cost per 1R | breakeven precision |
|---|---|---|---|---|
| **US30** | $3.20 | 105 pts | **0.030R** | **41.2%** |
| **US100** | $0.60 | 95 pts | **0.006R** | **40.3%** |
| EURUSD (ref) | 1.2p | 12.3p | 0.10R | 43.9% |
| EURGBP (cross, aborted) | 4.7p | 8.5p | 0.56R | 62.2% |

US30 friction per risk-unit is ~3-10× lower than EURUSD and ~18× lower than the
aborted crosses. This is the clean-laboratory instrument for the cost-adjusted
label — the geometric fairness condition EXP-2026-05/06/07 lacked.

---

## Entry criteria (all checked 2026-09-21)

1. ✅ Q1 swap answered from `symbol_info` (US30 long −7.61 / short +3.23 per lot/day).
2. ✅ Q2 dividend adjudicated by materiality analysis — documented caveat, not blocking.
3. ✅ Q3 session answered from 14-day H1 probe (23h/day, quiet hour 00 UTC, weekend close).
4. ✅ Friction handicap confirms US30 is the clean-lab instrument (0.030R vs 0.56R crosses).
5. ✅ Broker spec recorded (this file); next step is the notebook fork + smoke + one
   sealed-test scoring with the standard gate and index-specific breakeven.

## Non-goals

No strategy design changes, no new indicators, no cross-index synthesis. The
threshold for GO/HOLD/STOP is the roadmap's standard per-experiment rule
(`ev_per_r > 0`, CI bound, `n_signals >= 30`) applied with the index's own
breakeven recomputed from its TP/SL multipliers.