# REPORT — AUDIT-2026-09-28-FRIVAL-SHADOWRUN-CROSSCHECK

**Date:** 2026-09-28
**Status:** COMPLETE
**Recommendation:** **NOT CONFIRMED** — the operational record contains no usable outcome evidence of edge for the legacy H1 ML pipeline on 2026-09-28.

---

## 1. Objective

Cross-check the 2026-09-28 shadow-run signal evidence (`frival/output/signals/2026-09/2026-09-28.jsonl`) against execution records (`execution_log.jsonl`, `demo_trades_ledger.jsonl`) to confirm whether any edge exists.

---

## 2. Signal Evidence (2026-09-28)

| Metric | Value |
|---|---|
| Total signals | 19 (EURUSD 5, GBPUSD 4, USDCHF 5, USDCAD 5) |
| SHELVED (gate/agent veto) | 17 |
| FIRED | 2 — both EURUSD SELL, both via the **borderline lane** |

| FIRED signal | Probability | Threshold | Lane |
|---|---|---|---|
| `EURUSD_H1_SELL_2026-09-28T16:00:00Z` | 0.2451 | 0.276 | borderline (`0.20 ≤ p < threshold`) |
| `EURUSD_H1_SELL_2026-09-28T17:00:00Z` | 0.2495 | 0.276 | borderline |

Both fired signals had **both agents CONFIRM** (`gate_type: borderline`, `veto_reason: ""`).

**Lane semantics verified against source (`signal_gate.py`):** in borderline mode, bars with `BORDERLINE_THRESHOLD (0.20) ≤ p < threshold` are admitted to agent evaluation; `synthesize_borderline` (`agents/senior.py`) requires **both** agents to CONFIRM for FIRED. The two 09-28 fires are **by design, not a gate failure**.

**No threshold-passing (standard-lane) signal fired on 2026-09-28.**

---

## 3. Execution Cross-Reference

Both FIRED signals appear in `execution_log.jsonl` as `EXECUTED`:

| Timestamp (execution) | Signal | daily_pnl |
|---|---|---|
| 2026-09-28T16:03:22Z | EURUSD SELL 16:00Z | 0 |
| 2026-09-28T17:03:16Z | EURUSD SELL 17:00Z | 0 |

Execution latency ~3 min after the signal bar, consistent with the scheduler. **No ERROR/SKIPPED on either fire.**

Sep-2x `EXECUTED` total: 5 (GBPUSD SELL 09-21 ×2, GBPUSD SELL 09-23 ×1, EURUSD SELL 09-28 ×2). All booked `daily_pnl = 0`.

---

## 4. Outcome Evidence

| Source | Content | Outcome evidence? |
|---|---|---|
| `demo_trades_ledger.jsonl` | **2 rows, both gold**, legacy 09-22 era: GOLD sell SL −$5.00 (R −1.0); GOLD sell TP +$10.00 (R +2.0). Net +$5.00 | **No FX rows. Zero FX outcome records.** |
| `execution_log.jsonl` | 593 rows historical: 316 ERROR, 272 EXECUTED, 5 SKIPPED | `daily_pnl` is a booking field, not realized outcome tracking |
| `output/logs/2026-09-28_live.log` | Scheduler/pipeline activity | Operational, not PnL |

**Finding F1 (VERIFIED):** The FX virtual-fill ledger has **zero rows** since the 2026-09-22 demo-PnL fix. No exit/outcome is attributable to any FX signal, including the two 09-28 fires. The 09-28 shadow-run therefore produced **no outcome evidence from which an edge could be measured or inferred.**

**Finding F2 (VERIFIED):** The borderline lane fired exactly as designed (both agents CONFIRM; lane = `0.20 ≤ p < threshold`). The two fires are lower-confidence signals by construction — not evidence of model skill.

**Finding F3 (VERIFIED, operational gap):** The paper-PnL loop is not yet producing FX outcome rows. Whether this is a fill-generation gap, a closing/exit gap, or a ledger-write gap is **outside this audit's scope** but is a prerequisite for any future observability claim (PORTFOLIO-DEMO-SPEC requires auditable paper outcomes).

---

## 5. Conclusion

**NOT CONFIRMED — no edge evidence in the operational record.**

- The 2026-09-28 shadow run produced 19 signals; 17 vetoed, 2 fired in the designed low-confidence borderline lane and were executed.
- Neither the ledger nor the execution log contains any realized outcome for those (or any) FX signals.
- Zero outcome evidence ⇏ zero edge, but the record is consistent with and does not contradict the Family 1 CLOSED verdict. **No positive claim can be made.**

This audit makes no strategy recommendation and reopens no research family.

---

## 6. Evidence Files

- Signal records: `frival/output/signals/2026-09/2026-09-28.jsonl`
- Execution records: `frival/execution_bot/data/execution_log.jsonl`
- Ledger: `frival/execution_bot/data/demo_trades_ledger.jsonl`
- Gate semantics: `frival/signal_gate.py` (lines 25, 75–112)
- Borderline synthesis: `frival/agents/senior.py::synthesize_borderline`

*No files outside this audit folder were modified.*
