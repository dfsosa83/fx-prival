# -*- coding: utf-8 -*-
"""Gold Rules Engine — main loop (design doc §3.1, §3.5, §3.6, §6).

Owns everything the pure engine does not: MT5 I/O, position management
modifications, journaling, state persistence, session accounting, and the
resilience wrapper.

Run via run_gold_rules.bat (double-click) or:
    python run_gold_rules.py            # live engine (settings: config.yaml)
    python run_gold_rules.py --dry      # dry-run: log-only, no orders

Design doc contract points implemented here:
  §3.1  loop ticks every `session.loop_tick_seconds` (60s); full state machine
        runs on every tick using the latest closed M15 bar (edge detection is
        inherently newest-bar; unchanged bars simply no-op)
  §3.4  reuses OrderManager.execute_order() (dynamic_sizing=False) and
        close_position(); BE/trail/invalidation are NEW non-blocking checks
  §3.5  resilience wrapper: catch/log/continue, hard-stop after N consecutive
  §3.6  gold session / maintenance-break handling
  §6    journal + state persistence + session reports
  §2.4.2  comment-tagged session PnL accounting (GOLD_RULES_v1)
  §2.4.1  concurrency gate across ALL XAUUSD positions
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

# ── Environment ────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))          # gold_rules/ on path (bias, levels, engine)
sys.path.insert(0, str(HERE.parent))   # frival/ on path (execution_bot reuse)

CONFIG_FILE = HERE / "config.yaml"
STATE_FILE = HERE / "state" / "engine_state.json"
JOURNAL_DIR = HERE / "journal"
CONFIG_DIR = HERE / "config"           # credentials.env + settings.yaml (ConfigManager)

import engine as eng_module            # noqa: E402

try:
    from execution_bot.core.config_manager import ConfigManager  # noqa: E402
    from execution_bot.core.mt5_connector import MT5Connector  # noqa: E402
    from execution_bot.core.order_manager import OrderManager  # noqa: E402
    EXEC_AVAILABLE = True
except Exception as e:  # pragma: no cover — MT5 not required for --dry
    print(f"[gold] WARNING: execution_bot import failed ({e}); dry-run only")
    ConfigManager = MT5Connector = OrderManager = None  # type: ignore
    EXEC_AVAILABLE = False


def load_config() -> dict:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_state(state: eng_module.EngineState, extra: dict | None = None) -> None:
    """Atomically persist engine state (§6.4). `extra` carries runner-only
    markers (last bar seen) so a restart can detect a frozen market instantly."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = state.to_dict()
    payload["updated_at"] = datetime.utcnow().isoformat() + "Z"
    if extra:
        payload.update(extra)
    tmp = STATE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os_replace(tmp, STATE_FILE)


def os_replace(src: Path, dst: Path) -> None:
    import os
    os.replace(str(src), str(dst))


def load_state() -> tuple[eng_module.EngineState, dict]:
    """Return (engine_state, runner_meta) — runner_meta holds last-bar markers
    for immediate market-pause detection after a restart."""
    if STATE_FILE.exists():
        try:
            raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            state = eng_module.EngineState.from_dict(raw)
            meta = {}
            for k in ("last_bar_time", "last_bar_seen_utc"):
                if k in raw:
                    meta[k] = raw[k]
            return state, meta
        except Exception:
            print("[gold] state file corrupt — starting fresh WATCH_ZONE")
    return eng_module.EngineState(), {}


def journal(dt: datetime, entry: dict) -> None:
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    file = JOURNAL_DIR / f"{dt.date().isoformat()}.jsonl"
    line = {
        **entry,
        "ts": dt.isoformat() + "Z",      # bar open time (BROKER SERVER zone, not UTC)
        "utc": datetime.utcnow().isoformat() + "Z",  # true wall-clock UTC for audits
    }
    with open(file, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, default=str) + "\n")


