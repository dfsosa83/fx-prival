# -*- coding: utf-8 -*-
"""P0-01 regression tests: offline isolation of the desk test environment.

Run offline, no terminal, no live account:
    python frival/tests_offline/test_isolation.py

Covers the P0-01 acceptance tests R0-1..R0-5 plus a production-untouched check.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                 # so `import harness`/`fake_mt5` work

import harness                                # noqa: E402
from harness import DeskSandbox, IsolationError, SOURCE_DESK, MT5_PATH_SENTINEL  # noqa: E402


def _hash_tree(paths):
    out = {}
    for p in paths:
        p = Path(p)
        out[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    return out


class TestIsolation(unittest.TestCase):

    # R0-1 — isolation verified: every resolved path is inside the temp tree.
    def test_r0_1_paths_inside_temp_tree(self):
        with DeskSandbox() as sb:
            for attr in ("LOG_PATH", "STATE_PATH", "AUDIT_PATH", "KILL_SWITCH"):
                self.assertTrue(harness._is_within(getattr(sb.mod, attr), sb.tmp),
                                f"{attr} escaped the temp tree")
            self.assertTrue(harness._is_within(sb.mod.__file__, sb.tmp),
                            "module was not imported from the temp tree")
            self.assertEqual(sb.mod.TERMINAL_PATH, MT5_PATH_SENTINEL)

    # R0-2 — no real terminal: initialize is called on the fake with the sentinel.
    def test_r0_2_no_real_terminal(self):
        with DeskSandbox() as sb:
            code, out = sb.run_cli(["status"])
            inits = sb.fake.called("initialize")
            self.assertEqual(len(inits), 1, "initialize should be called exactly once")
            self.assertEqual(inits[0]["path"], MT5_PATH_SENTINEL)
            self.assertIs(sys.modules.get("MetaTrader5"), sb.fake)
            self.assertIn("account 81486396", out)
            self.assertEqual(code, 0)

    # R0-3 — fail-safe: if the fake is absent, refuse before any effect.
    def test_r0_3_refuses_without_fake(self):
        with DeskSandbox() as sb:
            before = sb.file_hashes()
            sys.modules.pop("MetaTrader5", None)          # simulate fake missing
            with self.assertRaises(IsolationError):
                sb.run_cli(["status"])
            self.assertEqual(before, sb.file_hashes(), "no effect expected on refusal")

    # R0-4 — `status` writes only the temp executor_state.json.
    def test_r0_4_status_only_writes_state(self):
        with DeskSandbox() as sb:
            before = sb.file_hashes()
            sb.run_cli(["status"])
            after = sb.file_hashes()
            self.assertEqual(before["trade_log.csv"], after["trade_log.csv"])
            self.assertEqual(before["execution_audit.jsonl"], after["execution_audit.jsonl"])
            self.assertNotEqual(before["executor_state.json"], after["executor_state.json"],
                                "status should rewrite the (temp) state file")

    # R0-5 — kill switch: `place` aborts before initialize (no broker call).
    def test_r0_5_kill_switch_blocks_before_broker(self):
        with DeskSandbox() as sb:
            sb.arm_kill_switch()
            code, out = sb.run_cli(["place", "--id", "T001"])
            self.assertEqual(sb.fake.called("initialize"), [],
                             "place must not touch the broker when the kill switch is armed")
            self.assertEqual(sb.fake.called("order_send"), [])
            self.assertIn("ABORT", out.upper())


class TestProductionUntouched(unittest.TestCase):

    def test_production_files_unchanged_by_suite(self):
        prod_py = [SOURCE_DESK / n for n in harness.MODULES]
        prod_data = [SOURCE_DESK / n for n in
                     ("trade_log.csv", "execution_audit.jsonl", "executor_state.json")]
        before = _hash_tree(prod_py + prod_data)
        with DeskSandbox() as sb:
            sb.run_cli(["status"])
        after = _hash_tree(prod_py + prod_data)
        # Source modules are the strict guarantee; data files should also be
        # untouched while the market is closed (the live cron could write them
        # during market hours — that would be the only legitimate difference).
        for p in prod_py:
            self.assertEqual(before[str(p)], after[str(p)],
                             f"test harness modified production source {p}")
        for p in prod_data:
            self.assertEqual(before[str(p)], after[str(p)],
                             f"test harness modified production data {p}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
