# Gold Engine (XAUUSD) — Evidence Recovery & Track-Record Plan

**Created:** 2026-09-22
**Status:** ⚠️ **DEPRIORITISED — see the note below.** The exit-management study
(EXP-2026-10/11) found **no robust edge** in the operator's own manual gold
entries, and the manual record itself is a net loss. Fixing the measurement of a
line with no demonstrated edge is no longer the top priority.
**Context:** Option A of `ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md` §6.2 (the
directional-ML program is closed; gold was the nominated destination — but the
audit found gold is *also* unproven).
**Related:** `docs/experiments/EXP-2026-03-RULEENGINE_gold-rules-engine-design.md`
(design contract), `frival/gold_rules/config.yaml` (parameters),
`frival/gold_rules/config/settings.yaml` (`trading.mode`).

> **Update 2026-09-22 (after EXP-2026-10/11):** the "would better SL/TP make the
> manual gold entries profitable?" question was tested and answered **no** — no
> mechanical exit policy extracts a robust edge (the one positive policy was
> driven by 3 trades in a single week with a −$58.7k simulated drawdown). The
> manual account itself is a net loss (139 trades, PF 0.94). So this plan's fix
> (make the gold engine measure itself) remains *technically correct* but is **no
> longer the highest-value next action** — see `ROADMAP-2026-Q4-AUDIT-AND-NEXT-STEPS.md`
> §6.4 for the revised strategic decision. Keep this document as the execution
> spec if/when a gold program is ever funded on a *new* hypothesis.

---

## 0. The problem this plan exists to fix (audit finding G7)

The roadmap repeatedly called gold "the only asset with real recorded PnL."
**That is false.** Verified 2026-09-22:

- `frival/gold_rules/config/settings.yaml` → `trading.mode: demo`.
- `OrderManager` therefore **simulates** orders — the journal's `ORDER_SENT`
  entries read `"comment": "DEMO MODE - Simulated execution"`, `order: 0`,
  `deal: 0`.
- But the engine's exit detection (`frival/gold_rules/engine.py:786`) closes the
  in-trade state whenever `snap.open_positions == 0`, and `open_positions` is fed
  from **real** broker positions (`run_gold_rules.py` `positions_open()` →
  `conn.get_positions("XAUUSD")`) — which is always 0 in demo, because no real
  position was ever opened.
- Result: **every simulated trade self-closes on the next 60-second tick.** The
  journal shows exactly this — 2 `ENTRY` events on 2026-09-22, each followed by
  `CLOSE` ~1 minute later with `"reason": "open XAUUSD position count == 0"` and
  `pnl: 0.0`.
- The alternative `--dry` path simulates the position slot (`dry_positions`) but
  **never realizes `dry_pnl`** — it stays 0.0 — so it measures nothing either.

**Net: zero usable gold evidence.** 6 journal days (2026-09-15→22) of
`WATCH_ZONE`/`CONFIRM` logging + 2 phantom trades with zero PnL. Gold is an
untested rules engine with a broken demo measurement loop — not a proven asset.

---

## 1. Fix scope — make demo mode simulate the *whole* trade lifecycle and realize PnL

**Objective.** In demo mode, the engine must: open a simulated position, hold it
across ticks, run its management (break-even at 50%, trailing, §2.7
invalidation), exit on simulated SL/TP/invalidation/close, and record a **realized
R and USD PnL per trade** — using price action, not broker positions.

**Files to modify (only these):**
- `frival/gold_rules/run_gold_rules.py`
  - `positions_open()` — in demo mode, return the **simulated** position count
    (as `--dry` already does via `dry_positions`), not the real broker count.
    This alone stops the instant self-close.
  - `execute_order()` / `close_position()` — in demo mode, update the simulated
    slot **and** compute realized PnL; on close, write the trade's realized
    `pnl`, `R` (= (exit−entry)/risk × direction), and exit reason into the
    journal + a per-trade ledger.
  - Add a `demo` condition that reuses the existing `dry_*` bookkeeping (today it
    is keyed only on the `--dry` CLI flag; it must also trigger when
    `cm.is_demo_mode()` is true).
- `frival/gold_rules/engine.py`
  - No state-machine change expected — the engine already emits
    SL/TP/BE/TRAIL/INVALIDATE decisions; the runner just needs to *act on them
    against price* in demo. Confirm `Snapshot.open_positions` semantics are
    "positions the engine believes it holds" (so demo passes the simulated count).

