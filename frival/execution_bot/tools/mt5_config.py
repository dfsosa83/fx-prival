# -*- coding: utf-8 -*-
"""EXEC-D1 MT5 initialize-config builder — VALIDATED PATH-ONLY production
pattern (offline fix, 2026-09-28, authorized).

Corrected behavior (replaces the earlier login-as-int design):
  - mt5.initialize(...) is ALWAYS invoked with the production pattern used by
    the rest of the project: **`mt5.initialize(path=...)` only** — attaching to
    an already-running, already-logged-in terminal. login / password / server
    are NEVER passed to the SDK.
  - `build_initialize_args(env)` therefore validates and returns ONLY
    `{"path": <str>}`.
  - The credential validators (`validate_login`, `validate_password`,
    `validate_server`) remain available as OPTIONAL environment-structure
    verification utilities (used by tests and the operator); they must never
    feed the SDK call.

History: the earlier interpreter of the repeated
`(-2, 'Invalid "login" argument')` failure assumed the login had to be passed
as an int. Under the path-only pattern no credentials are passed at all, so
that hypothesis is superseded; the verified, working production behavior is a
path-only attach to a terminal already logged into the demo account.

Rules (unchanged where applicable):
  - path: explicitly configured terminal executable (MT5_PATH first, then
    MT5_TERMINAL_PATH); must exist on disk and be `terminal64.exe` /
    `terminal.exe`; returned normalized as `str`.
  - login (verification utility): non-blank, no surrounding quotes, ASCII
    digits only, positive → normalized to `int`.
  - password / server (verification utilities): non-blank.

No MT5 runtime function is ever called from this module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

ACCEPTED_TERMINAL_NAMES = ("terminal64.exe", "terminal.exe")


class ConfigError(ValueError):
    """Invalid MT5 initialize configuration (safe, value-free message)."""


# ── optional environment-structure verification utilities ─────────────────────

def validate_login(raw: str) -> int:
    """Normalize the numeric MT5 login to a positive int (verification only;
    never passed to the SDK)."""
    if raw is None or not isinstance(raw, str):
        raise ConfigError("login: missing or non-string value")
    value = raw.strip()
    if not value:
        raise ConfigError("login: blank value")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        raise ConfigError("login: surrounding quotes are not accepted")
    if not value.isdigit():
        raise ConfigError("login: must be ASCII digits only")
    as_int = int(value)
    if as_int <= 0:
        raise ConfigError("login: must be a positive integer")
    return as_int


def validate_password(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ConfigError("password: blank value")
    return value


def validate_server(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ConfigError("server: blank value")
    return value


# ── terminal path (the ONLY input to mt5.initialize under the production
#    pattern) ────────────────────────────────────────────────────────────────

def resolve_terminal_path(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ConfigError("terminal path: missing value")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()          # tolerate quoted Windows paths
    path = Path(value)
    if not path.is_file():
        raise ConfigError("terminal path: does not exist on disk")
    if path.name.lower() not in ACCEPTED_TERMINAL_NAMES:
        raise ConfigError("terminal path: unexpected executable name")
    return str(path)


def pick_terminal_path(env: Dict[str, Any]) -> str:
    """Explicit configuration only: MT5_PATH first, then MT5_TERMINAL_PATH.

    Raises ConfigError when neither provides a usable explicit path.
    """
    for key in ("MT5_PATH", "MT5_TERMINAL_PATH"):
        raw = env.get(key, "")
        if raw and raw.strip():
            return resolve_terminal_path(raw)
    raise ConfigError("terminal path: not explicitly configured on disk")


def build_initialize_args(env: Dict[str, Any]) -> Dict[str, Any]:
    """Return the arguments for the MT5 path-only production pattern:
    `{"path": str}` and nothing else.

    login/password/server in `env` are IGNORED for the SDK call. Callers must
    use this IMMEDIATELY before `mt5.initialize(**args)` and never pass raw
    .env credential values (or their int forms) to the SDK.
    """
    path = pick_terminal_path(env)
    return {"path": path}