# RUN_LOG — EXP-2026-13-EVENT-DRIVEN

One dated entry per run. The unseen evaluation window (2025→present) is scored
ONCE per grid. Material change after scoring = EXP-2026-13b + supersede note.

| Date (UTC) | Action | Verification | Result | Notes |
|---|---|---|---|---|
| 2026-09-22 | Manifest pre-registered (a-priori sign rule, grid 6×3, gate) | n/a — no run yet | — | Universe 6 pairs; calendar 92,616 events (40,116 with Deviation); eval 2025→present |
| 2026-09-22 | **Sealed eval window scored (2025→present, events with Deviation)** | grid 6 pairs × {1,4,24}h; block-bootstrap CI | **HOLD (gate overridden by audit — see below)** | Raw gate: GO on XAUUSD 1/4/24h + GBPUSD 24h. Audit REJECTED that as trend/regime artifact. |

## Grid results (net-of-cost, bp per event, 2025+)

| Pair | 1h | 4h | 24h | Read |
|---|---|---|---|---|
| EURUSD | −1.04 | −1.16 | −1.50 | priced-in within the hour |
| GBPUSD | −1.76 | −1.01 | +0.30 | priced-in |
| USDCHF | −1.22 | −1.77 | −1.81 | priced-in |
| USDJPY | −0.94 | −1.76 | −0.58 | priced-in |
| XAUUSD | **+2.71** | **+2.54** | **+13.23** | see audit below |
| USDCAD | −0.78 | −1.67 | −0.44 | priced-in |

## Audit that overrode the naive GO (recorded evidence)

1. **FX 1h all negative/zero** — the textbook "macro surprise is efficiently priced
   within the hour" null; consistent and believable.
2. **XAUUSD 24h +13 bp is HALF trend**: unconditional gold 24h drift on ALL days
   2025+ is +6.9 bp, so the "reaction" is +7.7 bp over drift — the 24h cells are
   contaminated by the 2025–26 gold rally, not reaction.
3. **XAUUSD 1h, the defensible candidate, is 2025-ONLY**:
   - 2025: +4.89 bp, win 56.4%, **CI [+2.3, +7.7]** (significant)
   - 2026: +1.06 bp, win 53.1%, **CI [−6.0, +8.2]** (at zero)
   - HIGH-only 2025+: +3.82 bp, CI [−2.0, +8.6] (not significant)
   - unconditional 1h baseline: +0.59 bp.
   The effect existed in 2025 and has **faded into 2026**. That is a regime
   effect, not a stable edge.
4. **Block-bootstrap CI on overlapping sub-windows** is not fully independent for
   24h cells — event days are close, drift is shared.

## Verdict — HOLD (documented, not a false GO)

- No cell is robust across the full pre-registered eval window (2025→present):
  the naive XAUUSD GO came from the 2025 leg which does not persist into 2026.
- FX is a clean, consistent null: **scheduled macro surprises are priced in
  within the hour, net of cost, in FX** — a defensible scientific statement.
- XAUUSD 1h in 2025 is the ONLY statistically-significant positive, but it is
  *regime-dependent* (gold's 2025 USD-correlation environment) and gone in 2026.
- **Decision:** HOLD per the audit. Do not proceed to an ML/strategy stage on a
  non-stable regime effect. Record the FX null as a permanent result; keep XAUUSD
  1h flagged as a monitor-if-gold-environment-repeats, not an active trade.