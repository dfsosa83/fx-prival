"""A1 orders-disabled XAUUSD forward-observation session orchestrator.

One explicit bounded invocation = preflight + exactly one evaluation cycle, then
exit. No service, daemon, scheduler or watcher.

Orders disabled by construction: this module imports the validated read-only
feed component and the observation-only runtime; it contains no execution
adapter, no order path, no fill model and no PnL. It never builds or sends an
order request and never persists prices; it stores only append-only
observation-safe lifecycle records, heartbeats, a redacted session state and a
run log.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

SESSION_ID = "a1_xauusd_observ_20260930"
MODE = "OBSERVATION_ONLY"
INSTRUMENT = "XAUUSD"
TIMEFRAMES = ["H1", "M30", "M15"]
POLL_TIMEFRAME = "M15"

ALLOWED_LIFECYCLE = [
    "NO_SETUP", "SETUP_DETECTED", "SIGNAL_ACCEPTED", "ENTRY_PENDING",
    "EXPIRED_UNFILLED", "NO_VALID_PENDING", "RULE_REJECTED", "OBSERVATION_ERROR",
]
RESERVED_LIFECYCLE = [
    "MARKET_FILLED", "PENDING_TRIGGERED", "VIRTUAL_OPEN", "CLOSED_TP",
    "CLOSED_SL", "CLOSED_TIMEOUT", "EXTERNAL_STATE_CONFLICT",
]
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

EVENTS_FILE = "observation_events.jsonl"
HEARTBEATS_FILE = "observation_heartbeats.jsonl"
STATE_FILE = "session_state.json"
RUN_LOG_FILE = "RUN_LOG.md"
LOCK_FILE = "session.lock"


class PreflightError(Exception):
    pass


# ── assembled token sets (never appear verbatim in source) ───────────────────

def _prohibited_import_roots() -> List[str]:
    return ["meta" + "trader5", "mt5_" + "connector", "demo_" + "ledger",
            "order_" + "manager", "bro" + "ker", "reque" + "sts", "ht" + "tp",
            "sock" + "et", "subpro" + "cess", "dot" + "env", "execu" + "tion_bot",
            "netw" + "ork", "url" + "lib"]


def _prohibited_call_names() -> List[str]:
    return ["order_" + "send", "order_" + "check", "order_calc_" + "margin",
            "order_calc_" + "profit", "send_" + "order", "place_" + "order",
            "submit_" + "order", "execute_" + "trade", "virtual_" + "fill",
            "history_orders_" + "get", "history_deals_" + "get"]


def _prohibited_name_substrings() -> List[str]:
    return ["bro" + "ker", "order_" + "manager", "demo_" + "ledger",
            "mt5_" + "connector", "virtual_" + "fill", "execute_" + "trade"]


def _call_name(func) -> Optional[str]:
    import ast
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def static_scan(paths: List[Path], feed_path: Path) -> List[str]:
    """AST-based scan (imports + calls + attributes + identifiers). Docstrings and
    comments are ignored, matching the established house guard style. The
    read-only feed component is the only file permitted to import the terminal
    package directly."""
    import ast
    roots = {r.lower() for r in _prohibited_import_roots()}
    calls = {c.lower() for c in _prohibited_call_names()}
    subs = _prohibited_name_substrings()
    terminal = ("meta" + "trader5")
    feed_resolved = Path(feed_path).resolve()
    hits: List[str] = []
    for p in paths:
        pr = Path(p).resolve()
        tree = ast.parse(Path(p).read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    root = a.name.split(".")[0].lower()
                    if root in roots:
                        if root == terminal and pr == feed_resolved:
                            continue
                        hits.append(f"{Path(p).name}:import {a.name}")
            elif isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0].lower()
                if root in roots:
                    if root == terminal and pr == feed_resolved:
                        continue
                    hits.append(f"{Path(p).name}:from {node.module}")
            elif isinstance(node, ast.Call):
                name = _call_name(node.func)
                if name and name.split(".")[-1].lower() in calls:
                    hits.append(f"{Path(p).name}:call {name}")
            elif isinstance(node, ast.Attribute):
                if node.attr == ("en" + "viron"):
                    hits.append(f"{Path(p).name}:environ")
            elif isinstance(node, ast.Name):
                low = node.id.lower()
                for s in subs:
                    if s in low:
                        hits.append(f"{Path(p).name}:name {node.id}")
                        break
    return hits


# ── small utilities ──────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json_atomic(path: Path, obj: Dict[str, Any]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str),
                   encoding="utf-8", newline="")
    tmp.replace(path)


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def append_jsonl(path: Path, record: Dict[str, Any]) -> int:
    seq = _count_lines(path) + 1
    rec = dict(record)
    rec["sequence_id"] = seq
    line = json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")
    return seq


def append_run_log(path: Path, text: str) -> None:
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(text)


def acquire_lock(session_dir: Path) -> Path:
    lock = session_dir / LOCK_FILE
    try:
        with open(lock, "x", encoding="utf-8", newline="") as f:
            f.write(SESSION_ID + "\n")
    except FileExistsError:
        raise RuntimeError("concurrent session lock present")
    return lock


def release_lock(lock: Optional[Path]) -> None:
    if lock is not None:
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


# ── data acquisition (read-only feed only) ───────────────────────────────────

def build_frames(feed, gateway, counts: Dict[str, int]) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    for tf in TIMEFRAMES:
        rows = feed.read_symbol_bars(gateway, tf, counts[tf])
        if len(rows) < 2:
            raise PreflightError(f"INSUFFICIENT_BARS_{tf}")
        df = pd.DataFrame(rows)
        df["datetime"] = pd.to_datetime(df["time"], unit="s")
        df["volume"] = 0.0
        df = df[["datetime", "open", "high", "low", "close", "volume"]]
        frames[tf] = df.iloc[:-1].reset_index(drop=True)  # drop the forming bar
    if len(frames["M15"]) < 100:
        raise PreflightError("INSUFFICIENT_M15_HISTORY")
    if len(frames["H1"]) < 60:
        raise PreflightError("INSUFFICIENT_H1_HISTORY")
    if len(frames["M30"]) < 30:
        raise PreflightError("INSUFFICIENT_M30_HISTORY")
    return frames


def bars_identity(frames: Dict[str, pd.DataFrame]) -> str:
    parts: List[str] = []
    for tf in TIMEFRAMES:
        df = frames[tf]
        parts.append(tf + ":" + ",".join(df["datetime"].astype(str))
                     + "|" + ",".join(df["close"].astype(str)))
    return hashlib.sha256("||".join(parts).encode("utf-8")).hexdigest().upper()[:16]


# ── lifecycle mapping (observation-only) ─────────────────────────────────────

def to_lifecycle(action: str, engine_state: str) -> str:
    if action == "ERROR":
        return "OBSERVATION_ERROR"
    if action == "ENTRY" or engine_state == "IN_TRADE":
        return "ENTRY_PENDING"
    if engine_state == "ENTRY_READY":
        return "SIGNAL_ACCEPTED"
    if engine_state in ("WAIT_CANDLE_CLOSE", "CONFIRMED"):
        return "SETUP_DETECTED"
    if engine_state == "WATCH_ZONE":
        return "NO_VALID_PENDING" if action == "DROP" else "NO_SETUP"
    if engine_state in ("DONE", "INVALIDATED"):
        return "NO_VALID_PENDING"
    return "OBSERVATION_ERROR"


def sanitize_state_for_observation(state_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Orders disabled: the rule's would-be entry is recorded as a pending
    observation, but the engine is never advanced into a simulated trade, so no
    execution management (fill/BE/trail/close) can ever be modelled."""
    if state_dict.get("state") == "IN_TRADE":
        state_dict["state"] = "WATCH_ZONE"
        state_dict["active_trade"] = None
        state_dict["direction"] = None
        state_dict["watched_level"] = None
        state_dict["broken_level"] = None
        state_dict["confirm_candle"] = None
    return state_dict


