"""
Decision gates for SELL signal pipeline.

Filters raw model probabilities through three sequential gates:
1. Threshold   — probability must meet minimum (0.306)
2. Session     — only London and NY hours
3. Cooldown    — max 1 signal per N bars

Borderline gate (optional):
  Bars with 0.20 <= p < 0.306 can be evaluated by agents.
  Both agents must STRONGLY CONFIRM for the signal to fire.
"""

from typing import List, Optional, Dict, Any
import pandas as pd


BORDERLINE_THRESHOLD = 0.20


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