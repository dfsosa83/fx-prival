"""
Block bootstrap for time-series inference.

Provides block-bootstrap confidence interval estimation for serially
dependent data (e.g., overlapping trade returns, autocorrelated portfolio
returns). Implements the moving-block bootstrap (MBB) with circular block
resampling.

This is ported from the legacy project's experiments/_core/bootstrap.py,
generalized for any sequence of numeric observations.
"""

from typing import Optional, Sequence, Tuple, Union

import numpy as np


def block_bootstrap_ci(
    observations: Union[Sequence[float], np.ndarray],
    block_length: int = 10,
    n_resamples: int = 1000,
    ci: float = 0.95,
    statistic: str = "mean",
    random_seed: Optional[int] = None,
) -> Tuple[float, float, float]:
    """
    Compute a block-bootstrap confidence interval for a statistic.

    Uses the moving-block bootstrap (MBB) to account for serial dependence
    in the observation sequence. Overlapping labels, autocorrelated returns,
    or clustered trades violate the IID assumption — a naive IID bootstrap
    understates the true variance. The MBB preserves within-block dependence
    by resampling contiguous blocks of observations.

    Algorithm:
        1. Partition the observation sequence into overlapping blocks of
           length `block_length`.
        2. Sample `ceil(n / block_length)` blocks with replacement.
        3. Truncate the concatenated blocks to length n.
        4. Compute the statistic on the resampled sequence.
        5. Repeat `n_resamples` times.
        6. Return the point estimate (on original data) and the CI bounds
           from the bootstrap distribution.

    Args:
        observations: Sequence of numeric observations (e.g., per-trade
                      realized R, daily portfolio returns, PnL).
        block_length: Number of consecutive observations per block. Should
                      be at least the maximum overlap window. For H1 labels
                      with FORWARD_BARS=6, use block_length ≥ 6. For daily
                      returns with moderate autocorrelation, start with
                      block_length = 10.
        n_resamples: Number of bootstrap resamples (default 1000).
        ci: Confidence interval width (default 0.95 for 95% CI).
        statistic: Statistic to bootstrap — 'mean' only for now.
        random_seed: Optional seed for reproducibility.

    Returns:
        Tuple of (point_estimate, ci_lower, ci_upper).

    Raises:
        ValueError: If block_length > len(observations), observations is empty,
                    or statistic is unsupported.
    """
    obs = np.asarray(observations, dtype=np.float64)
    n = len(obs)

    if n == 0:
        raise ValueError("Observations array is empty")
    if block_length < 1:
        raise ValueError(f"block_length must be >= 1, got {block_length}")
    if block_length > n:
        raise ValueError(
            f"block_length ({block_length}) exceeds number of observations ({n})"
        )
    if statistic not in ("mean",):
        raise ValueError(f"Unsupported statistic: '{statistic}'")

    rng = np.random.RandomState(random_seed)

    # Point estimate on original data
    point_estimate = float(np.mean(obs))

    # Number of blocks needed to cover n observations
    n_blocks = int(np.ceil(n / block_length))

    # Pre-compute all possible blocks
    # There are (n - block_length + 1) overlapping blocks
    n_possible_blocks = n - block_length + 1

    bootstrap_estimates = np.empty(n_resamples, dtype=np.float64)

    for i in range(n_resamples):
        # Sample block start indices with replacement
        block_starts = rng.randint(0, n_possible_blocks, size=n_blocks)

        # Build resampled sequence
        resampled = np.concatenate([
            obs[start : start + block_length]
            for start in block_starts
        ])

        # Truncate to original length
        resampled = resampled[:n]

        bootstrap_estimates[i] = np.mean(resampled)

    # Percentile-based CI
    alpha = (1.0 - ci) / 2.0
    ci_lower = float(np.percentile(bootstrap_estimates, 100.0 * alpha))
    ci_upper = float(np.percentile(bootstrap_estimates, 100.0 * (1.0 - alpha)))

    return (point_estimate, ci_lower, ci_upper)


def iid_bootstrap_ci(
    observations: Union[Sequence[float], np.ndarray],
    n_resamples: int = 1000,
    ci: float = 0.95,
    random_seed: Optional[int] = None,
) -> Tuple[float, float, float]:
    """
    IID bootstrap — equivalent to block_bootstrap_ci with block_length=1.

    Provided for comparison and testing. The block bootstrap should reduce
    to this when block_length=1 and observations are independent.

    Args:
        observations: Sequence of numeric observations.
        n_resamples: Number of bootstrap resamples.
        ci: Confidence interval width.
        random_seed: Optional seed for reproducibility.

    Returns:
        Tuple of (point_estimate, ci_lower, ci_upper).
    """
    return block_bootstrap_ci(
        observations=observations,
        block_length=1,
        n_resamples=n_resamples,
        ci=ci,
        random_seed=random_seed,
    )


def ci_summary(
    observations: Union[Sequence[float], np.ndarray],
    block_length: int = 10,
    n_resamples: int = 1000,
    ci: float = 0.95,
    label: str = "",
) -> dict:
    """
    Produce a summary dictionary with point estimate and CI.

    Convenience wrapper around block_bootstrap_ci for experiment reporting.

    Args:
        observations: Sequence of observations.
        block_length: Block length for bootstrap.
        n_resamples: Number of resamples.
        ci: Confidence interval width.
        label: Optional label for the output dict.

    Returns:
        Dict with keys: label, n, point_estimate, ci_lower, ci_upper,
        ci_level, block_length, n_resamples.
    """
    point, lo, hi = block_bootstrap_ci(
        observations=observations,
        block_length=block_length,
        n_resamples=n_resamples,
        ci=ci,
    )
    return {
        "label": label,
        "n": len(observations),
        "point_estimate": point,
        "ci_lower": lo,
        "ci_upper": hi,
        "ci_level": ci,
        "block_length": block_length,
        "n_resamples": n_resamples,
    }