"""Shared cost model — single source of truth for per-pair trading friction.

ROADMAP-2026-Q4-RESEARCH.md, §2 Issue C / §9 P0.0.

Every backtest, cost-adjusted label, and paper-trading report reads its cost
constants from here. No experiment may carry its own copy of these numbers.

Cost model policy (as of 2026-09-21):
- ``MEASURED_SPREAD_PIPS``   — live-measured spread ONLY (Standard account, no
  commission line), measured 2026-09-18, quoted in pips.
- ``SLIPPAGE_PIPS``          — 0.0 everywhere until measured from the first ~30
  real paper fills per pair (roadmap §6.1 / P0.2). Do NOT guess it (Issue C).
  Use :func:`set_slippage_pips` when the measurement exists.
- ``SESSION_KEY`` / ``SESSION_MULTIPLIER`` — flat (1.0) everywhere until
  session-conditioned spread data exists (Issue C #3: Asian-session spread on
  EURUSD is routinely 2-3x the London/NY overlap spread). TODO: fill from live
  tick data per session.
- ``PIP_SIZE_PX``            — price units per pip per symbol, following the
  MT5 quotation convention: 5-decimal FX (EURUSD, GBPUSD, USDCHF, USDCAD,
  EURGBP) = 1e-4; 3-decimal FX (USDJPY, GBPJPY, EURJPY) = 1e-2; XAUUSD = 1e-2
  (gold "point"); index CFDs (US30, US100) = 1e-2 (MT5 point).
"""

from __future__ import annotations

from typing import Dict

# ── Pip conventions (price units per pip) ─────────────────────────────────────
PIP_SIZE_PX: Dict[str, float] = {
    "EURUSD": 1e-4,
    "GBPUSD": 1e-4,
    "USDCHF": 1e-4,
    "USDCAD": 1e-4,
    "USDJPY": 1e-2,
    "XAUUSD": 1e-2,  # MT5 gold point (0.01); the 2026-09-18 measurement used this unit
    "EURGBP": 1e-4,  # EXP-2026-07 crosses (spread measured 2026-09-21)
    "GBPJPY": 1e-2,
    "EURJPY": 1e-2,
    "US30": 1e-2,    # EXP-2026-08 index CFD: point convention (MT5 point=0.01)
    "US100": 1e-2,
}

# ── Live measured spread (pips) — 2026-09-18 (PROJECT-CONTEXT.md §6) ──────────
# Standard account: spread is embedded in ask/bid; there is NO commission line.
# These are point-in-time (mid-session) measurements, not session-conditioned.
MEASURED_SPREAD_PIPS: Dict[str, float] = {
    "EURUSD": 1.2,
    "GBPUSD": 1.6,
    "USDCHF": 1.5,
    "USDCAD": 1.5,
    "USDJPY": 1.3,
    "XAUUSD": 0.28,  # ~0.28 x 0.01 = ~0.0028 USD on gold
    # ── EXP-2026-07 liquid crosses — measured 2026-09-21, 3 stable samples each,
    #    mid-session (FPMarketsSC-Demo). JPY crosses genuinely run ~10-14 pips —
    #    expected for 3-decimal quotes; do NOT average these into majors.
    "EURGBP": 4.7,   # 0.00047 / 1e-4
    "GBPJPY": 13.6,  # 0.136  / 1e-2
    "EURJPY": 10.6,  # 0.106  / 1e-2
    # ── EXP-2026-08 index CFDs — measured live 2026-09-21 (point convention
    #    = 1e-2; "pip" here = 1 MT5 point, e.g. US30 3.2 / 0.01 = 320).
    #    Friction per 1R is ~0.03R (US30) / ~0.006R (US100) — the reason these
    #    are the clean-lab instrument for the cost-adjusted label.
    "US30": 320.0,   # 3.2 px spread on ~51k quote
    "US100": 60.0,   # 0.6 px spread on ~29k quote
}

# ── Slippage (pips) — unmeasured until P0.2 (paper fills) ────────────────────
# Do NOT fill by guessing. Measured from the first ~30 real paper fills per pair
# (roadmap §6.1 diagnostic: signal price vs actual MT5 fill price).
SLIPPAGE_PIPS: Dict[str, float] = {pair: 0.0 for pair in MEASURED_SPREAD_PIPS}


