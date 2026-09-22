# -*- coding: utf-8 -*-
"""Per-tag performance metrics — cost-adjusted EV/R with block-bootstrap CI.

ROADMAP-2026-Q4-RESEARCH.md §8 Stage 2 / §9 P0.2.

Single source of truth for the *statistics* used by the dashboard's Stage 2
per-comment-tag aggregation and by fx_rules_backtest reporting. The *cost
constants* and *bootstrap method* live in `ml-signal-service/experiments/_core`
(costs.py, bootstrap.py) — nothing here re-implements them.

Lifecycle rule (roadmap §9 P0.2 stopping condition): no code path reports a
zero-cost EV/R "as if it were final". Every EV/R emitted from this module is
net of the shared round-trip cost constant and carries a 95% CI.
"""

from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Sequence

# ── Hook ml-signal-service experiments (single source of truth) ───────────────
# dashboard/backend/tag_metrics.py -> frival/ -> fx-prival/ -> ml-signal-service
from pathlib import Path as _Path

_FX_PRIVAL = _Path(__file__).resolve().parents[3]
_ML_SERVICE = _FX_PRIVAL / "ml-signal-service"
if str(_ML_SERVICE) not in sys.path:
    sys.path.insert(0, str(_ML_SERVICE))

import numpy as _np  # noqa: E402

from experiments._core import bootstrap as _bootstrap  # noqa: E402
from experiments._core import costs as _costs  # noqa: E402


# ── Tag classification (matches dashboard's existing GOLD_COMMENTS) ───────────
GOLD_TAGS = ("GOLD_RULES_v1", "GOLD_RULES_C")
FX_ML_TAG = "FX_ML"          # non-gold MT5 deals attributed to the FX/ML book
DEFAULT_TAG = "UNKNOWN"


def classify_tag(comment: str) -> str:
    """Map an MT5 deal comment to a dashboard Stage-2 tag.

    Gold-engine orders carry GOLD_RULES_v1 / GOLD_RULES_C comments (§2.4.2);
    everything else that closed a position on the Frival account is the FX-ML
    book (execution bot writes `frival_...` comments). Unknown/empty comments
    are grouped under UNKNOWN rather than silently counted anywhere.
    """
    c = (comment or "").strip()
    for tag in GOLD_TAGS:
        if tag in c:
            return tag
    if c:
        return FX_ML_TAG if c.lower().startswith("frival") else DEFAULT_TAG
    return DEFAULT_TAG


def round_trip_cost_pips(pair: str, session: str = "ALL") -> float:
    """Round-trip friction in pips from the shared cost table (Issue C)."""
    return _costs.cost_pips(pair, session)


def cost_in_R(pair: str, cost_pips: float, risk_price: float) -> float:
    """Convert a pip-denominated round-trip cost into R-units.

    R is measured in units of the initial risk distance (|entry - SL|).
    cost_R = cost_in_price / risk_distance  =>  R_net = R - cost_R.
    """
    cost_price = _costs.to_price(pair, cost_pips)
    if risk_price <= 0.0:
        raise ValueError(f"risk price must be > 0 to convert cost into R; got {risk_price}")
    return cost_price / risk_price


def _default_block_length_for(rows: Sequence[Dict[str, Any]], forward_bars: int = 6) -> int:
    """Block length per roadmap Issue B: max(FORWARD_BARS, median gap in bars).

    Uses the ledger's own temporal spacing when timestamps exist ('t_open' or
    'open_time'/'ts', aligned to the pair's bar length = 1h H1 schedule),
    else the conservative forward window (6 bars) as the minimum.
    """
    import datetime as _dt

    ts_key = next((k for k in ("t_open", "open_time", "ts", "datetime")
                   if rows[0].get(k) is not None), None)
    if ts_key is None:
        return max(1, forward_bars)
    times = []
    for r in rows:
        v = r.get(ts_key)
        if isinstance(v, str):
            try:
                v = _dt.datetime.fromisoformat(str(v))
            except ValueError:
                continue
        if isinstance(v, (float, int)):
            v = _dt.datetime.fromtimestamp(v)
        if hasattr(v, "timestamp"):
            times.append(v)
    if len(times) < 2:
        return max(1, forward_bars)
    times = sorted(times)
    gaps_h = [(b - a).total_seconds() / 3600.0
              for a, b in zip(times[:-1], times[1:]) if (b - a).total_seconds() > 0]
    median_gap = float(_np.median(gaps_h)) if gaps_h else 0.0
    return _bootstrap.default_block_length(forward_bars, median_gap)