def session_pnl(comments: list, day: datetime) -> float:
    """Comment-tagged realized XAUUSD PnL for today (§2.4.2).

    Sums engine comments only (since Claim C, both `GOLD_RULES_v1` and
    `GOLD_RULES_C` are engine orders). Any manual gold trade (different
    comment) is excluded from this sum by design.
    """
    try:
        import MetaTrader5 as mt5
        start = datetime(day.year, day.month, day.day)
        deals = mt5.history_deals_get(start, start + timedelta(days=1))
        if not deals:
            return 0.0
        total = 0.0
        for d in deals:
            if d.symbol == "XAUUSD" and getattr(d, "comment", "") in comments:
                total += d.profit
        return float(total)
    except Exception:
        return 0.0


class GoldRunner:
    def __init__(self, dry: bool = False):
        self.cfg = load_config()
        self.engine = eng_module.GoldRulesEngine(self.cfg)
        self.state, self._state_meta = load_state()
        self.dry = dry
        self.comment = self.cfg.get("order", {}).get("comment", "GOLD_RULES_v1")
        # Both engine variants (A/B and Claim C) count toward the $50 daily cap.
        self._engine_comments = [self.comment,
                                 self.cfg.get("breakout", {}).get("comment", "GOLD_RULES_C")]

        res_cfg = self.cfg.get("resilience", {})
        self.max_consecutive_errors = int(res_cfg.get("max_consecutive_errors", 5))
        self.backoff = int(res_cfg.get("error_backoff_seconds", 60))
        self.tick = int(self.cfg.get("session", {}).get("loop_tick_seconds", 60))

        self.conn = None
        self.om = None
        self.cm = None
        self._market_paused = False
        self._silent_ticks = 0
        self._last_bar_key = None
        self._last_bar_seen_utc = None
        # ── startup-only cross-restart pause detection ────────────────────
        # The PREVIOUS run's last-seen bar + when it was first observed are
        # persisted in the state file. Stored separately from _last_bar_key so
        # the restart check below can compare against the OLD value, not the
        # live one (which is overwritten as soon as a new bar arrives).
        self._persisted_bar = self._state_meta.get("last_bar_time")
        self._persisted_bar_seen_utc = self._state_meta.get("last_bar_seen_utc")
        self._restart_check_done = False
        self._reported_no_bar = False
        self._previous_paused = False
        # Dry-run bookkeeping (simulates a single open position through IN_TRADE)
        self.dry_positions = 0
        self.dry_pnl = 0.0
        if not dry and EXEC_AVAILABLE:
            self.cm = ConfigManager(config_dir=str(CONFIG_DIR))
            self.conn = MT5Connector(self.cm)
            self.om = OrderManager(self.conn, self.cm)
        elif not dry:
            print("[gold] FATAL: execution_bot unavailable and --dry not set.")
            sys.exit(3)

    # ── MT5 wiring ─────────────────────────────────────────────────────────────
    def _ensure_mt5(self) -> bool:
        """Initialize MT5 read-only (needed for bar fetch even in dry mode)."""
        import MetaTrader5 as mt5
        if mt5.terminal_info() is not None:
            return True
        path = r"C:\Program Files\FPMarkets MT5 Terminal\terminal64.exe"
        if mt5.initialize(path=path):
            return True
        print(f"[gold] MT5 initialize failed: {mt5.last_error()}")
        return False

    def connect(self) -> bool:
        if self.dry:
            return self._ensure_mt5()
        try:
            if not self.conn.connect():
                return False
            info = self.conn.get_account_info()
            expected = str(self.cm.credentials.get("mt5_login", ""))
            if info and str(info.get("login")) != expected:
                print(f"[gold] LOGIN MISMATCH (§1.3.1 R4): connected {info.get('login')} "
                      f"!= configured {expected} — refusing to trade")
                self.conn.disconnect()
                return False
            print(f"[gold] connected account {info.get('login')} balance {info.get('balance')}")
            return True
        except Exception as e:
            print(f"[gold] connect error: {e}")
            return False

    def fetch_bars(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Fetch M15/M30/H1 CLOSED bars (design §3.2). Returns (m15, m30, h1).

        G1 enforcement (§2.3): `copy_rates_from_pos(pos=0)` returns the
        CURRENT FORMING (open) bar as the last row — verified live on this
        broker (M15: last row age 3 min = still open). Evaluating an open
        candle violates the single most important rule of the playbook
        ("Vela M15 abierta → No entras"), so the last row is dropped when its
        open time is younger than one full period vs the server clock. Only
        fully closed bars reach the engine.
        """
        import MetaTrader5 as mt5
        max_points = {"M15": 1000, "M30": 400, "H1": 200}
        period_sec = {"M15": 15 * 60, "M30": 30 * 60, "H1": 60 * 60}
        server_now = None
        try:
            t = mt5.symbol_info_tick("XAUUSD")
            if t is not None:
                server_now = t.time
        except Exception:
            pass
        frames = {}
        for name, tf in (("M15", mt5.TIMEFRAME_M15), ("M30", mt5.TIMEFRAME_M30), ("H1", mt5.TIMEFRAME_H1)):
            # Fetch one extra bar so dropping the forming row never starves history
            rates = mt5.copy_rates_from_pos("XAUUSD", tf, 0, max_points[name] + 1)
            if rates is None or len(rates) == 0:
                raise RuntimeError(f"MT5 returned no XAUUSD {name}: {mt5.last_error()}")
            df = pd.DataFrame(rates)
            if server_now is not None:
                closed = df["time"] <= (server_now - period_sec[name])
                df = df[closed]
            else:
                # server clock unavailable: conservative G1 fallback — drop the
                # newest bar entirely rather than risk acting on an open candle
                df = df.iloc[:-1]
            if len(df) == 0:
                raise RuntimeError(f"MT5 returned no CLOSED XAUUSD {name} bars")
            df["datetime"] = pd.to_datetime(df["time"], unit="s")
            df.drop(columns=["time", "spread", "real_volume"], inplace=True, errors="ignore")
            df.rename(columns={"tick_volume": "volume"}, inplace=True)
            frames[name] = df[["datetime", "open", "high", "low", "close", "volume"]].reset_index(drop=True)
        return frames["M15"], frames["M30"], frames["H1"]

    def positions_open(self) -> int:
        """§2.4.1: count ALL XAUUSD positions regardless of comment."""
        if self.dry:
            return self.dry_positions
        pos = self.conn.get_positions("XAUUSD")
        return len(pos) if pos else 0

    # ── order actions ──────────────────────────────────────────────────────────
    def execute_order(self, order: dict) -> dict:
        if self.dry:
            self.dry_positions = 1  # Gate 3 simulation: one slot now occupied
            self.dry_orders = getattr(self, "dry_orders", []) + [order]
            print(f"[gold][DRY] would send: {order}")
            return {"success": True, "dry": True, "order": 0}
        return self.om.execute_order(order)

    def modify_sltp(self, ticket: int, symbol: str, sl: float, tp: float) -> bool:
        """§3.4: non-blocking position modification (BE/trail)."""
        if self.dry:
            print(f"[gold][DRY] would modify {ticket}: sl={sl:.2f} tp={tp:.2f}")
            return True
        import MetaTrader5 as mt5
        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": round(sl, 2),
            "tp": round(tp, 2),
        }
        res = mt5.order_send(req)
        ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
        if not ok:
            print(f"[gold] modify failed: {res.retcode if res is not None else mt5.last_error()}")
        return ok

    def close_position(self, ticket: int) -> dict:
        if self.dry:
            self.dry_positions = 0
            print(f"[gold][DRY] would close {ticket}")
            return {"success": True, "dry": True}
        return self.om.close_position(ticket)

    # ── one evaluation cycle ───────────────────────────────────────────────────
    def cycle(self) -> str:
        """Evaluate on the latest closed M15 bar. Returns 'ok' | 'error'."""
        # Ensure MT5 is initialized: live via connector, dry via _ensure_mt5.
        # (Bugfix: previously the `or` short-circuit skipped connect() in dry
        #  mode, leaving MT5 uninitialized so the session check idled forever.)
        if self.dry:
            if not self._ensure_mt5():
                return "error"
        elif not (self.conn and self.conn.validate_connection()):
            if not self.connect():
                return "error"

        # §3.6 market-open check.
        # NOTE: `is_market_open()` (trade_mode != DISABLED) returns True on
        # FPMarkets gold even during the daily 1h maintenance halt — it is not
        # sufficient alone. Bar-freshness detection below catches the halt:
        # gold's M15 feed freezes during the break, so "no new bar for 20 min"
        # means paused. This handles the daily halt, weekends and holidays
        # uniformly, without hardcoding a UTC window.
        market_open = True
        if self.dry:
            try:
                import MetaTrader5 as mt5
                si = mt5.symbol_info("XAUUSD")
                if si is None or si.trade_mode == 0:
                    market_open = False
            except Exception:
                market_open = False
        elif not self.conn.is_market_open("XAUUSD"):
            market_open = False

        try:
            m15, m30, h1 = self.fetch_bars()
        except Exception as e:
            print(f"[gold] fetch error: {e}")
            return "error"

        last_time = m15["datetime"].iloc[-1]
        bar_key = str(last_time)

        # Bar-freshness: if no new M15 bar has closed for ~20 min, the market
        # is in the maintenance halt / weekend / holiday → idle, don't evaluate.
        #
        # Immediate-detection on restart: the previous run's last bar + the UTC
        # instant it was first seen are persisted in the state file. If we come
        # up and the SAME bar is still the newest AND it was first seen more
        # than ~20 min ago in UTC terms, the market has been frozen across the
        # restart — go straight to paused instead of burning 20 startup ticks.
        now_utc = datetime.utcnow()
        new_bar = (bar_key != getattr(self, "_last_bar_key", None))
        if new_bar:
            self._silent_ticks = 0
            self._last_bar_key = bar_key
            self._last_bar_seen_utc = now_utc.isoformat() + "Z"
        else:
            self._silent_ticks = getattr(self, "_silent_ticks", 0) + 1
            # Informational notice ONLY once a bar is genuinely overdue.
            # At tick 2 this fires every 15 min during LIVE trading (normal gap
            # between M15 closes) — pure noise. At tick 16 the next bar is ~1 min
            # late, so a quiet market / start of a halt is plausible; the real
            # pause still latches at 20.
            if self._silent_ticks == 16 and not self._reported_no_bar:
                self._reported_no_bar = True
                print(f"[gold] no new M15 bar since {bar_key} — bar overdue; "
                      f"likely entering the daily halt / weekend. Engine stays "
                      f"alive and resumes automatically on the next bar.")

        if new_bar:
            self._reported_no_bar = False

        # ── STARTUP-ONLY cross-restart pause detection ─────────────────────────
        # If the previous run ended with bar X (frozen market) and we come back
        # to find the SAME bar X still the newest AND it was first observed more
        # than ~20 min ago (in UTC), the market has been frozen across the
        # restart — go straight to paused instead of burning 20 startup ticks.
        # Runs once: `_restart_check_done` prevents re-evaluating this against
        # later bars, which previously re-paused the engine on every new bar
        # after the first reopen (persisted_bar was being overwritten by the
        # live _last_bar_key before the comparison).
        if not self._restart_check_done:
            self._restart_check_done = True
            if self._persisted_bar == bar_key and self._persisted_bar_seen_utc:
                try:
                    seen = datetime.fromisoformat(self._persisted_bar_seen_utc.replace("Z", "+00:00"))
                    seen_utc = seen.replace(tzinfo=None)
                    if (now_utc - seen_utc).total_seconds() > 20 * 60:
                        self._market_paused = True
                        self._previous_paused = True
                        self._reported_no_bar = True
                        return "ok"
                except ValueError:
                    pass

        if self._silent_ticks >= 20 or not market_open:
            self._market_paused = True
            self._previous_paused = True
            self._reported_no_bar = True
            return "ok"  # idle; keep-alive tick in run() reports state

        # ── market transition: leave the paused state on a fresh bar ───────────
        was_paused = self._market_paused
        self._market_paused = False
        if new_bar and (was_paused or self._previous_paused):
            self._previous_paused = False
            print(f"[gold] MARKET RESUMED — new M15 bar {last_time} detected, "
                  f"resuming live evaluation.")
        else:
            self._previous_paused = False

        try:
            import MetaTrader5 as mt5
            tick = mt5.symbol_info_tick("XAUUSD")
            bid = float(tick.bid) if tick else float(m15["close"].iloc[-1])
            ask = float(tick.ask) if tick else bid + 0.2
        except Exception:
            bid = float(m15["close"].iloc[-1])
            ask = bid + 0.2

        pnl = session_pnl(self._engine_comments, datetime.utcnow()) if not self.dry else self.dry_pnl

        snap = eng_module.Snapshot(
            m15_df=m15, m30_df=m30, h1_df=h1,
            utc_now=last_time + timedelta(minutes=16),
            bid=bid, ask=ask,
            open_positions=self.positions_open(),
            today_realized_pnl=pnl,
        )

        try:
            new_state, dec = self.engine.evaluate(snap, self.state)
        except Exception as e:
            print(f"[gold] engine error: {e}")
            journal(datetime.utcnow(), {"action": "ENGINE_ERROR", "error": str(e)})
            return "error"

        self.state = new_state
        self.state.last_action = dec.action
        self.state.last_reason = dec.reason
        save_state(self.state, extra={"last_bar_time": bar_key,
                                      "last_bar_seen_utc": self._last_bar_seen_utc})

        # journal every decision BEFORE acting (action lifecycle §6.1)
        journal(last_time.to_pydatetime(), {**dec.to_dict(), "bid": bid, "ask": ask, "pnl": pnl})

        # ── act on the decision ─────────────────────────────────────────────
        if dec.action == eng_module.ENTRY and dec.order:
            result = self.execute_order(dec.order)
            journal(last_time.to_pydatetime(), {"action": "ORDER_SENT", "result": result})
            if result.get("success") and self.state.active_trade:
                self.state.active_trade["ticket"] = result.get("order", result.get("deal", 0))
                save_state(self.state, extra={"last_bar_time": bar_key,
                                              "last_bar_seen_utc": self._last_bar_seen_utc})
            print(f"[gold] >>> ENTRY ORDER SENT: {dec.order}")
            print(f"[gold] >>> result: {result}")

        elif dec.action in (eng_module.BE, eng_module.TRAIL) and self.state.active_trade:
            ticket = self.state.active_trade.get("ticket")
            sl = self.state.active_trade.get("sl")
            tp1 = self.state.active_trade.get("tp1")
            if ticket and sl:
                ok = self.modify_sltp(ticket, self.cfg.get("symbol", "XAUUSD"), float(sl), float(tp1 or 0.0))
                journal(last_time.to_pydatetime(), {"action": dec.action, "ok": ok, "sl": sl, "tp": tp1})
                print(f"[gold] {dec.action} on ticket {ticket}: SL -> {sl:.2f}, TP {tp1 or '--'} ({'OK' if ok else 'FAILED'})")

        elif dec.action == eng_module.INVALIDATE and self.state.active_trade:
            ticket = self.state.active_trade.get("ticket")
            if ticket:
                result = self.close_position(ticket)
                journal(last_time.to_pydatetime(), {"action": "CLOSE_POSITION", "ticket": ticket, "result": result})
                print(f"[gold] >>> INVALIDATED — closing ticket {ticket}: {result}")

# ── heartbeat: one visible line per NEW completed M15 bar ───────────
        # Uses the upstream `new_bar` flag (freshness block already updated
        # _last_bar_key); the MARKET RESUMED announcement is emitted in the
        # transition block above, so only the plain heartbeat prints here.
        if new_bar:
            print(f"[gold] [{datetime.utcnow().strftime('%H:%M:%S')}Z] bar {last_time} "
                  f"| bid {bid:.2f} | {self.state.state} | {self.state.h1_bias} "
                  f"| {dec.reason}")

        return "ok"

    # ── main loop ─────────────────────────────────────────────────────────────
    def run(self):
        print("=" * 60)
        print("  Gold Rules Engine — XAUUSD (EXP-2026-03-RULEENGINE)")
        print(f"  mode: {'DRY-RUN (log-only, no orders)' if self.dry else 'LIVE'}")
        print(f"  config: {CONFIG_FILE}")
        print("=" * 60)

        if not self.dry:
            if not self.connect():
                print("[gold] cannot connect to MT5 — exit. Start the FPMarkets terminal.")
                sys.exit(1)

        consecutive = 0
        last_alive_print = time.time()
        print("[gold] entering loop; Ctrl+C to stop")
        # Immediate recovered-state confirmation: proves the process is alive
        # from second zero (the 10-min keep-alive covers longer idle stretches).
        trade_info = ""
        if self.state.active_trade:
            trade_info = f", open trade {self.state.active_trade.get('ticket')}"
        # _persisted_bar (from the state file) is the last bar the engine
        # actually processed before this launch; _last_bar_key gets reset to
        # None at startup and is only filled when the first new bar is seen.
        shown_bar = self._persisted_bar or "none yet (first launch)"
        print(f"[gold] resumed: {self.state.state} | bias {self.state.h1_bias} | "
              f"last bar {shown_bar}{trade_info}")
        print("[gold] waiting for a confirmed setup (WATCH_ZONE → break → retest → gates). "
              "You will see a heartbeat on every new M15 bar.")
        while True:
            try:
                start = time.time()
                result = self.cycle()
                if result == "error":
                    consecutive += 1
                    print(f"[gold][{datetime.utcnow().isoformat()}] cycle error "
                          f"({consecutive}/{self.max_consecutive_errors})")
                    if consecutive >= self.max_consecutive_errors:
                        print("[gold] too many consecutive errors — HARD STOP (§3.5)")
                        sys.exit(2)
                    time.sleep(self.backoff)
                else:
                    consecutive = 0
                    # keep-alive tick: proves the process is alive even when the
                    # market is closed (weekend/halt) and no bar changes occur
                    if time.time() - last_alive_print > 600:
                        last_alive_print = time.time()
                        paused = getattr(self, "_market_paused", False)
                        status = "MARKET PAUSED (daily halt/weekend — engine idle, resumes automatically)" if paused else "ALIVE"
                        print(f"[gold] [{datetime.utcnow().strftime('%H:%M:%S')}Z] {status} — "
                              f"state {self.state.state}, bias {self.state.h1_bias}, "
                              f"positions {self.positions_open()}, session PnL "
                              f"{session_pnl(self._engine_comments, datetime.utcnow()) if not self.dry else self.dry_pnl:.2f}")
            except KeyboardInterrupt:
                print("\n[gold] stopped by user — state persisted, resumes next launch")
                break
            except Exception as e:
                print(f"[gold] unhandled cycle exception: {e}")
                consecutive += 1
                if consecutive >= self.max_consecutive_errors:
                    print("[gold] too many consecutive errors — HARD STOP (§3.5)")
                    sys.exit(2)
                time.sleep(self.backoff)

            elapsed = time.time() - start
            time.sleep(max(1.0, self.tick - elapsed))


def main():
    ap = argparse.ArgumentParser(description="Gold Rules Engine (XAUUSD)")
    ap.add_argument("--dry", action="store_true", help="dry-run: log decisions only, no orders")
    args = ap.parse_args()
    GoldRunner(dry=args.dry).run()


if __name__ == "__main__":
    main()