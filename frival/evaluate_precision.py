"""
Precision evaluation against forward outcomes.

Reads the signal log and checks each FIRED signal against actual
forward price movement using the ATR-barrier race label logic:
  TP = entry - ATR(14) * 1.5
  SL = entry + ATR(14) * 1.0
  Win  = low reaches TP before high reaches SL within FORWARD_BARS

Computes:
- Precision (win rate)
- Expected value per trade (R)
- Wilson 95% confidence interval
- Monthly breakdown
"""

import json
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd

from model import compute_features
from model.features import ATR_PERIOD, ATR_TP_MULT, ATR_SL_MULT, FORWARD_BARS


def evaluate_signals(
    signal_dir: str = "frival/output/signals",
    data_file: str = "ml-signal-service/data/raw/mt5/H1/EURUSD_H1.csv",
    run_id_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate precision of all FIRED signals against forward outcomes.

    Parameters
    ----------
    signal_dir : str
        Path to the signals directory.
    data_file : str
        Path to the EURUSD H1 CSV data file.
    run_id_filter : str, optional
        Only evaluate signals from a specific run_id.

    Returns
    -------
    dict with precision, EV, Wilson CI, monthly breakdown.
    """
    # ── Load signals ──────────────────────────────────────────────────────
    signals = _load_signals(signal_dir, run_id_filter)
    fired = [s for s in signals if s["final_decision"] == "FIRED"]

    if not fired:
        return {"error": "No FIRED signals found", "total_fired": 0}

    print(f"Loaded {len(fired)} FIRED signals from {len(signals)} total")

    # ── Load price data ───────────────────────────────────────────────────
    df = pd.read_csv(data_file, parse_dates=["datetime"])
    if "tick_volume" in df.columns and "volume" not in df.columns:
        df.rename(columns={"tick_volume": "volume"}, inplace=True)

    # Compute features on ALL data (needed for ATR)
    df_feat = compute_features(df)

    # Unpack OHLCV arrays for fast lookups
    close = df_feat["close"].values
    high  = df_feat["high"].values
    low   = df_feat["low"].values
    atr   = df_feat["atr_14"].values
    datetimes = df_feat["datetime"].values
    n = len(df_feat)

    # ── Evaluate each signal ──────────────────────────────────────────────
    results = []
    for sig in fired:
        outcome = _check_outcome(
            sig, datetimes, close, high, low, atr, n,
            tp_mult=ATR_TP_MULT, sl_mult=ATR_SL_MULT, forward=FORWARD_BARS,
        )
        results.append(outcome)

    # ── Compute statistics ────────────────────────────────────────────────
    wins = sum(1 for r in results if r["win"])
    losses = sum(1 for r in results if not r["win"] and not r["no_data"])
    no_data = sum(1 for r in results if r["no_data"])
    total = len(results)

    precision = wins / max(1, wins + losses)
    ci_low, ci_high = _wilson_ci(wins, wins + losses)

    # EV per trade (in R)
    avg_r = sum(r["trade_r"] for r in results) / max(1, total)
    total_r = sum(r["trade_r"] for r in results)

    # Monthly breakdown
    monthly = {}
    for r in results:
        m = r["timestamp_utc"][:7]  # YYYY-MM
        if m not in monthly:
            monthly[m] = {"signals": 0, "wins": 0, "total_r": 0.0}
        monthly[m]["signals"] += 1
        if r["win"]:
            monthly[m]["wins"] += 1
        monthly[m]["total_r"] += r["trade_r"]

    return {
        "signals_evaluated": total,
        "wins": wins,
        "losses": losses,
        "no_data": no_data,
        "precision": round(precision, 4),
        "wilson_ci_95": [round(ci_low, 4), round(ci_high, 4)],
        "ev_per_trade_r": round(avg_r, 4),
        "total_r": round(total_r, 2),
        "monthly": {
            m: {
                "signals": v["signals"],
                "wins": v["wins"],
                "win_rate": round(v["wins"] / max(1, v["signals"]), 4),
                "total_r": round(v["total_r"], 2),
            }
            for m, v in sorted(monthly.items())
        },
        "results": results,
    }


def _load_signals(signal_dir: str, run_id_filter: Optional[str]) -> List[Dict]:
    signals = []
    pattern = f"{signal_dir}/**/*.jsonl"
    for filepath in sorted(glob.glob(pattern, recursive=True)):
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                try:
                    sig = json.loads(line)
                    if run_id_filter and sig.get("run_id") != run_id_filter:
                        continue
                    signals.append(sig)
                except json.JSONDecodeError:
                    continue
    return signals


def _check_outcome(
    sig: Dict,
    datetimes: np.ndarray,
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr: np.ndarray,
    n: int,
    tp_mult: float,
    sl_mult: float,
    forward: int,
) -> Dict[str, Any]:
    """Check whether a SELL signal's TP or SL was hit first."""
    ts = sig["timestamp_utc"]
    bar_dt = pd.Timestamp(ts)

    # Find the bar index
    matches = np.where(datetimes == bar_dt.to_datetime64())[0]
    if len(matches) == 0:
        return {
            "timestamp_utc": ts,
            "win": False,
            "no_data": True,
            "trade_r": 0.0,
            "entry": sig["model"]["probability"],
            "note": "bar not found in data",
        }

    i = matches[0]
    if i + forward >= n:
        return {
            "timestamp_utc": ts,
            "win": False,
            "no_data": True,
            "trade_r": 0.0,
            "entry": float(close[i]),
            "note": "insufficient forward data",
        }

    entry = close[i]
    tp_level = entry - atr[i] * tp_mult
    sl_level = entry + atr[i] * sl_mult

    win = False
    for j in range(1, forward + 1):
        k = i + j
        tp_hit = low[k] <= tp_level
        sl_hit = high[k] >= sl_level
        if tp_hit and sl_hit:
            win = False  # same bar ambiguity → loss (conservative)
            break
        elif tp_hit:
            win = True
            break
        elif sl_hit:
            win = False
            break

    trade_r = tp_mult if win else -sl_mult

    return {
        "timestamp_utc": ts,
        "win": win,
        "no_data": False,
        "trade_r": round(trade_r, 2),
        "entry": float(entry),
        "tp_level": float(tp_level),
        "sl_level": float(sl_level),
    }


def _wilson_ci(wins: int, n: int, z: float = 1.96) -> tuple:
    """Wilson 95% confidence interval for a proportion."""
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * np.sqrt((p * (1 - p) + z**2 / (4 * n)) / n) / denom
    return max(0, center - margin), min(1, center + margin)