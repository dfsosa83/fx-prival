# -*- coding: utf-8 -*-
"""EXP-2026-04 — FX rule-engine backtest runner (Deliverable 2).

Replays the unmodified gold-rules engine bar-by-bar over each pair's history,
simulating the full position lifecycle (entry -> SL/TP/invalidation/end-of-window).
One-pass, deterministic, read-only. Emits a per-pair trade ledger + decision log.

Design contract: EXP-2026-04 §3. Decision rule §5.
Key constants (frozen before run — no tuning after seeing results):
  - Warm-up: 200 M30, 50 H1, 15 M15 (bar counts)
  - Measurement window: last N M15 bars (default 90 days of bars, capped by data)
  - Unit re-normalization (§3.3):
      loc_tol_floor  = per-pair 1.0 * std(M15 close-to-close), min 1 pip
      sl_buffer_min  = per-pair 0.3 * v_same_unit
      max_risk_usd   = 25.0 * ATR_M15_pair / ATR_M15_XAUUSD   (gold-referenced)
"""
from __future__ import annotations

import json
import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

# gold_rules modules on path (engine, bias, levels)
sys.path.insert(0, str(HERE.parent / "gold_rules"))
sys.path.insert(0, str(HERE.parent))

import engine as eng_mod                 # noqa: E402
from engine import EngineState, Snapshot  # noqa: E402
import levels as levels_mod               # noqa: E402
import bias as bias_mod                   # noqa: E402

from acquire_data import load_pair, PAIRS  # noqa: E402

# ── Spec constants ──────────────────────────────────────────────────────────────
WARMUP_M30 = 200
WARMUP_H1 = 50
WARMUP_M15 = 15
WINDOW_DAYS_BARS = 90 * 96          # ~90 days of M15 bars (96/day); capped by data
FLAT_LOT = 0.01
CONTRACT_FX = 100_000.0
CONTRACT_XAU = 100.0
GOLD_ATR_REF = None                 # set in main() from gold M15 fixture
MIN_LOC_TOLORMIN_PIPS = 0.0001       # 1 pip floor for FX majors (USDJPY 0.01 floor)


def pair_unit(pair: str) -> float:
    """Per-pair 'natural pip' floor: 1 pip for most, 0.01 for JPY."""
    return 0.01 if "JPY" in pair else 0.0001


def std_m15(pair: str) -> float:
    df = load_pair(pair, "M15")
    ret = df["close"].diff().dropna()
    return float(ret.std())


def atr_m15_pair(pair: str) -> float:
    df = load_pair(pair, "M15")
    return levels_mod.compute_atr(df, period=14)


def build_cfg(pair: str, std: float, atr_pair: float, lot: float = FLAT_LOT) -> dict:
    """Engine config with §3.3 re-normalization.

    Risk cap FIX (v1.1 of the study — root-caused 2026-09-17): the original
    spec formula `25 × ATR_pair/ATR_gold` is unit-wrong — gold ATR is in
    price *points*, but the cap is in *dollars*. Scaling the dollar cap by a
    price-point ratio without the contract conversion collapsed the EURUSD
    cap to ~$0.004, so EVERY ENTRY_READY failed the risk gate (0/8,641 bars
    produced an entry; 100% of gate failures were risk=False).

    Correct rule (keeps the intent: max ~2.5x ATR_M15 of loss per trade):
        cap_usd = RISK_ATR_MULT * ATR_M15_pair * contract_pair * lot
    with RISK_ATR_MULT = 2.5 chosen so that gold's cap lands back at $25.
    """
    unit = max(std, pair_unit(pair))
    cap_usd = 2.5 * atr_pair * CONTRACT_FX * lot
    return {
        "symbol": pair,
        "bias": {"ema_fast": 20, "ema_slow": 50},
        "levels": {
            "lookback_bars_m30": 200,
            "fractal_wing": 2,
            "merge_distance_atr_mult": 0.5,
            "pending_retest_max_bars_m15": 20,
            "confirm_max_bars_m15": 3,
        },
        "gates": {
            "location_tolerance_atr_mult": 0.15,
            "location_tolerance_min_usd": float(unit),      # re-based pip
            "min_rr": 1.5,
        },
        "risk": {
            "fixed_lot": FLAT_LOT,
            "max_risk_usd": float(cap_usd),                 # ATR-based cap (fixed)
            "max_concurrent_positions": 1,
            "daily_loss_cap_usd": 50.0,
            "sl_buffer_atr_mult": 0.05,
            "sl_buffer_min_usd": float(0.3 * unit),         # re-based pip
            "contract_size": CONTRACT_FX,
        },
        "management": {"be_trigger_fraction": 0.5},
        "candles": {"solid_body_min_fraction": 0.30},
        "order": {"comment": f"RULES_D_{pair}", "dynamic_sizing": False},
        "breakout": {"enabled": False, "comment": f"RULES_D_{pair}_C", "min_rr": 1.5},  # Claim C excluded
    }


