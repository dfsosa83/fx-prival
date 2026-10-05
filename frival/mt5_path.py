"""Resolve the MT5 terminal path for the machine this code is running on.

The terminal install path is NOT the same across the machines this repo runs
on. It differs in a way that is easy to miss:

    desktop : C:\\Program Files\\FPMarkets MT5 Terminal\\terminal64.exe
    laptop  : C:\\Program Files\\FP Markets MT5 Terminal\\terminal64.exe
                                              ^ a space, different folder

Hardcoding either one breaks the other machine. Resolution order:

  1. MT5_PATH in the process environment.
  2. MT5_PATH= in frival/config/.env  (gitignored, so it is per machine).
  3. The first known default install path that actually exists on disk.
  4. The last default, returned unchanged, so a missing terminal fails loudly
     at mt5.initialize() rather than silently attaching to the wrong build.

config/.env is per machine by design: the credentials and the terminal path
never travel between laptops through git.
"""
from __future__ import annotations

import os
from pathlib import Path

# Known-good Windows install locations, checked in order. Both are real:
# FP Markets ships the terminal under "FP Markets MT5 Terminal" on current
# installs and under "FPMarkets MT5 Terminal" on older ones.
DEFAULT_PATHS = (
    r"C:\Program Files\FP Markets MT5 Terminal\terminal64.exe",
    r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe",
)


def _read_mt5_path(here: Path) -> str:
    """Return MT5_PATH from frival/config/.env, or '' if not configured."""
    env_file = here / "config" / ".env"
    if not env_file.exists():
        return ""
    try:
        text = env_file.read_text(encoding="utf-8")
    except OSError:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "MT5_PATH":
            return value.strip().strip('"').strip("'")
    return ""


def resolve_terminal_path(here: Path) -> str:
    """Pick the terminal path for this machine. Never raises."""
    env = (os.environ.get("MT5_PATH") or "").strip()
    if env:
        return env

    configured = _read_mt5_path(here)
    if configured:
        return configured

    for candidate in DEFAULT_PATHS:
        try:
            if Path(candidate).exists():
                return candidate
        except OSError:
            continue

    return DEFAULT_PATHS[-1]


def describe(here: Path) -> str:
    """Human-readable one-liner showing how the path was chosen."""
    env = (os.environ.get("MT5_PATH") or "").strip()
    if env:
        return f"{env}  (from environment MT5_PATH)"
    configured = _read_mt5_path(here)
    if configured:
        return f"{configured}  (from config/.env MT5_PATH)"
    for candidate in DEFAULT_PATHS:
        if Path(candidate).exists():
            return f"{candidate}  (auto-detected install)"
    return f"{DEFAULT_PATHS[-1]}  (fallback — no install detected)"