def build_event_record(*, cycle_number: int, label: str, rule_version_id: str,
                       input_identity: str, before: str, after: str,
                       lifecycle: str, dec, engine, risk_caps: Dict[str, Any],
                       direction: Optional[str], error_status: Optional[str],
                       pending_expiry: Optional[str]) -> Dict[str, Any]:
    order = getattr(dec, "order", None) or {}
    is_entry = lifecycle == "ENTRY_PENDING"
    level_info = getattr(dec, "level_info", None) or {}
    rb, ra = before, after
    if is_entry:
        rb, ra = "ENTRY_READY", "ENTRY_PENDING"
    return {
        "event_id": f"{SESSION_ID}:{cycle_number}",
        "rule_version_id": rule_version_id,
        "instrument": INSTRUMENT,
        "timeframe": POLL_TIMEFRAME,
        "timestamp_label_internal_or_source_timestamp": label,
        "mode": MODE,
        "market_data_input_identity": input_identity,
        "rule_state_before": rb,
        "rule_state_after": ra,
        "candidate_signal_direction": direction,
        "setup_type": (level_info.get("side") if isinstance(level_info, dict) else None),
        "structural_level_fields": level_info or None,
        "entry_zone": float(order["entry"]) if is_entry and order.get("entry") is not None else None,
        "stop_level": float(order["stop_loss"]) if is_entry and order.get("stop_loss") is not None else None,
        "target_level": float(order["take_profit"]) if is_entry and order.get("take_profit") is not None else None,
        "risk_cap_fields": risk_caps,
        "pending_entry_status": "PENDING_OBSERVED" if is_entry else None,
        "pending_expiry_time": pending_expiry if is_entry else None,
        "accept_reject_reason": getattr(dec, "reason", "") or "",
        "lifecycle_status": lifecycle,
        "error_status": error_status,
    }


