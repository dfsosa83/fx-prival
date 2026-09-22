# EXP-2026-13 — Event-driven macro reaction

**Verdict (2026-09-22):** HOLD. FX macro surprises are **priced in within the
hour** (a clean, believable null); the one positive (XAUUSD 1h) is a **2025-only
regime effect** that fades to zero in 2026.

## Hypothesis (one line)

A scheduled macro event's Deviation (actual vs Consensus) predicts price
movement in the direction implied by the surprised currency, net of cost.

## Design

- 6 pairs (EURUSD, GBPUSD, USDCHF, USDJPY, XAUUSD, USDCAD) × windows {1, 4, 24}h.
- **Zero fitted parameters**: a-priori sign rule (base-currency surprise → long,
  quote-currency surprise → short; gold is USD-quote).
- Events: HIGH/MED impact with known Deviation from the real 92,616-event
  economic calendar (2007–2026), evaluated on the unseen **2025→present** window.
- Costs: round-trip spread from `_core/costs.py`.

## Result (net-of-cost, bp/event, 2025+)

| Pair | 1h | 4h | 24h |
|---|---|---|---|
| EURUSD | −1.04 | −1.16 | −1.50 |
| GBPUSD | −1.76 | −1.01 | +0.30 |
| USDCHF | −1.22 | −1.77 | −1.81 |
| USDJPY | −0.94 | −1.76 | −0.58 |
| XAUUSD | +2.71 | +2.54 | +13.23 |
| USDCAD | −0.78 | −1.67 | −0.44 |

## Why not GO (the audit that mattered)

- The raw gate GO (XAUUSD all windows + GBPUSD 24h) was **rejected** after:
  - XAUUSD 24h is half unconditional gold drift (+6.9 bp on all days).
  - XAUUSD 1h is **2025-only**: 2025 +4.89 bp CI [+2.3,+7.7]; **2026 +1.06 bp
    CI [−6,+8]** — the effect does not persist.
  - FX 1h all negative = the honest, expected "efficiently priced" null.

## Run it
```
python experiments/EXP-2026-13-EVENT-DRIVEN/run_event.py
```
(Costs + calendar + H1 data already in place; no new data acquisition.)