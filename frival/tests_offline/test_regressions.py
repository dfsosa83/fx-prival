# -*- coding: utf-8 -*-
"""P0-01 defect regressions: D1 (cleanup on failed __enter__) and D2 (path
containment). Runnable offline, no terminal:

    python frival/tests_offline/test_regressions.py
"""
from __future__ import annotations

import contextlib
import io
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness                                 # noqa: E402
from harness import DeskSandbox, IsolationError, CleanupError  # noqa: E402

GLOBAL_KEYS = ("MetaTrader5", "mt5_path", "order_executor")


def snapshot():
    return {
        "path": list(sys.path),
        "env": os.environ.get("MT5_PATH"),
        "mods": {k: sys.modules.get(k) for k in GLOBAL_KEYS},
    }


class _RestoreMixin:
    def assert_restored(self, before):
        self.assertEqual(sys.path, before["path"], "sys.path not restored")
        self.assertEqual(os.environ.get("MT5_PATH"), before["env"], "MT5_PATH not restored")
        for k, v in before["mods"].items():
            self.assertIs(sys.modules.get(k), v, f"sys.modules[{k!r}] not restored")


class TestD1CleanupOnFailure(_RestoreMixin, unittest.TestCase):
    """__enter__ must fully restore globals if it fails before returning."""

    def test_import_failure_restores_globals(self):
        before = snapshot()
        with self.assertRaises(Exception):
            DeskSandbox(module_name="nonexistent_mod_xyz").__enter__()
        self.assert_restored(before)
        self.assertIsNone(sys.modules.get("nonexistent_mod_xyz"))

    def test_import_failure_preserves_original_exception(self):
        try:
            DeskSandbox(module_name="nonexistent_mod_xyz").__enter__()
        except Exception as exc:                       # noqa: BLE001
            self.assertIsInstance(exc, FileNotFoundError,
                                  "cleanup masked the original import error")
        else:
            self.fail("expected an exception")

    def test_verification_failure_restores_globals(self):
        before = snapshot()
        original = harness.verify_isolation

        def boom(mod, tmp):
            raise IsolationError("injected post-import verification failure")

        harness.verify_isolation = boom
        try:
            with self.assertRaises(IsolationError):
                DeskSandbox().__enter__()
        finally:
            harness.verify_isolation = original
        self.assert_restored(before)

    def test_restores_absent_module_entry(self):
        sys.modules.pop("order_executor", None)
        before = snapshot()                            # order_executor -> None
        original = harness.verify_isolation
        harness.verify_isolation = lambda mod, tmp: (_ for _ in ()).throw(
            IsolationError("injected"))
        try:
            with self.assertRaises(IsolationError):
                DeskSandbox().__enter__()
        finally:
            harness.verify_isolation = original
        self.assertIsNone(sys.modules.get("order_executor"),
                          "leaked module entry that was absent before")

    def test_restores_preexisting_module_entry(self):
        sentinel = object()
        sys.modules["order_executor"] = sentinel
        original = harness.verify_isolation
        harness.verify_isolation = lambda mod, tmp: (_ for _ in ()).throw(
            IsolationError("injected"))
        try:
            with self.assertRaises(IsolationError):
                DeskSandbox().__enter__()
            self.assertIs(sys.modules.get("order_executor"), sentinel,
                          "pre-existing module entry not restored")
        finally:
            harness.verify_isolation = original
            sys.modules.pop("order_executor", None)

    def test_cleanup_idempotent_and_exit_safe_after_failure(self):
        sb = DeskSandbox(module_name="nonexistent_mod_xyz")
        with self.assertRaises(Exception):
            sb.__enter__()
        sb.__exit__(None, None, None)                  # must be safe
        sb.__exit__(None, None, None)                  # and idempotent