def set_slippage_pips(pair: str, pips: float) -> None:
    """Record measured slippage for a pair (roadmap §6.1 / P0.2).

    Called by the paper-trading measurement step once enough fills exist.
    """
    if pair not in MEASURED_SPREAD_PIPS:
        raise KeyError(
            f"Slippage can only be set for pairs with a measured spread; got {pair!r}. "
            "Add the pair to MEASURED_SPREAD_PIPS first."
        )
    if pips < 0.0:
        raise ValueError(f"Slippage cannot be negative; got {pips}. Same-side slippage "
                         "is a cost in the barrier direction, never a rebate.")
    SLIPPAGE_PIPS[pair] = float(pips)
    ROUND_TRIP_COST_PIPS[pair] = {
        session: _round_trip(pair, session) for session in SESSIONS
    }


def _round_trip(pair: str, session: str = "ALL") -> float:
    """Total round-trip cost in pips for a pair/session (spread + slippage).

    Used internally by :func:`cost_pips` and :data:`ROUND_TRIP_COST_PIPS` so
    the label, backtest, and dashboard all read the exact same number.
    """
    if pair not in MEASURED_SPREAD_PIPS:
        raise KeyError(
            f"No measured cost for pair {pair!r}. Measured: {sorted(MEASURED_SPREAD_PIPS)}."
        )
    return MEASURED_SPREAD_PIPS[pair] + SLIPPAGE_PIPS[pair]


# Session keys follow the feature flags in frival/model/features.py
# (session_asian / session_london / session_ny / session_overlap).
SESSIONS = ("ALL", "ASIAN", "LONDON", "NEWYORK", "OVERLAP")


def _build_round_trip_table() -> Dict[str, Dict[str, float]]:
    """Materialize the nested per-pair/per-session table (roadmap P0.0 spec)."""
    return {
        pair: {session: _round_trip(pair, session) for session in SESSIONS}
        for pair in MEASURED_SPREAD_PIPS
    }


# Single source of truth consumed by labels, backtests and the dashboard.
# Regenerated whenever slippage is updated via :func:`set_slippage_pips`.
ROUND_TRIP_COST_PIPS: Dict[str, Dict[str, float]] = _build_round_trip_table()


def cost_pips(pair: str, session: str = "ALL") -> float:
    """Round-trip cost in pips for a pair and session.

    Session dimension is flat (1.0 multiplier) until session-conditioned spread
    data is measured — see module docstring. Raises for unknown pairs/sessions
    so mistakes surface immediately instead of silently using a wrong cost.
    """
    if session not in SESSIONS:
        raise KeyError(f"Unknown session {session!r}. Valid: {SESSIONS}.")
    return ROUND_TRIP_COST_PIPS[pair][session]


def to_price(pair: str, pips: float) -> float:
    """Convert pips into price units for a pair (pips * pip size)."""
    if pair not in PIP_SIZE_PX:
        raise KeyError(
            f"No pip convention for pair {pair!r}. Known: {sorted(PIP_SIZE_PX)}."
        )
    return float(pips) * PIP_SIZE_PX[pair]


def apply_cost_to_barrier(
    entry: float,
    atr: float,
    mult: float,
    direction: str,
    cost_pips: float,
    pair: str | None = None,
    pip_size: float | None = None,
) -> float:
    """Apply round-trip friction to a TP barrier level.

    Cost makes the barrier HARDER to reach, never easier (roadmap §3 label #1):

    - SELL (short): TP sits below entry; the cost pushes it further down.
        barrier = entry - atr*mult  - cost_in_price
    - BUY  (long):  TP sits above entry; the cost pushes it further up.
        barrier = entry + atr*mult  + cost_in_price

    Parameters
    ----------
    entry : entry price (close[t])
    atr : ATR(14) value at t
    mult : TP multiplier (ATR_TP_MULT)
    direction : "BUY" or "SELL"
    cost_pips : round-trip cost in pips (see :func:`cost_pips`)
    pair : symbol, used to derive pip_size from PIP_SIZE_PX (recommended)
    pip_size : alternative to `pair`, price units per pip

    Returns
    -------
    float : cost-adjusted TP barrier price.
    """
    direction = direction.upper()
    if direction not in ("BUY", "SELL"):
        raise ValueError(f"direction must be 'BUY' or 'SELL'; got {direction!r}")

    if pip_size is None:
        if pair is None:
            raise ValueError("apply_cost_to_barrier needs `pair` or `pip_size` to "
                             "convert pips to price units (see to_price).")
        pip_size = PIP_SIZE_PX[pair]

    cost_price = float(cost_pips) * pip_size
    distance = float(mult) * float(atr)

    if direction == "SELL":
        # TP below entry; cost pushes it FURTHER below entry.
        return float(entry) - distance - cost_price
    # BUY: TP above entry; cost pushes it FURTHER above entry.
    return float(entry) + distance + cost_price