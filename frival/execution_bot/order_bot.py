"""
Order Bot — Bridges Frival signals to MT5 execution.

Receives validated signals from signal_watcher, applies risk gates,
and executes orders via the demo_bot OrderManager.

Risk gates (applied in order):
  1. Emergency stop — terminates if emergency_stop.txt exists
  2. Pair allowed — skips shadow-only pairs
  3. Daily PnL — blocks if daily loss exceeds configured limit
  4. Duplicate position — skips if a position already open on this symbol
  5. Margin check — skips if insufficient free margin
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import MetaTrader5 as mt5

from core.config_manager import ConfigManager
from core.demo_ledger import (append_trade, close_pool, load_ledger,
                              manage_open, open_virtual)
from core.mt5_connector import MT5Connector
from core.order_manager import OrderManager

LOG_FILE = Path(__file__).resolve().parent / "data" / "execution_log.jsonl"
EMERGENCY_STOP = Path(__file__).resolve().parents[1] / "data" / "emergency_stop.txt"
DEMO_LEDGER_FILE = Path(__file__).resolve().parent / "data" / "demo_trades_ledger.jsonl"


class OrderBot:
    """
    Automated order executor for Frival signals.

    Usage:
        config = ConfigManager(config_dir="config")
        bot = OrderBot(config)
        bot.start()
        bot.handle_signal(signal_dict)   # called by signal_watcher callback
        bot.stop()
    """

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.connector: Optional[MT5Connector] = None
        self.order_manager: Optional[OrderManager] = None
        self.daily_pnl = 0.0
        self.signals_executed = 0
        self.signals_rejected = 0
        # Demo virtual-fill book (PORTFOLIO-DEMO-SPEC §3): simulated orders get a
        # real lifecycle and realized PnL so paper trading produces evidence.
        self.demo_positions = load_ledger(DEMO_LEDGER_FILE)
        self._load_pair_config()

    def _load_pair_config(self):
        """Load per-pair execution config from settings.yaml."""
        pairs = self.config.get_config("pairs") or {}
        self.pair_config = {}
        for symbol, cfg in pairs.items():
            self.pair_config[symbol.upper()] = {
                "allowed": not cfg.get("shadow", False),
                "lot_size": cfg.get("lot_size", 0.08),
                "direction": cfg.get("direction", "SELL"),
            }

    def start(self) -> bool:
        """Connect to MT5 and initialize the order manager."""
        if EMERGENCY_STOP.exists():
            print("\n[OrderBot] EMERGENCY STOP ACTIVE — delete emergency_stop.txt to resume")
            print(f"            File: {EMERGENCY_STOP}")
            return False

        # Initialize MT5
        creds = self.config.get_mt5_credentials()
        terminal_path = creds.get("terminal_path")
        mt5_cfg = self.config.get_config("mt5") or {}
        timeout = mt5_cfg.get("timeout", 30)
        max_retries = mt5_cfg.get("retries", 3)

        try:
            self.connector = MT5Connector(self.config)
            if not self.connector.connect():
                print("[OrderBot] Failed to connect to MT5")
                return False
        except Exception as e:
            print(f"[OrderBot] MT5 connection error: {e}")
            return False

        # Initialize order manager
        self.order_manager = OrderManager(self.connector, self.config)

        # Log startup
        account = self.connector.get_account_info()
        print(f"\n[OrderBot] Connected — Account {account.get('login')}")
        print(f"  Balance: ${account.get('balance', 0):,.2f}")
        print(f"  Equity:  ${account.get('equity', 0):,.2f}")
        print(f"  Leverage: 1:{account.get('leverage', 0)}")
        print(f"  Demo mode: {self.config.is_demo_mode()}")

        return True

    def stop(self):
        """Disconnect from MT5."""
        if self.connector:
            self.connector.disconnect()
        print(f"\n[OrderBot] Session summary: {self.signals_executed} executed, "
              f"{self.signals_rejected} rejected")

    def handle_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Process a Frival signal. Called by signal_watcher callback.

        Returns True if signal was handled (executed or intentionally skipped),
        False if there was a transient error (retry on next poll).
        """
        if EMERGENCY_STOP.exists():
            print("[OrderBot] Emergency stop — signal rejected")
            return True

        # ── Manage open DEMO virtual positions against the live market ─────
        # Called on every tick so simulated fills actually resolve (SL/TP),
        # compute realized PnL, and get appended to the ledger.
        self._manage_demo_positions()

        if not self.connector or not self.order_manager:
            print("[OrderBot] Not connected — signal rejected")
            return False

        symbol = signal.get("symbol", "").upper()
        direction = signal.get("direction", "SELL")
        trade = signal.get("trade", {})
        # Accept both old (flat) and new (nested) signal formats
        entry = trade.get("entry") or signal.get("entry_price") or signal.get("entry", 0)
        stop_loss = trade.get("stop_loss") or signal.get("stop_loss", 0)
        take_profit = trade.get("take_profit") or signal.get("take_profit", 0)
        sig_id = signal.get("signal_id", "?")

        # Defense-in-depth: reject zero-level signals even if watcher missed them
        if not entry or not stop_loss or not take_profit:
            self.signals_rejected += 1
            self._log(signal, "SKIPPED", f"zero levels e={entry} sl={stop_loss} tp={take_profit}")
            return True

        # ── Gate 1: Pair config ──────────────────────────────────────
        pair_cfg = self.pair_config.get(symbol, {})
        if not pair_cfg.get("allowed", True):
            print(f"[OrderBot] {symbol} is shadow-only — signal skipped")
            self.signals_rejected += 1
            self._log(signal, "SKIPPED", "shadow pair")
            return True

        lot_size = pair_cfg.get("lot_size", 0.08)

        # ── Gate 2: Daily PnL ────────────────────────────────────────
        risk = self.config.get_risk_config()
        max_daily_loss = risk.get("max_daily_loss", 50.0)
        self.daily_pnl = self._calculate_daily_pnl()
        if self.daily_pnl <= -max_daily_loss:
            print(f"[OrderBot] Daily loss limit reached: ${self.daily_pnl:.2f} "
                  f"(limit: ${max_daily_loss:.2f})")
            self.signals_rejected += 1
            self._log(signal, "SKIPPED", f"daily loss limit: ${self.daily_pnl:.2f}")
            return True

        # ── Gate 3: Duplicate position ───────────────────────────────
        positions = self.connector.get_positions(symbol)
        if positions:
            print(f"[OrderBot] {symbol} already has {len(positions)} open position(s) — signal skipped")
            self.signals_rejected += 1
            self._log(signal, "SKIPPED", "duplicate position")
            return True

        # ── Gate 4: Margin check ─────────────────────────────────────
        account = self.connector.get_account_info()
        margin_free = account.get("margin_free", 0)
        symbol_info = self.connector.get_symbol_info(symbol)
        if not symbol_info:
            print(f"[OrderBot] {symbol} not available")
            self.signals_rejected += 1
            return True

        action = "sell" if direction.upper() == "SELL" else "buy"

        try:
            margin_required = mt5.order_calc_margin(
                mt5.ORDER_TYPE_SELL if action == "sell" else mt5.ORDER_TYPE_BUY,
                symbol, lot_size, entry
            )
            if margin_required and margin_required > margin_free * 0.5:
                print(f"[OrderBot] Insufficient margin: need ${margin_required:.2f}, "
                      f"free ${margin_free:.2f}")
                self.signals_rejected += 1
                return True
        except Exception:
            pass  # order_calc_margin can fail on some symbols; proceed anyway

        # ── Execute ──────────────────────────────────────────────────
        order_params = {
            "symbol": symbol,
            "action": action,
            "lot_size": lot_size,
            "entry_price": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "comment": f"frival_{sig_id[-20:]}",
            "order_type": "MARKET",
            "risk_profile": self.config.get_trading_config().get("default_risk_profile", "MODERATE"),
        }

        print(f"[OrderBot] EXECUTING: {symbol} {action.upper()} {lot_size} lots")
        print(f"  Entry: {entry:.5f}  SL: {stop_loss:.5f}  TP: {take_profit:.5f}")

        # §6.1 diagnostics: measure latency and capture fill/spread/slippage.
        _t0 = time.time()
        try:
            result = self.order_manager.execute_order(order_params)
        except Exception as e:
            _t1 = time.time()
            print(f"[OrderBot] Execution error: {e}")
            diag = self._diagnostics(signal, symbol, entry, None, _t0, _t1)
            diag["execution_time_s"] = round(_t1 - _t0, 3)
            self._log(signal, "ERROR", str(e), **diag)
            return False
        _t1 = time.time()

        if result and result.get("success"):
            ticket = result.get("order")
            # DEMO mode: OrderManager returns order=0 by design (node 501-516).
            # Treat that as a REAL virtual fill: open a ledger position so the
            # paper account accumulates realized PnL (PORTFOLIO-DEMO-SPEC §3).
            demo_fill = bool(ticket is None or ticket == 0)
            if demo_fill:
                direction_l = "buy" if action.upper() == "BUY" else "sell"
                pos = open_virtual(
                    self.demo_positions, symbol, direction_l,
                    lot_size, entry, stop_loss, take_profit,
                    event_ts=datetime.now(timezone.utc).isoformat(),
                )
                print(f"[OrderBot] DEMO virtual fill opened — {pos.ticket}")
                diag = self._diagnostics(signal, symbol, entry, result, _t0, _t1)
                diag["execution_time_s"] = round(_t1 - _t0, 3)
                self._log(signal, "EXECUTED", f"ticket={pos.ticket} (virtual)", **diag)
                self.signals_executed += 1
                return True

            if ticket is None:
                self._log(signal, "FAILED", "success=True but no order id returned")
                self.signals_rejected += 1
                return True
            self.signals_executed += 1
            print(f"[OrderBot] Order placed — ticket: {ticket}")
            diag = self._diagnostics(signal, symbol, entry, result, _t0, _t1)
            diag["execution_time_s"] = round(_t1 - _t0, 3)
            self._log(signal, "EXECUTED", f"ticket={ticket}", **diag)

            # ── Break-Even-at-50% monitor (opt-in via settings.yaml) ────
            be_cfg = self.config.get_config("break_even") or {}
            if be_cfg.get("enabled", True) and not self.config.is_demo_mode():
                entry = signal.get("trade", {}).get("entry", entry)
                sl = signal.get("trade", {}).get("stop_loss", stop_loss)
                tp = signal.get("trade", {}).get("take_profit", take_profit)
                dr = direction.upper()
                try:
                    be_result = self.order_manager.monitor_break_even(
                        ticket=int(ticket), symbol=symbol,
                        entry_price=entry, stop_loss=sl, take_profit=tp,
                        direction="buy" if dr == "BUY" else "sell",
                        max_wait_seconds=be_cfg.get("max_wait_seconds", 600),
                        poll_interval=be_cfg.get("poll_interval_seconds", 30),
                    )
                    if be_result.get("triggered"):
                        print(f"[OrderBot] Break-even triggered: "
                              f"SL moved to {entry:.5f}")
                    else:
                        print(f"[OrderBot] Break-even: "
                              f"{be_result.get('reason', 'not triggered')}")
                except Exception as e:
                    print(f"[OrderBot] Break-even monitor error: {e} (non-fatal)")

            return True
        else:
            error_msg = result.get("error", "unknown") if result else "no result"
            print(f"[OrderBot] Order failed: {error_msg}")
            diag = self._diagnostics(signal, symbol, entry, result, _t0, _t1)
            diag["execution_time_s"] = round(_t1 - _t0, 3)
            self._log(signal, "FAILED", str(error_msg), **diag)
            self.signals_rejected += 1
            return True

    def _calculate_daily_pnl(self) -> float:
        """Calculate today's realized PnL from MT5 history."""
        try:
            today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
            deals = mt5.history_deals_get(today, datetime.now(timezone.utc))
            if deals is None:
                return 0.0
            return sum(d.profit for d in deals if abs(d.profit) < 50000)
        except Exception:
            return 0.0

    def _manage_demo_positions(self) -> None:
        """Advance open DEMO virtual positions against the latest tick.

        For each open virtual position, read the current bid/ask (live or, in
        demo, the last available quote), resolve SL/TP, compute realized USD + R,
        and append the closed trade to the ledger. Non-blocking/failure-tolerant:
        a transient tick read failure simply leaves the position open.
        """
        if not self.demo_positions:
            return
        for pos in list(self.demo_positions):
            if pos.status != "OPEN":
                continue
            try:
                price: Optional[float] = None
                if self.connector is not None:
                    tick = self.connector.get_symbol_tick(pos.symbol)
                    if tick:
                        price = float(getattr(tick, "ask", 0.0) or getattr(tick, "bid", 0.0) or 0.0) or None
                        if price is None and hasattr(tick, "get"):
                            price = float(tick.get("ask") or 0.0) or None
                if price is None or price <= 0.0:
                    continue
                closed = manage_open(self.demo_positions, price)
                for c in closed:
                    append_trade(DEMO_LEDGER_FILE, c)
                    print(f"[OrderBot] DEMO close {c.ticket} -> {c.exit_reason} "
                          f"pnl={c.realized_usd:+.2f} R={c.r:+.2f}")
            except Exception as e:
                print(f"[OrderBot] demo manage error ({pos.symbol}): {e}")

    def _log(self, signal: Dict, status: str, detail: str, **extra):
        """Write an execution log entry.

        `extra` carries §6.1 diagnostic fields (slippage, latency, spread-at-fill)
        when the status path measured them; otherwise they are simply absent.
        Additive only — never changes trading behavior.
        """
        os.makedirs(LOG_FILE.parent, exist_ok=True)
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "signal_id": signal.get("signal_id", "?"),
            "symbol": signal.get("symbol", "?"),
            "direction": signal.get("direction", "?"),
            "status": status,
            "detail": detail,
            "daily_pnl": round(self.daily_pnl, 2),
        }
        entry.update(extra)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    # ── §6.1 execution diagnostics (ROADMAP-2026-Q4 §6.1) ──────────────────────
    # Measures slippage, latency, and spread-at-fill per executed signal so the
    # cost model (_core/costs.py) can be upgraded from spread-only assumptions
    # to measured values. All fields are informational; nothing here gates orders.
    @staticmethod
    def _core_costs():
        """Lazily import the shared cost table (single source of truth).

        Mirrors dashboard/backend/tag_metrics.py: resolves fx-prival root and
        hooks ml-signal-service so `experiments._core.costs` is importable from
        the frival/ tree. Returns None (silently) if unavailable so diagnostics
        never break order execution.
        """
        try:
            import sys as _sys
            from pathlib import Path as _P

            root = _P(__file__).resolve().parents[2]  # .../fx-prival/
            ml = root / "ml-signal-service"
            if str(ml) not in _sys.path:
                _sys.path.insert(0, str(ml))
            from experiments._core import costs as _c
            return _c
        except Exception:
            return None

    @staticmethod
    def _signal_ts_utc(signal: Dict) -> Optional[datetime]:
        raw = signal.get("timestamp_utc") or signal.get("ts")
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(str(raw)[:19])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None

    def _diagnostics(self, signal: Dict, symbol: str, entry: float,
                     result: Optional[Dict], t0: float, t1: float) -> Dict:
        """Collect per-trade §6.1 metrics. Never raises on data gaps."""
        diag: Dict[str, Any] = {}
        signal_ts = self._signal_ts_utc(signal)
        if signal_ts is not None:
            sent_ts = datetime.fromtimestamp(t1, tz=timezone.utc)
            diag["latency_seconds"] = round(max(0.0, (sent_ts - signal_ts).total_seconds()), 2)
            diag["signal_ts_utc"] = signal_ts.isoformat()
            diag["sent_ts_utc"] = sent_ts.isoformat()

        pip_size = None
        try:
            tick = self.connector.get_symbol_tick(symbol)
        except Exception:
            tick = None
        if tick is not None and tick.get("spread") is not None:
            diag["spread_at_fill_price"] = round(float(tick["spread"]), 6)
            diag["bid_at_fill"] = round(float(tick["bid"]), 6)
            diag["ask_at_fill"] = round(float(tick["ask"]), 6)

        # pip size: shared cost table first, symbol info fallback
        core_costs = self._core_costs()
        pip_size = core_costs.PIP_SIZE_PX.get(symbol.upper()) if core_costs else None
        if pip_size is None:
            try:
                sym = self.connector.get_symbol_info(symbol)
                pip_size = sym.get("point", 1e-4)
            except Exception:
                pip_size = None

        if entry:
            diag["requested_entry"] = round(float(entry), 6)

        # backtest-assumed round-trip cost from the shared table (Issue C)
        if core_costs is not None:
            diag["cost_assumed_pips"] = core_costs.ROUND_TRIP_COST_PIPS.get(
                symbol.upper(), {}).get("ALL")
        else:
            diag["cost_assumed_pips"] = None

        if result:
            diag["retcode"] = result.get("retcode")
            fill = result.get("price")
            if fill is not None:
                diag["fill_price"] = round(float(fill), 6)
                if entry and pip_size:
                    # signed: positive = adverse fill for the traded direction
                    diag["slippage_price"] = round(float(fill) - float(entry), 6)
                    diag["slippage_pips"] = round((float(fill) - float(entry)) / pip_size, 3)
                if diag.get("spread_at_fill_price") is not None and pip_size:
                    diag["spread_at_fill_pips"] = round(
                        diag["spread_at_fill_price"] / pip_size, 3)
        return diag