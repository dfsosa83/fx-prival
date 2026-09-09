"""
Decision gates for signal pipeline.

Filters raw model probabilities through sequential gates:
1. Threshold   — probability must meet minimum
2. Session     — only London and NY hours
3. Cooldown    — max 1 signal per N bars
4. Candle-close — current M15 bar must align with predicted direction

Borderline gate (optional):
  Bars with 0.20 <= p < threshold can be evaluated by agents.
  Both agents must STRONGLY CONFIRM for the signal to fire.
"""

from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
import numpy as np

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None


BORDERLINE_THRESHOLD = 0.20

# Candle-close gate constants
M15_CANDLE_WINDOW = 15               # minutes per M15 bar
CANDLE_NEUTRAL_BODY_RATIO = 0.3      # body < 30% of range = doji/neutral → pass
CANDLE_NEUTRAL_RANGE_RATIO = 0.5     # range < 50% of ATR → low conviction → pass


def apply_gates(
    df: pd.DataFrame,
    *,
    threshold: float = 0.306,
    cooldown_bars: int = 4,
    session_filter: bool = True,
    borderline: bool = False,
) -> pd.DataFrame:
    """
    Apply all decision gates to a DataFrame of model predictions.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: datetime, probability. Sorted chronologically.
    threshold : float
        Minimum probability to pass threshold gate.
    cooldown_bars : int
        Minimum bars between consecutive signals.
    session_filter : bool
        If True, only London (07:00–15:59 UTC) and NY (13:00–21:59 UTC) bars.
    borderline : bool
        If True, bars with BORDERLINE_THRESHOLD <= p < threshold can be
        evaluated by agents (with stricter confirmation rules).

    Returns
    -------
    pd.DataFrame with columns:
    - pass_threshold   : bool
    - pass_borderline  : bool (only if borderline=True)
    - pass_session     : bool
    - pass_cooldown    : bool
    - gate_result      : bool — full threshold + session + cooldown
    - gate_borderline  : bool — borderline + session + cooldown + NOT threshold
    - gate_reason      : str
    """
    df = df.copy()
    n = len(df)

    # ── Gate 1: Threshold ─────────────────────────────────────────────────
    df["pass_threshold"] = df["probability"] >= threshold

    # ── Gate 1b: Borderline (p in [BORDERLINE_THRESHOLD, threshold)) ──
    if borderline:
        df["pass_borderline"] = (
            (df["probability"] >= BORDERLINE_THRESHOLD)
            & (df["probability"] < threshold)
        )
    else:
        df["pass_borderline"] = False

    # ── Gate 2: Session ───────────────────────────────────────────────────
    if session_filter and "datetime" in df.columns:
        hour = df["datetime"].dt.hour
        df["pass_session"] = ((hour >= 7) & (hour < 16)) | ((hour >= 13) & (hour < 22))
    else:
        df["pass_session"] = True

    # ── Gate 3: Cooldown (shared between threshold and borderline) ────────
    df["pass_cooldown"] = False
    last_signal_idx = -cooldown_bars - 1

    for i in range(n):
        qualifies = df.iloc[i]["pass_threshold"] or df.iloc[i]["pass_borderline"]
        if qualifies and df.iloc[i]["pass_session"]:
            if i - last_signal_idx > cooldown_bars:
                df.iloc[i, df.columns.get_loc("pass_cooldown")] = True
                last_signal_idx = i

    # ── Combine ───────────────────────────────────────────────────────────
    df["gate_result"] = (
        df["pass_threshold"] & df["pass_session"] & df["pass_cooldown"]
    )
    df["gate_borderline"] = (
        borderline
        & df["pass_borderline"]
        & df["pass_session"]
        & df["pass_cooldown"]
        & ~df["pass_threshold"]
    )

    # ── Reasons ───────────────────────────────────────────────────────────
    reasons = []
    for i in range(n):
        row = df.iloc[i]
        if row["gate_result"]:
            tag = "standard"
        elif row["gate_borderline"]:
            tag = "borderline"
        else:
            failed = []
            if not row["pass_threshold"] and not row["pass_borderline"]:
                failed.append("threshold")
            elif row["pass_borderline"] and not row["pass_cooldown"]:
                failed.append("cooldown")
            if not row["pass_session"]:
                failed.append("session")
            if not row["pass_cooldown"] and row["pass_threshold"]:
                failed.append("cooldown")
            tag = "|".join(failed)
        reasons.append(tag)
    df["gate_reason"] = reasons

    return df


