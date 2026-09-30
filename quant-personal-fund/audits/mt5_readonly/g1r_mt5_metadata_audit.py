#!/usr/bin/env python
# READ_ONLY_ONLY
"""G1-R read-only MT5 metadata & provenance audit adapter.

READ_ONLY_ONLY: this script performs READ-ONLY MT5 queries only. It never calls
any order/trade-action API. A source-level self-guard (below) assembles the
forbidden token names from split literals and refuses to run if any appear
verbatim in this file.

Standalone and script-only. It must NEVER be imported by the research library
(core/, data/pipelines/, signals/, portfolio/, risk/, backtest/, llm_tools/,
monitoring/). It writes artifacts ONLY under the experiment folder.

No secrets, account numbers, server identifiers, or terminal paths are ever
printed or persisted. Credentials (terminal path) are read locally only, never
emitted.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import sys
from pathlib import Path

# ── static no-trading self-guard (tokens assembled from split literals) ──────
_A, _B = "order_", "send"
_C, _D = "order_", "check"
_TA = "TRADE_ACTION_"
_FORBIDDEN = [_A + _B, _C + _D, _TA + "DEAL", _TA + "PENDING",
              _TA + "SLTP", _TA + "REMOVE"]
_SRC = Path(__file__).read_text(encoding="utf-8", errors="replace")
_GUARD_HITS = [t for t in _FORBIDDEN if t in _SRC]
if _GUARD_HITS:
    sys.stderr.write("READ_ONLY_SAFETY_FAILURE: forbidden token(s) present in source\n")
    sys.exit(3)

REPO = Path(__file__).resolve().parents[3]
EXP_DIR = (REPO / "quant-personal-fund" / "experiments"
           / "QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION")
CREDS = REPO / "frival" / "execution_bot" / "config" / "credentials.env"
LOCAL = REPO / "ml-signal-service" / "data" / "raw" / "mt5" / "H1"
CANONICAL = ("EURUSD", "GBPUSD")


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _load_terminal_path():
    """Read the terminal path locally only; never print it."""
    path = None
    try:
        for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            if key.strip() == "MT5_TERMINAL_PATH":
                path = val.strip().strip('"').strip("'")
    except Exception:
        path = None
    return path


def _discover_symbols(mt5):
    names = [s.name for s in mt5.symbols_get()]
    out = {}
    for canon in CANONICAL:
        exact = canon if canon in names else None
        if exact is None:
            cands = [n for n in names if canon in n]
            exact = cands[0] if cands else None
        out[canon] = {"symbol_as_received": exact,
                      "mapping_status": ("CONFIRMED_FOR_CURRENT_MT5_SAMPLE"
                                         if exact else "UNRESOLVED")}
    return out


def _symbol_meta(si):
    def g(name, default=None):
        return getattr(si, name, default) if si is not None else default
    return {
        "digits": g("digits"), "point": g("point"),
        "trade_tick_size": g("trade_tick_size"),
        "trade_contract_size": g("trade_contract_size"),
        "volume_min": g("volume_min"), "volume_max": g("volume_max"),
        "volume_step": g("volume_step"), "trade_mode": g("trade_mode"),
        "spread_current_points": g("spread"),
        "swap_long": g("swap_long"), "swap_short": g("swap_short"),
        "swap_rollover3days": g("swap_rollover3days"),
        "currency_base": g("currency_base"), "currency_profit": g("currency_profit"),
        "currency_margin": g("currency_margin"),
        "visible": g("visible"), "selectable": g("selectable"),
        "start_time": g("start_time"), "expiration_time": g("expiration_time"),
    }


def _bars_to_rows(rates, broker_sym, canon, stamp, limit):
    rows = []
    if rates is None:
        return rows
    for r in list(rates)[:limit]:
        rows.append({
            "broker_symbol": broker_sym, "canonical_symbol": canon,
            "retrieval_timestamp_utc": stamp,
            "time": int(r["time"]), "open": float(r["open"]),
            "high": float(r["high"]), "low": float(r["low"]),
            "close": float(r["close"]), "tick_volume": int(r["tick_volume"]),
            "spread": int(r["spread"]), "real_volume": int(r["real_volume"]),
            "bar_completed": "true",
        })
    return rows


def main() -> int:
    stamp = _utcnow().isoformat()
    summary = {"retrieval_timestamp_utc": stamp, "read_only": True, "errors": []}

    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        summary["errors"].append("MetaTrader5 import failed: " + type(exc).__name__)
        _emit(summary)
        return 1

    term_path = _load_terminal_path()
    ok = mt5.initialize(path=term_path) if term_path else mt5.initialize()
    if not ok:
        code = mt5.last_error()[0]
        summary["errors"].append(f"initialize failed code={code}")
        _emit(summary)
        return 1

    try:
        ti = mt5.terminal_info()
        summary["terminal"] = {
            "connected": bool(getattr(ti, "connected", False)),
            "build": int(getattr(ti, "build", 0)),
            "trade_allowed": bool(getattr(ti, "trade_allowed", False)),
        }
        ai = mt5.account_info()
        if ai is not None:
            summary["account"] = {
                "login": "REDACTED", "server": "REDACTED",
                "trade_mode": int(getattr(ai, "trade_mode", -1)),
                "currency": str(getattr(ai, "currency", "")),
                "leverage": int(getattr(ai, "leverage", 0)),
                "margin_mode": int(getattr(ai, "margin_mode", -1)),
            }

        mapping = _discover_symbols(mt5)
        summary["symbols"] = {}
        meta = {}
        for canon, info in mapping.items():
            sym = info["symbol_as_received"]
            entry = dict(info)
            if sym:
                si = mt5.symbol_info(sym)
                if si is not None:
                    if not getattr(si, "visible", False):
                        mt5.symbol_select(sym, True)  # read-only visibility toggle
                    entry["visible"] = bool(getattr(si, "visible", False))
                    entry["selectable"] = bool(getattr(si, "selectable", False))
                    meta[canon] = _symbol_meta(si)
            summary["symbols"][canon] = entry

        # ── bounded completed H1 bars (skip position 0 = forming bar) ────────
        h1 = {}
        for canon in CANONICAL:
            sym = mapping[canon]["symbol_as_received"]
            if not sym:
                h1[canon] = {"returned": 0, "method": "symbol_unresolved"}
                continue
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 1, 500)
            rows = _bars_to_rows(rates, sym, canon, stamp, 500)
            if rows:
                _write_csv(EXP_DIR / f"audit_mt5_h1_sample_{canon}.csv", rows)
            h1[canon] = {
                "returned": len(rows),
                "method": "copy_rates_from_pos(start_pos=1, count=500); "
                          "position 0 (current forming bar) excluded",
                "first_time": rows[0]["time"] if rows else None,
                "last_time": rows[-1]["time"] if rows else None,
                "fields": list(rows[0].keys()) if rows else [],
            }
        summary["h1_sample"] = h1

        # ── bounded recent ticks ─────────────────────────────────────────────
        tick_rows = []
        tick_info = {}
        for canon in CANONICAL:
            sym = mapping[canon]["symbol_as_received"]
            if not sym:
                tick_info[canon] = {"returned": 0, "reason": "symbol_unresolved"}
                continue
            frm = _utcnow() - dt.timedelta(days=2)
            ticks = mt5.copy_ticks_from(sym, frm, 1000, mt5.COPY_TICKS_ALL)
            n = 0 if ticks is None else len(ticks)
            fields = []
            if ticks is not None and n:
                fields = list(ticks.dtype.names)
                for t in list(ticks)[:1000]:
                    tick_rows.append({
                        "canonical_symbol": canon, "broker_symbol": sym,
                        "retrieval_timestamp_utc": stamp,
                        "time": int(t["time"]),
                        "time_msc": int(t["time_msc"]) if "time_msc" in fields else "",
                        "bid": float(t["bid"]), "ask": float(t["ask"]),
                        "last": float(t["last"]), "volume": float(t["volume"]),
                        "volume_real": float(t["volume_real"]) if "volume_real" in fields else "",
                        "flags": int(t["flags"]),
                    })
            tick_info[canon] = {"returned": n, "fields": fields}
        if tick_rows:
            _write_csv(EXP_DIR / "audit_mt5_tick_sample_redacted.csv", tick_rows)
        summary["ticks"] = tick_info

        if meta:
            (EXP_DIR / "audit_mt5_symbol_metadata_redacted.json").write_text(
                json.dumps(meta, indent=2, default=str), encoding="utf-8")
        summary["symbol_metadata"] = meta

        # ── timezone / completion evidence (qualitative) ─────────────────────
        eur = h1.get("EURUSD", {})
        last_completed = eur.get("last_time")
        summary["timezone_evidence"] = {
            "system_utc_now": stamp,
            "latest_completed_h1_bar_epoch_server": last_completed,
            "mt5_time_semantics_evidence": (
                "MT5 API documents bar/tick 'time' as server time; UTC offset and "
                "DST are not directly exposed by the read API."),
            "server_offset_directly_identified": False,
            "server_timezone_status": "UNRESOLVED",
            "bar_completion_semantics": (
                "completed bars selected by start_pos=1; position 0 excluded as "
                "the forming bar"),
        }

        _emit(summary)
        return 0
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _write_csv(path: Path, rows):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def _emit(summary):
    text = json.dumps(summary, indent=2, default=str)
    (EXP_DIR / "audit_mt5_run_summary_redacted.json").write_text(text, encoding="utf-8")
    sys.stdout.write(text + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
