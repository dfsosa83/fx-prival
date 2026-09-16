# -*- coding: utf-8 -*-
"""Gold Rules state machine — design doc §2.2–§2.7.

Pure, deterministic engine. No MT5, no I/O. Every evaluation takes a
Snapshot (closed bars + market context) plus the persisted EngineState and
returns (new_state, decision). The loop/orchestrator (run_gold_rules.py)
owns MT5, order placement, position queries, and journaling; it treats this
module as the decision authority.

State flow (design doc §2.2, corrected single-direction arming):

    WATCH_ZONE --break-through close--> WAIT_CANDLE_CLOSE --retest reject close--> CONFIRMED
    WATCH_ZONE --rejection wick close--> CONFIRMED
    CONFIRMED  --next close breaks confirm-candle extreme--> ENTRY_READY
    ENTRY_READY --gates pass-> market entry--> IN_TRADE
    IN_TRADE   --BE-50 / structural trail / invalidation / TP or position-close--> DONE
    DONE -> WATCH_ZONE
    Any state, level breached per §2.7 -> INVALIDATED (closes position)

Deterministic definitions implemented here (exact references to the contract):
  - G1 §2.3: only act on completed M15 bars (_bar_closed()).
  - G2 §2.3: rejection wick is NOT a signal; next close must break the
    confirmation candle's trade-side extreme (SELL: below its low; BUY: above
    its high) — operational reading of "breaks the wick's local extreme".
  - G3 §2.3: entry never precedes the justifying close; ENTRY_READY is
    consumed by a market order after the triggering close.
  - Gates §2.4: location, R:R>=1.5, risk ($25 / 1-position / -$50 day).
  - SL buffer §2.7.1: hard SL sits beyond the invalidation level.
  - Management §2.6: M1 BE-50, M2 structural trail, M4 no-averaging.
  - Timeouts: WAIT_CANDLE_CLOSE dies after pending_retest_max_bars_m15;
    CONFIRMED dies after confirm_max_bars_m15 (config).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

import bias as bias_mod
import levels as levels_mod

# ── State names ────────────────────────────────────────────────────────────────
WATCH_ZONE = "WATCH_ZONE"
WAIT_CANDLE_CLOSE = "WAIT_CANDLE_CLOSE"
CONFIRMED = "CONFIRMED"
ENTRY_READY = "ENTRY_READY"
IN_TRADE = "IN_TRADE"
INVALIDATED = "INVALIDATED"
DONE = "DONE"

# ── Actions (journal §6.1) ─────────────────────────────────────────────────────
NONE = "NONE"
WATCH = "WATCH"
CONFIRM = "CONFIRM"
ENTRY = "ENTRY"
BE = "BE"
TRAIL = "TRAIL"
INVALIDATE = "INVALIDATE"
CLOSE = "CLOSE"
HALT = "HALT"
DROP = "DROP"
ERROR = "ERROR"

VALID_STATES = {WATCH_ZONE, WAIT_CANDLE_CLOSE, CONFIRMED, ENTRY_READY, IN_TRADE, INVALIDATED, DONE}


@dataclass
class EngineState:
    """Persisted engine state (design doc §6.4 schema)."""
    state: str = WATCH_ZONE
    h1_bias: str = bias_mod.FLAT
    direction: Optional[str] = None            # "buy" | "sell"
    watched_level: Optional[Dict[str, Any]] = None
    broken_level: Optional[Dict[str, Any]] = None   # variant-B break (awaiting retest)
    confirm_candle: Optional[Dict[str, Any]] = None  # {time, extreme, side}
    timeout_bars: int = 0                       # bars elapsed in current sub-state
    active_trade: Optional[Dict[str, Any]] = None   # {ticket, entry, sl, tp1, tp2, invalidation, be_triggered, comment}
    daily_halted: bool = False
    last_action: str = NONE
    last_reason: str = ""
    updated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "h1_bias": self.h1_bias,
            "direction": self.direction,
            "watched_level": self.watched_level,
            "broken_level": self.broken_level,
            "confirm_candle": self.confirm_candle,
            "timeout_bars": self.timeout_bars,
            "active_trade": self.active_trade,
            "daily_halted": self.daily_halted,
            "last_action": self.last_action,
            "last_reason": self.last_reason,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "EngineState":
        if not d:
            return cls()
        return cls(
            state=d.get("state", WATCH_ZONE),
            h1_bias=d.get("h1_bias", bias_mod.FLAT),
            direction=d.get("direction"),
            watched_level=d.get("watched_level"),
            broken_level=d.get("broken_level"),
            confirm_candle=d.get("confirm_candle"),
            timeout_bars=d.get("timeout_bars", 0),
            active_trade=d.get("active_trade"),
            daily_halted=d.get("daily_halted", False),
            last_action=d.get("last_action", NONE),
            last_reason=d.get("last_reason", ""),
            updated_at=d.get("updated_at", ""),
        )


@dataclass
class Snapshot:
    """Everything the engine needs to decide on ONE completed M15 bar."""
    m15_df: pd.DataFrame                  # closed M15 bars, oldest -> newest
    m30_df: pd.DataFrame                  # closed M30 bars
    h1_df: pd.DataFrame                   # closed H1 bars
    utc_now: datetime
    bid: float
    ask: float
    open_positions: int = 0               # count of XAUUSD positions (any comment)
    today_realized_pnl: float = 0.0       # gold engine's own comment-tagged PnL (§2.4.2)

    def last_bar(self) -> pd.Series:
        return self.m15_df.iloc[-1]


@dataclass
class Decision:
    """Decision + journal fields emitted by one evaluation (§6.1)."""
    action: str = NONE
    reason: str = ""
    state: str = WATCH_ZONE
    level_info: Dict[str, Any] = field(default_factory=dict)
    gate_results: Dict[str, Any] = field(default_factory=dict)
    order: Optional[Dict[str, Any]] = None   # filled only when action == ENTRY
    state_changes: Dict[str, Any] = field(default_factory=dict)  # mutations for journal

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "state": self.state,
            "levels": self.level_info,
            "gate_results": self.gate_results,
        }


class GoldRulesEngine:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.symbol = cfg.get("symbol", "XAUUSD")
        bias_cfg = cfg.get("bias", {})
        self.ema_fast = int(bias_cfg.get("ema_fast", 20))
        self.ema_slow = int(bias_cfg.get("ema_slow", 50))

        levels_cfg = cfg.get("levels", {})
        self.lookback_m30 = int(levels_cfg.get("lookback_bars_m30", 200))
        self.fractal_wing = int(levels_cfg.get("fractal_wing", 2))
        self.merge_atr_mult = float(levels_cfg.get("merge_distance_atr_mult", 0.5))
        self.pending_retest_max_bars = int(levels_cfg.get("pending_retest_max_bars_m15", 20))
        self.confirm_max_bars = int(levels_cfg.get("confirm_max_bars_m15", 3))

        gates_cfg = cfg.get("gates", {})
        self.loc_tol_atr = float(gates_cfg.get("location_tolerance_atr_mult", 0.15))
        self.loc_tol_min = float(gates_cfg.get("location_tolerance_min_usd", 1.00))
        self.min_rr = float(gates_cfg.get("min_rr", 1.5))

        risk_cfg = cfg.get("risk", {})
        self.fixed_lot = float(risk_cfg.get("fixed_lot", 0.01))
        self.max_risk_usd = float(risk_cfg.get("max_risk_usd", 25.0))
        self.max_positions = int(risk_cfg.get("max_concurrent_positions", 1))
        self.daily_loss_cap = float(risk_cfg.get("daily_loss_cap_usd", 50.0))
        self.sl_buffer_atr = float(risk_cfg.get("sl_buffer_atr_mult", 0.05))
        self.sl_buffer_min = float(risk_cfg.get("sl_buffer_min_usd", 0.30))
        self.contract_size = float(risk_cfg.get("contract_size", 100.0))

        mgmt_cfg = cfg.get("management", {})
        self.be_fraction = float(mgmt_cfg.get("be_trigger_fraction", 0.5))

        candles_cfg = cfg.get("candles", {})
        self.solid_body_frac = float(candles_cfg.get("solid_body_min_fraction", 0.30))

        order_cfg = cfg.get("order", {})
        self.comment = order_cfg.get("comment", "GOLD_RULES_v1")

        # ── Claim C — breakout-continuation variant (design doc v1.4) ─────
        # A SECOND, separate trigger: when price closes (solid body) THROUGH a
        # structural level in the direction of the H1 bias, enter at market
        # immediately — riding the momentum instead of waiting for a retest.
        # Same atomics as A/B (0.01 lot, $25 risk, $50/day, 1 position) but a
        # different order comment so per-variant PnL attribution is clean.
        breakout_cfg = cfg.get("breakout", {})
        self.breakout_enabled = bool(breakout_cfg.get("enabled", False))
        self.breakout_comment = breakout_cfg.get("comment", "GOLD_RULES_C")
        self.breakout_min_rr = float(breakout_cfg.get("min_rr", self.min_rr))
        # breakout entry steps ONE level beyond the broken level (risk = the
        # just-broken level plus the SL buffer) so a failed break costs ~1R.
        self.breakout_rr_enforce = bool(breakout_cfg.get("rr_enforce", True))

    # ── helpers ────────────────────────────────────────────────────────────────

    def _bar_closed(self, bar_time, utc_now: datetime) -> bool:
        """G1 §2.3: no action on an open candle."""
        return (utc_now - pd.Timestamp(bar_time)).total_seconds() >= 14 * 60

    def _bar_edge_event(self, bar, level_price: float, direction: str) -> Optional[str]:
        """Return 'break' / 'rejection' / None for a closed bar vs the armed
        level price (design doc §2.2 for WATCH_ZONE, variant B steps 1 and
        variant R step 1). Edge detection runs BEFORE the consumed check so the
        break bar itself transitions the setup."""
        if direction == "sell":
            if self._solid(bar) and bar["close"] > level_price:
                return "break"
            if bar["high"] > level_price and bar["close"] < level_price:
                return "rejection"
        else:
            if self._solid(bar) and bar["close"] < level_price:
                return "break"
            if bar["low"] < level_price and bar["close"] > level_price:
                return "rejection"
        return None

    def _held_level_valid(self, held: dict, levels_df: pd.DataFrame) -> bool:
        """True if the held level still exists in the current level set and is
        not consumed. A consumed level ends the setup (§2.1.2 rule 3)."""
        if levels_df is None or levels_df.empty:
            return False
        price, kind = held.get("price"), held.get("kind")
        rows = levels_df[(levels_df["price"] == price) & (levels_df["kind"] == kind)]
        if rows.empty:
            return False
        return bool(rows.iloc[0]["consumed"] is False)

    def _solid(self, bar) -> bool:
        return levels_mod._is_solid_body(
            bar["open"], bar["close"], bar["high"], bar["low"], self.solid_body_frac
        )

    def _loc_tol(self, atr_m15: float) -> float:
        if atr_m15 != atr_m15 or atr_m15 is None:  # NaN or None
            return self.loc_tol_min
        return max(self.loc_tol_atr * atr_m15, self.loc_tol_min)

    # ── entry/structure computation ────────────────────────────────────────────

    def _compute_bias_and_levels(self, snap: Snapshot):
        h1_bias = bias_mod.compute_h1_bias(snap.h1_df, self.ema_fast, self.ema_slow)
        res = levels_mod.build_active_levels(
            snap.m30_df,
            lookback=self.lookback_m30,
            merge_atr_mult=self.merge_atr_mult,
        )
        levels_df = levels_mod.active_level_status(
            res["levels"], snap.m15_df, self.solid_body_frac
        )
        atr_m30 = res["atr_m30"]
        return h1_bias, levels_df, atr_m30

    def _entry_metrics(self, snap: Snapshot, direction: str, watched_level_price: float,
                       levels_df: pd.DataFrame, atr_m15: float):
        """Build the entry math: entry, SL (buffered), TP1, invalidation, R:R,
        and $ risk. Direction must match the armed level side.

        §2.7: the invalidation level is the setup's structural level itself —
        the just-broken level being retested (Variant B) or the rejection level
        (Variant R). The broker SL sits a buffer beyond it (§2.7.1).
        TP1 is the nearest unconsumed swing point beyond entry (§2.6.1).
        """
        entry = snap.ask if direction == "buy" else snap.bid
        # NaN guard: ATR needs 15+ bars. If invalid, fall back to the floors so
        # the SL-buffer math never produces NaN orders (gates still fail-safe).
        if atr_m15 != atr_m15:
            sl_buffer = self.sl_buffer_min
        else:
            sl_buffer = max(self.sl_buffer_atr * atr_m15, self.sl_buffer_min)

        if direction == "buy":
            invalidation = watched_level_price
            tp = levels_mod.nearest_swing_above(levels_df, entry)
            if tp is None:
                return None
            sl = invalidation - sl_buffer
            sl = min(sl, entry)  # defensive clamp: never above entry
            risk_dist = entry - sl
            reward_dist = tp["price"] - entry
        else:
            invalidation = watched_level_price
            tp = levels_mod.nearest_swing_below(levels_df, entry)
            if tp is None:
                return None
            sl = invalidation + sl_buffer
            sl = max(sl, entry)  # defensive clamp: never below entry
            risk_dist = sl - entry
            reward_dist = entry - tp["price"]

        if risk_dist <= 0 or reward_dist <= 0:
            return None

        risk_usd = risk_dist * self.contract_size * self.fixed_lot
        rr = reward_dist / risk_dist
        return {
            "entry": entry,
            "sl": sl,
            "tp1": tp["price"],
            "tp2": None,  # §2.6.1: next beyond TP1; filled by orchestrator/engine later
            "invalidation": invalidation,
            "risk_dist": risk_dist,
            "reward_dist": reward_dist,
            "risk_usd": risk_usd,
            "rr": rr,
        }

    def _run_gates(self, snap: Snapshot, metrics: dict, min_rr: float | None = None) -> Dict[str, Any]:
        """All three hard gates §2.4. No resize, no relax.

        `min_rr` overrides the A/B default (used by Claim C, which has its
        own R:R requirement from the breakout config).
        """
        rr_threshold = min_rr if min_rr is not None else self.min_rr
        loc = bool(metrics["loc_ok"])
        rr = bool(metrics["rr"] >= rr_threshold)
        risk = bool(metrics["risk_usd"] <= self.max_risk_usd)
        concurrency = bool(snap.open_positions < self.max_positions)
        day = bool(snap.today_realized_pnl > -self.daily_loss_cap) and not (
            snap.today_realized_pnl <= -self.daily_loss_cap
        )
        return {
            "location": loc,
            "rr": rr,
            "risk": risk,
            "concurrency": concurrency,
            "daily": day,
            "pass": all([loc, rr, risk, concurrency, day]),
        }

    # ── state machine ──────────────────────────────────────────────────────────

    def evaluate(self, snap: Snapshot, state: EngineState) -> tuple[EngineState, Decision]:
        dec = Decision()
        bar = snap.last_bar()
        stable = state

        if not self._bar_closed(bar["datetime"], snap.utc_now):
            dec.action = NONE
            dec.reason = "G1: M15 candle still open — no action"
            dec.state = stable.state
            return stable, dec

        try:
            h1_bias, levels_df, atr_m30 = self._compute_bias_and_levels(snap)
            atr_m15 = levels_mod.compute_atr(snap.m15_df)
        except Exception as e:  # defensive: a data hiccup must not crash the loop
            stable.last_action = ERROR
            stable.last_reason = f"indicator error: {e}"
            dec.action = ERROR
            dec.reason = stable.last_reason
            dec.state = stable.state
            return stable, dec

        stable.h1_bias = h1_bias

        # ── IN_TRADE: management first (§2.6 M1/M2, §2.7 invalidation) ──
        if stable.state == IN_TRADE and stable.active_trade:
            new_state, decision = self._manage_trade(snap, stable, dec, levels_df, atr_m15)
            decision.state = new_state.state
            return new_state, decision

        # ── terminal/stale states ─────────────────────────────────────────────
        if stable.state in (DONE, INVALIDATED):
            stable.state = WATCH_ZONE
            stable.active_trade = None
            stable.direction = None
            dec.action = NONE
            dec.reason = "terminal state cleared -> WATCH_ZONE"
            dec.state = stable.state
            return stable, dec

        # ── Bias flip voids any ongoing setup (S4.1) ──────────────────────────
        # Previous bias must be saved BEFORE assignment (bug fix: was comparing
        # the value against itself).
        prev_bias = stable.h1_bias
        stable.h1_bias = h1_bias
        if prev_bias and prev_bias != bias_mod.FLAT and prev_bias != h1_bias:
            if stable.state not in (WATCH_ZONE, IN_TRADE, INVALIDATED):
                stable.state = WATCH_ZONE
                stable.direction = None
                stable.broken_level = None
                stable.confirm_candle = None
                stable.watched_level = None
                dec.action = DROP
                dec.reason = "H1 bias flipped — pre-trade setup void (S4.1)"
                dec.state = stable.state
                stable.last_action = dec.action
                stable.last_reason = dec.reason
                return stable, dec

        # ── Claim C — breakout-continuation trigger (checked first) ─────────
        # A clean trend-aligned breakout fires immediately (market entry at the
        # closing bar), ahead of the A/B retest-waiting path. If C fills a
        # trade, it consumes the level and WATCH clears; A/B never sees it.
        if stable.state == WATCH_ZONE:
            breakout_state, breakout_dec = self._check_breakout(
                snap, stable, dec, levels_df, atr_m15)
            if breakout_dec.action == ENTRY:
                breakout_dec.state = breakout_state.state
                stable.last_action = breakout_dec.action
                stable.last_reason = breakout_dec.reason
                return breakout_state, breakout_dec

        # ── WATCH_ZONE with an armed level: edge events first ──────────────────
        # CRITICAL ordering: edge detection (break/rejection) runs against the
        # HELD level BEFORE any re-arm or consumed check. A solid-body break
        # bar consumes the level in the SAME bar it triggers the transition —
        # checking "is the level still intact" first would discard the break
        # and the setup would never leave WATCH_ZONE.
        if stable.state == WATCH_ZONE and stable.watched_level is not None:
            held = stable.watched_level
            direction = "buy" if held["kind"] == "swing_low" else "sell"
            stable.direction = direction
            dec.level_info = {"watched_level": held.get("price"),
                              "side": held.get("kind")}
            event = self._bar_edge_event(bar, float(held["price"]), direction)
            if event == "break":
                stable.state = WAIT_CANDLE_CLOSE
                stable.broken_level = held
                stable.timeout_bars = 0
                dec.action = WATCH
                dec.reason = f"Break through {held['kind']} level {held['price']:.2f} — awaiting retest"
                stable.last_action = dec.action
                stable.last_reason = dec.reason
                dec.state = stable.state
                return stable, dec
            if event == "rejection":
                stable.state = CONFIRMED
                stable.confirm_candle = self._confirm_candle(bar, direction)
                stable.timeout_bars = 0
                dec.action = CONFIRM
                dec.reason = f"Rejection wick at {held['kind']} level {held['price']:.2f} — awaiting break of extreme"
                stable.last_action = dec.action
                stable.last_reason = dec.reason
                dec.state = stable.state
                return stable, dec
            if not self._held_level_valid(held, levels_df):
                # no edge event AND the held level is now consumed by earlier
                # bars: drop the setup and fall through to re-arm
                stable.watched_level = None
                stable.direction = None
            else:
                dec.action = NONE
                dec.reason = f"watching {held['kind']} @ {held['price']:.2f}"
                dec.state = stable.state
                return stable, dec

        # ── WATCH_ZONE idle: arm the single bias-consistent level ──────────────
        watched = levels_mod.select_watched_level(h1_bias, levels_df, snap.bid)
        dec.level_info = {"watched_level": (watched.get("price") if watched else None),
                          "side": (watched.get("kind") if watched else None)}

        if stable.state == WATCH_ZONE:
            stable.watched_level = watched

        watched = stable.watched_level  # the level in force

        if watched is None:
            stable.state = WATCH_ZONE
            stable.direction = None
            stable.broken_level = None
            stable.confirm_candle = None
            dec.action = WATCH if h1_bias != bias_mod.FLAT else NONE
            dec.reason = "no bias-consistent intact level armed"
            stable.last_action = dec.action
            stable.last_reason = dec.reason
            dec.state = stable.state
            return stable, dec

        # determine intended direction from the armed level side (S4.1 filter)
        direction = "buy" if watched["kind"] == "swing_low" else "sell"
        stable.direction = direction

        if stable.state in (WATCH_ZONE, WAIT_CANDLE_CLOSE, CONFIRMED, ENTRY_READY):
            new_state, decision = self._advance_pre_trade(snap, stable, dec, levels_df, atr_m15, direction)
            decision.state = new_state.state
            return new_state, decision
        dec.state = stable.state
        return stable, dec

    def _advance_pre_trade(self, snap: Snapshot, state: EngineState, dec: Decision,
                           levels_df: pd.DataFrame, atr_m15: float,
                           direction: Optional[str]) -> tuple[EngineState, Decision]:
        bar = snap.last_bar()
        watched = state.watched_level
        if watched is None:
            state.state = WATCH_ZONE
            dec.action = NONE
            return state, dec

        level_price = float(watched["price"])
        tol = self._loc_tol(atr_m15)

        # breakout event (variant B step 1): solid-body close beyond the level
        broke = (
            (direction == "sell" and self._solid(bar) and bar["close"] > level_price)
            or (direction == "buy" and self._solid(bar) and bar["close"] < level_price)
        )
        # rejection event (variant R step 1 / retest rejection): close at level, wick beyond
        rejection = (
            (direction == "sell" and bar["high"] > level_price and bar["close"] < level_price)
            or (direction == "buy" and bar["low"] < level_price and bar["close"] > level_price)
        )

        if state.state == WATCH_ZONE:
            if broke:
                state.state = WAIT_CANDLE_CLOSE
                state.broken_level = watched
                state.timeout_bars = 0
                dec.action = WATCH
                dec.reason = f"Break through {watched['kind']} level {level_price:.2f} — awaiting retest"
                return state, dec
            if rejection:
                state.state = CONFIRMED
                state.confirm_candle = self._confirm_candle(bar, direction)
                state.timeout_bars = 0
                dec.action = CONFIRM
                dec.reason = f"Rejection wick at {watched['kind']} level {level_price:.2f} — awaiting break of extreme"
                return state, dec
            dec.action = NONE
            dec.reason = f"watching {watched['kind']} @ {level_price:.2f}"
            return state, dec

        if state.state == WAIT_CANDLE_CLOSE:
            state.timeout_bars += 1
            if state.timeout_bars > self.pending_retest_max_bars:
                state.state = WATCH_ZONE
                state.broken_level = None
                dec.action = DROP
                dec.reason = f"retest timeout ({state.timeout_bars} bars) — returning to WATCH_ZONE"
                return state, dec
            # retest: price returns toward broken level and closes with rejection
            if rejection:
                state.state = CONFIRMED
                state.confirm_candle = self._confirm_candle(bar, direction)
                state.timeout_bars = 0
                dec.action = CONFIRM
                dec.reason = f"retest rejection at broken level {level_price:.2f}"
                return state, dec
            dec.action = NONE
            dec.reason = "awaiting retest rejection candle"
            return state, dec

        if state.state == CONFIRMED:
            state.timeout_bars += 1
            if state.timeout_bars > self.confirm_max_bars:
                state.state = WATCH_ZONE
                state.confirm_candle = None
                dec.action = DROP
                dec.reason = "confirmation extreme not broken in time — candidate dropped"
                return state, dec
            if state.confirm_candle:
                extreme = state.confirm_candle["extreme"]
                broke_extreme = (
                    (direction == "sell" and bar["close"] < extreme)
                    or (direction == "buy" and bar["close"] > extreme)
                )
                if broke_extreme:
                    # Setup complete — gates are evaluated on the NEXT cycle in
                    # ENTRY_READY. action=CONFIRM (not ENTRY): ENTRY must mean
                    # only "order emitted after gates pass".
                    state.state = ENTRY_READY
                    dec.action = CONFIRM
                    dec.reason = f"break of confirm-candle extreme {extreme:.2f} -> ENTRY_READY (gates next cycle)"
                    return state, dec
            dec.action = NONE
            dec.reason = "awaiting close beyond confirmation extreme"
            return state, dec

        if state.state == ENTRY_READY:
            # gates must pass at the live price; then emit the order
            metrics = self._entry_metrics(snap, direction, level_price, levels_df, atr_m15)
            if metrics is None:
                state.state = WATCH_ZONE
                state.confirm_candle = None
                dec.action = DROP
                dec.reason = "no structural SL/TP resolvable at entry price — dropped"
                return state, dec
            # Gate 1 location: entry within tolerance of the armed level (§2.4)
            tol = self._loc_tol(atr_m15)
            metrics["loc_ok"] = abs(metrics["entry"] - level_price) <= tol
            gates = self._run_gates(snap, metrics)
            dec.gate_results = gates
            if not gates["pass"]:
                state.state = WATCH_ZONE
                state.confirm_candle = None
                dec.action = DROP
                dec.reason = f"gates failed: { {k: v for k, v in gates.items() if k != 'pass'} }"
                return state, dec

            # Gate 3 concurrency re-check at order time (R4 / §2.4.1)
            if snap.open_positions >= self.max_positions:
                state.state = WATCH_ZONE
                state.confirm_candle = None
                dec.action = DROP
                dec.reason = "concurrent position occupied — dropped"
                return state, dec

            state.active_trade = {
                "entry": metrics["entry"],
                "sl": metrics["sl"],
                "tp1": metrics["tp1"],
                "tp2": metrics["tp2"],
                "invalidation": metrics["invalidation"],
                "be_triggered": False,
                "comment": self.comment,
            }
            dec.order = {
                "symbol": self.symbol,
                "action": direction,
                "lot_size": self.fixed_lot,
                "stop_loss": metrics["sl"],
                "take_profit": metrics["tp1"],
                "dynamic_sizing": False,
                "comment": self.comment,
            }
            dec.reason = (f"ENTRY {direction.upper()} 0.01 @{metrics['entry']:.2f} "
                          f"SL {metrics['sl']:.2f} TP1 {metrics['tp1']:.2f} "
                          f"R:R {metrics['rr']:.2f} risk ${metrics['risk_usd']:.2f}")
            dec.action = ENTRY
            state.state = IN_TRADE
            return state, dec

        dec.action = NONE
        dec.reason = "unhandled state path"
        return state, dec

    def _confirm_candle(self, bar, direction: str) -> Dict[str, Any]:
        """Trade-side extreme of the confirmation candle (G2 §2.3)."""
        return {
            "time": str(bar["datetime"]),
            "extreme": float(bar["low"] if direction == "sell" else bar["high"]),
            "open": float(bar["open"]),
            "close": float(bar["close"]),
        }

    # ── Claim C — breakout-continuation trigger ────────────────────────────────
    def _check_breakout(self, snap: Snapshot, state: EngineState, dec: Decision,
                        levels_df: pd.DataFrame, atr_m15: float,
                        ) -> tuple[EngineState, Decision]:
        """Evaluate a trend-aligned structural breakout (Claim C).

        Logic (design doc v1.4):
          BULLISH bias  -> watch nearest intact swing_high ABOVE the bar close;
                           a solid M15 close THROUGH it = BUY at market.
          BEARISH bias  -> watch nearest intact swing_low BELOW the bar close;
                           a solid M15 close THROUGH it = SELL at market.
          FLAT bias     -> nothing.

        IMPORTANT: level selection uses the BAR CLOSE (the event price), not
        the live bid — the close is the reference for "has price crossed this
        level". A/B atomics apply through the same gates; only the order
        comment differs (GOLD_RULES_C) so Claim-C PnL is attributable.
        """
        if not self.breakout_enabled:
            return state, dec
        if state.state != WATCH_ZONE or state.active_trade is not None:
            return state, dec

        bias = state.h1_bias
        if bias not in (bias_mod.BULLISH, bias_mod.BEARISH):
            return state, dec

        bar = snap.last_bar()
        if not self._solid(bar):
            return state, dec

        close = float(bar["close"])
        prev_close = float(snap.m15_df.iloc[-2]["close"]) if len(snap.m15_df) >= 2 else close

        # Consumption must EXCLUDE the current bar: the break bar itself is the
        # event that consumes the level, so a level set computed over the full
        # df would mark it consumed in the same evaluation C must register the
        # cross (same ordering rule as A/B edge detection).
        res_pre = levels_mod.build_active_levels(
            snap.m30_df, lookback=self.lookback_m30, merge_atr_mult=self.merge_atr_mult)
        levels_pre = levels_mod.active_level_status(
            res_pre["levels"], snap.m15_df.iloc[:-1], self.solid_body_frac)
        if levels_pre is None or levels_pre.empty:
            return state, dec

        intact = levels_pre[levels_pre["consumed"] == False]  # noqa: E712
        if intact.empty:
            return state, dec

        if bias == bias_mod.BULLISH:
            # level just crossed: an intact swing_high it between prev_close and
            # close (price was under it, now above). Take the NEAREST one to close.
            cand = intact[(intact["kind"] == "swing_high")
                          & (intact["price"] < close)
                          & (intact["price"] > prev_close)]
            direction = "buy"
            lvl = cand.sort_values("price").iloc[-1] if not cand.empty else None
        else:
            # bearish: intact swing_low crossed from above.
            cand = intact[(intact["kind"] == "swing_low")
                          & (intact["price"] > close)
                          & (intact["price"] < prev_close)]
            direction = "sell"
            lvl = cand.sort_values("price").iloc[0] if not cand.empty else None

        if lvl is None:
            return state, dec

        level_price = float(lvl["price"])
        broke = (close > level_price) if direction == "buy" else (close < level_price)
        if not broke:
            return state, dec

        # Build the trade using the standard entry math (SL buffered beyond the
        # broken level, TP = next intact structure, R:R + $risk via gates).
        metrics = self._entry_metrics(snap, direction, level_price, levels_df, atr_m15)
        if metrics is None:
            return state, dec
        metrics["loc_ok"] = True  # Gate 1 (location) is inherently satisfied: the
                                  # close THROUGH the level is the entry itself.
        gates = self._run_gates(snap, metrics, min_rr=self.breakout_min_rr)
        dec.gate_results = gates
        if not gates["pass"]:
            return state, dec

        # Gate 3 concurrency re-check at order time (§2.4.1)
        if snap.open_positions >= self.max_positions:
            return state, dec

        state.active_trade = {
            "entry": metrics["entry"],
            "sl": metrics["sl"],
            "tp1": metrics["tp1"],
            "tp2": metrics["tp2"],
            "invalidation": metrics["invalidation"],
            "be_triggered": False,
            "comment": self.breakout_comment,
            "variant": "C",
        }
        dec.order = {
            "symbol": self.symbol,
            "action": direction,
            "lot_size": self.fixed_lot,
            "stop_loss": metrics["sl"],
            "take_profit": metrics["tp1"],
            "dynamic_sizing": False,
            "comment": self.breakout_comment,
        }
        dec.reason = (f"CLAIM-C BREAKOUT {direction.upper()} 0.01 @{metrics['entry']:.2f} "
                      f"through {level_price:.2f} | SL {metrics['sl']:.2f} TP1 {metrics['tp1']:.2f} "
                      f"R:R {metrics['rr']:.2f} risk ${metrics['risk_usd']:.2f}")
        dec.action = ENTRY
        state.state = IN_TRADE
        state.direction = direction
        state.watched_level = None      # C consumed the level; A/B re-arms fresh
        state.broken_level = None
        state.confirm_candle = None
        return state, dec

    def _manage_trade(self, snap: Snapshot, state: EngineState, dec: Decision,
                      levels_df: pd.DataFrame, atr_m15: float) -> tuple[EngineState, Decision]:
        """§2.6 M1/M2, §2.7 invalidation. Pure checks on closed bars + live price."""
        trade = state.active_trade
        direction = state.direction
        if trade is None or direction is None:
            state.state = DONE
            dec.action = CLOSE
            dec.reason = "active_trade missing in IN_TRADE — closing"
            return state, dec

        entry = float(trade["entry"])

        # position gone (closed externally or hit broker SL/TP) -> DONE
        if snap.open_positions == 0:
            state.state = DONE
            state.active_trade = None
            state.direction = None
            dec.action = CLOSE
            dec.reason = "open XAUUSD position count == 0 (broker TP/SL or external close) — done"
            return state, dec

        bar = snap.last_bar()
        # §2.7 invalidation: any recent M15/M30 close with solid body beyond invalidation
        invalidation = float(trade["invalidation"])
        def _close_beyond_df(df: pd.DataFrame) -> bool:
            for _, r in df.tail(4).iterrows():
                if not levels_mod._is_solid_body(r["open"], r["close"], r["high"], r["low"], self.solid_body_frac):
                    continue
                if direction == "sell" and r["close"] > invalidation:
                    return True
                if direction == "buy" and r["close"] < invalidation:
                    return True
            return False

        if _close_beyond_df(snap.m15_df) or _close_beyond_df(snap.m30_df):
            state.state = INVALIDATED
            dec.action = INVALIDATE
            dec.reason = f"invalidation level {invalidation:.2f} breached on a closed bar — closing position"
            return state, dec

        # §2.6 M1: break-even at 50% of entry->TP1
        tp1 = float(trade["tp1"])
        if not trade["be_triggered"]:
            half = entry + (tp1 - entry) * self.be_fraction
            hit = (snap.bid >= half) if direction == "buy" else (snap.bid <= half)
            if hit:
                trade["be_triggered"] = True
                trade["sl"] = entry
                dec.action = BE
                dec.reason = f"BE-50 triggered at {half:.2f} — SL dragged to entry {entry:.2f}"
                state.last_action = BE
                return state, dec

        # §2.6 M2: structural trail after BE
        if trade["be_triggered"]:
            suggested = float(bar["low"] if direction == "buy" else bar["high"])
            cur_sl = float(trade["sl"])
            improved = (suggested > cur_sl) if direction == "buy" else (suggested < cur_sl)
            if improved:
                trade["sl"] = suggested
                dec.action = TRAIL
                dec.reason = f"structural trail: SL {cur_sl:.2f} -> {suggested:.2f}"
                return state, dec

        dec.action = NONE
        dec.reason = "in trade; managing"
        return state, dec


def default_engine() -> GoldRulesEngine:
    """Engine with atomic v1 parameters (used by launcher / tests when no config)."""
    return GoldRulesEngine(_ATOMIC_DEFAULTS)


_ATOMIC_DEFAULTS: Dict[str, Any] = {
    "symbol": "XAUUSD",
    "bias": {"ema_fast": 20, "ema_slow": 50},
    "levels": {
        "lookback_bars_m30": 200,
        "fractal_wing": 2,
        "merge_distance_atr_mult": 0.5,
        "pending_retest_max_bars_m15": 20,
        "confirm_max_bars_m15": 3,
    },
    "gates": {
        "location_tolerance_atr_mult": 0.15,
        "location_tolerance_min_usd": 1.00,
        "min_rr": 1.5,
    },
    "risk": {
        "fixed_lot": 0.01,
        "max_risk_usd": 25.0,
        "max_concurrent_positions": 1,
        "daily_loss_cap_usd": 50.0,
        "sl_buffer_atr_mult": 0.05,
        "sl_buffer_min_usd": 0.30,
        "contract_size": 100.0,
    },
    "management": {"be_trigger_fraction": 0.5},
    "candles": {"solid_body_min_fraction": 0.30},
    "order": {"comment": "GOLD_RULES_v1", "dynamic_sizing": False},
}