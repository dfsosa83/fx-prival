"""Tests for experiments/_core/bootstrap.py.

Roadmap P0.0 validation checks (ROADMAP-2026-Q4-RESEARCH.md §9 P0.0):
1. On synthetic IID Gaussian returns, the block-bootstrap CI width converges to
   the IID-bootstrap CI width as block_length -> 1 (implementation reduces to
   the known-correct case).
2. On synthetic AR(1)-correlated returns (autocorrelation rho=0.5), the block
   bootstrap (block_length > 1) produces a WIDER CI than a naive IID bootstrap
   on the same data — proves the correction does something.
"""

import numpy as np
import pytest

from experiments._core import bootstrap


def _iid_gaussian(n=500, mean=0.0, std=1.0, seed=11):
    rng = np.random.default_rng(seed)
    return rng.normal(mean, std, size=n).tolist()


def _ar1(n=1000, rho=0.5, std=1.0, seed=7):
    """Positive-autocorrelated series AR(1): x_t = rho * x_{t-1} + eps_t."""
    rng = np.random.default_rng(seed)
    eps = rng.normal(0.0, std, size=n)
    x = np.empty(n)
    x[0] = eps[0]
    for t in range(1, n):
        x[t] = rho * x[t - 1] + eps[t]
    return x.tolist()


# ── Sanity: shape of the result ──────────────────────────────────────────────

def test_returns_point_lo_hi_tuple():
    res = bootstrap.block_bootstrap_ci([0.1, -0.3, 0.5, 0.2, -0.1, 0.4], block_length=2)
    assert len(res) == 3
    point, lo, hi = res
    assert lo <= point <= hi
    assert lo < hi


def test_point_evr_is_mean():
    x = [0.1, -0.3, 0.5, 0.2]
    assert bootstrap.point_evr(x) == pytest.approx(np.mean(x))


def test_empty_returns_raise():
    with pytest.raises(ValueError):
        bootstrap.block_bootstrap_ci([], block_length=2)
    with pytest.raises(ValueError):
        bootstrap.iid_bootstrap_ci([])


def test_invalid_block_length_raises():
    with pytest.raises(ValueError):
        bootstrap.block_bootstrap_ci([0.1, 0.2, 0.3], block_length=0)


def test_default_block_length_rule():
    # max(FORWARD_BARS, median gap) with floor at 1
    assert bootstrap.default_block_length(6, median_gap_bars=12) == 12
    assert bootstrap.default_block_length(6, median_gap_bars=3) == 6
    assert bootstrap.default_block_length(6, median_gap_bars=0) == 6
    assert bootstrap.default_block_length(1, median_gap_bars=0.0) == 1


# ── Roadmap P0.0 validation check 1: block->1 converges to IID ───────────────

def test_block_length_1_matches_iid_bootstrap():
    """Same RNG stream and block length 1 must give the same draw sequence as
    the IID bootstrap — identical resample distribution, identical CI."""
    x = _iid_gaussian()
    rng_block = np.random.default_rng(42)
    rng_iid = np.random.default_rng(42)  # identical seed -> identical draws
    p_b, lo_b, hi_b = bootstrap.block_bootstrap_ci(x, block_length=1, rng=rng_block)
    p_i, lo_i, hi_i = bootstrap.iid_bootstrap_ci(x, rng=rng_iid)
    assert p_b == pytest.approx(p_i)
    assert lo_b == pytest.approx(lo_i)
    assert hi_b == pytest.approx(hi_i)


def test_block_length_1_width_equals_iid_width():
    """A looser statistical check (widely used seeds): width ratio ~1."""
    widths = []
    for seed in (1, 2, 3):
        x = _iid_gaussian(seed=100 + seed)
        _, lo_b, hi_b = bootstrap.block_bootstrap_ci(x, block_length=1, seed=seed)
        _, lo_i, hi_i = bootstrap.iid_bootstrap_ci(x, seed=seed)
        widths.append((hi_b - lo_b) / (hi_i - lo_i))
    assert all(0.90 <= r <= 1.10 for r in widths)


# ── Roadmap P0.0 validation check 2: AR(1) block > IID width ─────────────────

def test_ar1_block_bootstrap_wider_than_iid():
    x = _ar1(rho=0.5, n=2000)
    _, lo_block, hi_block = bootstrap.block_bootstrap_ci(
        x, block_length=20, n_resamples=1000, seed=3
    )
    _, lo_iid, hi_iid = bootstrap.iid_bootstrap_ci(x, n_resamples=1000, seed=3)
    width_block = hi_block - lo_block
    width_iid = hi_iid - lo_iid
    # Positive autocorrelation means IID understates variance; block must be wider.
    assert width_block > 1.02 * width_iid, (
        f"block width {width_block:.5f} should exceed IID width {width_iid:.5f} "
        f"on positively autocorrelated data"
    )


def test_larger_block_preserves_wider_than_iid_on_ar1():
    """The overlap correction must hold for a larger block length too."""
    x = _ar1(rho=0.6, n=2000)
    _, lo40, hi40 = bootstrap.block_bootstrap_ci(x, block_length=40, seed=5)
    _, lo_iid, hi_iid = bootstrap.iid_bootstrap_ci(x, seed=5)
    assert (hi40 - lo40) > (hi_iid - lo_iid)


# ── Reproducibility ──────────────────────────────────────────────────────────

def test_block_bootstrap_reproducible_with_seed():
    x = _ar1(rho=0.4, n=500)
    r1 = bootstrap.block_bootstrap_ci(x, block_length=15, seed=99)
    r2 = bootstrap.block_bootstrap_ci(x, block_length=15, seed=99)
    assert r1 == r2


def test_block_bootstrap_respects_rng():
    x = _iid_gaussian()
    g1 = np.random.default_rng(1)
    g2 = np.random.default_rng(2)  # different stream -> different CIs generally
    r1 = bootstrap.block_bootstrap_ci(x, block_length=4, rng=g1)
    r2 = bootstrap.block_bootstrap_ci(x, block_length=4, rng=g2)
    # point estimate identical (same data), CI may differ
    assert r1[0] == r2[0]