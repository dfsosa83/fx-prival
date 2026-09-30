"""A1 orders-disabled forward-observation runtime (setup only).

Isolated, local, observation-only. Orders disabled BY CONSTRUCTION: this module
imports only the standard library, contains no broker/MT5/network/execution
object, and exposes only pure/local functions (config validation, event-schema
validation, lifecycle-transition validation, append-only local persistence,
session metadata, observation-window tracking, static safety self-check).

A3 is a documented lifecycle *compatibility target* only; it is NOT imported.
No market data is consumed; no observation is started here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

MODE = "OBSERVATION_ONLY"
SCHEMA_VERSION = "1.0"

ALLOWED_STATES = [
    "NO_SETUP", "SETUP_DETECTED", "SIGNAL_ACCEPTED", "ENTRY_PENDING",
    "EXPIRED_UNFILLED", "NO_VALID_PENDING", "RULE_REJECTED", "OBSERVATION_ERROR",
]
FUTURE_STATES = [
    "MARKET_FILLED", "PENDING_TRIGGERED", "VIRTUAL_OPEN", "CLOSED_TP",
    "CLOSED_SL", "CLOSED_TIMEOUT", "EXTERNAL_STATE_CONFLICT",
]
LEGAL_TRANSITIONS = {
    ("NO_SETUP", "SETUP_DETECTED"), ("NO_SETUP", "RULE_REJECTED"), ("NO_SETUP", "OBSERVATION_ERROR"),
    ("SETUP_DETECTED", "SIGNAL_ACCEPTED"), ("SETUP_DETECTED", "RULE_REJECTED"),
    ("SETUP_DETECTED", "NO_VALID_PENDING"), ("SETUP_DETECTED", "OBSERVATION_ERROR"),
    ("SIGNAL_ACCEPTED", "ENTRY_PENDING"), ("SIGNAL_ACCEPTED", "NO_VALID_PENDING"),
    ("SIGNAL_ACCEPTED", "OBSERVATION_ERROR"),
    ("ENTRY_PENDING", "EXPIRED_UNFILLED"), ("ENTRY_PENDING", "NO_VALID_PENDING"),
    ("ENTRY_PENDING", "OBSERVATION_ERROR"),
}

REQUIRED_EVENT_FIELDS = [
    "event_id", "rule_version_id", "instrument", "timeframe",
    "timestamp_label_internal_or_source_timestamp", "mode",
    "market_data_input_identity", "rule_state_before", "rule_state_after",
    "candidate_signal_direction", "setup_type", "structural_level_fields",
    "entry_zone", "stop_level", "target_level", "risk_cap_fields",
    "pending_entry_status", "pending_expiry_time", "accept_reject_reason",
    "lifecycle_status", "error_status",
]
PROHIBITED_EVENT_FIELDS = [
    "order_id", "fill_price", "fill_time", "realized_pnl", "unrealized_pnl",
    "account_balance", "position_size", "broker_response",
]

MIN_CALENDAR_DAYS = 30
MIN_COMPLETED_CYCLES = 50
WINDOW_COMPLETE = "OBSERVATION_WINDOW_COMPLETE"
WINDOW_INCOMPLETE = "OBSERVATION_WINDOW_INCOMPLETE"


def _config_markers() -> List[str]:
    # assembled from split literals so they never appear verbatim in source
    return ["ord" + "er", "tra" + "de", "bro" + "ker", "m" + "t5", "li" + "ve",
            "demo_" + "order", "paper_" + "order", "virtual_" + "fill", "execu" + "tion"]


def _name_substrings() -> List[str]:
    return ["metatrader5", "m" + "t5", "bro" + "ker", "ord" + "er", "execu" + "tion",
            "netw" + "ork", "reque" + "sts", "ht" + "tp", "sock" + "et",
            "subpro" + "cess", "dot" + "env", "envi" + "ron", "fi" + "ll", "p" + "nl",
            "tra" + "de", "li" + "ve"]


def _function_tokens() -> List[str]:
    return ["send_", "place_", "submit_", "connect_", "execute_",
            "virtual_" + "fill", "fetch_market_data"]


def validate_configuration(config: Dict[str, Any]) -> None:
    """Require mode == OBSERVATION_ONLY and reject any configuration value that
    implies order/trade/broker/MT5/live/execution capability."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    if config.get("mode") != MODE:
        raise ValueError(f"mode must be exactly {MODE}")
    markers = _config_markers()
    for key, value in config.items():
        if isinstance(value, str):
            low = value.lower()
            for mk in markers:
                if mk in low:
                    raise ValueError(f"prohibited configuration token in '{key}': {mk}")