class TestD2Containment(unittest.TestCase):
    """verify_isolation must use path-aware containment, not string prefix."""

    def _mod(self, base: Path, log: Path):
        return types.SimpleNamespace(LOG_PATH=log, STATE_PATH=base / "s.json",
                                     AUDIT_PATH=base / "a.jsonl",
                                     KILL_SWITCH=base / "k.txt")

    def _tmp(self):
        return Path(tempfile.mkdtemp(prefix="frival_contain_"))

    def test_inside_root_ok(self):
        tmp = self._tmp()
        try:
            mod = self._mod(tmp / "frival", tmp / "frival" / "trade_log.csv")
            harness.verify_isolation(mod, tmp)         # must not raise
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_sibling_prefix_rejected(self):
        tmp = self._tmp()
        try:
            sibling = tmp.parent / (tmp.name + "_x")
            mod = self._mod(tmp / "frival", sibling / "trade_log.csv")
            with self.assertRaises(IsolationError):
                harness.verify_isolation(mod, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_outside_rejected(self):
        tmp = self._tmp()
        try:
            outside = tmp.parent / "elsewhere_frival"
            mod = self._mod(tmp / "frival", outside / "trade_log.csv")
            with self.assertRaises(IsolationError):
                harness.verify_isolation(mod, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestCleanupFailureHandling(_RestoreMixin, unittest.TestCase):
    """D1 follow-up: cleanup must survive its own failures and stay observable."""

    def _break_rmtree(self):
        original = harness.shutil.rmtree
        harness.shutil.rmtree = lambda *a, **k: (_ for _ in ()).throw(
            OSError("injected rmtree failure"))
        return original

    def test_init_failure_with_cleanup_failure_keeps_original_primary(self):
        before = snapshot()
        original = self._break_rmtree()
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                with self.assertRaises(FileNotFoundError) as cm:
                    DeskSandbox(module_name="nonexistent_mod_xyz").__enter__()
        finally:
            harness.shutil.rmtree = original
        self.assertIsInstance(cm.exception, FileNotFoundError,
                              "cleanup failure masked the original exception")
        self.assertTrue(getattr(cm.exception, "_sandbox_cleanup_failures", None),
                        "cleanup failure was not recorded on the exception")
        self.assertIn("cleanup incomplete", err.getvalue(),
                      "cleanup failure was not reported as a diagnostic")
        self.assert_restored(before)

    def test_one_step_failure_does_not_abort_others(self):
        before = snapshot()
        original = self._break_rmtree()
        try:
            with self.assertRaises(CleanupError) as cm:
                with DeskSandbox() as _sb:
                    pass
        finally:
            harness.shutil.rmtree = original
        # independent restorations still happened despite the rmtree failure
        self.assert_restored(before)
        self.assertIn("rmtree", [name for name, _ in cm.exception.failures])

    def test_cleanup_failure_is_reported(self):
        original = self._break_rmtree()
        try:
            with self.assertRaises(CleanupError) as cm:
                with DeskSandbox() as _sb:
                    pass
        finally:
            harness.shutil.rmtree = original
        self.assertIn("cleanup incomplete", str(cm.exception))
        self.assertIn("rmtree", str(cm.exception))

    def test_cleanup_failure_after_success_not_silent(self):
        original = self._break_rmtree()
        entered = False
        try:
            with self.assertRaises(CleanupError):
                with DeskSandbox() as _sb:
                    entered = True                     # body itself succeeded
        finally:
            harness.shutil.rmtree = original
        self.assertTrue(entered, "context body should have run before the failure")

    def test_repeated_cleanup_completed_and_pending(self):
        # completed case: a second cleanup is a no-op
        with DeskSandbox() as sb:
            pass
        self.assertTrue(sb._cleanup_complete)
        self.assertEqual(sb._cleanup(), [])

        # pending case: incomplete, then completes once the failing step works
        original = self._break_rmtree()
        try:
            sb2 = DeskSandbox(module_name="nonexistent_mod_xyz")
            with self.assertRaises(FileNotFoundError):
                sb2.__enter__()
            self.assertFalse(sb2._cleanup_complete)
            self.assertTrue(sb2._cleanup_failures)
        finally:
            harness.shutil.rmtree = original
        self.assertEqual(sb2._cleanup(), [], "retry should complete once rmtree works")
        self.assertTrue(sb2._cleanup_complete)


if __name__ == "__main__":
    unittest.main(verbosity=2)
