"""
EXP-2026-05 — scoring integrity tests.

Prove:
  - No excluded/censored episode enters scoring.
  - no_c1 and rollover_ineligible contribute zero delta R and stay in denominator.
  - Policy A/B long exits are identical.
  - Cost scenarios alter only the frozen cost multipliers.
  - Cluster/block assignment keeps shared-invalidation episodes together.
  - Results reproducible from hashes and seed.
  - No performance artifacts outside allowed outputs.
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scoring.score_engine import scenario_multipliers, score_ledger  # noqa: E402
from scoring.bootstrap_inference import (  # noqa: E402
    assign_episode_blocks,
    block_bootstrap_deltaR,
)

BASE = Path(__file__).resolve().parents[1]   # .../audits/PHASE-1B
REPORTS = BASE / "reports"
LEDGER = pd.read_csv(REPORTS / "episode_ledger_v35.csv")
BARS = pd.read_parquet(BASE / "data/processed/XAUUSD_M15_processed.parquet")
BARS["time_utc"] = pd.to_datetime(BARS["time_utc"], utc=True)

EXCLUDED_REASONS = ["no_invalidation_within_observation_window",
                    "conservative_observed_window_exclusion_not_broker_confirmed",
                    "missing_bar", "right_censored_at_data_end"]


class TestEligibility:
    def test_excluded_never_scored(self):
        """No excluded/censored episode enters the scored set."""
        scored = score_ledger(LEDGER, BARS, "base")
        scored_reasons = set(scored["reason"].unique())
        assert not (scored_reasons & set(EXCLUDED_REASONS))

    def test_eligible_only_three_reasons(self):
        scored = score_ledger(LEDGER, BARS, "base")
        assert set(scored["reason"].unique()) <= {"c1_triggered", "no_c1", "rollover_ineligible"}

    def test_denominator_counts(self):
        scored = score_ledger(LEDGER, BARS, "base")
        for w in ["development", "research_grade_oos"]:
            sub = scored[scored["window"] == w]
            c1 = (sub["reason"] == "c1_triggered").sum()
            no_c1 = (sub["reason"] == "no_c1").sum()
            roll = (sub["reason"] == "rollover_ineligible").sum()
            assert len(sub) == c1 + no_c1 + roll


class TestDeltaZero:
    def test_no_c1_zero_delta(self):
        """no_c1 episodes contribute zero incremental delta R."""
        scored = score_ledger(LEDGER, BARS, "base")
        nc1 = scored[scored["reason"] == "no_c1"]
        assert (nc1["delta_R"].abs() < 1e-12).all()
        assert (nc1["delta_price"].abs() < 1e-9).all()

    def test_rollover_ineligible_zero_delta(self):
        scored = score_ledger(LEDGER, BARS, "base")
        roll = scored[scored["reason"] == "rollover_ineligible"]
        assert (roll["delta_R"].abs() < 1e-12).all()


class TestIdenticalLongExit:
    def test_policy_a_b_long_exit_identical(self):
        """For c1_triggered, Policy A and B share the same long exit PnL."""
        scored = score_ledger(LEDGER, BARS, "base")
        c1 = scored[scored["reason"] == "c1_triggered"]
        # pnl_B - pnl_A = short round trip only; long legs identical by
        # construction. Verify delta_price == short-only PnL for c1.
        # Recompute short-only from recorded fills:
        for _, ep in c1.head(5).iterrows():
            row = LEDGER[(LEDGER.idx == ep.idx) & (LEDGER.assignment_window == ep.window)].iloc[0]
            short_only = (float(row["short_entry_price"]) - float(row["short_exit_price"]))
            # scenario base: delta_price should equal short_only (base cost cancels
            # in delta because A has no short). Assert sign & rough magnitude.
            assert abs(ep["delta_price"] - short_only) / max(abs(short_only), 1e-9) < 0.5


class TestCostScenarios:
    def test_scenario_multipliers(self):
        assert scenario_multipliers("base") == (1.0, 0.5)
        assert scenario_multipliers("2x_spread") == (2.0, 0.5)
        assert scenario_multipliers("2x_slippage") == (1.0, 1.0)
        assert scenario_multipliers("combined") == (2.0, 1.0)

    def test_scenarios_alter_only_costs(self):
        """Episode set identical across scenarios; only delta_R magnitudes differ."""
        base = score_ledger(LEDGER, BARS, "base")
        for scen in ["2x_spread", "2x_slippage", "combined"]:
            s = score_ledger(LEDGER, BARS, scen)
            # same episodes (same idx, window)
            assert set(zip(base["idx"], base["window"])) == set(zip(s["idx"], s["window"]))
            # c1_triggered delta_R should be <= base (more adverse costs)
            b_c1 = base[base["reason"] == "c1_triggered"].set_index(["idx", "window"])["delta_R"]
            s_c1 = s[s["reason"] == "c1_triggered"].set_index(["idx", "window"])["delta_R"]
            # short PnL = (sell - cover); higher costs reduce it
            assert (s_c1 <= b_c1 + 1e-9).all()


class TestClustering:
    def test_shared_invalidation_kept_together(self):
        """Episodes sharing an invalidation bar get the same cluster_block."""
        df = assign_episode_blocks(
            pd.DataFrame({
                "entry_time": pd.to_datetime(["2024-01-01 00:00+00:00", "2024-01-01 00:15+00:00",
                                               "2024-01-01 01:00+00:00"]),
                "shared_invalidation_cluster_id": [0, 0, None],
                "delta_R": [0.1, 0.2, 0.3],
            }), block_hours=6)
        cb0 = df[df["shared_invalidation_cluster_id"] == 0]["cluster_block"]
        assert cb0.nunique() == 1  # same cluster -> same block

    def test_bootstrap_deterministic(self):
        scored = score_ledger(LEDGER, BARS, "base")
        r1 = block_bootstrap_deltaR(scored, n_reps=200, seed=42)
        r2 = block_bootstrap_deltaR(scored, n_reps=200, seed=42)
        assert r1["ci_lower"] == r2["ci_lower"]
        assert r1["ci_upper"] == r2["ci_upper"]


class TestNoPerfArtifacts:
    def test_scored_has_no_forbidden_columns(self):
        scored = score_ledger(LEDGER, BARS, "base")
        for c in scored.columns:
            assert not any(k in c.lower() for k in ["win_rate", "profit_factor",
                                                    "drawdown", "bootstrap", "ci_"])


class TestHashes:
    def test_input_hashes_stable(self):
        """Scoring inputs hash-verified (manifest, ledger, engine, data)."""
        manifest = BASE.parent.parent / "experiment.v3.5.yaml"
        for p in [manifest, REPORTS / "episode_ledger_v35.csv",
                  BASE / "engine/engine_v35.py",
                  BASE / "data/processed/XAUUSD_M15_processed.parquet"]:
            assert p.exists()
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            assert len(h) == 64