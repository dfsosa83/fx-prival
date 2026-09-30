"""
EXP-2026-05 — historical performance scoring engine (v3.5 ledger).

Scoring rules (frozen):
  - Score ONLY A-vs-B eligible episodes (c1_triggered, no_c1, rollover_ineligible).
  - Policy A: long exit at recorded next-bar-open after invalidation; flat.
  - Policy B: identical long exit; short only for c1_triggered.
  - no_c1 and rollover_ineligible: zero incremental short PnL, in denominator.
  - delta_R = combined_PolicyB_R - combined_PolicyA_R (per episode).
  - Primary endpoint: mean delta_R over ALL A-vs-B eligible episodes.
  - Costs: v3.5 base (S=points*point; buy/cover=P+S/2+L; sell/short=P-S/2-L; L=0.5S)
    plus 2x spread, 2x slippage, combined. Scenarios alter ONLY cost multipliers.
  - R = |resistance - support| (structural setup risk).
  - No exclusions beyond the four pre-registered non-eligible codes.

Cost-scenario application:
  The v3.5 ledger stores fills at BASE cost. We recover the RAW (pre-cost)
  execution price for each fill using the bar spread at the fill's source
  index, then reapply each scenario's (spread_mult, slip_mult).

  Entry / long-exit / short-entry are market fills at a bar's open or close.
  Short-exit may be a stop (min(open,stop)), time (close), or forced (close).
  The v3.5 engine recorded the fill and its source index; we invert base cost
  to get the raw price, then re-apply scenario cost.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

POINT = 0.01  # XAUUSD frozen


def scenario_multipliers(scenario):
    """(spread_mult, slip_mult). Base slip is 0.5; 2x slippage = 1.0."""
    return {
        "base": (1.0, 0.5),
        "2x_spread": (2.0, 0.5),
        "2x_slippage": (1.0, 1.0),
        "combined": (2.0, 1.0),
    }[scenario]


def apply_cost(raw, spread_points, side, smult, lmult):
    """Apply adverse modeled cost to a raw price. Returns fill price."""
    s = spread_points * POINT * smult
    l = 0.5 * spread_points * POINT * lmult
    return raw + s / 2 + l if side in ("buy", "cover") else raw - s / 2 - l


def recover_raw(fill_price, spread_points, side, smult=1.0, lmult=0.5):
    """Invert base cost from a recorded base fill to get the raw price."""
    s = spread_points * POINT * smult
    l = 0.5 * spread_points * POINT * lmult
    return fill_price - (s / 2 + l) if side in ("buy", "cover") else fill_price + (s / 2 + l)


def build_fill_spread_map(bars):
    """Map bar index -> spread_points (the bar's own spread field)."""
    return bars["spread"].to_numpy()


def score_ledger(ledger, bars, scenario):
    """Score all A-vs-B eligible episodes under a scenario.

    Returns DataFrame with per-episode: delta_price, delta_R, PnL_A, PnL_B,
    reason, R, entry_time, cluster, time_block.

    Fills and their source indices are read from the ledger. The raw price is
    recovered by inverting the BASE cost (the recorded fill was computed at
    base multipliers); then scenario multipliers are applied.
    """
    smult, lmult = scenario_multipliers(scenario)
    spread_map = build_fill_spread_map(bars)

    eligible = ledger[ledger["reason"].isin(["c1_triggered", "no_c1", "rollover_ineligible"])].copy()

    rows = []
    for _, ep in eligible.iterrows():
        R = abs(float(ep["resistance"]) - float(ep["support"]))
        if pd.isna(R) or R <= 0:
            continue

        # --- Long leg (Policy A and B identical) ---
        # entry: buy at entry_fill_idx open (raw recovered from base fill)
        entry_idx = int(ep["entry_fill_idx"])
        sp_entry = float(spread_map[entry_idx])
        raw_entry = recover_raw(float(ep["entry_fill_price"]), sp_entry, "buy")
        # long exit: sell at invalidation+1 open
        exit_idx = int(ep["invalidation_idx"]) + 1
        sp_exit = float(spread_map[exit_idx])
        raw_exit = recover_raw(float(ep["exit_fill_price"]), sp_exit, "sell")

        pnl_A_long_price = raw_exit - raw_entry  # per unit (long close - open)

        # --- Short leg (Policy B only, c1_triggered) ---
        pnl_short_price = 0.0
        raw_se = raw_entry
        raw_sx = raw_exit
        sp_se = sp_entry
        sp_sx = sp_exit
        if ep["reason"] == "c1_triggered":
            short_entry_idx = int(ep["short_entry_idx"])
            sp_se = float(spread_map[short_entry_idx])
            raw_se = recover_raw(float(ep["short_entry_price"]), sp_se, "sell")
            short_exit_idx = int(ep["short_exit_idx"])
            sp_sx = float(spread_map[short_exit_idx])
            raw_sx = recover_raw(float(ep["short_exit_price"]), sp_sx, "cover")
            pnl_short_price = raw_se - raw_sx  # per unit short (entry - exit)

        # Apply scenario costs to the ROUND TRIP (both legs) — this is the
        # incremental cost of the short relative to flat.
        # Policy A PnL (per unit, scenario-costed): long entry+exit adverse.
        fill_entry_A = apply_cost(raw_entry, sp_entry, "buy", smult, lmult)
        fill_exit_A = apply_cost(raw_exit, sp_exit, "sell", smult, lmult)
        pnl_A_scen = fill_exit_A - fill_entry_A

        if ep["reason"] == "c1_triggered":
            # Policy B: long identical + short round trip costed at scenario.
            fill_se = apply_cost(raw_se, sp_se, "sell", smult, lmult)
            fill_sx = apply_cost(raw_sx, sp_sx, "cover", smult, lmult)
            pnl_B_scen = pnl_A_scen + (fill_se - fill_sx)
            delta_price = pnl_B_scen - pnl_A_scen  # = short round-trip net
        else:
            # no_c1 / rollover_ineligible: Policy B is IDENTICAL to A (no short).
            pnl_B_scen = pnl_A_scen
            delta_price = 0.0

        rows.append({
            "idx": ep["idx"],
            "window": ep["assignment_window"],
            "reason": ep["reason"],
            "R": R,
            "pnl_A_price": pnl_A_scen,
            "pnl_B_price": pnl_B_scen,
            "delta_price": delta_price,
            "delta_R": delta_price / R,
            "entry_time": ep["entry_time"],
            "invalidation_time": ep["invalidation_time"],
            "shared_invalidation_cluster_id": ep["shared_invalidation_cluster_id"],
            "time_block": ep["time_block"],
        })

    return pd.DataFrame(rows)