def gate_summary(df_gated: pd.DataFrame) -> Dict[str, Any]:
    """
    Produce a summary of gate performance.
    """
    n = len(df_gated)
    n_threshold  = int(df_gated["pass_threshold"].sum())
    n_borderline = int(df_gated["pass_borderline"].sum())
    n_session    = int(df_gated[df_gated["pass_threshold"] | df_gated["pass_borderline"]]
                       ["pass_session"].sum())
    n_cooldown   = int(df_gated["pass_cooldown"].sum())
    n_standard   = int(df_gated["gate_result"].sum())
    n_bl         = int(df_gated["gate_borderline"].sum())

    return {
        "total_bars": n,
        "passed_threshold": n_threshold,
        "passed_borderline": n_borderline,
        "passed_session": n_session,
        "passed_cooldown": n_cooldown,
        "gated_standard": n_standard,
        "gated_borderline": n_bl,
        "gated_total": n_standard + n_bl,
        "rate_standard": round(n_standard / n, 4) if n else 0,
        "rate_total": round((n_standard + n_bl) / n, 4) if n else 0,
    }


# ============================================================================
# Candle-Close Gate (M15 alignment check)
# ============================================================================

def fetch_m15_candle(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the most recently COMPLETED M15 bar from MT5 (not the forming one).

    Returns dict with open/high/low/close or None if MT5 unavailable / no data.
    """
    if mt5 is None:
        return None
    try:
        # copy_rates_from_pos returns newest-first → index 1 = last completed bar
        bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 1, 2)
        if bars is None or len(bars) < 2:
            return None
        completed = bars[1]  # row: (time, open, high, low, close, tick_volume, spread, real_volume)
        return {
            "open": float(completed[1]),
            "high": float(completed[2]),
            "low": float(completed[3]),
            "close": float(completed[4]),
        }
    except Exception:
        return None


def check_candle_alignment(
    direction: str,
    symbol: str = "EURUSD",
) -> Tuple[bool, str]:
    """
    Candle-close alignment gate.

    Checks whether the most recently completed M15 bar is consistent with the
    model's predicted direction. Blocks trades where the completed candle
    contradicts the call.

    Parameters
    ----------
    direction : str
        "BUY" or "SELL" — the model's predicted trade direction.
    symbol : str
        MT5 symbol for M15 fetch (EURUSD_AGNOSTIC → mapped to EURUSD by caller).

    Returns
    -------
    (passes, reason)
        passes : True if the candle does NOT contradict the direction
        reason : human-readable explanation
    """
    candle = fetch_m15_candle(symbol)
    if candle is None:
        return True, "M15 data unavailable — gate skipped (fail-open)"

    body = candle["close"] - candle["open"]
    total_range = candle["high"] - candle["low"]
    is_bullish = body > 0

    # Neutral candle (doji, small range) → pass (no conviction either way)
    if total_range == 0:
        return True, "flat candle — pass"
    body_ratio = abs(body) / total_range
    if body_ratio < CANDLE_NEUTRAL_BODY_RATIO:
        return True, f"doji (body_ratio={body_ratio:.2f}) — pass"

    if direction.upper() == "SELL":
        if is_bullish:
            return False, (
                f"M15 closed bullish (open={candle['open']:.5f} close={candle['close']:.5f} "
                f"body_ratio={body_ratio:.2f}) — contradicts SELL"
            )
        return True, f"M15 closed bearish — aligned with SELL"
    else:  # BUY
        if not is_bullish:
            return False, (
                f"M15 closed bearish (open={candle['open']:.5f} close={candle['close']:.5f} "
                f"body_ratio={body_ratio:.2f}) — contradicts BUY"
            )
        return True, f"M15 closed bullish — aligned with BUY"