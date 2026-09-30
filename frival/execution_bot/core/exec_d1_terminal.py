# -*- coding: utf-8 -*-
"""EXEC-D1 → MT5 DEMO TERMINAL executor (authorized 2026-09-29).

CONTEXT (project owner decision):
  - Execute real orders in the FP Markets DEMO terminal (account 7409623,
    FPMarketsSC-Demo, $5,000 demo money) to test hypotheses (burn/hold).
  - ALL FOUR pairs participate.
  - Entry semantics: if the executable quote is inside the entry zone at
    processing time -> market entry immediately; otherwise the signal stays
    PENDING for up to 10 minutes from T0; a quote touch fills it at the
    qualifying (conservative) quote; no touch by T0+10min -> EXPIRED_UNFILLED,
    no order. NO_VALID_PENDING -> never any order.
  - This module is the TRANSPORT layer for the EXEC-D1 decision engine: the
    LifecycleEngine decides (zone/expiry/claims), this executor sends the real
    order to the demo terminal and records the outcome.

Design:
  - The order request mirrors the project's proven order_manager._prepare_order:
      action=TRADE_ACTION_DEAL, symbol, volume, type=ORDER_TYPE_SELL/BUY,
      price=<conservative fill quote>, sl/tp mandatory, deviation=30,
      type_filling=ORDER_FILLING_IOC, comment=<signal_id>.
  - Every send is guarded (preflight) and blocked with a recorded SKIP reason
    if any check fails:
      emergency stop file, connection/demo-env, market open, no existing
      position for symbol+direction, daily loss cap, idempotency.
  - Outcomes are appended (fsync) to data/exec_d1_executions.jsonl and, when a
    real close is executed, recorded in the lifecycle store (CLOSED_*).

Only demo money is touched. No live account is ever used. The runner keeps the
terminal open and is started by the operator (see run_exec_d1_terminal.py).
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── project layout ────────────────────────────────────────────────────────────
EXEC_BOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = EXEC_BOT_DIR / "data"
LOGS_DIR = Path(__file__).resolve().parents[2] / "output" / "logs"
SETTINGS_PATH = EXEC_BOT_DIR / "config" / "settings.yaml"
EMERGENCY_STOP = Path(__file__).resolve().parents[2] / "data" / "emergency_stop.txt"
EXECUTIONS_LOG = DATA_DIR / "exec_d1_executions.jsonl"

COMMENT_TAG = "D1"

# MT5 hard limit for MqlTradeRequest.comment. The MetaTrader5 Python wrapper
# rejects (returns None / last_error "(-2, 'Invalid \"comment\" argument')")
# BEFORE the request reaches the broker whenever it is exceeded, so a comment
# can never be longer than this. The 2026-09-30 failure: f"D1-{signal_id}"
# produced 38 chars, so EVERY real order was silently rejected.
MAX_COMMENT_LEN = 31


def order_comment(signal_id: str, tag: str = COMMENT_TAG) -> str:
    """Build an MT5-safe order comment (<= MAX_COMMENT_LEN characters).

    Keeps `tag-<signal_id>` when it already fits. Otherwise truncates the
    readable signal prefix and appends a short digest of the FULL signal id so
    distinct long ids can never collide after truncation.
    """
    sid = str(signal_id)
    raw = f"{tag}-{sid}"
    if len(raw) <= MAX_COMMENT_LEN:
        return raw
    digest = hashlib.sha1(sid.encode("utf-8")).hexdigest()[:6]
    keep = MAX_COMMENT_LEN - len(tag) - 2 - len(digest)   # two '-' separators
    return f"{tag}-{sid[:keep]}-{digest}"


def validate_levels(*, is_sell: bool, price: float,
                    sl: Optional[float], tp: Optional[float],
                    digits: int) -> None:
    """Fail fast on SL/TP that MT5 would reject as invalid stops.

    MT5 requires, for a market order: SELL -> stop_loss ABOVE and take_profit
    BELOW the fill price; BUY -> the reverse. Validating here turns a broker
    retcode (10016 invalid stops) into a clear, logged local error.
    """
    if sl is None and tp is None:
        return
    price_f = round(float(price), digits)
    if sl is not None:
        sl_f = round(float(sl), digits)
        if is_sell and not sl_f > price_f:
            raise ExecutorError(
                f"invalid SELL stop_loss {sl_f}: must be above fill {price_f}")
        if not is_sell and not sl_f < price_f:
            raise ExecutorError(
                f"invalid BUY stop_loss {sl_f}: must be below fill {price_f}")
    if tp is not None:
        tp_f = round(float(tp), digits)
        if is_sell and not tp_f < price_f:
            raise ExecutorError(
                f"invalid SELL take_profit {tp_f}: must be below fill {price_f}")
        if not is_sell and not tp_f > price_f:
            raise ExecutorError(
                f"invalid BUY take_profit {tp_f}: must be above fill {price_f}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def tick_to_quote(tick: Optional[Dict[str, Any]],
                  symbol: str = "") -> Optional[Dict[str, Any]]:
    """Normalize an MT5 tick snapshot into an EXEC-D1 quote dict.

    The quote timestamp is the LOCAL UTC wall clock at fetch time, NOT the
    broker `tick.time` epoch. MT5 `tick.time` is SERVER time, which is not the
    UTC clock the EXEC-D1 window (t0 .. t_exp) is defined on; mixing the two
    placed the quote outside the window and produced the 2026-09-29 `no_quote`
    expiry of the EURUSD 16:00Z signal. `broker_time` is carried for audit and
    is consumed by `TickFreshness`, never by the decision engine. Returns None
    when bid/ask are absent so the caller skips the signal instead of
    fabricating a quote.
    """
    if not isinstance(tick, dict):
        return None
    bid = tick.get("bid")
    ask = tick.get("ask")
    if bid is None or ask is None:
        return None
    return {"ts": _iso(_utcnow()), "bid": bid, "ask": ask,
            "broker_time": tick.get("time")}


class TickFreshness:
    """Offset-free staleness tracker for MT5 server ticks.

    Every broker symbol shares one server clock, so a live feed is detected by
    the broker tick time ADVANCING over local wall time — no server-offset
    knowledge is required. A symbol whose broker time has not advanced for more
    than `max_stale_seconds` is treated as a frozen feed (daily halt,
    disconnect, symbol not subscribed) and must not trigger a real order.

    The first observation of a symbol cannot be judged and is accepted; call
    `observe()` every poll so a freeze is detected before the next entry.
    """

    def __init__(self, max_stale_seconds: float = 90.0, now_fn=None):
        self.max_stale = float(max_stale_seconds)
        self.now_fn = now_fn or _utcnow
        self._last: Dict[str, Any] = {}   # symbol -> (broker_time, wall_at_advance)

    def observe(self, symbol: str, broker_time: Any) -> bool:
        """Record one poll; return True when the feed is fresh (safe to act)."""
        now = self.now_fn()
        prev = self._last.get(symbol)
        if prev is None:
            self._last[symbol] = (broker_time, now)
            return True                       # first sight: cannot judge yet
        last_bt, wall = prev
        advanced = (isinstance(broker_time, (int, float)) and
                    (not isinstance(last_bt, (int, float)) or broker_time > last_bt))
        if advanced:
            self._last[symbol] = (broker_time, now)
            return True
        return (now - wall).total_seconds() <= self.max_stale


def exec_d1_enabled(settings_path=SETTINGS_PATH) -> bool:
    """Dependency-free parser: is `execution.enabled: true`?

    Used by the legacy order bot as a delegation gate so it does not
    double-consume FIRED signals while the EXEC-D1 terminal runner is active.
    """
    path = Path(settings_path)
    if not path.exists():
        return False
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.lstrip()
        if not s or s.startswith("#"):
            continue
        entries.append((len(raw) - len(s), s))
    i = 0
    while i < len(entries):
        indent, text = entries[i]
        if indent == 0 and text == "execution:":
            j = i + 1
            while j < len(entries) and entries[j][0] > 0:
                if entries[j][1].startswith("enabled:"):
                    # Strip any inline comment (real settings.yaml writes
                    # "enabled: true   # note"); otherwise the value compares as
                    # "true   # note" != "true" and the delegation gate silently
                    # fails (2026-09-29 bug: legacy bot kept opening phantom
                    # virtual fills while EXEC-D1 was meant to be the only path).
                    value = entries[j][1].split(":", 1)[1].split("#", 1)[0]
                    return value.strip().lower() == "true"
                j += 1
            return False
        i += 1
    return False


def entry_semantics(settings_path=SETTINGS_PATH) -> str:
    """Dependency-free parser: `execution.entry_semantics` ("zone" | "reanchor").

    Defaults to "zone" when absent/unreadable so behavior is unchanged unless the
    operator opts in. "reanchor" = market-enter at the first in-window tick and
    re-anchor SL/TP on the actual fill (removes the close-zone latency dependence).
    """
    path = Path(settings_path)
    if not path.exists():
        return "zone"
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.lstrip()
        if not s or s.startswith("#"):
            continue
        entries.append((len(raw) - len(s), s))
    i = 0
    while i < len(entries):
        indent, text = entries[i]
        if indent == 0 and text == "execution:":
            j = i + 1
            while j < len(entries) and entries[j][0] > 0:
                if entries[j][1].startswith("entry_semantics:"):
                    value = entries[j][1].split(":", 1)[1].split("#", 1)[0]
                    return value.strip().lower() or "zone"
                j += 1
            return "zone"
        i += 1
    return "zone"


class ExecutorError(RuntimeError):
    pass


class Mt5Gateway:
    """Thin shim over the MetaTrader5 module (or a fake in offline tests).

    Only the read operations needed by the executor plus order_send are used.
    The connector attaches PATH-ONLY (production pattern) to the already
    running, already logged-in demo terminal; credentials are never passed.
    """

    SYMBOL_MODE_SELL = "SELL"

    def __init__(self, mt5_module=None):
        self._mt5 = mt5_module

    # ── lifecycle ─────────────────────────────────────────────────────────────
    def attach(self, terminal_path: str) -> bool:
        return bool(self._mt5.initialize(path=terminal_path))

    def detach(self) -> None:
        try:
            self._mt5.shutdown()
        except Exception:
            pass

    def last_error(self):
        try:
            return self._mt5.last_error()
        except Exception as exc:  # pragma: no cover
            return repr(exc)

    # ── reads ─────────────────────────────────────────────────────────────────
    def account(self) -> Optional[Dict[str, Any]]:
        acc = self._mt5.account_info()
        if acc is None:
            return None
        return {
            "login": str(getattr(acc, "login", "") or ""),
            "server": getattr(acc, "server", "") or "",
            "trade_mode": getattr(acc, "trade_mode", None),
            "balance": getattr(acc, "balance", None),
        }

    def tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        t = self._mt5.symbol_info_tick(symbol)
        if t is None:
            return None
        return {"bid": getattr(t, "bid", None), "ask": getattr(t, "ask", None),
                "time": getattr(t, "time", None)}

    def positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        try:
            rows = self._mt5.positions_get(symbol=symbol) if symbol else self._mt5.positions_get()
        except Exception:
            return []
        if not rows:
            return []
        out = []
        for p in rows:
            out.append({
                "ticket": getattr(p, "ticket", None),
                "symbol": getattr(p, "symbol", None),
                "type": getattr(p, "type", None),
            })
        return out

    def daily_realized_pnl(self, tz_day_start=None) -> Optional[float]:
        """Realized PnL today (history deals). None when unavailable."""
        try:
            from datetime import datetime as _dt, timedelta as _td
            try:
                import pytz
                tz = tz_day_start or pytz.timezone("America/Panama")
            except Exception:
                tz = timezone(_td(hours=-5))       # America/Panama (no DST)
            now = _dt.now(tz)
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            deals = self._mt5.history_deals_get(start, now)
        except Exception:
            return None
        if not deals:
            return 0.0
        total = 0.0
        for d in deals:
            profit = getattr(d, "profit", None)
            if isinstance(profit, (int, float)):
                total += float(profit)
        return total

    def resolve_filling(self, symbol: str) -> Optional[int]:
        """Return a filling mode the symbol actually supports, or None.

        MT5 rejects an order whose `type_filling` the symbol does not permit
        (retcode 10030 Unsupported filling mode). `SymbolInfo.filling_mode` is a
        bitmask of SYMBOL_FILLING_* flags; prefer IOC, then FOK. Returns None
        when metadata is unavailable so the caller keeps its configured default.
        """
        try:
            si = self._mt5.symbol_info(symbol)
        except Exception:
            return None
        mask = getattr(si, "filling_mode", None) if si is not None else None
        if not isinstance(mask, int):
            return None
        ioc_flag = getattr(self._mt5, "SYMBOL_FILLING_IOC", 2)
        fok_flag = getattr(self._mt5, "SYMBOL_FILLING_FOK", 1)
        if mask & ioc_flag:
            return getattr(self._mt5, "ORDER_FILLING_IOC", 1)
        if mask & fok_flag:
            return getattr(self._mt5, "ORDER_FILLING_FOK", 0)
        return None

    # ── writes (the ONLY authorized side effect: real demo order_send) ───────
    def place_market(self, *, symbol: str, volume: float, mt5_type: int,
                     price: float, sl: Optional[float] = None,
                     tp: Optional[float] = None, comment: str,
                     digits: int = 5,
                     require_levels: bool = True) -> Dict[str, Any]:
        if require_levels and (sl is None or tp is None):
            raise ExecutorError("all open orders must carry BOTH sl and tp (safety control)")
        if not isinstance(comment, str) or not comment:
            raise ExecutorError("order comment must be a non-empty string")
        if len(comment) > MAX_COMMENT_LEN:
            raise ExecutorError(
                f"order comment is {len(comment)} chars; MT5 allows at most "
                f"{MAX_COMMENT_LEN} (would be rejected as 'Invalid comment argument')")
        volume_f = float(volume)
        if not volume_f > 0:
            raise ExecutorError(f"order volume must be positive, got {volume!r}")
        is_sell = mt5_type == self._mt5.ORDER_TYPE_SELL
        validate_levels(is_sell=is_sell, price=price, sl=sl, tp=tp, digits=digits)
        filling = self.resolve_filling(symbol)
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume_f,
            "type": mt5_type,
            "price": round(float(price), digits),
            "deviation": 30,
            "comment": comment,
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": (filling if filling is not None
                             else self._mt5.ORDER_FILLING_IOC),
        }
        if sl is not None:
            request["sl"] = round(float(sl), digits)
        if tp is not None:
            request["tp"] = round(float(tp), digits)
        result = self._mt5.order_send(request)
        if result is None:
            return {"success": False, "retcode": None,
                    "error": f"order_send None: {self.last_error()}"}
        return {
            "success": result.retcode == self._mt5.TRADE_RETCODE_DONE,
            "retcode": result.retcode,
            "ticket": getattr(result, "order", None),
            "deal": getattr(result, "deal", None),
        }


class TerminalExecutor:
    """Executes EXEC-D1 fill decisions on the DEMO terminal (guarded)."""

    ORDER_TYPE_MT5 = {"SELL": None, "BUY": None}   # resolved per gateway

    def __init__(self, gateway: Mt5Gateway, *,
                 login_expected: str, server_expected: str = "FPMarketsSC-Demo",
                 lots: Optional[Dict[str, float]] = None,
                 max_daily_loss: float = 100.0,
                 executions_path=EXECUTIONS_LOG,
                 now_fn=None):
        self.gateway = gateway
        self.login_expected = login_expected
        self.server_expected = server_expected
        self.lots = lots or {"EURUSD": 0.08, "GBPUSD": 0.08,
                             "USDCHF": 0.04, "USDCAD": 0.08}
        self.max_daily_loss = float(max_daily_loss)
        self.executions_path = Path(executions_path)
        self.now_fn = now_fn or _utcnow
        self._type_map = {
            "SELL": gateway._mt5.ORDER_TYPE_SELL,
            "BUY": gateway._mt5.ORDER_TYPE_BUY,
        }

    # ── bookkeeping ───────────────────────────────────────────────────────────
    def _append_execution(self, record: Dict[str, Any]) -> None:
        record = {"event_id": uuid.uuid4().hex,
                  "ts_utc": _iso(self.now_fn()), **record}
        self.executions_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.executions_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, (json.dumps(record) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    def executed_signal_ids(self) -> set:
        """Signal ids with a SUCCESSFUL real order (decision == 'EXECUTED').

        Used at startup to detect a VIRTUAL_OPEN whose real send never
        succeeded (a phantom) and reconcile it.
        """
        if not self.executions_path.exists():
            return set()
        out = set()
        for line in self.executions_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
            except Exception:
                continue
            if record.get("decision") == "EXECUTED" and record.get("signal_id"):
                out.add(record["signal_id"])
        return out

    def has_execution(self, signal_id: str) -> bool:
        if not self.executions_path.exists():
            return False
        for line in self.executions_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                if json.loads(line).get("signal_id") == signal_id:
                    return True
            except Exception:
                continue
        return False

    # ── guards ────────────────────────────────────────────────────────────────
    def _emergency_stop(self) -> bool:
        return EMERGENCY_STOP.exists()

    def _demo_env_ok(self) -> bool:
        acc = self.gateway.account()
        if acc is None:
            return False
        if str(acc.get("login", "")) != self.login_expected:
            return False
        if acc.get("server", "") and acc.get("server") != self.server_expected:
            return False
        return acc.get("trade_mode") == 0            # demo terminal

    def preflight(self, *, symbol: str, direction: str,
                  allow_demo_env_check: bool = True) -> tuple:
        """Return (ok, reason). Blocks any send whose precondition fails."""
        if self._emergency_stop():
            return False, "emergency_stop"
        if allow_demo_env_check and not self._demo_env_ok():
            return False, "demo_env_mismatch"
        positions = self.gateway.positions(symbol)
        for pos in positions:
            pos_type = pos.get("type")
            if direction == "SELL" and pos_type == 1:   # POSITION_TYPE_SELL
                return False, "position_exists_sell"
            if direction == "BUY" and pos_type == 0:    # POSITION_TYPE_BUY
                return False, "position_exists_buy"

        daily = self.gateway.daily_realized_pnl()
        if daily is not None and daily <= -self.max_daily_loss:
            return False, "daily_loss_cap"
        return True, "ok"

    is_demo_env_checked = False

    # ── the one real side effect ──────────────────────────────────────────────
    def execute_fill(self, *, signal_id: str, symbol: str, direction: str,
                     fill_price: float, sl: float, tp: float,
                     quote_bid: float = None, quote_ask: float = None) -> Dict[str, Any]:
        """Send ONE real demo-terminal order for an EXEC-D1 fill decision."""
        if self.has_execution(signal_id):
            return {"decision": "SKIP", "reason": "already_executed"}
        ok, reason = self.preflight(symbol=symbol, direction=direction)
        if not ok:
            self._append_execution({
                "signal_id": signal_id, "symbol": symbol, "direction": direction,
                "decision": "SKIP", "reason": reason, "fill_price": fill_price,
            })
            return {"decision": "SKIP", "reason": reason}

        lot = self.lots.get(symbol)
        if not lot:
            return {"decision": "SKIP", "reason": f"no_lot_config_{symbol}"}

        try:
            result = self.gateway.place_market(
                symbol=symbol, volume=lot,
                mt5_type=self._type_map[direction],
                price=fill_price, sl=sl, tp=tp,
                comment=order_comment(signal_id))
        except ExecutorError as exc:
            # A locally invalid request must never abort the monitor loop; it is
            # recorded as a FAILED execution so it cannot silently vanish.
            result = {"success": False, "retcode": None,
                      "error": f"request_invalid: {exc}"}

        record = {
            "signal_id": signal_id, "symbol": symbol, "direction": direction,
            "decision": "EXECUTED" if result.get("success") else "FAILED",
            "fill_price": fill_price,
            "quote_bid": quote_bid, "quote_ask": quote_ask,
            "lot": lot, "sl": sl, "tp": tp, "retcode": result.get("retcode"),
            "ticket": result.get("ticket"), "deal": result.get("deal"),
            "error": result.get("error"),
        }
        self._append_execution(record)
        return record

    # ── closes (terminal SL/TP normally manages; optional horizon close) ─────
    def close_position(self, *, symbol: str, volume: float,
                       side_open: str, comment: str) -> Dict[str, Any]:
        """Offsetting market order to close a position manually (no SL/TP)."""
        close_side = "BUY" if side_open == "SELL" else "SELL"
        result = self.gateway.place_market(
            symbol=symbol, volume=volume, mt5_type=self._type_map[close_side],
            price=0.0, comment=comment, require_levels=False)
        return result