**Do NOT change:** entry logic, gates, risk atomics, config parameters, the
design-doc contract. This is a **measurement** fix, not a strategy change — so it
does not consume experiment budget or alter the thing being tested.

**Acceptance criteria (all must hold):**
1. A deterministic replay over historical XAUUSD M15 bars (extend
   `frival/gold_rules/tests/sanity_walk.py`) produces ≥ 20 simulated trades whose
   lifecycle spans multiple ticks — i.e. no instant self-close.
2. Each simulated trade records `entry`, `sl`, `tp1`, `exit`, `exit_reason`,
   `realized_R`, `realized_usd` — and the journal's `CLOSE` shows a **non-zero**
   `pnl` for at least some trades (a permanently-zero PnL is the current bug
   signature and must be impossible).
3. Break-even/trailing/invalidation are exercised in the replay (assert at least
   one BE move and one invalidation fire in the fixture walk).
4. `frival/gold_rules/tests/` suite stays green; add a regression test that the
   demo/dry path **never** consults real broker positions for lifecycle state.

**Feasibility note (cheap):** the existing `--dry` bookkeeping proves the
simulated-slot mechanism already exists — the fix is mainly (a) widening its
trigger to demo mode and (b) adding PnL realization. This is a small, well-scoped
change, not a rewrite.

---

## 2. Then — accumulate a real track record (evidence, not optimization)

Once the loop measures correctly, the engine needs **paper evidence before any
research decision**. Proposed, pre-registered:

- **Window:** ≥ 4 weeks of continuous demo operation (the engine ticks every 60 s,
  M15/M30/H1-driven; expect a realistic handful of trades, not hundreds).
- **Record per trade:** entry/exit, reason, realized R, realized USD, MFE/MAE,
  duration; plus daily session PnL and daily-cap events.
- **Metrics to report:** trade count, win%, mean realized R, R distribution,
  max drawdown, daily-cap breach count — the same EV/R vocabulary used across the
  ML experiments, so results are directly comparable.
- **Decision gate (pre-register before the window starts):**
  - **CONTINUE →** investigate an ML/extension program: mean realized R > 0 with
    CI lower bound > −0.05 over ≥ 30 trades.
  - **HOLD →** insufficient trades or CI straddles zero: extend the window.
  - **STOP →** mean realized R ≤ −0.05 with CI upper bound < 0: the A/B + Claim-C
    rules do not work on gold either; close the rules line.
- **Discipline:** no parameter tuning during the window (mirror the ML
  experiments' single-scoring rule). Any change restarts the window.

**Honest expectation setting:** `EXP-2026-04` already showed the A/B gold rules do
**not** transfer to FX. The gold rules have never been measured on gold. A
negative result here is as likely as a positive one — the point is to *finally
have a number* instead of an assumption.

---

## 3. Risks / caveats

- **Demo fills are not real fills.** Simulated entry at `bid`/`ask` ignores
  slippage and re-quote; treat realized R as an *upper bound* until live. (Same
  §6.1 measurement gap flagged in the audit — applies to gold too.)
- **Swap/financing** on gold is not modelled in the simulation; XAUUSD CFD carry
  is real and regime-dependent. Add as a diagnostic line, not a silent omission.
- **Tiny sample risk.** A 60-second-tick rules engine on M15 may produce very few
  trades in 4 weeks → HOLD may be the most common outcome; size the window
  accordingly and don't force a verdict on < 30 trades.
- **The `ENGINE_ERROR` bug** seen once on 2026-09-15 (`'tuple' object has no
  attribute 'h1_bias'`) should be confirmed fixed and covered by a test before
  the evidence window starts.

---

## 4. Order of work (execution checklist)

1. [ ] Confirm the self-close mechanism with a 10-minute local replay (expect:
      instant `CLOSE`, `pnl 0.0` — the bug).
2. [ ] Implement the demo-mode simulation + PnL realization (§1).
3. [ ] Add/extend the replay test to the acceptance criteria in §1; run
      `frival/gold_rules/tests/`.
4. [ ] Confirm the `ENGINE_ERROR` from 2026-09-15 is fixed + tested.
5. [ ] Start the paper-evidence window (§2) and record the pre-registered gate
      in the EXP-2026-03 RUN_LOG (or a new `EXP-2026-10-GOLD-EVIDENCE` manifest).
6. [ ] After the window: apply the §2 gate; only then decide whether a gold
      research program is warranted.

*Until step 4 passes, gold remains an unmeasured assumption — the same status the
roadmap wrongly believed it had escaped.*