# -*- coding: utf-8 -*-
"""P0-02 offline replacements for the quarantined live kill-switch harness.

Runs entirely offline against the accepted P0-01 fake broker and disposable
data — no terminal, no credentials, no production files:

    python frival/tests_offline/test_kill_switch_offline.py

R0-6 place aborts with the switch armed (before any broker call)
R0-7 close-all is permitted while armed (no --force) and closes fixture positions
R0-8 after disarm, place reaches the guardrails and is BLOCKED (no order_send)
R0-9 a pre-existing kill switch survives, even after an intermediate exception
R0-10 the seeded ledger is unchanged by the kill-switch test
Plus: the blocked legacy entry point is inert on import and exits non-zero.
"""
from __future__ import annotations

import contextlib
import csv
import importlib.util
import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
FRIVAL_DIR = HERE.parent
sys.path.insert(0, str(HERE))

import fake_mt5                                 # noqa: E402
from harness import DeskSandbox                 # noqa: E402


def _load_blocked():
    spec = importlib.util.spec_from_file_location(
        "blocked_test_kill_switch", FRIVAL_DIR / "test_kill_switch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestKillSwitchOffline(unittest.TestCase):

    # R0-6 — place aborts with the switch armed, before any broker access.
    def test_r0_6_place_aborts_with_switch_armed(self):
        with DeskSandbox() as sb:
            sb.arm_kill_switch()
            code, out = sb.run_cli(["place", "--id", "T001"])
            self.assertEqual(sb.fake.called("initialize"), [],
                             "place must not touch the broker while armed")
            self.assertEqual(sb.fake.called("order_send"), [])
            self.assertIn("ABORT", out.upper())

    # Mapping of legacy check 2: read-only status is unaffected while armed.
    def test_r0_6b_status_readonly_with_switch_armed(self):
        with DeskSandbox() as sb:
            sb.arm_kill_switch()
            code, out = sb.run_cli(["status"])
            self.assertEqual(code, 0)
            self.assertIn("KILL SWITCH ACTIVE", out)
            self.assertEqual(sb.fake.called("order_send"), [])

    # R0-7 — close-all is permitted while armed (no --force) on fixture data.
    def test_r0_7_close_all_permitted_while_armed(self):
        with DeskSandbox() as sb:
            sb.arm_kill_switch()
            sb.fake.ORDER_FILLING_IOC = 1                      # constant not in P0-01 fake
            sb.fake.symbols["XAUUSD"] = fake_mt5.symbol_info("XAUUSD")
            sb.fake.ticks["XAUUSD"] = fake_mt5.tick("XAUUSD", bid=2000.0, ask=2000.2)
            sb.fake.positions = [fake_mt5.position("XAUUSD", ticket=501, ptype=0)]
            code, out = sb.run_cli(["close-all", "--reason", "offline test"])
            self.assertNotIn("ABORT", out.upper())
            sends = sb.fake.called("order_send")
            self.assertEqual(len(sends), 1, "one close per fixture position")
            self.assertIn("CLOSE", out.upper())

    # R0-8 — after disarm, place reaches the guardrails and is BLOCKED.
    def test_r0_8_place_reaches_guardrails_after_disarm(self):
        with DeskSandbox() as sb:
            sb.fake.symbols["XAUUSD"] = fake_mt5.symbol_info("XAUUSD")
            sb.fake.ticks["XAUUSD"] = fake_mt5.tick("XAUUSD", bid=2000.0, ask=2000.2)
            ledger = sb.tree / "trade_log.csv"
            header = ledger.read_text(encoding="utf-8").splitlines()[0].split(",")
            decoy = {c: "" for c in header}
            decoy.update({"log_id": "TDECOY", "logged_at_local": "t",
                          "logged_at_server": "t", "symbol": "XAUUSD", "side": "BUY",
                          "order_type": "MARKET", "volume": "1.00",
                          "entry_price": "4000.00", "stop_loss": "3900.00",
                          "tp1": "4300.00", "status": "PENDING_FILL", "notes": "decoy"})
            with ledger.open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([decoy[c] for c in header])
            code, out = sb.run_cli(["place", "--id", "TDECOY"])
            self.assertIn("BLOCKED", out.upper())
            self.assertNotIn("ABORT", out.upper())
            self.assertEqual(sb.fake.called("order_send"), [],
                             "a guardrail-blocked signal must never be sent")

    # R0-9 — a pre-existing kill switch survives an intermediate exception.
    def test_r0_9_preexisting_kill_switch_survives_exception(self):
        with DeskSandbox() as sb:
            ks = sb.arm_kill_switch("PRE-EXISTING")
            sb.run_cli(["status"])
            try:
                raise RuntimeError("injected intermediate failure")
            except RuntimeError:
                pass
            self.assertTrue(ks.exists(), "kill switch must survive an exception")
            self.assertEqual(ks.read_text(encoding="utf-8"), "PRE-EXISTING")

    # R0-10 — the seeded ledger is unchanged by the kill-switch test.
    def test_r0_10_ledger_unchanged(self):
        with DeskSandbox() as sb:
            before = sb.file_hashes()
            sb.arm_kill_switch()
            sb.run_cli(["place", "--id", "T001"])               # aborts, no write
            after = sb.file_hashes()
            self.assertEqual(before["trade_log.csv"], after["trade_log.csv"],
                             "ledger must not change during the kill-switch test")
            self.assertEqual(before["executor_state.json"], after["executor_state.json"])


class TestBlockedLegacyEntryPoint(unittest.TestCase):

    def test_blocked_source_has_no_broker_or_subprocess(self):
        src = (FRIVAL_DIR / "test_kill_switch.py").read_text(encoding="utf-8")
        for forbidden in ("import MetaTrader5", "import subprocess",
                          "subprocess.run", "subprocess.Popen",
                          "mt5.initialize", "--force"):
            self.assertNotIn(forbidden, src,
                             f"blocked entry must not contain {forbidden!r}")

    def test_import_has_no_operational_side_effects(self):
        sys.modules.pop("MetaTrader5", None)
        mod = _load_blocked()
        self.assertNotIn("MetaTrader5", sys.modules,
                         "importing the blocked entry must not import MT5")
        self.assertTrue(hasattr(mod, "main"))

    def test_main_exits_nonzero(self):
        mod = _load_blocked()
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            rc = mod.main()
        self.assertNotEqual(rc, 0)
        self.assertIn("DISABLED", buf.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
