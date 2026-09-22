"""Overlap-aware confidence intervals on EV/R — moving-block bootstrap.

ROADMAP-2026-Q4-RESEARCH.md, §2 Issue B / §9 P0.0.

Problem: label construction scans ``FORWARD_BARS`` bars ahead, so consecutive
trades can share outcome windows (the same underlying price path drives both).
A naive IID bootstrap would treat those correlated trades as independent draws
and report a confidence interval that is *narrower than reality* — making a
noisy result look like a confirmed edge.

Fix: a **moving (circular) block bootstrap** that resamples contiguous blocks
of the ordered trade sequence, preserving the serial dependence structure.

API
---
- :func:`point_evr` — EV/R point estimate (mean realized R).
- :func:`iid_bootstrap_ci` — plain resample-with-replacement (kept ONLY as the
  baseline for tests and diagnostics; never report this as the CI).
- :func:`block_bootstrap_ci` — the real estimator. Use this everywhere.
- :func:`default_block_length` — the roadmap's block-length rule:
  ``max(FORWARD_BARS, median bar-gap between signals)``.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence, Tuple

import numpy as np

# Construction order:
#   returns: 1-D float array of realized R per trade (chronological).
#   block_length: number of consecutive trades per resampled block.
#   n_resamples: bootstrap count (roadmap: 1,000).
#   ci: confidence level (0.95).
#   rng / seed: reproducibility. Pass the same rng to both functions in tests
#     to make draws identical for a like-for-like comparison.


def _as_1d(returns: Sequence[float]) -> np.ndarray:
    arr = np.asarray(returns, dtype=float).reshape(-1)
    if arr.size == 0:
        raise ValueError("returns is empty; cannot estimate EV/R.")
    return arr


def point_evr(returns: Sequence[float]) -> float:
    """EV/R point estimate = mean of per-trade realized R."""
    return float(_as_1d(returns).mean())


def _percentile_ci(means: np.ndarray, ci: float) -> Tuple[float, float]:
    lo_p = 100.0 * (1.0 - ci) / 2.0
    hi_p = 100.0 * (1.0 + ci) / 2.0
    lo, hi = np.percentile(means, [lo_p, hi_p])
    return float(lo), float(hi)


def _prepare_rng(
    rng: Optional[np.random.Generator], seed: Optional[int]
) -> np.random.Generator:
    if rng is not None:
        return rng
    return np.random.default_rng(seed)


def iid_bootstrap_ci(
    returns: Sequence[float],
    n_resamples: int = 1000,
    ci: float = 0.95,
    rng: Optional[np.random.Generator] = None,
    seed: Optional[int] = 42,
) -> Tuple[float, float, float]:
    """IID bootstrap CI on EV/R. Baseline/diagnostic only (see module docstring)."""
    arr = _as_1d(returns)
    n = arr.size
    rng = _prepare_rng(rng, seed)
    means = np.empty(n_resamples)
    for b in range(n_resamples):
        sample = arr[rng.integers(0, n, size=n)]
        means[b] = sample.mean()
    lo, hi = _percentile_ci(means, ci)
    return point_evr(arr), lo, hi


def block_bootstrap_ci(
    returns: Sequence[float],
    block_length: int,
    n_resamples: int = 1000,
    ci: float = 0.95,
    rng: Optional[np.random.Generator] = None,
    seed: Optional[int] = 42,
) -> Tuple[float, float, float]:
    """Moving (circular) block bootstrap CI on EV/R — the estimator to use.

    Resamples contiguous blocks of ``block_length`` consecutive trades, with
    wrap-around at the end of the sequence so all trades are reachable. Block
    length 1 reduces exactly to the IID case (validated in tests).
    """
    arr = _as_1d(returns)
    n = arr.size
    if block_length < 1:
        raise ValueError(f"block_length must be >= 1; got {block_length}.")
    block_length = min(int(block_length), n)  # clamp to full span at most
    rng = _prepare_rng(rng, seed)

    # Wrap the array so a block starting near the end can wrap to the head.
    wrapped = np.concatenate([arr, arr[: block_length - 1]])
    n_blocks = max(1, int(math.ceil(n / block_length)))

    starts = rng.integers(0, n, size=(n_resamples, n_blocks))
    offsets = np.arange(block_length)
    # blocks: (n_resamples, n_blocks, block_length)
    blocks = wrapped[starts[:, :, None] + offsets]
    flat = blocks.reshape(n_resamples, n_blocks * block_length)
    means = flat[:, :n].mean(axis=1)

    lo, hi = _percentile_ci(means, ci)
    return point_evr(arr), lo, hi


def default_block_length(forward_bars: int, median_gap_bars: Optional[float] = None) -> int:
    """Roadmap block-length rule: max(FORWARD_BARS, median signal gap in bars)."""
    if int(forward_bars) < 1:
        raise ValueError(f"forward_bars must be >= 1; got {forward_bars}.")
    length = int(forward_bars)
    if median_gap_bars is not None:
        length = max(length, int(round(float(median_gap_bars))))
    return max(1, length)