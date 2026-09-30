"""
Risk-parity (equal risk contribution) portfolio weights — Stage 1B frozen spec.

Objective: each instrument's marginal risk contribution equals total risk / N.
Solver: cyclic coordinate descent; convergence on max |RC_i - target| < 1e-6;
init equal weights; fallback = last iterate with convergence flag.

Long-only, fully invested, no leverage, no cash.
"""

from __future__ import annotations

import numpy as np


def risk_contributions(weights: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """Marginal risk contribution per asset: w_i * (Sigma w)_i / sqrt(w' Sigma w)."""
    w = np.asarray(weights, dtype=float)
    sigma = np.asarray(cov, dtype=float)
    port_var = float(w @ sigma @ w)
    if port_var <= 0:
        return np.full_like(w, 0.0)
    port_vol = np.sqrt(port_var)
    mrc = w * (sigma @ w) / port_vol
    return mrc


def risk_parity_weights(
    cov: np.ndarray,
    tol: float = 1e-6,
    max_iter: int = 2000,
    init: np.ndarray | None = None,
) -> dict:
    """
    Compute equal-risk-contribution weights by cyclic coordinate descent.

    At each step, adjust one weight so that its risk contribution equals the
    target (total_risk / N), renormalize, iterate.

    Args:
        cov: N x N covariance matrix (positive definite).
        tol: convergence tolerance on max |RC_i - target|.
        max_iter: iteration cap.
        init: initial weights (default equal 1/N).

    Returns:
        dict with weights, converged (bool), n_iter, final_max_deviation.
    """
    cov = np.asarray(cov, dtype=float)
    n = cov.shape[0]
    if init is None:
        w = np.full(n, 1.0 / n)
    else:
        w = np.asarray(init, dtype=float).copy()
        w = np.maximum(w, 0.0)
        s = w.sum()
        if s <= 0:
            w = np.full(n, 1.0 / n)
        else:
            w = w / s

    converged = False
    n_iter = 0
    max_dev = float("inf")

    for n_iter in range(1, max_iter + 1):
        # target risk contribution = total_risk / n
        rc = risk_contributions(w, cov)
        total_risk = float(rc.sum())
        if total_risk <= 0:
            break
        target = total_risk / n
        max_dev = float(np.max(np.abs(rc - target)))

        if max_dev < tol:
            converged = True
            break

        # coordinate descent: adjust each weight toward target contribution
        for i in range(n):
            sigma_i = cov[i, :]
            port_var = float(w @ cov @ w)
            if port_var <= 0:
                break
            # current contribution of i
            contrib_i = w[i] * (sigma_i @ w) / np.sqrt(port_var)
            if contrib_i <= 0 or w[i] <= 0:
                continue
            # multiplicative update toward target
            ratio = target / contrib_i if contrib_i > 0 else 1.0
            w_new_i = w[i] * np.clip(ratio, 0.5, 2.0)  # step cap for stability
            w[i] = w_new_i
            w = np.maximum(w, 0.0)
            s = w.sum()
            if s > 0:
                w = w / s

    return {
        "weights": w,
        "converged": converged,
        "n_iter": n_iter,
        "final_max_deviation": max_dev,
        "risk_contributions": risk_contributions(w, cov),
    }


def ensure_psd(cov: np.ndarray, eps: float = 1e-10) -> np.ndarray:
    """Ensure positive definiteness: add |min_eig|+eps to diagonal if needed."""
    cov = np.asarray(cov, dtype=float)
    if not np.isfinite(cov).all():
        raise ValueError("covariance contains NaN/Inf; callers must drop invalid rows first")
    try:
        eig = np.linalg.eigvalsh(cov)
    except np.linalg.LinAlgError:
        # non-convergence guard: jitter diagonal and retry
        cov = cov + eps * np.eye(cov.shape[0])
        eig = np.linalg.eigvalsh(cov)
    if eig.min() < 0:
        cov = cov + (abs(eig.min()) + eps) * np.eye(cov.shape[0])
    return cov