def build_expired_record(*, cycle_number: int, label: str, rule_version_id: str,
                         input_identity: str, pending: Dict[str, Any],
                         rule_caps: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": f"{SESSION_ID}:{cycle_number}:pending-expired",
        "rule_version_id": rule_version_id,
        "instrument": INSTRUMENT,
        "timeframe": POLL_TIMEFRAME,
        "timestamp_label_internal_or_source_timestamp": label,
        "mode": MODE,
        "market_data_input_identity": input_identity,
        "rule_state_before": "ENTRY_PENDING",
        "rule_state_after": "EXPIRED_UNFILLED",
        "candidate_signal_direction": pending.get("direction"),
        "setup_type": None,
        "structural_level_fields": None,
        "entry_zone": pending.get("entry_zone"),
        "stop_level": pending.get("stop_level"),
        "target_level": pending.get("target_level"),
        "risk_cap_fields": rule_caps,
        "pending_entry_status": "EXPIRED_UNFILLED",
        "pending_expiry_time": pending.get("expiry_label"),
        "accept_reject_reason": "observation-only pending entry expired without a fill (no order was placed)",
        "lifecycle_status": "EXPIRED_UNFILLED",
        "error_status": None,
    }


# ── the single bounded cycle ─────────────────────────────────────────────────

