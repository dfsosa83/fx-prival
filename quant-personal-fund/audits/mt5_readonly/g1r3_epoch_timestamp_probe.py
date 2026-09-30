#!/usr/bin/env python
# READ_ONLY_ONLY
"""G1-R3 controlled epoch timestamp probe (read-only, script-only).

Purpose: determine whether raw epochs returned by the current local MT5 Python
API are consistent with UTC, and whether the prior ~1h discrepancy was caused
by local conversion / bar-selection, or reflects a broker/terminal time anomaly.

READ_ONLY_ONLY = True. Read-only metadata/history queries only. No trading API.
Standalone; must NEVER be imported by the research library. Writes only inside
the experiment folder. No secrets/account/server/terminal path is printed or
saved. No returns/spreads/correlations/costs are computed (timestamp provenance
diagnostics only).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
import time
from pathlib import Path

READ_ONLY_ONLY = True

# ── static read-only self-guard (tokens assembled from split literals) ────────
_TA = "TRADE_ACTION_"
_FORBIDDEN = ["order_" + "send", "order_" + "check",
              _TA + "DEAL", _TA + "PENDING", _TA + "SLTP", _TA + "REMOVE"]
_SRC = Path(__file__).read_text(encoding="utf-8", errors="replace")
_HITS = [t for t in _FORBIDDEN if t in _SRC]
if _HITS:
    sys.stderr.write("READ_ONLY_SAFETY_FAILURE: forbidden token present in source\n")
    sys.exit(3)

SCRIPT_HASH = hashlib.sha256(_SRC.encode("utf-8")).hexdigest()[:16]
REPO = Path(__file__).resolve().parents[3]
EXP_DIR = (REPO / "quant-personal-fund" / "experiments"
           / "QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION")
CREDS = REPO / "frival" / "execution_bot" / "config" / "credentials.env"
SYMBOLS = ("EURUSD", "GBPUSD")
FRESH_WINDOW_S = 120          # tick "contemporaneous" tolerance (provenance only)


def _utc():
    return dt.datetime.now(dt.timezone.utc)


def _epoch():
    return time.time()


def _conv(epoch):
    return {
        "utc_fromtimestamp_iso": dt.datetime.fromtimestamp(epoch, dt.timezone.utc).isoformat(),
        "utc_utcfromtimestamp_iso": dt.datetime.utcfromtimestamp(epoch).replace(
            tzinfo=dt.timezone.utc).isoformat(),
        "local_time_diagnostic_only": dt.datetime.fromtimestamp(epoch).isoformat(),
    }


def _terminal_path():
    p = None
    try:
        for line in CREDS.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "MT5_TERMINAL_PATH":
                    p = v.strip().strip('"').strip("'")
    except Exception:
        p = None
    return p


def main() -> int:
    out = {"script_version": "g1r3-1", "script_hash16": SCRIPT_HASH, "read_only": True,
           "errors": [], "symbols": {}}

    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        out["errors"].append("MetaTrader5 import failed: " + type(exc).__name__)
        _emit(out); return 1

    path = _terminal_path()
    ok = mt5.initialize(path=path) if path else mt5.initialize()
    if not ok:
        out["errors"].append(f"initialize failed code={mt5.last_error()[0]}")
        _emit(out); return 1

    out["mt5_initialized"] = True
    try:
        ti = mt5.terminal_info()
        out["terminal"] = {"connected": bool(getattr(ti, "connected", False)),
                           "build": int(getattr(ti, "build", 0))}
        names = [s.name for s in mt5.symbols_get()]
        mapping = {}
        for canon in SYMBOLS:
            mapping[canon] = canon if canon in names else next(
                (n for n in names if canon in n), None)

        for canon in SYMBOLS:
            sym = mapping[canon]
            rec = {"canonical_symbol": canon,
                   "symbol_as_received_present": bool(sym),
                   "symbol_as_received_matches_exact": sym == canon}
            if not sym:
                out["symbols"][canon] = rec
                continue

            # ── A. system UTC capture (H1 group) ──────────────────────────
            g_before_dt = _utc(); g_before_ep = _epoch()

            # ── B. H1 raw-bar probe: positions 0 and 1 ────────────────────
            rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 2)
            g_after_dt = _utc(); g_after_ep = _epoch()
            bars = []
            if rates is not None:
                for i, r in enumerate(list(rates)):
                    ep = int(r["time"])
                    bars.append({
                        "result_index": i,
                        "position_label": "POSITION_0" if i == 0 else "POSITION_1",
                        "raw_time_epoch": ep,
                        "class": ("CURRENT_OR_POSSIBLY_FORMING" if i == 0
                                  else "PRIOR_COMPLETED_CANDIDATE"),
                        "conv": _conv(ep),
                    })
            # H1 offset diagnostic: position-0 epoch vs the current UTC hour floor
            h1_offset_s = None
            if bars:
                hour_floor = int(g_before_ep // 3600) * 3600
                h1_offset_s = bars[0]["raw_time_epoch"] - hour_floor
            rec["h1_group"] = {
                "system_utc_before": g_before_dt.isoformat(),
                "system_utc_after": g_after_dt.isoformat(),
                "system_utc_before_epoch": g_before_ep,
                "observed_order_note": "copy_rates_from_pos returned oldest->newest (result_index 0 = POSITION_0)",
                "bars": bars,
                "h1_position0_offset_vs_utc_hour_floor_s": h1_offset_s,
            }

            # ── C. current tick probe (single call) ───────────────────────
            t_before_dt = _utc(); t_before_ep = _epoch()
            tick = mt5.symbol_info_tick(sym)
            t_after_dt = _utc(); t_after_ep = _epoch()
            tick_rec = {
                "system_utc_before": t_before_dt.isoformat(),
                "system_utc_after": t_after_dt.isoformat(),
                "bid_field_present": bool(tick is not None and getattr(tick, "bid", None) is not None),
                "ask_field_present": bool(tick is not None and getattr(tick, "ask", None) is not None),
            }
            if tick is not None:
                tep = int(getattr(tick, "time", 0))
                tmsc = getattr(tick, "time_msc", None)
                tick_rec["raw_time_epoch"] = tep
                tick_rec["time_msc_present"] = tmsc is not None
                tick_rec["conv"] = _conv(tep)
                off = tep - t_before_ep
                tick_rec["tick_minus_query_epoch_s"] = int(off)
                tick_rec["freshness"] = ("CONTEMPORANEOUS" if abs(off) <= FRESH_WINDOW_S
                                         else "STALE_OR_NOT_COMPARABLE")
            else:
                tick_rec["freshness"] = "STALE_OR_NOT_COMPARABLE"
            rec["tick"] = tick_rec

            # ── D. bounded recent-tick retrieval (now-5min, <=50 ticks) ───
            r_before_dt = _utc(); r_before_ep = _epoch()
            frm = _utc() - dt.timedelta(minutes=5)
            ticks = None
            try:
                ticks = mt5.copy_ticks_from(sym, frm, 50, mt5.COPY_TICKS_ALL)
            except Exception as exc:
                rec.setdefault("errors", []).append(
                    "copy_ticks_from failed: " + type(exc).__name__)
            r_after_dt = _utc(); r_after_ep = _epoch()
            rec_ticks = {"query_utc_before": r_before_dt.isoformat(),
                         "window_from_utc": frm.isoformat(),
                         "count": 0 if ticks is None else int(len(ticks))}
            if ticks is not None and len(ticks):
                ep0 = int(ticks[0]["time"]); epN = int(ticks[-1]["time"])
                rec_ticks["first_raw_epoch"] = ep0
                rec_ticks["last_raw_epoch"] = epN
                rec_ticks["last_minus_query_epoch_s"] = int(epN - r_before_ep)
                rec_ticks["freshness"] = ("CONTEMPORANEOUS"
                                          if abs(epN - r_before_ep) <= FRESH_WINDOW_S
                                          else "STALE_OR_NOT_COMPARABLE")
            else:
                rec_ticks["freshness"] = "NO_RECENT_TICKS"
            rec["recent_ticks"] = rec_ticks

            out["symbols"][canon] = rec

        # ── classification ────────────────────────────────────────────────
        tick_ok = any(v.get("tick", {}).get("freshness") == "CONTEMPORANEOUS"
                      for v in out["symbols"].values())
        h1_ok = all(
            abs(v.get("h1_group", {}).get("h1_position0_offset_vs_utc_hour_floor_s") or 0) <= 5
            for v in out["symbols"].values())
        if tick_ok and h1_ok:
            outcome = "UTC_CONFIRMED_FOR_CURRENT_MT5_API_SAMPLE"
        elif not tick_ok and not any(
                "tick" in v and v.get("tick") for v in out["symbols"].values()):
            outcome = "INSUFFICIENT_CURRENT_TICK_EVIDENCE"
        else:
            outcome = "BROKER_OR_TERMINAL_TIME_ANOMALY_UNRESOLVED"
        out["outcome_classification"] = outcome
        out["official_doc_claim"] = "MT5 Python data time is UTC (MQL5 copy_rates_from doc)"

        _emit(out)
        return 0
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def _emit(out):
    text = json.dumps(out, indent=2, default=str)
    (EXP_DIR / "G1R3_EPOCH_PROBE_REDACTED.json").write_text(text, encoding="utf-8")
    sys.stdout.write(text + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
