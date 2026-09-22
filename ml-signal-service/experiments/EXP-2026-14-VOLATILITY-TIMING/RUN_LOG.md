# RUN_LOG — EXP-2026-14-VOLATILITY-TIMING

| Date (UTC) | Action | Verification | Result | Notes |
|---|---|---|---|---|
| 2026-09-22 | Manifest pre-registered (CALM vs VOLATILE trade-EV, 2019-24 learn / 2025+ eval) | n/a — no run yet | — | 4 majors; regime = ATR < trailing 30-day median |
| 2026-09-22 | **Sealed eval window scored** | grid 4 pairs × 2 regimes, block CI | **REJECTED** (no CALM EV > 0) | records below |

## Result (net-of-cost EV, bp/trade, 2025+)

| Pair | CALM EV | VOL EV | diff | CALM CI |
|---|---|---|---|---|
| EURUSD | −3.48 | −9.67 | +6.18 | [−3.94, −3.02] |
| GBPUSD | −3.60 | −9.96 | +6.37 | [−4.06, −3.09] |
| USDCHF | −3.79 | −9.11 | +5.32 | [−4.34, −3.25] |
| USDCAD | −3.27 | −7.52 | +4.25 | [−3.61, −2.95] |

## Interpretation

- **Directional truth confirmed:** CALM is consistently less negative than VOLATILE
  (+4.2 to +6.4 bp), i.e. volatility-clustering is present and trades do worse in
  expansion regimes — exactly as the stylized fact predicts.
- **But not tradeable:** even the calm pocket is **negative** everywhere (−3.3 to
  −3.8 bp). The signal-to-cost ratio is insufficient even where it is best.
- **Verdict: REJECTED** as a portfolio ingredient — the regime split is a useful
  *risk* fact ("never trade in expansion") but cannot be a standalone edge.
- This is the first experiment where we broke into *why* rather than *whether*:
  the effect exists, the costs don't let it pay. Same conclusion, better resolution.