def run_once(session_dir: Path, repo_root: Path, trigger: str,
             terminal_path: Optional[str], config_path: Path) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "session_id": SESSION_ID, "stage": "A1_MT5_OBSERVATION_ONLY_FORWARD_START",
        "status": None, "preflight": {}, "cycle": {}, "blocker": None,
        "paths": {
            "feed": "quant-personal-fund/experiments/QPF-RV-2027-11-A1-MT5-DEMO-OBSERVATION-ENVIRONMENT/a1_mt5_demo_observation_environment.py",
            "runtime": "quant-personal-fund/experiments/QPF-RV-2027-10-A1-ORDERS-DISABLED-FORWARD-OBSERVATION-SETUP/A1_OBSERVATION_ONLY_RUNTIME.py",
            "runner": "quant-personal-fund/tools/a1_offline_runner/a1_offline_runner.py",
            "a1_dir": "frival/gold_rules",
        },
    }
    lock = acquire_lock(session_dir)
    gateway = None
    try:
        feed_path = repo_root / result["paths"]["feed"]
        runtime_path = repo_root / result["paths"]["runtime"]
        runner_path = repo_root / result["paths"]["runner"]
        a1_dir = repo_root / result["paths"]["a1_dir"]
        engine_file = a1_dir / "engine.py"
        bias_file = a1_dir / "bias.py"
        levels_file = a1_dir / "levels.py"

        feed = load_module_from_path("a1_feed", feed_path)
        runtime = load_module_from_path("a1_runtime", runtime_path)
        runner = load_module_from_path("a1_runner", runner_path)

        # 5/6: static scan over orchestrator + all direct imports
        scan_paths = [Path(__file__).resolve(), feed_path, runtime_path, runner_path,
                      engine_file, bias_file, levels_file]
        hits = static_scan(scan_paths, feed_path)
        if hits:
            raise PreflightError("STATIC_SCAN_FAILED:" + ";".join(hits))
        result["preflight"]["static_scan"] = "CLEAN"
        result["preflight"]["no_execution_component_imported"] = True

        # 3/4: config mode + orders-disabled attestation
        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        runtime.validate_configuration(cfg)
        result["preflight"]["mode"] = cfg["mode"]
        result["preflight"]["orders_disabled_attestation"] = True

        # 1/2: source hashes
        hashes = {
            "engine.py": sha256_file(engine_file),
            "bias.py": sha256_file(bias_file),
            "levels.py": sha256_file(levels_file),
            "a1_offline_runner.py": sha256_file(runner_path),
            "A1_OBSERVATION_ONLY_RUNTIME.py": sha256_file(runtime_path),
            "a1_mt5_demo_observation_environment.py": sha256_file(feed_path),
        }
        result["preflight"]["source_hashes"] = hashes

        # 7-9: initialize demo, verify identity, verify symbol
        gateway = feed.RealMt5Gateway(terminal_path=terminal_path)
        if not gateway.initialize():
            raise PreflightError("MT5_INIT_FAILED")
        if not feed.verify_demo_account(gateway.account_info()):
            raise PreflightError("ACCOUNT_NOT_VERIFIED_DEMO")
        if not feed.xauusd_available(gateway):
            raise PreflightError("XAUUSD_UNAVAILABLE")
        result["preflight"]["demo_verified"] = True
        result["preflight"]["xauusd_available"] = True

        # 10: count-only collision check
        counts = feed.reconcile_counts(gateway.positions_get(), gateway.orders_get())
        external = (counts["positions_count"] + counts["orders_count"]) > 0
        result["preflight"]["positions_count"] = counts["positions_count"]
        result["preflight"]["orders_count"] = counts["orders_count"]
        result["preflight"]["external_demo_activity"] = external

        # 11: bars + tick
        bars = cfg["bar_fetch_counts"]
        frames = build_frames(feed, gateway, bars)
        tick = gateway.symbol_info_tick(INSTRUMENT)
        if tick is None:
            raise PreflightError("TICK_UNAVAILABLE")
        bid = float(getattr(tick, "bid"))
        ask = float(getattr(tick, "ask"))
        tick_time = int(getattr(tick, "time", 0))
        result["preflight"]["feed_status"] = "XAUUSD_H1_M30_M15_TICK_OK"
        result["preflight"]["data_timestamps"] = {
            tf: str(frames[tf]["datetime"].iloc[-1]) for tf in TIMEFRAMES
        }
        result["preflight"]["tick_epoch"] = tick_time

        m15, m30, h1 = frames["M15"], frames["M30"], frames["H1"]
        utc_now = m15.iloc[-1]["datetime"] + pd.Timedelta(minutes=15)
        m30_hist = m30[m30["datetime"] + pd.Timedelta(minutes=30) <= utc_now].reset_index(drop=True)
        h1_hist = h1[h1["datetime"] + pd.Timedelta(minutes=60) <= utc_now].reset_index(drop=True)
        input_identity = bars_identity(frames)
        label = "NOT_UTC:" + str(m15.iloc[-1]["datetime"])

        # 12: run frozen A1 through the approved offline-safe interface
        bias_mod, levels_mod, engine_mod = runner.load_a1_modules(a1_dir)
        eng = engine_mod.GoldRulesEngine({})
        risk_caps = {
            "fixed_lot": eng.fixed_lot,
            "max_risk_usd": eng.max_risk_usd,
            "max_concurrent_positions": eng.max_positions,
            "daily_loss_cap_usd": eng.daily_loss_cap,
        }
        rule_version_id = hashes["engine.py"]

        state = read_json(session_dir / STATE_FILE) or {}
        cycle_number = int(state.get("cycle_count", 0)) + 1
        emitted = 0

        snap = engine_mod.Snapshot(
            m15_df=m15, m30_df=m30_hist, h1_df=h1_hist,
            utc_now=utc_now.to_pydatetime(), bid=bid, ask=ask,
            open_positions=0, today_realized_pnl=0.0)

        # resolve any prior pending observation (expiry, never a fill)
        pending_prev = state.get("pending_observed")
        if pending_prev and int(pending_prev.get("cycle_number", 0)) < cycle_number:
            exp = build_expired_record(cycle_number=cycle_number, label=label,
                                       rule_version_id=rule_version_id,
                                       input_identity=input_identity,
                                       pending=pending_prev, rule_caps=risk_caps)
            runtime.validate_event_schema(exp)
            append_jsonl(session_dir / EVENTS_FILE, exp)
            emitted += 1
            state["pending_observed"] = None

        before = engine_mod.EngineState.from_dict(state.get("engine_state")).state
        st = engine_mod.EngineState.from_dict(state.get("engine_state"))
        err = None
        try:
            new_state, dec = eng.evaluate(snap, st)
        except Exception as e:  # never crash: record an explicit observation error
            new_state, dec = st, engine_mod.Decision()
            dec.action = "ERROR"; dec.reason = f"{type(e).__name__}: {e}"; dec.state = st.state
            err = dec.reason
        after = getattr(new_state, "state", before)
        new_dict = sanitize_state_for_observation(new_state.to_dict())

        lifecycle = to_lifecycle(dec.action, after)
        if lifecycle not in ALLOWED_LIFECYCLE or lifecycle in RESERVED_LIFECYCLE:
            lifecycle = "OBSERVATION_ERROR"
        direction = None
        order = getattr(dec, "order", None) or {}
        if lifecycle == "ENTRY_PENDING":
            direction = order.get("action") or getattr(new_state, "direction", None)
        else:
            direction = getattr(new_state, "direction", None)
        expiry_label = None
        if lifecycle == "ENTRY_PENDING":
            expiry_label = "NOT_UTC:" + str(m15.iloc[-1]["datetime"] + pd.Timedelta(
                minutes=15 * int(cfg.get("pending_entry_expiry_bars", 3))))

        event = build_event_record(cycle_number=cycle_number, label=label,
                                   rule_version_id=rule_version_id,
                                   input_identity=input_identity, before=before,
                                   after=after, lifecycle=lifecycle, dec=dec,
                                   engine=eng, risk_caps=risk_caps, direction=direction,
                                   error_status=err, pending_expiry=expiry_label)
        runtime.validate_event_schema(event)
        seq = append_jsonl(session_dir / EVENTS_FILE, event)
        emitted += 1

        # heartbeat (one per cycle)
        heartbeat = {
            "session_id": SESSION_ID,
            "cycle_number": cycle_number,
            "mode": MODE,
            "demo_verification_status": "DEMO_VERIFIED",
            "feed_status": "XAUUSD_H1_M30_M15_TICK_OK",
            "data_timestamps": {tf: str(frames[tf]["datetime"].iloc[-1]) for tf in TIMEFRAMES},
            "tick_epoch": tick_time,
            "records_emitted": emitted,
            "orders_disabled": True,
            "external_demo_activity": external,
            "status": "OK" if lifecycle != "OBSERVATION_ERROR" else "CYCLE_ERROR",
            "error_status": err,
            "checked_at_utc": now_iso(),
        }
        append_jsonl(session_dir / HEARTBEATS_FILE, heartbeat)

        # 12/13: persist session state (atomic) then shut down (finally)
        first_cycle = state.get("first_cycle_utc") or now_iso()
        elapsed_days = (datetime.now(timezone.utc) - datetime.fromisoformat(first_cycle)).days
        state.update({
            "session_id": SESSION_ID,
            "mode": MODE,
            "instrument": INSTRUMENT,
            "contains_broker_or_source_price_data": False,
            "orders_disabled": True,
            "source_hashes": hashes,
            "config_path": str(config_path),
            "terminal_path_recorded": False,
            "demo_verified": True,
            "positions_count": counts["positions_count"],
            "orders_count": counts["orders_count"],
            "external_demo_activity": external,
            "engine_state": new_dict,
            "cycle_count": cycle_number,
            "event_count": _count_lines(session_dir / EVENTS_FILE),
            "heartbeat_count": _count_lines(session_dir / HEARTBEATS_FILE),
            "last_lifecycle_status": lifecycle,
            "last_data_timestamps": {tf: str(frames[tf]["datetime"].iloc[-1]) for tf in TIMEFRAMES},
            "last_heartbeat_utc": now_iso(),
            "first_cycle_utc": first_cycle,
            "trigger": trigger,
            "pending_observed": ({
                "cycle_number": cycle_number,
                "direction": direction,
                "entry_zone": event["entry_zone"],
                "stop_level": event["stop_level"],
                "target_level": event["target_level"],
                "expiry_label": expiry_label,
            } if lifecycle == "ENTRY_PENDING" else None),
            "paused": False,
        })
        state["observation_window"] = {
            "target": {"min_calendar_days": 30, "min_completed_cycles": 50},
            "calendar_days_elapsed": elapsed_days,
            "completed_cycles": cycle_number,
            "status": runtime.track_observation_window({
                "observation_window_target": {"min_calendar_days": 30, "min_completed_cycles": 50},
                "calendar_days_elapsed": elapsed_days,
                "completed_cycles": cycle_number,
            }),
        }
        write_json_atomic(session_dir / STATE_FILE, state)

        result["status"] = "STARTED"
        result["cycle"] = {
            "cycle_number": cycle_number,
            "lifecycle_status": lifecycle,
            "records_emitted": emitted,
            "event_sequence": seq,
            "engine_state_before": before,
            "engine_state_after": after,
            "rule_action": dec.action,
            "window_status": state["observation_window"]["status"],
        }
        append_run_log(session_dir / RUN_LOG_FILE,
                       f"\n## {now_iso()} — cycle {cycle_number} (START)\n"
                       f"- lifecycle_status: `{lifecycle}`; rule_action: `{dec.action}`\n"
                       f"- records_emitted: {emitted}; engine {before} -> {after}\n"
                       f"- demo_verified: true; feed: XAUUSD H1/M30/M15 + tick OK\n"
                       f"- collision counts: positions {counts['positions_count']}, "
                       f"orders {counts['orders_count']}; external_demo_activity {external}\n"
                       f"- orders_disabled: true; no order/fill/PnL/trading activity\n"
                       f"- window: {state['observation_window']['status']} "
                       f"({elapsed_days}d / {cycle_number} cycles)\n")
    except PreflightError as e:
        result["status"] = "PAUSE"
        result["blocker"] = str(e)
        state = read_json(session_dir / STATE_FILE) or {}
        state.update({
            "session_id": SESSION_ID, "mode": MODE, "instrument": INSTRUMENT,
            "orders_disabled": True, "contains_broker_or_source_price_data": False,
            "paused": True, "pause_reason": str(e), "paused_at_utc": now_iso(),
            "cycle_count": int(state.get("cycle_count", 0)),
        })
        write_json_atomic(session_dir / STATE_FILE, state)
        append_run_log(session_dir / RUN_LOG_FILE,
                       f"\n## {now_iso()} — PAUSE\n- blocker: `{e}`\n"
                       f"- no observation session active; no A1 event record written\n")
    except Exception as e:  # unexpected -> PAUSE, never a silent start
        result["status"] = "PAUSE"
        result["blocker"] = f"UNEXPECTED:{type(e).__name__}: {e}"
        append_run_log(session_dir / RUN_LOG_FILE,
                       f"\n## {now_iso()} — PAUSE\n- blocker: `{result['blocker']}`\n")
    finally:
        if gateway is not None:
            try:
                gateway.shutdown()
            except Exception:
                pass
        release_lock(lock)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=str(Path.cwd()))
    ap.add_argument("--trigger", default=now_iso())
    ap.add_argument("--terminal", default=None)
    ap.add_argument("--session-dir", default=None)
    args = ap.parse_args()
    repo_root = Path(args.repo_root).resolve()
    session_dir = Path(args.session_dir).resolve() if args.session_dir else (
        repo_root / "quant-personal-fund/experiments/"
        "QPF-RV-2027-12-A1-XAUUSD-ORDERS-DISABLED-FORWARD-OBSERVATION")
    config_path = session_dir / "A1_OBSERVATION_SESSION_CONFIG.yaml"
    res = run_once(session_dir, repo_root, args.trigger, args.terminal, config_path)
    print(json.dumps(res, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
