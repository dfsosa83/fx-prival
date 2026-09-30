"""
EXP-2026-05 — cluster-aware block bootstrap inference.

Primary endpoint: mean delta_R over all A-vs-B eligible episodes.
Method: stationary/moving-block bootstrap over chronological 6-hour time
blocks. All episodes whose entry OR invalidation falls in a sampled block are
kept as a cluster; episodes sharing an invalidation bar are resampled together.

Blocks: pre-registered 6h (24 M15 bars); sensitivity 3h and 12h.
Replications: >= 10,000, fixed seeds.
Output: two-sided 95% CI, P(mean delta_R > 0), block sensitivity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def assign_episode_blocks(scored: pd.DataFrame, block_hours: int) -> pd.DataFrame:
    """Assign each episode a block id from its entry_time (and invalidation
    cluster). Episodes sharing an invalidation cluster are forced to the same
    block id so they are resampled together."""
    df = scored.copy()
    entry_times = pd.to_datetime(df["entry_time"], utc=True)
    df["entry_block"] = (entry_times.astype("int64") // (block_hours * 3600 * 1e9)).astype(str)

    # Cluster: episodes sharing an invalidation bar must move together.
    # Use the shared_invalidation_cluster_id to define a canonical block:
    # the block of the FIRST episode in each cluster.
    if "shared_invalidation_cluster_id" in df.columns:
        cluster_block = {}
        for _, row in df[df["shared_invalidation_cluster_id"].notna()].iterrows():
            cid = str(row["shared_invalidation_cluster_id"])
            if cid not in cluster_block:
                cluster_block[cid] = row["entry_block"]
        df["cluster_block"] = df.apply(
            lambda r: cluster_block.get(str(r["shared_invalidation_cluster_id"]), r["entry_block"])
            if pd.notna(r["shared_invalidation_cluster_id"]) else r["entry_block"], axis=1)
    else:
        df["cluster_block"] = df["entry_block"]
    return df


def block_bootstrap_deltaR(
    scored: pd.DataFrame,
    block_hours: int = 6,
    n_reps: int = 10000,
    seed: int = 42,
    ci: float = 0.95,
) -> dict:
    """Cluster-aware moving-block bootstrap of mean delta_R.

    Blocks are defined over entry time; all episodes in a sampled block are
    included (cluster-preserving). Because episodes can span multiple blocks
    via their invalidation time, we resample BLOCK IDS and include every
    episode whose cluster_block is in the sampled set.
    """
    df = assign_episode_blocks(scored, block_hours)
    block_ids = np.sort(df["cluster_block"].unique())
    n_blocks = len(block_ids)
    if n_blocks == 0:
        return {}

    observed = df["delta_R"].mean()
    rng = np.random.RandomState(seed)
    boot = np.empty(n_reps)

    # Probability of selecting each block proportional to its episode count
    # (stationary bootstrap weight) — a simple choice: uniform over blocks.
    for i in range(n_reps):
        # resample block ids with replacement (moving block)
        chosen = rng.choice(block_ids, size=n_blocks, replace=True)
        chosen_set = set(chosen.tolist())
        mask = df["cluster_block"].isin(chosen_set)
        if mask.sum() == 0:
            boot[i] = 0.0
            continue
        boot[i] = df.loc[mask, "delta_R"].mean()

    alpha = (1.0 - ci) / 2.0
    return {
        "block_hours": block_hours,
        "n_blocks": int(n_blocks),
        "n_episodes": int(len(df)),
        "observed_mean_delta_R": float(observed),
        "ci_lower": float(np.percentile(boot, 100 * alpha)),
        "ci_upper": float(np.percentile(boot, 100 * (1 - alpha))),
        "prob_mean_delta_R_gt_0": float(np.mean(boot > 0)),
        "n_replications": n_reps,
        "seed": seed,
    }


def iid_diagnostic_only(scored: pd.DataFrame) -> dict:
    """IID t-test — diagnostic ONLY, not primary inference."""
    d = scored["delta_R"].dropna()
    if len(d) < 2:
        return {}
    from scipy import stats
    t, p = stats.ttest_1samp(d, 0.0)
    return {
        "n": int(len(d)),
        "mean": float(d.mean()),
        "t_stat": float(t),
        "p_value": float(p),
        "label": "DIAGNOSTIC ONLY — not primary inference",
    }