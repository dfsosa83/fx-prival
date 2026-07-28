"""
Decision gates for SELL signal pipeline.

Filters raw model probabilities through three sequential gates:
1. Threshold   — probability must meet minimum
2. Session     — only London and NY hours
3. Cooldown    — max 1 signal per N bars
"""

from typing import List, Optional, Dict, Any
import pandas as pd


def apply_gates(
    df: pd.DataFrame,
    *,
    threshold: float = 0.306,
    cooldown_bars: int = 4,
    session_filter: bool = True,
) -> pd.DataFrame:
    """
    Apply all decision gates to a DataFrame of model predictions.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain: datetime, probability.
        Rows sorted chronologically (oldest first).
    threshold : float
        Minimum probability to pass threshold gate.
    cooldown_bars : int
        Minimum bars between consecutive signals.
    session_filter : bool
        If True, only London (07:00–15:59 UTC) and NY (13:00–21:59 UTC) bars.

    Returns
    -------
    pd.DataFrame
        Copy of input with added columns:
        - pass_threshold : bool
        - pass_session   : bool
        - pass_cooldown  : bool
        - gate_result    : bool — True only if ALL gates passed
        - gate_reason    : str  — reason for rejection (empty if passed)
    """
    df = df.copy()
    n = len(df)

    # ── Gate 1: Threshold ─────────────────────────────────────────────────
    df["pass_threshold"] = df["probability"] >= threshold

    # ── Gate 2: Session ───────────────────────────────────────────────────
    if session_filter and "datetime" in df.columns:
        hour = df["datetime"].dt.hour
        df["pass_session"] = ((hour >= 7) & (hour < 16)) | ((hour >= 13) & (hour < 22))
    else:
        df["pass_session"] = True

    # ── Gate 3: Cooldown ──────────────────────────────────────────────────
    df["pass_cooldown"] = False
    last_signal_idx = -cooldown_bars - 1

    for i in range(n):
        if df.iloc[i]["pass_threshold"] and df.iloc[i]["pass_session"]:
            if i - last_signal_idx > cooldown_bars:
                df.iloc[i, df.columns.get_loc("pass_cooldown")] = True
                last_signal_idx = i

    # ── Combine ───────────────────────────────────────────────────────────
    df["gate_result"] = df["pass_threshold"] & df["pass_session"] & df["pass_cooldown"]

    reasons = []
    for i in range(n):
        row = df.iloc[i]
        if row["gate_result"]:
            reasons.append("")
        else:
            failed = []
            if not row["pass_threshold"]:
                failed.append("threshold")
            if not row["pass_session"]:
                failed.append("session")
            if not row["pass_cooldown"]:
                if row["pass_threshold"] and row["pass_session"]:
                    failed.append("cooldown")
            reasons.append("|".join(failed))
    df["gate_reason"] = reasons

    return df


def gate_summary(df_gated: pd.DataFrame) -> Dict[str, Any]:
    """
    Produce a summary of gate performance.

    Returns dict with counts and rates per gate.
    """
    n = len(df_gated)
    n_threshold = int(df_gated["pass_threshold"].sum())
    n_session   = int(df_gated[df_gated["pass_threshold"]]["pass_session"].sum())
    n_cooldown  = int(df_gated["pass_cooldown"].sum())
    n_final     = int(df_gated["gate_result"].sum())

    return {
        "total_bars": n,
        "passed_threshold": n_threshold,
        "passed_session": n_session,
        "passed_cooldown": n_cooldown,
        "passed_all": n_final,
        "rate_threshold": round(n_threshold / n, 4) if n else 0,
        "rate_final": round(n_final / n, 4) if n else 0,
    }