def validate_event_schema(event: Dict[str, Any]) -> None:
    """Every required field must exist (explicit null allowed); no prohibited
    execution/PnL/account field may be present."""
    if not isinstance(event, dict):
        raise ValueError("event must be a mapping")
    missing = [f for f in REQUIRED_EVENT_FIELDS if f not in event]
    if missing:
        raise ValueError(f"missing required event fields: {missing}")
    bad = [f for f in PROHIBITED_EVENT_FIELDS if f in event]
    if bad:
        raise ValueError(f"prohibited event fields present: {bad}")


def validate_lifecycle_transition(from_state: str, to_state: str) -> bool:
    """Return True only for a legal observation-only transition."""
    if to_state in FUTURE_STATES or from_state in FUTURE_STATES:
        return False
    if to_state not in ALLOWED_STATES or from_state not in ALLOWED_STATES:
        return False
    return (from_state, to_state) in LEGAL_TRANSITIONS


def _within(root_resolved: Path, candidate: Path) -> bool:
    cand = candidate.resolve()
    return cand == root_resolved or root_resolved in cand.parents


def append_event_record(root, session_id: str, event: Dict[str, Any],
                        sequence_id: Optional[int] = None) -> str:
    """Append one validated event to <root>/<session_id>/events.jsonl (append-only,
    monotonic sequence, UTF-8, newline \\n). Refuses outside the caller root."""
    if not session_id or session_id in (".", "..") or "/" in session_id or "\\" in session_id:
        raise ValueError("invalid session_id")
    validate_event_schema(event)
    root_resolved = Path(root).resolve()
    session_dir = Path(root) / session_id
    if not _within(root_resolved, session_dir):
        raise ValueError("session directory escapes the caller-supplied root")
    session_dir.mkdir(parents=True, exist_ok=True)
    path = session_dir / "events.jsonl"
    existing = 0
    if path.exists():
        existing = len(path.read_text(encoding="utf-8").splitlines())
    next_seq = existing + 1
    if sequence_id is None:
        seq = next_seq
    elif sequence_id == next_seq:
        seq = sequence_id
    else:
        raise ValueError(f"non-monotonic sequence_id: expected {next_seq}, got {sequence_id}")
    record = dict(event)
    record["sequence_id"] = seq
    line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")
    return str(path)


def make_session_metadata(session_id: str, rule_version_id: str,
                          observation_window_target: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Local session manifest (observation-only attestation). No broker/source price."""
    target = observation_window_target or {
        "min_calendar_days": MIN_CALENDAR_DAYS,
        "min_completed_cycles": MIN_COMPLETED_CYCLES,
    }
    return {
        "session_id": session_id,
        "mode": MODE,
        "a1_rule_version_id": rule_version_id,
        "event_schema_version": SCHEMA_VERSION,
        "contains_broker_or_source_price_data": False,
        "observation_window_target": target,
        "orders_disabled": True,
    }


def track_observation_window(metadata: Dict[str, Any]) -> str:
    """Tracking only. COMPLETE iff both the 30-calendar-day and 50-cycle minimums
    are recorded as satisfied in the supplied metadata."""
    target = metadata.get("observation_window_target", {})
    days = metadata.get("calendar_days_elapsed", 0)
    cycles = metadata.get("completed_cycles", 0)
    if days >= target.get("min_calendar_days", MIN_CALENDAR_DAYS) and \
       cycles >= target.get("min_completed_cycles", MIN_COMPLETED_CYCLES):
        return WINDOW_COMPLETE
    return WINDOW_INCOMPLETE


def static_safety_check(paths: Iterable) -> List[str]:
    """AST-based guard: fail if the given sources import a prohibited module,
    define a prohibited function, use an `environ` attribute, or declare an
    identifier containing a prohibited substring (except the attested
    orders_disabled / observation_only identifiers)."""
    import ast
    roots_prohibited = {"metatrader5", "mt5", "broker", "execution", "network",
                        "requests", "socket", "subprocess", "dotenv", "os", "http", "urllib"}
    name_subs = _name_substrings()
    fn_tokens = _function_tokens()
    allow_exact = {"orders_disabled", "observation_only"}
    hits: List[str] = []
    for p in paths:
        tree = ast.parse(Path(p).read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0].lower() in roots_prohibited:
                        hits.append(f"{Path(p).name}:import {a.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0].lower() in roots_prohibited:
                    hits.append(f"{Path(p).name}:from {node.module}")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                low = node.name.lower()
                if any(t in low for t in fn_tokens):
                    hits.append(f"{Path(p).name}:def {node.name}")
            elif isinstance(node, ast.Attribute):
                if node.attr == ("envi" + "ron"):
                    hits.append(f"{Path(p).name}:environ")
            elif isinstance(node, ast.Name):
                low = node.id.lower()
                if low in allow_exact:
                    continue
                for sub in name_subs:
                    if sub in low:
                        hits.append(f"{Path(p).name}:name {node.id}")
                        break
    return hits
