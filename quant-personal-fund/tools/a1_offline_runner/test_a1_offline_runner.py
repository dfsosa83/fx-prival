"""Offline validation tests for the A1 isolated fixture runner.

Uses ONLY the existing local XAUUSD fixtures and temporary directories.
Never imports MT5/broker/execution. This is a unit-level validation of the new
runner — NOT the formal two-run reproducibility stage.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import a1_offline_runner as runner  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
A1_DIR = REPO / "frival" / "gold_rules"
FIX = A1_DIR / "tests" / "fixtures"
M15, M30, H1 = FIX / "XAUUSD_M15.csv", FIX / "XAUUSD_M30.csv", FIX / "XAUUSD_H1.csv"


def _canon_list(records, strip_run=True):
    out = []
    for r in records:
        c = dict(r)
        if strip_run:
            c["event_id"] = c["event_id"].split(":")[-1]
        out.append(json.dumps(c, sort_keys=True, separators=(",", ":"), default=str))
    return out


class TestA1OfflineRunner(unittest.TestCase):
    def test_01_no_prohibited_imports_in_runner_or_modules(self):
        bias_mod, levels_mod, engine_mod = runner.load_a1_modules(A1_DIR)
        hits = runner.forbidden_import_scan(
            [Path(runner.__file__), Path(engine_mod.__file__),
             Path(bias_mod.__file__), Path(levels_mod.__file__)])
        self.assertEqual(hits, [], f"prohibited imports found: {hits}")

    def test_02_fixtures_hash_identical_before_and_after(self):
        before = {p.name: runner.sha256_file(p) for p in (M15, M30, H1)}
        runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="t2")
        after = {p.name: runner.sha256_file(p) for p in (M15, M30, H1)}
        self.assertEqual(before, after)

    def test_03_fixture_schema_validates_and_fails_clearly(self):
        df = runner.load_fixture_bars(M15)
        runner.validate_fixture_schema(df)  # must not raise
        bad = df.drop(columns=["close"])
        with self.assertRaises(ValueError):
            runner.validate_fixture_schema(bad)

    def test_04_binds_real_pure_module_paths_and_hashes(self):
        res = runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="t4")
        for name in ("engine.py", "bias.py", "levels.py"):
            self.assertIn(name, res["module_hashes"])
            self.assertEqual(len(res["module_hashes"][name]), 64)
        for p in (M15, M30, H1):
            self.assertTrue(str(p).endswith(".csv"))

    def test_05_records_have_all_required_fields(self):
        res = runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="t5")
        self.assertGreater(res["cycle_count"], 0)
        for rec in res["records"]:
            for f in runner._EVENT_FIELDS:
                self.assertIn(f, rec)

    def test_06_records_have_no_execution_or_pnl_fields(self):
        res = runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="t6")
        for rec in res["records"]:
            for f in runner._PROHIBITED_EVENT_FIELDS:
                self.assertNotIn(f, rec)

    def test_07_deterministic_serialization_within_one_run(self):
        res = runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="t7")
        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / "a.jsonl"
            b = Path(td) / "b.jsonl"
            runner.write_event_records(res["records"], a)
            runner.write_event_records(res["records"], b)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_08_two_runs_identical_excluding_run_metadata(self):
        r1 = runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="runA")
        r2 = runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="runB")
        self.assertEqual(_canon_list(r1["records"]), _canon_list(r2["records"]))

    def test_09_temp_outputs_inside_tempdir_and_cleaned(self):
        res = runner.run_a1_offline(M15, M30, H1, A1_DIR, warmup_m15=100, run_id="t9")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "events.jsonl"
            runner.write_event_records(res["records"], out)
            self.assertTrue(out.exists())
            self.assertTrue(str(out).startswith(str(Path(td))))
        self.assertFalse(Path(td).exists())  # cleaned up

    def test_10_no_broker_mt5_network_exec_env_access(self):
        bias_mod, levels_mod, engine_mod = runner.load_a1_modules(A1_DIR)
        hits = runner.forbidden_import_scan(
            [Path(runner.__file__), Path(engine_mod.__file__),
             Path(bias_mod.__file__), Path(levels_mod.__file__)])
        self.assertEqual(hits, [])
        self.assertNotIn("MetaTrader5", sys.modules)
        self.assertNotIn("execution_bot", sys.modules)
        for m in (engine_mod, bias_mod, levels_mod):
            self.assertTrue(str(Path(m.__file__)).endswith(("engine.py", "bias.py", "levels.py")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
