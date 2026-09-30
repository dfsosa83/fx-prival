#!/usr/bin/env python
"""Re-score with v3.6 engine (corrected short exits).

The v3.5 ledger records buggy short-exit prices; v3.6 re-runs the SAME episode
identification with the corrected short stop. This driver:
  1. Runs the v3.6 engine on full history (identical population to v3.5).
  2. Recomputes each eligible episode's fills from RAW prices (recovered by
     inverting base cost at the fill's source bar spread).
  3. Applies the four cost scenarios.
  4. Runs cluster-aware block bootstrap (6h/3h/12h, 10k reps, seed 42).
  5. Emits per-window per-scenario results + diagnostics.
NO strategy GO. No MT5. No orders.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
sys.path.insert(0, str(BASE))
OUT = BASE / "scoring_results"
OUT.mkdir(parents=True, exist_ok=True)

from engine.engine_v36 import run_engine_v36  # noqa: E402
from scoring.bootstrap_inference import block_bootstrap_deltaR, iid_diagnostic_only  # noqa: E402

# ── cost helpers (v3.5/v3.6 frozen) ─────────────────────────────────────────
POINT = 0.01
SCENARIOS = ["base", "2x_spread", "2x_slippage", "combined"]
MULTS = {"base": (1.0, 0.5), "2x_spread": (2.0, 0.5),
         "2x_slippage": (1.0, 1.0), "combined": (2.0, 1.0)}


def apply_cost(raw, spread_points, side, smult, lmult):
    s = spread_points * POINT * smult
    l = 0.5 * spread_points * POINT * lmult
    return raw + s / 2 + l if side in ("buy", "cover") else raw - s / 2 - l


def recover_raw(fill_price, spread_points, side):
    """Invert BASE cost (smult=1, lmult=0.5) to get raw price."""
    s = spread_points * POINT
    l = 0.5 * spread_points * POINT
    return fill_price - (s / 2 + l) if side in ("buy", "cover") else fill_price + (s / 2 + l)


# ── Load data + run v3.6 engine ─────────────────────────────────────────────
m15 = pd.read_parquet(BASE / "data/processed/XAUUSD_M15_processed.parquet")
h1 = pd.read_parquet(BASE / "data/processed/XAUUSD_H1_processed.parquet")
m15["time_utc"] = pd.to_datetime(m15["time_utc"], utc=True)
h1["time_utc"] = pd.to_datetime(h1["time_utc"], utc=True)

out = run_engine_v36(m15, h1)
eps = out["episodes"]
spread_map = m15["spread"].to_numpy()
times = pd.to_datetime(m15["time_utc"], utc=True)

# ── Build episode frame with corrected short exits ──────────────────────────
rows = []
for ep in eps:
    if ep.reason not in ("c1_triggered", "no_c1", "rollover_ineligible"):
        continue
    R = abs(float(ep.resistance) - float(ep.support))
    if pd.isna(R) or R <= 0:
        continue
    entry_idx = int(ep.entry_fill_idx)
    sp_entry = float(spread_map[entry_idx])
    raw_entry = recover_raw(float(ep.entry_fill_price), sp_entry, "buy")
    exit_idx = int(ep.invalidation_idx) + 1
    sp_exit = float(spread_map[exit_idx])
    raw_exit = recover_raw(float(ep.exit_fill_price), sp_exit, "sell")

    short_raw_entry = None
    short_raw_exit = None
    sp_se = sp_exit
    sp_sx = sp_exit
    if ep.reason == "c1_triggered":
        se_idx = int(ep.short_entry_idx)
        sp_se = float(spread_map[se_idx])
        short_raw_entry = recover_raw(float(ep.short_entry_price), sp_se, "sell")
        sx_idx = int(ep.short_exit_idx)
        sp_sx = float(spread_map[sx_idx])
        short_raw_exit = recover_raw(float(ep.short_exit_price), sp_sx, "cover")

    rows.append({
        "idx": ep.idx,
        "window": ep.assignment_window,
        "reason": ep.reason,
        "R": R,
        "entry_time": ep.entry_time,
        "invalidation_time": ep.invalidation_time,
        "cluster": ep.shared_invalidation_cluster_id,
        "time_block": ep.time_block,
        "raw_entry": raw_entry, "raw_exit": raw_exit,
        "sp_entry": sp_entry, "sp_exit": sp_exit,
        "short_raw_entry": short_raw_entry, "short_raw_exit": short_raw_exit,
        "sp_se": sp_se, "sp_sx": sp_sx,
        "short_exit_idx": ep.short_exit_idx,
        "short_entry_idx": ep.short_entry_idx,
    })

frame = pd.DataFrame(rows)

# ── Per-scenario scoring ────────────────────────────────────────────────────
report = {"prior_scoring": "INVALID — short-stop condition defect",
          "scenarios": {}}

for scen in SCENARIOS:
    smult, lmult = MULTS[scen]
    f = frame.copy()
    # Policy A (long) PnL under scenario
    f["fill_entry_A"] = f.apply(lambda r: apply_cost(r["raw_entry"], r["sp_entry"], "buy", smult, lmult), axis=1)
    f["fill_exit_A"] = f.apply(lambda r: apply_cost(r["raw_exit"], r["sp_exit"], "sell", smult, lmult), axis=1)
    f["pnl_A"] = f["fill_exit_A"] - f["fill_entry_A"]
    f["delta_price"] = 0.0
    f["pnl_B"] = f["pnl_A"]
    short_mask = f["reason"] == "c1_triggered"
    f.loc[short_mask, "fill_se"] = f.loc[short_mask].apply(
        lambda r: apply_cost(r["short_raw_entry"], r["sp_se"], "sell", smult, lmult), axis=1)
    f.loc[short_mask, "fill_sx"] = f.loc[short_mask].apply(
        lambda r: apply_cost(r["short_raw_exit"], r["sp_sx"], "cover", smult, lmult), axis=1)
    f.loc[short_mask, "pnl_B"] = f.loc[short_mask, "pnl_A"] + (
        f.loc[short_mask, "fill_se"] - f.loc[short_mask, "fill_sx"])
    f.loc[short_mask, "delta_price"] = f.loc[short_mask, "pnl_B"] - f.loc[short_mask, "pnl_A"]
    f["delta_R"] = f["delta_price"] / f["R"]

    scen_rep = {"windows": {}}
    for w in ["development", "research_grade_oos"]:
        sub = f[f["window"] == w]
        n = len(sub)
        c1 = (sub["reason"] == "c1_triggered").sum()
        nc1 = (sub["reason"] == "no_c1").sum()
        roll = (sub["reason"] == "rollover_ineligible").sum()
        dr = sub["delta_R"]
        pos_sum = float(dr[dr > 0].sum())
        neg_sum = float(abs(dr[dr < 0].sum()))
        pf = pos_sum / neg_sum if neg_sum > 0 else float("inf")
        # exit type decomposition (short)
        c1sub = sub[sub["reason"] == "c1_triggered"]
        hold = c1sub["short_exit_idx"] - c1sub["short_entry_idx"]
        time_exits = int((hold == 12).sum())
        forced_unknown = int((hold < 12).sum())
        scen_rep["windows"][w] = {
            "n_eligible_denominator": int(n),
            "c1_triggered": int(c1),
            "no_c1": int(nc1),
            "rollover_ineligible": int(roll),
            "mean_delta_R": float(dr.mean()),
            "median_delta_R": float(dr.median()),
            "pct_positive": float((dr > 0).mean() * 100),
            "avg_positive_delta_R": float(dr[dr > 0].mean()) if (dr > 0).any() else 0.0,
            "avg_negative_delta_R": float(dr[dr < 0].mean()) if (dr < 0).any() else 0.0,
            "profit_factor_diagnostic": pf,
            "c1_exit_types": {"time_exit_12bars": time_exits,
                              "stop_or_forced_lt12": forced_unknown,
                              "hold_bars_dist": hold.value_counts().head(6).to_dict()},
            "bootstrap_6h": block_bootstrap_deltaR(sub, 6, 10000, 42),
            "bootstrap_3h": block_bootstrap_deltaR(sub, 3, 10000, 42),
            "bootstrap_12h": block_bootstrap_deltaR(sub, 12, 10000, 42),
            "iid_diagnostic_only": iid_diagnostic_only(sub),
        }
    report["scenarios"][scen] = scen_rep

with open(OUT / "SCORING_RESULTS_V36.json", "w") as f:
    json.dump(report, f, indent=2, default=str)

# quick print
for s in SCENARIOS:
    print(f"=== {s} ===")
    for w in ["development", "research_grade_oos"]:
        x = report["scenarios"][s]["windows"][w]
        b = x["bootstrap_6h"]
        print(f"  {w}: n={x['n_eligible_denominator']} c1={x['c1_triggered']} "
              f"mean_dR={x['mean_delta_R']:.4f} 6hCI=[{b['ci_lower']:.4f},{b['ci_upper']:.4f}] "
              f"P(>0)={b['prob_mean_delta_R_gt_0']:.3f} pf={x['profit_factor_diagnostic']:.3f} "
              f"exit_types={x['c1_exit_types']}")