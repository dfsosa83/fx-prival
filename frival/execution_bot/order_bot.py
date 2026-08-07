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
from core.mt5_connector import MT5Connector
from core.order_manager import OrderManager

LOG_FILE = Path(__file__).resolve().parent / "data" / "execution_log.jsonl"
EMERGENCY_STOP = Path(__file__).resolve().parents[1] / "data" / "emergency_stop.txt"


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

        try:
            result = self.order_manager.execute_order(order_params)
        except Exception as e:
            print(f"[OrderBot] Execution error: {e}")
            self._log(signal, "ERROR", str(e))
            return False

        if result and result.get("success"):
            self.signals_executed += 1
            ticket = result.get("order", "?")
            print(f"[OrderBot] Order placed — ticket: {ticket}")
            self._log(signal, "EXECUTED", f"ticket={ticket}")
            return True
        else:
            error_msg = result.get("error", "unknown") if result else "no result"
            print(f"[OrderBot] Order failed: {error_msg}")
            self._log(signal, "FAILED", str(error_msg))
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

    def _log(self, signal: Dict, status: str, detail: str):
        """Write an execution log entry."""
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
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")