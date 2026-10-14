# -*- coding: utf-8 -*-
"""Offline desk test harness (P0-01).

Builds a throwaway tree ``<tmp>/frival/`` containing COPIES of the desk modules,
seeds synthetic fixtures, installs the fake broker (``fake_mt5.FakeMT5``) into
``sys.modules["MetaTrader5"]``, imports the module under test FROM THE TEMP TREE,
and refuses to run anything unless it can PROVE isolation:

* every path the module resolves (LOG_PATH, STATE_PATH, AUDIT_PATH, KILL_SWITCH)
  is inside the temp tree;
* the ``MetaTrader5`` in use is the fake, never the real package.

No existing repository file is read except the schema header is not needed; all
fixtures are synthetic. Nothing in the live desk is touched.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import fake_mt5

SOURCE_DESK = Path(__file__).resolve().parent.parent          # the real frival/
MODULES = ("order_executor.py", "mt5_path.py", "log_trade.py",
           "counterfactual.py", "reconcile_deals.py", "market_context.py",
           "eod_review.py")

MT5_PATH_SENTINEL = r"__OFFLINE_SENTINEL_NO_TERMINAL__"

# Minimal synthetic ledger schema (only the columns the code paths under test
# read). Deliberately NOT the live file.
LEDGER_HEADER = (
    "log_id,logged_at_local,logged_at_server,symbol,side,order_type,volume,"
    "entry_price,stop_loss,tp1,status,notes,pnl_usd,r_multiple,"
    "exit_time_local,exit_price,fill_price,sl_distance\n"
)
LEDGER_ROW = (
    "T001,2026-01-01 00:00:00,2026-01-01 03:00:00,XAUUSD,BUY,LIMIT,0.05,"
    "2000.00,1990.00,2020.00,CLOSED,offline fixture,-10.00,-1.00,"
    "2026-01-01 01:00:00,1990.00,2000.00,10.00\n"
)


class IsolationError(RuntimeError):
    """Raised when the sandbox cannot prove it is isolated from production."""


def _seed_tree(tmp: Path) -> Path:
    tree = tmp / "frival"
    tree.mkdir(parents=True, exist_ok=True)
    (tree / "data").mkdir(exist_ok=True)

    for name in MODULES:
        src = SOURCE_DESK / name
        if src.exists():
            shutil.copy2(src, tree / name)

    # Synthetic fixtures. No config/.env (so resolve_terminal_path falls back to
    # the MT5_PATH sentinel we set in the environment).
    (tree / "trade_log.csv").write_text(LEDGER_HEADER + LEDGER_ROW, encoding="utf-8")
    (tree / "execution_audit.jsonl").write_text("", encoding="utf-8")
    (tree / "executor_state.json").write_text(
        json.dumps({"session_date": "1970-01-01", "session_start_equity": 0.0,
                    "consecutive_losses": 0, "daily_realised": 0.0}),
        encoding="utf-8")
    return tree


def verify_isolation(mod, tmp: Path) -> None:
    """Abort (raise) unless every resolved path is inside the temp tree."""
    tmp_s = str(tmp.resolve())
    for attr in ("LOG_PATH", "STATE_PATH", "AUDIT_PATH", "KILL_SWITCH"):
        p = getattr(mod, attr, None)
        if p is None:
            raise IsolationError(f"{attr} missing on module under test")
        if not str(Path(p).resolve()).startswith(tmp_s):
            raise IsolationError(f"{attr}={p} escapes the temp tree {tmp}")


class DeskSandbox:
    """Context manager: isolated temp tree + fake broker + module under test."""

    def __init__(self, module_name: str = "order_executor"):
        self.module_name = module_name
        self.tmp: Path | None = None
        self.tree: Path | None = None
        self.fake: fake_mt5.FakeMT5 | None = None
        self.mod = None
        self._saved = None

    def __enter__(self):
        self._saved = {
            "path": list(sys.path),
            "env": os.environ.get("MT5_PATH"),
            "mods": {k: sys.modules.get(k) for k in
                     ("MetaTrader5", "mt5_path", self.module_name)},
        }
        self.tmp = Path(tempfile.mkdtemp(prefix="frival_offline_"))
        self.tree = _seed_tree(self.tmp)
        self.fake = fake_mt5.FakeMT5(sentinel_path=MT5_PATH_SENTINEL)

        os.environ["MT5_PATH"] = MT5_PATH_SENTINEL
        for k in ("MetaTrader5", "mt5_path", self.module_name):
            sys.modules.pop(k, None)
        sys.modules["MetaTrader5"] = self.fake
        sys.path.insert(0, str(self.tree))

        spec = importlib.util.spec_from_file_location(
            self.module_name, self.tree / f"{self.module_name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[self.module_name] = mod
        spec.loader.exec_module(mod)
        self.mod = mod

        verify_isolation(mod, self.tmp)
        if sys.modules.get("MetaTrader5") is not self.fake:
            raise IsolationError("MetaTrader5 is not the fake broker")
        return self

    def __exit__(self, *exc):
        s = self._saved
        sys.path[:] = s["path"]
        if s["env"] is None:
            os.environ.pop("MT5_PATH", None)
        else:
            os.environ["MT5_PATH"] = s["env"]
        for k, v in s["mods"].items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
        if self.tmp and self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)
        return False

    # ── helpers ─────────────────────────────────────────────────────────────
    def arm_kill_switch(self, text: str = "STOP") -> Path:
        ks = self.tree / "data" / "emergency_stop.txt"
        ks.write_text(text, encoding="utf-8")
        return ks

    def file_hashes(self) -> dict:
        out = {}
        for name in ("trade_log.csv", "execution_audit.jsonl", "executor_state.json"):
            p = self.tree / name
            out[name] = p.read_bytes() if p.exists() else None
        return out

    def run_cli(self, argv: list) -> tuple:
        """Run the module's CLI in-process with the fake broker installed."""
        if sys.modules.get("MetaTrader5") is not self.fake:
            raise IsolationError("refusing to run: real MetaTrader5 would be used")
        buf = io.StringIO()
        saved_argv = sys.argv
        code = 0
        try:
            sys.argv = [f"{self.module_name}.py"] + list(argv)
            with contextlib.redirect_stdout(buf):
                self.mod.main()
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        finally:
            sys.argv = saved_argv
        return code, buf.getvalue()
