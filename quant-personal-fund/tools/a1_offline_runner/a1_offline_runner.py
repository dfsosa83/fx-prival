"""A1 Gold Rules Engine — isolated OFFLINE fixture runner.

Fixture-only, caller-path-driven adapter that binds the existing pure A1 modules
(`engine.py`, `bias.py`, `levels.py`) to already-existing local XAUUSD fixture CSVs
and emits normalized event records for the A1 reproducibility check.

Safety: this module NEVER imports or references MT5/MetaTrader5/broker/execution/
order/demo-ledger/network/subprocess/environment code. It cannot place orders, fetch
data, calculate PnL, or connect to MT5. It is a technical adapter, not a new rule.
No execution at import time; no default repository paths.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

MODE_OFFLINE_REPLAY = "OFFLINE_REPLAY"
REQUIRED_FIXTURE_COLUMNS = ["datetime", "open", "high", "low", "close", "volume"]

# Prohibited import roots (checked via AST import nodes only — never text-scanned,
# so docstrings/comments that merely mention a word do not trigger the guard).
_PROHIBITED_IMPORT_ROOTS = {
    "metatrader5", "mt5", "execution_bot", "order_manager", "mt5_connector",
    "demo_ledger", "requests", "socket", "subprocess", "dotenv", "http",
    "urllib", "os", "broker", "network",
}

_EVENT_FIELDS = [
    "event_id", "rule_version_id", "instrument", "timeframe",
    "timestamp_label_internal_or_source_timestamp", "mode",
    "market_data_input_identity", "rule_state_before", "rule_state_after",
    "candidate_signal_direction", "setup_type", "structural_level_fields",
    "entry_zone", "stop_level", "target_level", "risk_cap_fields",
    "pending_entry_status", "pending_expiry_time", "accept_reject_reason",
    "lifecycle_status", "error_status",
]
_PROHIBITED_EVENT_FIELDS = [
    "order_id", "fill_price", "fill_time", "realized_pnl", "unrealized_pnl",
    "account_balance", "position_size", "broker_response",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def forbidden_import_scan(paths: List[Path]) -> List[str]:
    """AST-based static guard: flag prohibited module imports (and os.environ /
    getenv use) in the runner source and the pure A1 modules it imports.
    Docstrings/comments are ignored because only AST import nodes are inspected."""
    import ast
    hits: List[str] = []
    for p in paths:
        tree = ast.parse(Path(p).read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name.split(".")[0].lower() in _PROHIBITED_IMPORT_ROOTS:
                        hits.append(f"{Path(p).name}:import {a.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0].lower() in _PROHIBITED_IMPORT_ROOTS:
                    hits.append(f"{Path(p).name}:from {node.module}")
            elif isinstance(node, ast.Attribute) and node.attr == "environ":
                hits.append(f"{Path(p).name}:os.environ")
            elif isinstance(node, ast.Name) and node.id in ("getenv", "putenv"):
                hits.append(f"{Path(p).name}:{node.id}")
    return hits


def validate_fixture_schema(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_FIXTURE_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"fixture missing columns: {missing}")
    if df[REQUIRED_FIXTURE_COLUMNS].isna().any().any():
        raise ValueError("fixture contains nulls")
    if df["datetime"].duplicated().any():
        raise ValueError("fixture has duplicate datetime labels")
    if not df["datetime"].is_monotonic_increasing:
        raise ValueError("fixture datetime labels not strictly ascending")


def load_fixture_bars(csv_path: Path) -> pd.DataFrame:
    """Read a local fixture CSV (read-only). Keeps the original label string in
    `label`; parses `datetime` to NAIVE pandas timestamps for engine use (no
    timezone inference). Does not write, copy, fetch or interpolate."""
    df = pd.read_csv(csv_path)
    validate_fixture_schema(df)
    df["label"] = df["datetime"].astype(str)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=False)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="raise")
    return df[REQUIRED_FIXTURE_COLUMNS + ["label"]].reset_index(drop=True)


def load_a1_modules(a1_module_dir: Path):
    """Insert the pure A1 module dir on sys.path and import bias/levels/engine."""
    d = str(Path(a1_module_dir).resolve())
    if d not in sys.path:
        sys.path.insert(0, d)
    bias_mod = importlib.import_module("bias")
    levels_mod = importlib.import_module("levels")
    engine_mod = importlib.import_module("engine")
    return bias_mod, levels_mod, engine_mod


def module_hashes(mods) -> Dict[str, str]:
    out = {}
    for m in mods:
        f = getattr(m, "__file__", None)
        if f:
            out[Path(f).name] = sha256_file(Path(f))
    return out


def build_a1_offline_inputs(m15: pd.DataFrame, m30: pd.DataFrame, h1: pd.DataFrame,
                            warmup_m15: int = 100):
    """Yield (cycle_index, label, snapshot_kwargs) with strictly past, completed
    M30/H1 bars (no look-ahead, no tz inference)."""
    inputs = []
    for i in range(warmup_m15, len(m15)):
        bt = m15.iloc[i]["datetime"]
        m30_hist = m30[m30["datetime"] + pd.Timedelta(minutes=30) <= bt]
        h1_hist = h1[h1["datetime"] + pd.Timedelta(minutes=60) <= bt]
        inputs.append({
            "cycle_index": i,
            "label": m15.iloc[i]["label"],
            "bar_time": bt,
            "m15_df": m15.iloc[:i + 1][REQUIRED_FIXTURE_COLUMNS].reset_index(drop=True),
            "m30_df": m30_hist[REQUIRED_FIXTURE_COLUMNS].reset_index(drop=True),
            "h1_df": h1_hist[REQUIRED_FIXTURE_COLUMNS].reset_index(drop=True),
            "price": float(m15.iloc[i]["close"]),
        })
    return inputs


def normalize_a1_event_record(run_id: str, cycle_index: int, label: str,
                              rule_version_id: str, input_identity: str,
                              state_before: str, state_after: str,
                              dec, risk_caps: Dict[str, Any],
                              error_status: Optional[str]) -> Dict[str, Any]:
    order = getattr(dec, "order", None) or {}
    is_entry = getattr(dec, "action", None) == "ENTRY"
    level_info = getattr(dec, "level_info", None) or {}
    rec = {
        "event_id": f"{run_id}:{cycle_index}",
        "rule_version_id": rule_version_id,
        "instrument": "XAUUSD",
        "timeframe": "M15",
        "timestamp_label_internal_or_source_timestamp": label,
        "mode": MODE_OFFLINE_REPLAY,
        "market_data_input_identity": input_identity,
        "rule_state_before": state_before,
        "rule_state_after": state_after,
        "candidate_signal_direction": (order.get("direction") or order.get("action")) if is_entry else None,
        "setup_type": level_info.get("setup_type") if isinstance(level_info, dict) else None,
        "structural_level_fields": level_info or None,
        "entry_zone": order.get("entry") if is_entry else None,
        "stop_level": order.get("sl") if is_entry else None,
        "target_level": order.get("tp") if is_entry else None,
        "risk_cap_fields": risk_caps,
        "pending_entry_status": None,
        "pending_expiry_time": None,
        "accept_reject_reason": getattr(dec, "reason", "") or "",
        "lifecycle_status": state_after,
        "error_status": error_status,
    }
    return rec


def _canonical(rec: Dict[str, Any]) -> str:
    return json.dumps(rec, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def write_event_records(records: List[Dict[str, Any]], out_path: Path) -> None:
    """Deterministic serialization: UTF-8, newline \\n, canonical JSON per line."""
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        for rec in records:
            f.write(_canonical(rec) + "\n")


def run_a1_offline(m15_path: Path, m30_path: Path, h1_path: Path, a1_module_dir: Path,
                   config: Optional[Dict[str, Any]] = None, warmup_m15: int = 100,
                   run_id: str = "offline_run") -> Dict[str, Any]:
    """Run the frozen A1 engine over fixtures offline. Returns metadata + records."""
    cfg = dict(config or {})
    m15 = load_fixture_bars(Path(m15_path))
    m30 = load_fixture_bars(Path(m30_path))
    h1 = load_fixture_bars(Path(h1_path))
    bias_mod, levels_mod, engine_mod = load_a1_modules(Path(a1_module_dir))
    mods = [engine_mod, bias_mod, levels_mod]
    mod_hashes = module_hashes(mods)
    rule_version_id = mod_hashes.get("engine.py", "")

    fixture_hashes = {
        "m15": sha256_file(Path(m15_path)),
        "m30": sha256_file(Path(m30_path)),
        "h1": sha256_file(Path(h1_path)),
    }
    input_identity = hashlib.sha256(
        ("|".join(f"{k}={v}" for k, v in sorted(fixture_hashes.items()))).encode()
    ).hexdigest().upper()[:16]

    eng = engine_mod.GoldRulesEngine(cfg)
    risk_caps = {
        "fixed_lot": eng.fixed_lot,
        "max_risk_usd": eng.max_risk_usd,
        "max_concurrent_positions": eng.max_positions,
        "daily_loss_cap_usd": eng.daily_loss_cap,
    }

    inputs = build_a1_offline_inputs(m15, m30, h1, warmup_m15=warmup_m15)
    state = engine_mod.EngineState()
    records = []
    errors = 0
    for item in inputs:
        snap = engine_mod.Snapshot(
            m15_df=item["m15_df"], m30_df=item["m30_df"], h1_df=item["h1_df"],
            utc_now=(item["bar_time"] + pd.Timedelta(minutes=15)).to_pydatetime(),
            bid=item["price"], ask=item["price"], open_positions=0, today_realized_pnl=0.0)
        err = None
        before = state.state
        try:
            new_state, dec = eng.evaluate(snap, state)
        except Exception as e:  # record explicit error; never crash the run
            new_state, dec = state, engine_mod.Decision()
            dec.action = "ERROR"; dec.reason = f"{type(e).__name__}: {e}"; dec.state = state.state
            err = dec.reason
            errors += 1
        rec = normalize_a1_event_record(run_id, item["cycle_index"], item["label"],
                                        rule_version_id, input_identity, before,
                                        getattr(new_state, "state", before), dec, risk_caps, err)
        records.append(rec)
        state = new_state

    return {
        "mode": MODE_OFFLINE_REPLAY,
        "module_hashes": mod_hashes,
        "fixture_hashes": fixture_hashes,
        "market_data_input_identity": input_identity,
        "cycle_count": len(records),
        "error_count": errors,
        "event_field_names": _EVENT_FIELDS,
        "records": records,
    }