def run_backtest(pair: str, window_bars: int = WINDOW_DAYS_BARS) -> dict:
    m15 = load_pair(pair, "M15")
    m30 = load_pair(pair, "M30")
    # H1: fetch live (closed) from MT5 via the same harness — on-disk H1 is
    # 47k bars from 2019; bias needs >=50, use the live M30 resampled to H1
    # is NOT derivable; instead use the on-disk H1 CSV directly.
    import os
    h1_path = Path(r"C:\Users\david\OneDrive\Documents\fx-prival\ml-signal-service\data\raw\mt5\H1") / f"{pair}_H1.csv"
    if h1_path.exists():
        h1 = pd.read_csv(h1_path, parse_dates=["datetime"])
    else:
        # fallback: fetch H1 read-only
        from acquire_data import _init_mt5
        mt5 = _init_mt5()
        h1 = pd.DataFrame(mt5.copy_rates_range(pair, mt5.TIMEFRAME_H1,
                                               datetime.utcnow() - timedelta(days=40),
                                               datetime.utcnow()))
        mt5.shutdown()
        h1["datetime"] = pd.to_datetime(h1["time"], unit="s")
        h1.drop(columns=["time", "spread", "real_volume"], inplace=True, errors="ignore")
        h1.rename(columns={"tick_volume": "volume"}, inplace=True)
        h1 = h1[["datetime", "open", "high", "low", "close", "volume"]]

    # Alignment: keep M30/M15/H1 bars only within the M15 span
    m15_start = m15["datetime"].min()
    m30 = m30[m30["datetime"] >= m15_start].reset_index(drop=True)
    h1 = h1[h1["datetime"] >= m15_start].reset_index(drop=True)

    # Slice measurement window: skip warm-up, take the last `window_bars` M15
    total = len(m15)
    win_start = max(0, total - window_bars - 1)
    m15_win = m15.iloc[win_start:].reset_index(drop=True)
    print(f"[{pair}] total M15={total}  window bars={len(m15_win)}  "
          f"({m15_win['datetime'].iloc[0]:%Y-%m-%d} -> {m15_win['datetime'].iloc[-1]:%Y-%m-%d})")

    # Engine config
    std = std_m15(pair)
    atr_pair = atr_m15_pair(pair)
    cfg = build_cfg(pair, std, atr_pair)
    engine = eng_mod.GoldRulesEngine(cfg)

    state = EngineState()
    ledger = []
    decisions = []
    sim_pos = None            # open simulated position {entry,sl,tp,invalidation,...}
    day_pnl: dict = {}
    n_entries = 0
    still_open = 0

    def run_pnl(pnl: dict) -> None:
        d = pnl["t_close"][:10]
        day_pnl[d] = day_pnl.get(d, 0.0) + pnl["usd"]

    for i in range(len(m15_win)):
        frame = m15_win.iloc[: i + 1]
        bar = frame.iloc[-1]
        bid = float(bar["close"])
        ask = bid + 0.0   # spread ignored at backtest resolution
        open_pos = 1 if sim_pos is not None else 0
        day = str(bar["datetime"])[:10]
        # Slice M30/H1 to a bounded tail (200+ for levels, 80+ for bias) so the
        # engine's internal .tail(N) + consumption scans stay O(window), not
        # O(history) — identical outputs, since the engine only ever reads the
        # most recent bars. (EXP-2026-04 §3.5: no leakage — all bars are closed
        # and <= t.)
        m30_t = m30[m30["datetime"] <= bar["datetime"]].tail(400).reset_index(drop=True)
        h1_t = h1[h1["datetime"] <= bar["datetime"]].tail(120).reset_index(drop=True)
        snap = Snapshot(
            m15_df=frame,
            m30_df=m30_t,
            h1_df=h1_t,
            utc_now=bar["datetime"] + timedelta(minutes=16),
            bid=bid, ask=ask,
            open_positions=open_pos,
            today_realized_pnl=day_pnl.get(day, 0.0),
        )
        new_state, dec = engine.evaluate(snap, state)
        state = new_state
        decisions.append({**dec.to_dict(), "ts": str(bar["datetime"])})

        # Position lifecycle: if a sim position is open, check SL/TP/invalidation
        if sim_pos is not None:
            sp = sim_pos
            direction = state.direction or "buy"
            is_buy = direction == "buy"
            risk_dist = (sp["entry"] - sp["sl"]) if is_buy else (sp["sl"] - sp["entry"])
            risk_dist = abs(risk_dist) or 1e-12
            # Never let a structurally-tight SL (<< 1 pip) score as an R monster:
            # if the entry-to-SL distance is below the pair unit, the entry is
            # unmountable — treat as a zero-R scratch.
            if risk_dist < pair_unit(pair):
                sp["sl"] = sp["entry"]  # flatten; next bar will close at ~0R
            hit = None
            # SL/TP intrabar check
            if is_buy:
                if bar["low"] <= sp["sl"]:
                    hit = ("SL", sp["sl"])
                elif bar["high"] >= sp["tp"]:
                    hit = ("TP", sp["tp"])
            else:
                if bar["high"] >= sp["sl"]:
                    hit = ("SL", sp["sl"])
                elif bar["low"] <= sp["tp"]:
                    hit = ("TP", sp["tp"])

            if hit:
                kind, px = hit
                if abs(risk_dist) < 1e-12 or risk_dist < pair_unit(pair):
                    R = 0.0
                else:
                    R = -1.0 if kind == "SL" else ((sp["tp"] - sp["entry"]) / risk_dist if is_buy else (sp["entry"] - sp["tp"]) / risk_dist)
                # Direction-correct PnL: BUY: (exit-entry), SELL: (entry-exit)
                px_delta = (px - sp["entry"]) if is_buy else (sp["entry"] - px)
                pnl = px_delta * CONTRACT_FX * FLAT_LOT
                ledger.append({**sp, "exit_time": str(bar["datetime"]),
                               "exit_px": px, "close_kind": kind, "R": R,
                               "sim_pnl_usd": pnl})
                run_pnl({"R": R, "t_close": str(bar["datetime"]), "usd": pnl})
                sim_pos = None
                state = EngineState()   # position closed -> clean watch state
            elif dec.action == eng_mod.BE:
                sp["sl"] = sp["entry"]                      # BE only: SL -> entry
            elif dec.action == eng_mod.TRAIL:
                sp["sl"] = sp["entry"]                      # gold trail rule: follow swing; simplified to entry stop at BE for backtest
            elif dec.action == eng_mod.INVALIDATE:
                px = bar["close"]
                if abs(risk_dist) < 1e-12 or risk_dist < pair_unit(pair):
                    R = 0.0
                else:
                    R = (px - sp["entry"]) / risk_dist if is_buy else (sp["entry"] - px) / risk_dist
                px_delta = (px - sp["entry"]) if is_buy else (sp["entry"] - px)
                pnl = px_delta * CONTRACT_FX * FLAT_LOT
                ledger.append({**sp, "exit_time": str(bar["datetime"]),
                               "exit_px": px, "close_kind": "INVALIDATE", "R": R,
                               "sim_pnl_usd": pnl})
                run_pnl({"R": R, "t_close": str(bar["datetime"]), "usd": pnl})
                sim_pos = None
                state = EngineState()
        else:
            # Check for new ENTRY
            if dec.action == eng_mod.ENTRY and dec.order:
                o = dec.order
                sl = o.get("stop_loss")
                tp = o.get("take_profit")
                act = state.active_trade
                if sl and tp and act:
                    sim_pos = {
                        "entry": act.get("entry", bid),
                        "sl": sl, "tp": tp,
                        "invalidation": act.get("invalidation", sl),
                        "dir": state.direction or o.get("action"),
                        "t_open": str(bar["datetime"]),
                    }
                    n_entries += 1

    # End-of-window: anything still open -> censored
    if sim_pos is not None:
        sp = sim_pos
        ledger.append({**sp, "exit_time": "END_OF_WINDOW", "exit_px": None,
                       "close_kind": "CENSORED", "R": None, "sim_pnl_usd": None})
        still_open = 1

    return {
        "pair": pair,
        "std_m15": std,
        "atr_m15": atr_pair,
        "n_entries": n_entries,
        "still_open": still_open,
        "ledger": ledger,
        "decisions": decisions,
        "day_pnl": day_pnl,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", help="run a single pair (whole set if omitted)")
    args = ap.parse_args()

    targets = [args.pair] if args.pair else PAIRS

    # Gold ATR reference for the cap scaling
    gold_m15 = None
    cands = [Path(r"C:\Users\david\OneDrive\Documents\fx-prival\frival\gold_rules\tests\fixtures\XAUUSD_M15.csv"),
             Path(r"C:\Users\david\OneDrive\Documents\fx-prival\frival\gold_rules\journal\..\tests\fixtures\XAUUSD_M15.csv")]
    for c in cands:
        if c.exists():
            gold_m15 = pd.read_csv(c, parse_dates=["datetime"])
            break
    if gold_m15 is None:
        from acquire_data import _init_mt5
        mt5 = _init_mt5()
        r = mt5.copy_rates_range("XAUUSD", mt5.TIMEFRAME_M15,
                                 datetime.utcnow() - timedelta(days=40), datetime.utcnow())
        mt5.shutdown()
        gold_m15 = pd.DataFrame(r)
        gold_m15["datetime"] = pd.to_datetime(gold_m15["time"], unit="s")
        gold_m15.drop(columns=["time", "spread", "real_volume"], inplace=True, errors="ignore")
    GOLD_ATR_REF = levels_mod.compute_atr(gold_m15, period=14)
    print(f"[gold] ATR_M15_REF = {GOLD_ATR_REF:.2f}\n", flush=True)

    for pair in targets:
        res = run_backtest(pair)
        (RESULTS / f"{pair}_ledger.csv").write_text(
            pd.DataFrame(res["ledger"]).to_csv(index=False) if res["ledger"] else "",
            encoding="utf-8")
        (RESULTS / f"{pair}_decisions.jsonl").write_text(
            "\n".join(json.dumps(d, default=str) for d in res["decisions"]),
            encoding="utf-8")
        print(f"[{pair}] entries={res['n_entries']} still_open={res['still_open']}", flush=True)