def evr_series(ledger: Sequence[Dict[str, Any]], pair: str,
               session: str = "ALL",
               risk_key: str = "risk_price",
               r_key: str = "R") -> Dict[str, Any]:
    """Cost-adjusted EV/R + block-bootstrap CI for one trade set.

    Parameters
    ----------
    ledger : closed trades, each with
        r_key ('R')       : realized R (already a risk multiple), or
        risk_key          : |entry - SL| in price units to derive R from
                            profit, and (optional) 'profit' in R units.
    pair : symbol for the shared cost table and pip size.
    session : 'ALL' (flat) until session-conditioned spreads are measured.

    Returns
    -------
    dict with n, n_cost_adjusted, evr_raw, evr_net, ev_ci_95_lo, ev_ci_95_hi,
    block_length_used, cost_pips_used. The raw EV/R is reported for audit but
    *never* as the headline figure.
    """
    rows = [t for t in ledger if t.get(r_key) is not None]
    n = len(rows)
    if n == 0:
        return {
            "n": 0, "n_cost_adjusted": 0, "small_sample": False,
            "evr_raw": None, "evr_net": None,
            "ev_ci_95_lo": None, "ev_ci_95_hi": None,
            "block_length_used": None, "cost_pips_used": None,
        }

    cost_pips = round_trip_cost_pips(pair, session)

    Rs = [float(t[r_key]) for t in rows]
    evr_raw = sum(Rs) / n

    net_Rs = []
    adjusted = 0
    for t in rows:
        risk = t.get(risk_key)
        if risk is None or risk <= 0:
            continue  # cannot cost-adjust without a risk distance -> excluded
        cost_r = cost_in_R(pair, cost_pips, float(risk))
        net_Rs.append(float(t[r_key]) - cost_r)
        adjusted += 1
    if not net_Rs:
        # fall back to median risk of the set so the CI is still computable
        risks = [float(t[risk_key]) for t in rows if (t.get(risk_key) or 0) > 0]
        if risks:
            med_risk = float(_np.median(risks))
            cost_r = cost_in_R(pair, cost_pips, med_risk)
            net_Rs = [float(t[r_key]) - cost_r for t in rows]
            adjusted = n

    block = _default_block_length_for(rows)
    # Issue B guard: if the dependence-rule block length >= n, the circular
    # block bootstrap degenerates to rotations of the *entire* sample -> a
    # zero-variance CI that UNDERSTATES uncertainty (the exact failure mode
    # Issue B exists to prevent). Cap the block so the resample still varies,
    # and flag the condition so a small sample is never mistaken for a tight CI.
    small_sample = block >= n
    if small_sample and n > 1:
        block = max(2, n // 2)
    if len(net_Rs) >= 2:
        _, lo, hi = _bootstrap.block_bootstrap_ci(net_Rs, block_length=block, seed=20260921)
    else:
        lo = hi = net_Rs[0] if net_Rs else None
    evr_net = sum(net_Rs) / len(net_Rs) if net_Rs else None

    return {
        "n": n,
        "n_cost_adjusted": adjusted,
        "small_sample": small_sample,
        "evr_raw": round(evr_raw, 4),
        "evr_net": round(evr_net, 4) if evr_net is not None else None,
        "ev_ci_95_lo": round(lo, 4) if lo is not None else None,
        "ev_ci_95_hi": round(hi, 4) if hi is not None else None,
        "block_length_used": block,
        "cost_pips_used": cost_pips,
    }


def aggregate_by_tag(ledger: Sequence[Dict[str, Any]],
                     pair_by_symbol: Optional[Dict[str, str]] = None,
                     session: str = "ALL") -> Dict[str, Any]:
    """Group a flat closed-trade ledger by comment tag and score each group.

    Expected per-trade fields (in addition to R/risk_price as in evr_series):
        'symbol'  : MT5 symbol (e.g. EURUSD) — resolved to pair for the cost
                    table via pair_by_symbol (defaults to symbol itself).
        'comment' : MT5 deal/order comment (classify_tag maps it to a tag).
        'profit'  : realized PnL in account currency (optional; for win%/pnl).

    Returns {tag: {...}} for every tag present, sorted alphabetically.
    Each group carries: trade_count, win_pct, pnl_usd, evr_raw, evr_net,
    ev_ci_95_lo, ev_ci_95_hi, block_length_used, cost_pips_used. EV/R fields
    are None (never fabricated) when R is not derivable for that group.
    """
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for t in ledger:
        symbol = t.get("symbol", "")
        pair = (pair_by_symbol or {}).get(symbol, symbol)
        groups.setdefault(classify_tag(t.get("comment", "")), []).append({**t, "_pair": pair})

    out: Dict[str, Any] = {}
    for tag, trades in sorted(groups.items()):
        profits = [float(t["profit"]) for t in trades
                   if t.get("profit") is not None and float(t["profit"]) != 0.0]
        wins = sum(1 for p in profits if p > 0)
        summary = {
            "trade_count": len(trades),
            "win_pct": round(100 * wins / len(profits), 1) if profits else None,
            "pnl_usd": round(sum(profits), 2) if profits else 0.0,
        }
        summary.update(
            evr_series(trades, pair=trades[0].get("_pair", ""), session=session)
        )
        out[tag] = summary
    return out