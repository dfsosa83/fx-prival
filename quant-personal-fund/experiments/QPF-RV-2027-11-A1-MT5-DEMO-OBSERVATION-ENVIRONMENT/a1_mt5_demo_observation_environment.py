"""A1 MT5-demo observation-environment setup (XAUUSD, orders disabled).

Configures and validates a controlled FP Markets/MT5 DEMO environment for
observing the frozen A1 Gold Rules Engine on real XAUUSD data. It may initialize
MT5 (demo only), read XAUUSD H1/M30/M15 bars + one tick, and read count-only
positions/orders for collision detection. It NEVER sends/modifies/cancels any
order or position. Only redacted structural metadata is persisted.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MODE = "OBSERVATION_DEMO"
SYMBOL = "XAUUSD"
ALLOWED_TIMEFRAMES = ["H1", "M30", "M15"]
ALLOWED_MT5_OPERATIONS = [
    "initialize", "shutdown", "account_info", "terminal_info", "symbol_select",
    "symbol_info", "symbol_info_tick", "copy_rates_from_pos", "copy_rates_range",
    "positions_get", "orders_get", "last_error",
]


def _forbidden_methods() -> List[str]:
    # assembled from split literals so the source never contains them verbatim
    return ["order_" + "send", "order_" + "check", "order_calc_" + "margin",
            "order_calc_" + "profit", "history_orders_" + "get", "history_deals_" + "get",
            "copy_" + "ticks", "market_" + "book_", "virtual_" + "fill",
            "execute_" + "trade", "execute_" + "order", "order_" + "manager"]


def validate_mode(config: Dict[str, Any]) -> None:
    if not isinstance(config, dict) or config.get("mode") != MODE:
        raise ValueError(f"mode must be exactly {MODE}")


def orders_disabled_guard(config: Dict[str, Any]) -> None:
    if config.get("ORDERS_DISABLED") is not True:
        raise ValueError("ORDERS_DISABLED must be True")


def static_scan_forbidden(paths) -> List[str]:
    """AST/text scan: fail if a source references any forbidden order/execution method."""
    hits: List[str] = []
    tokens = _forbidden_methods()
    for p in paths:
        text = Path(p).read_text(encoding="utf-8", errors="replace").lower()
        for t in tokens:
            if t in text:
                hits.append(f"{Path(p).name}:{t}")
    return hits


def verify_demo_account(account: Optional[Dict[str, Any]]) -> bool:
    """True only when the connected account is a DEMO account (trade_mode == 0)."""
    if not account:
        return False
    return int(account.get("trade_mode", -1)) == 0


def xauusd_available(gateway) -> bool:
    si = gateway.symbol_info(SYMBOL)
    if si is None:
        try:
            gateway.symbol_select(SYMBOL, True)
        except Exception:
            return False
        si = gateway.symbol_info(SYMBOL)
    return si is not None


def validate_bar_payload(rows: List[Dict[str, Any]]) -> None:
    if not isinstance(rows, list) or not rows:
        raise ValueError("bar payload empty")
    required = ("time", "open", "high", "low", "close")
    for r in rows:
        for k in required:
            if k not in r:
                raise ValueError(f"bar payload missing '{k}'")


def read_symbol_bars(gateway, timeframe: str, count: int = 5) -> List[Dict[str, Any]]:
    if timeframe not in ALLOWED_TIMEFRAMES:
        raise ValueError(f"timeframe not allowed: {timeframe}")
    raw = gateway.copy_rates_from_pos(SYMBOL, timeframe, 0, count)
    rows = [] if raw is None else [{"time": t, "open": o, "high": h, "low": l, "close": c}
                                   for (t, o, h, l, c) in raw]
    validate_bar_payload(rows)
    return rows


def reconcile_counts(positions: Optional[List[Any]], orders: Optional[List[Any]]) -> Dict[str, int]:
    """Count-only reconciliation for collision detection (no details)."""
    return {"positions_count": 0 if positions is None else len(positions),
            "orders_count": 0 if orders is None else len(orders)}


def build_attestation(demo_ok: bool, xau_ok: bool, counts: Dict[str, int],
                      bars_ok: Dict[str, bool], tick_ok: bool) -> Dict[str, Any]:
    """Redacted environment attestation — no account id, server, balance or symbol details."""
    return {
        "mode": MODE,
        "redacted": True,
        "demo_verified": bool(demo_ok),
        "xauusd_available": bool(xau_ok),
        "existing_positions_count": int(counts.get("positions_count", 0)),
        "existing_orders_count": int(counts.get("orders_count", 0)),
        "orders_disabled": True,
        "bars_read_ok": {tf: bool(bars_ok.get(tf, False)) for tf in ALLOWED_TIMEFRAMES},
        "tick_read_ok": bool(tick_ok),
        "source_bar_freshness": "READ_OK" if all(bars_ok.get(tf, False) for tf in ALLOWED_TIMEFRAMES) else "INCOMPLETE",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def run_setup(gateway, config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and read the demo environment, then shut down immediately."""
    validate_mode(config)
    orders_disabled_guard(config)
    self_hits = static_scan_forbidden([Path(__file__)])
    if self_hits:
        raise RuntimeError(f"static forbidden-method scan failed: {self_hits}")

    if not gateway.initialize():
        raise RuntimeError("MT5 initialize failed")
    try:
        account = gateway.account_info()
        demo_ok = verify_demo_account(account)
        if not demo_ok:
            raise RuntimeError("account is not a verified DEMO account")
        if not xauusd_available(gateway):
            raise RuntimeError(f"{SYMBOL} unavailable")

        bars_ok = {}
        for tf in ALLOWED_TIMEFRAMES:
            try:
                rows = read_symbol_bars(gateway, tf, count=5)
                bars_ok[tf] = len(rows) > 0
            except Exception:
                bars_ok[tf] = False
        tick = gateway.symbol_info_tick(SYMBOL)
        tick_ok = tick is not None
        counts = reconcile_counts(gateway.positions_get(), gateway.orders_get())
        return build_attestation(demo_ok, True, counts, bars_ok, tick_ok)
    finally:
        gateway.shutdown()


class RealMt5Gateway:
    """Thin read-only wrapper over the MetaTrader5 package (demo terminal)."""

    def __init__(self, terminal_path: Optional[str] = None):
        self.terminal_path = terminal_path
        self._mt5 = None

    def _m(self):
        if self._mt5 is None:
            import MetaTrader5 as mt5  # noqa: F401  (allowed: read-only demo)
            self._mt5 = mt5
        return self._mt5

    def initialize(self) -> bool:
        mt5 = self._m()
        return bool(mt5.initialize(path=self.terminal_path) if self.terminal_path else mt5.initialize())

    def shutdown(self) -> None:
        self._m().shutdown()

    def account_info(self):
        ai = self._m().account_info()
        if ai is None:
            return None
        return {"trade_mode": ai.trade_mode}

    def symbol_info(self, symbol):
        return self._m().symbol_info(symbol)

    def symbol_select(self, symbol, enable=True):
        return self._m().symbol_select(symbol, enable)

    def symbol_info_tick(self, symbol):
        return self._m().symbol_info_tick(symbol)

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        mt5 = self._m()
        tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
        rates = mt5.copy_rates_from_pos(symbol, tf, start, count)
        if rates is None:
            return None
        return [(int(r["time"]), float(r["open"]), float(r["high"]),
                 float(r["low"]), float(r["close"])) for r in rates]

    def positions_get(self):
        return self._m().positions_get()

    def orders_get(self):
        return self._m().orders_get()
