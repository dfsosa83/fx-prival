# -*- coding: utf-8 -*-
"""Authorized READ-ONLY MT5 SymbolInfo validation — SINGLE attempt (2026-09-28,
second authorization; credentials from execution_bot/config/credentials.env).

AUTHORIZED CALLS (1x each where applicable, nothing else):
  1. mt5.initialize(path)                    -- exactly ONCE, PATH-ONLY
                                                  (production pattern; NO
                                                  login/password/server passed)
  2. mt5.account_info()                      -- confirm demo + identity
  3. mt5.symbol_info(symbol)                 -- per authorized symbol
  4. mt5.last_error()                        -- ONLY on init failure
  5. mt5.shutdown()                          -- always, after the attempt

Allowed symbol fields to record (only these, where present):
  trade_stops_level, trade_freeze_level, filling_mode, expiration_mode,
  order_mode
Symbols: EURUSD, GBPUSD, USDCHF, USDCAD.

MANDATORY STOP CONDITIONS (enforced by this probe):
  - initialize fails            -> record sanitized error, shutdown, STOP
  - account/server/demo mismatch-> shutdown, STOP before symbol queries
  - anything beyond the allowed calls is never attempted; a need to do so
    would have required stopping and requesting new authorization.

STRICT PROHIBITIONS (never present here): order_send / order/position/deal /
history inspection or modification; settings mutation of any kind; EXEC-D1
wiring; credential printing/persistence (masked identifiers only in output);
file changes outside frival/execution_bot/.

DIAGNOSIS FIX (offline, 2026-09-28, AUTHORIZED): the probe now uses the
production pattern — `mt5.initialize(path=...)` ONLY. Configuration is
validated by tools/mt5_config.py before initialization and invalid configuration
fails with STOPPED_INVALID_CONFIG before any MT5 call. Credentials are never
passed to the SDK; the connected demo environment is confirmed AFTER a
successful path-only attach via the masked account/server comparison.

Output (sanitized):
  data/mt5_symbolinfo_probe.json           (structured)
  reports/mt5_symbolinfo_validation_attempt2.md   (report)
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

CREDENTIALS_PATH = Path(
    r"C:\Users\david\OneDrive\Documents\fx-prival\frival\execution_bot\config\credentials.env")
TERMINAL_EXE = None          # resolved at runtime from the explicit configured path
SYMBOLS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD"]
ALLOWED_FIELDS = ["trade_stops_level", "trade_freeze_level", "filling_mode",
                  "expiration_mode", "order_mode"]
OUT_PATH = Path(
    r"C:\Users\david\OneDrive\Documents\fx-prival\frival\execution_bot\data\mt5_symbolinfo_probe.json")


def mask(account: str) -> str:
    if not account:
        return "<unset>"
    return f"{account[:2]}...{account[-3:]}"


def parse_env() -> dict:
    env = {}
    with open(CREDENTIALS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    return env


_CALLS: dict = {}


def log_call(fn: str):
    _CALLS[fn] = _CALLS.get(fn, 0) + 1


def calls_snapshot():
    return [{"fn": fn, "times": times} for fn, times in sorted(_CALLS.items())]


def finalize(mt5, record: dict):
    try:
        mt5.shutdown()
        record["shutdown_called"] = True
    except Exception as exc:  # pragma: no cover
        record["shutdown_called"] = False
        record["last_error"] = f"shutdown raised: {type(exc).__name__}: {exc}"
    record["calls"] = calls_snapshot()
    record["ended_utc"] = datetime.now(timezone.utc).isoformat()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, sort_keys=True)
    return record["status"]


def main() -> str:
    import MetaTrader5 as mt5

    try:
        from mt5_config import ConfigError, build_initialize_args
    except ImportError:                      # invoked as a package module
        from tools.mt5_config import ConfigError, build_initialize_args

    env = parse_env()

    record = {
        "task": "authorized read-only MT5 SymbolInfo validation (attempt 2)",
        "credentials_source": CREDENTIALS_PATH.name,
        "authorized_server": env.get("MT5_SERVER", ""),
        "authorized_account_masked": mask(env.get("MT5_LOGIN", "")),
        "calls": [],            # each entry: {"fn": ..., "times": N}
        "account": None,
        "symbols": {},
        "last_error": None,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PENDING",
        "shutdown_called": None,
    }
    _CALLS.clear()

    # ── CONFIG VALIDATION FIRST: never call initialize with malformed args ──
    try:
        args = build_initialize_args(env)
    except ConfigError as exc:
        record["status"] = "STOPPED_INVALID_CONFIG"
        record["last_error"] = f"config validation failed: {exc}"
        return finalize(mt5, record)
    terminal = args["path"]          # PATH-ONLY production pattern
    login = env.get("MT5_LOGIN", "")     # used ONLY for masked display and the
    server = env.get("MT5_SERVER", "")   # post-attach account/server comparison

    try:

        # ── 1) EXACTLY ONE initialize — path-only, NO credentials ────────────
        log_call("initialize")
        try:
            init_ok = bool(mt5.initialize(path=terminal))
        except Exception as exc:
            record["last_error"] = f"initialize raised: {type(exc).__name__}: {exc}"
            init_ok = False
        if not init_ok:
            log_call("last_error")
            try:
                record["last_error"] = str(mt5.last_error())
            except Exception as exc:  # pragma: no cover
                record["last_error"] = f"last_error unavailable: {exc!r}"
            record["status"] = "STOPPED_INIT_FAILED"
            return finalize(mt5, record)

        # ── 2) CONFIRM AUTHORIZED DEMO ENVIRONMENT (minimum read) ────────────
        log_call("account_info")
        try:
            acc = mt5.account_info()
        except Exception as exc:
            record["last_error"] = f"account_info raised: {type(exc).__name__}: {exc}"
            record["status"] = "STOPPED_UNKNOWN"
            return finalize(mt5, record)
        if acc is None:
            record["last_error"] = "account_info returned None"
            record["status"] = "STOPPED_UNKNOWN"
            return finalize(mt5, record)

        rec_login = str(getattr(acc, "login", "") or "")
        rec_server = str(getattr(acc, "server", "") or "")
        rec_mode = getattr(acc, "trade_mode", None)
        record["account"] = {
            "login_match": bool(rec_login) and rec_login == login,
            "server_match": bool(rec_server) and rec_server == server,
            "trade_mode": rec_mode,          # 0 = demo terminal
            "is_demo": rec_mode == 0,
            "display": {
                "login_masked": mask(rec_login),
                "server": rec_server or "<none>",
            },
        }
        mismatch = (bool(rec_login) and rec_login != login) or \
                   (bool(rec_server) and rec_server != server) or rec_mode != 0
        if mismatch:
            record["status"] = "STOPPED_ENV_MISMATCH"
            record["last_error"] = ("connected terminal/account/server does not "
                                    "match the authorized demo environment")
            return finalize(mt5, record)
        record["status"] = "ENV_CONFIRMED"

        # ── 3) symbol_info per authorized symbol (only the 5 allowed fields) ─
        for symbol in SYMBOLS:
            log_call("symbol_info")
            try:
                si = mt5.symbol_info(symbol)
            except Exception as exc:
                record["symbols"][symbol] = {
                    "exists": False, "error": f"{type(exc).__name__}: {exc}"}
                continue
            if si is None:
                record["symbols"][symbol] = {"exists": False}
                continue
            fields = {}
            for fname in ALLOWED_FIELDS:
                try:
                    fields[fname] = getattr(si, fname, None)
                except Exception:
                    fields[fname] = "<unreadable>"
            record["symbols"][symbol] = {
                "exists": True,
                "fields": {k: v for k, v in fields.items()},
                "present": {k: (v is not None) for k, v in fields.items()},
            }
        record["status"] = "OK_VALIDATED"
    except Exception as exc:  # pragma: no cover -- unexpected
        record["last_error"] = f"{type(exc).__name__}: {exc}"
        record["status"] = "STOPPED_UNKNOWN"
    finally:
        log_call("shutdown")
        try:
            record["shutdown_called"] = bool(mt5.shutdown())
        except Exception as exc:  # pragma: no cover
            record["shutdown_called"] = False
            record["last_error"] = f"shutdown raised: {exc!r}"

    record["calls"] = calls_snapshot()
    record["ended_utc"] = datetime.now(timezone.utc).isoformat()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, sort_keys=True)
    return record["status"]


if __name__ == "__main__":
    status = main()
    print(f"PROBE_STATUS={status}")
    sys.exit(0 if status == "OK_VALIDATED" else 3)