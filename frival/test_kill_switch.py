#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""LEGACY LIVE HARNESS — DISABLED (P0-02 quarantine).

This module used to run the kill-switch checks against the LIVE MT5 account and
rewrite the production ledger (it created a decoy row, ran a real ``close-all``
and a real ``place``). It is quarantined. Running it now prints a notice and
exits non-zero; it performs:

* no MetaTrader5 import and no ``initialize``;
* no file writes (it never touches the ledger, state or the kill switch);
* no subprocess and no project-command execution.

There is no override flag that re-enables the legacy live behaviour. The
original is preserved, byte-identical and non-executable, at
``auditorias/2026-10-11_frival_test_kill_switch_original.txt``. The offline
equivalents live in ``frival/tests_offline/test_kill_switch_offline.py``.

Importing this module has no operational side effects (safe for test
discovery).
"""
from __future__ import annotations

import sys

_NOTICE = (
    "[DISABLED] The legacy live kill-switch harness is quarantined (P0-02).\n"
    "It used to place/close real orders and rewrite the production ledger.\n"
    "It now performs no broker access, no initialization and no writes.\n"
    "Offline equivalents:\n"
    "    python frival/tests_offline/test_kill_switch_offline.py\n"
)


def main() -> int:
    sys.stderr.write(_NOTICE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
