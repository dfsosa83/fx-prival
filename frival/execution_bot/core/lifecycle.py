# -*- coding: utf-8 -*-
"""EXEC-D1 — FX entry-zone and 10-minute expiry lifecycle engine (execution-only).

Implements the approved EXEC-D1 final plan (2026-09-28) WITHOUT changing any
strategy logic: Y1 labels, models, thresholds, agents, TP/SL generation, risk
sizing, and the M15/borderline/cooldown policies are all UNTOUCHED. This module
defines only the *execution-lifecycle mechanics* for a FIRED signal.

Approved semantics (all reproduced verbatim here so the runtime is auditable):
  D-1  Entry validity expires 10 minutes from signal time T0.
  D-2  If the executable quote already crossed the zone in the FAVOURABLE
       direction before processing (SELL bid < E-Z, or BUY ask > E+Z) -> no
       pending order is created; the signal is recorded NO_VALID_PENDING.
       We do not chase price.
  D-3  Pending trigger level = the appropriate zone boundary:
         SELL_STOP at E+Z when bid is above the zone;
         BUY_STOP  at E-Z  when ask is below the zone.
  D-4  Conservative gap handling (corrected): the fill quote is the FIRST
       observable executable-side quote that satisfies the trigger condition.
       - SELL_STOP: normal touch fills at the qualifying bid (bid <= L). If the
         first observable bid after triggering is BELOW L (gap through), fill at
         that lower bid.
       - BUY_STOP: normal touch fills at the qualifying ask (ask >= L). If the
         first observable ask after triggering is ABOVE L (gap through), fill at
         that higher ask.
       Recorded on every fill: trigger_level, prior_quote, triggering_quote,
       fill_quote, gap_flag, adverse_gap_pips.
       Limit-order fill policy is deliberately NOT defined here and must NEVER
       be inferred from the stop-order logic.
  D-5  Only executable-side quotes are used: bid for SELL, ask for BUY.
  D-6  Frozen absolute SL/TP levels from the signal are preserved. Effective
       risk, R:R, costs and PnL are computed from the ACTUAL fill price, and the
       effective R:R is recorded on every open.
  D-7  At most one pending or open position per (symbol, direction). A new
       same-side signal while one is active is skipped with a logged reason
       (CONCURRENCY_SKIPPED).
  D-9  The two 2026-09-28 fills are migrated as INVALID_SYNTHETIC_FILL_NO_OUTCOME
       (see core/invalid_fills.py) and are excluded from every metric.

Review fixes in this revision (2026-09-28 follow-up):
  C-1  process() wraps the entire read-check-decide-write sequence in exclusive
       claims (per signal + per (symbol,direction) slot) and re-reads the event
       log (`store.refresh()`) before deciding, so two concurrent `--once`
       processes cannot double-accept a signal or double-open a slot.
  M-1  VIRTUAL_OPEN is the SINGLE authoritative fill+open event: it carries the
       triggering/fill quotes, gap diagnostics, frozen SL/TP, effective R:R and
       risk. The former PENDING_TRIGGERED/MARKET_FILLED + VIRTUAL_OPEN two-write
       crash window no longer exists — replay derives the open position from
       exactly one event.
  M-2  `advance_pending(signal_id, quote)` continues a persisted pending with a
       newly received quote (fill on touch; watermark rejection of stale or
       duplicate quotes; post-expiry quotes never fill).

States (terminal semantics):
  SIGNAL_RECEIVED      -> origin (no trade by itself)
  ENTRY_PENDING        -> pending persisted, awaiting touch, t_exp = t0 + 10 min
  PENDING_UPDATED      -> quote watermark advanced (audit; pending unchanged)
  MARKET_FILLED        -> classification of process(): in-zone market entry
  PENDING_TRIGGERED    -> classification of process()/advance_pending(): touch
  VIRTUAL_OPEN         -> the single authoritative fill+open event (on disk)
  NO_VALID_PENDING     -> D-2 terminal; NOT a trade, NOT a loss
  EXPIRED_UNFILLED     -> pending existed, no touch by t_exp; NOT a trade/loss
  CLOSED_TP / CLOSED_SL / CLOSED_TIMEOUT  -> terminal closes
  EXECUTION_FAILED     -> the real order behind a VIRTUAL_OPEN was not placed
                          (broker rejection/blocked preflight/missing real
                          position at startup); phantom open retracted, NOT a
                          trade and NOT a loss
  EXTERNAL_STATE_CONFLICT -> manual/external closure observed -> excluded from
                             all paper-performance metrics (never CLOSED_MANUAL)
  DUPLICATE_SKIPPED / CONCURRENCY_SKIPPED -> audit-only no-ops

Y1 label/execution alignment (documented, NOT addressed here):
  The Y1 label simulates IMMEDIATE entry at H1 close[t]. This lifecycle instead
  executes a CONDITIONAL market-in-zone or <=10-minute zone-touch entry with the
  fill price actually observed. The model probability therefore describes the
  close-entry hypothetical, NOT necessarily the pending-zone trade. This is a
  documented design/evaluation mismatch that requires a SEPARATE research
  decision; it is explicitly out of scope for this operational implementation.

This module never imports MetaTrader5, never touches MT5, and performs no
strategy-simulation beyond the approved execution mechanics. Demo/paper use only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── EXEC-D1 parameters (execution mechanics only; NOT strategy parameters) ────
ZONE_HALF_WIDTH_DEFAULT = 0.00020          # +-2 pips @ EURUSD (as in main.py)
ENTRY_VALIDITY_SECONDS = 600               # D-1: 10 minutes from T0
ROUND_EPS = 1e-9
HORIZON_HOURS_DEFAULT = 6                  # Y1 forward window used only for timeout

# Event types (single vocabulary for the lifecycle store and reports)
SIGNAL_RECEIVED = "SIGNAL_RECEIVED"
ENTRY_PENDING = "ENTRY_PENDING"
PENDING_UPDATED = "PENDING_UPDATED"
MARKET_FILLED = "MARKET_FILLED"
PENDING_TRIGGERED = "PENDING_TRIGGERED"
VIRTUAL_OPEN = "VIRTUAL_OPEN"
NO_VALID_PENDING = "NO_VALID_PENDING"
EXPIRED_UNFILLED = "EXPIRED_UNFILLED"
CLOSED_TP = "CLOSED_TP"
CLOSED_SL = "CLOSED_SL"
CLOSED_TIMEOUT = "CLOSED_TIMEOUT"
EXTERNAL_STATE_CONFLICT = "EXTERNAL_STATE_CONFLICT"
DUPLICATE_SKIPPED = "DUPLICATE_SKIPPED"
CONCURRENCY_SKIPPED = "CONCURRENCY_SKIPPED"
# The real order behind a VIRTUAL_OPEN could not be placed (broker rejection,
# blocked preflight, or no real position found at startup). Terminal for the
# signal, but it is NOT a trade and NOT a close: the phantom open is retracted.
EXECUTION_FAILED = "EXECUTION_FAILED"

CLOSED_STATES = {CLOSED_TP, CLOSED_SL, CLOSED_TIMEOUT}
NO_TRADE_TERMINAL = {NO_VALID_PENDING, EXPIRED_UNFILLED}
EXCLUDED_STATES = {EXTERNAL_STATE_CONFLICT}
EXECUTION_TERMINAL = {EXECUTION_FAILED}

# Only SELL_STOP / BUY_STOP may ever be created by this engine (D-3 + D-4 limit
# separation). MARKET fills are not pending orders.
EMITTABLE_PENDING_TYPES = ("SELL_STOP", "BUY_STOP")

# Values of the `filled_via` field of the authoritative VIRTUAL_OPEN event.
FILL_VIA_MARKET = MARKET_FILLED
FILL_VIA_STOP = PENDING_TRIGGERED

# Entry-semantics modes (execution mechanics; owner decision 2026-09-29).
#   zone     -> legacy: in-zone market entry, else <=10-min zone-touch pending.
#   reanchor -> market-enter at the first in-window tick and re-anchor SL/TP on
#               the ACTUAL fill (preserving the signal's pip distances). This
#               removes the latency dependence of the fixed +-2-pip close zone.
ENTRY_MODE_ZONE = "zone"
ENTRY_MODE_REANCHOR = "reanchor"

_NO_OUTCOME = ""                # advance_pending no-op / stale-quote sentinel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_utc(value: str) -> datetime:
    """Parse an ISO timestamp and force it to tz-aware UTC."""
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────────────
# Input models
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class ExecutionSignal:
    """The execution-relevant view of a FIRED signal (strategy fields preserved)."""
    signal_id: str
    symbol: str
    direction: str                       # "SELL" | "BUY"
    entry: float                         # nominal E = close[H1 bar] (label anchor)
    stop_loss: float                     # frozen absolute level (D-6)
    take_profit: float                   # frozen absolute level (D-6)
    zone_lo: float
    zone_hi: float
    t0: datetime                         # signal time (bar close), tz-aware UTC
    pip_mult: float = 10000.0
    horizon: timedelta = timedelta(hours=HORIZON_HOURS_DEFAULT)
    source: Dict[str, Any] = field(default_factory=dict)

    @property
    def texp(self) -> datetime:
        """D-1 expiry = signal time + 10 minutes."""
        return self.t0 + timedelta(seconds=ENTRY_VALIDITY_SECONDS)

    @property
    def executable_side(self) -> str:
        """D-5: bid for SELL, ask for BUY."""
        return "bid" if self.direction == "SELL" else "ask"

    @property
    def t_horizon(self) -> datetime:
        return self.t0 + self.horizon


@dataclass
class Quote:
    """A single observed executable-side quote with an exact timestamp."""
    ts: datetime
    price: float


def from_signal_dict(signal: Dict[str, Any],
                     zone_half_width: float = ZONE_HALF_WIDTH_DEFAULT,
                     pip_mult_key: str = "pip_multiplier") -> ExecutionSignal:
    """Build an ExecutionSignal from a pipeline signal dict (main.py schema).

    Accepts `trade.entry_zone` if present (any [lo, hi] order) and normalises it;
    otherwise the zone is centered on the nominal entry with zone_half_width.
    Raises ValueError if required signal fields are missing or invalid.
    """
    trade = signal.get("trade") if isinstance(signal.get("trade"), dict) else {}
    entry = trade.get("entry") or signal.get("entry_price")
    stop_loss = trade.get("stop_loss") or signal.get("stop_loss")
    take_profit = trade.get("take_profit") or signal.get("take_profit")
    direction = str(signal.get("direction", "")).upper()
    signal_id = signal.get("signal_id")
    symbol = signal.get("symbol")
    t0_raw = signal.get("timestamp_utc") or trade.get("t0_utc")

    if not signal_id or not symbol or direction not in ("SELL", "BUY"):
        raise ValueError(
            f"invalid signal: need signal_id, symbol, direction in {{SELL,BUY}} "
            f"got signal_id={signal_id!r} symbol={symbol!r} direction={direction!r}"
        )
    if entry is None or stop_loss is None or take_profit is None:
        raise ValueError("invalid signal: trade.entry / stop_loss / take_profit required")
    if t0_raw is None:
        raise ValueError("invalid signal: timestamp_utc required")

    zone = trade.get("entry_zone")
    if zone and len(zone) == 2:
        zone_lo, zone_hi = min(float(zone[0]), float(zone[1])), max(float(zone[0]), float(zone[1]))
    else:
        zone_lo, zone_hi = float(entry) - zone_half_width, float(entry) + zone_half_width

    pip_mult = float(signal.get(pip_mult_key, 10000.0) or 10000.0)
    horizon_hours = float(signal.get("horizon_hours", HORIZON_HOURS_DEFAULT) or HORIZON_HOURS_DEFAULT)

    return ExecutionSignal(
        signal_id=str(signal_id), symbol=str(symbol), direction=direction,
        entry=float(entry), stop_loss=float(stop_loss), take_profit=float(take_profit),
        zone_lo=zone_lo, zone_hi=zone_hi, t0=parse_utc(t0_raw),
        pip_mult=pip_mult, horizon=timedelta(hours=horizon_hours),
        source={"from_signal_dict": True, "graphql_signal_id": signal_id},
    )


def select_executable(quote: Dict[str, Any], side: str) -> float:
    """Return the executable-side price of a raw quote dict (bid/ask)."""
    return float(quote[side])


def signal_from_received_payload(signal_id: str, symbol: str, direction: str,
                                 payload: Dict[str, Any]) -> ExecutionSignal:
    """Rebuild an ExecutionSignal from a persisted SIGNAL_RECEIVED payload.

    Used to reconstruct the frozen trade parameters after a process restart so
    that open positions (and pendings) can still be advanced/closed
    (EXEC-D1 §3 durability / review M-2).
    """
    if not payload:
        raise ValueError("SIGNAL_RECEIVED payload missing for reconstruction")
    return ExecutionSignal(
        signal_id=str(signal_id), symbol=str(symbol), direction=str(direction),
        entry=float(payload["entry"]), stop_loss=float(payload["stop_loss"]),
        take_profit=float(payload["take_profit"]),
        zone_lo=float(payload["zone_lo"]), zone_hi=float(payload["zone_hi"]),
        t0=parse_utc(payload["t0_utc"]), pip_mult=float(payload["pip_mult"]),
        horizon=timedelta(hours=float(payload.get("horizon_hours", HORIZON_HOURS_DEFAULT))),
        source={"reconstructed": True},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Pure classification and trigger logic (unit-testable, no I/O)
# ──────────────────────────────────────────────────────────────────────────────

def classify_quote(esig: ExecutionSignal, quote_price: float) -> str:
    """Return MARKET | STOP | NO_VALID_PENDING for the first executable quote.

    D-2/entry semantics:
      SELL: bid <  E-Z -> NO_VALID_PENDING (already crossed the zone favourably)
            bid in [E-Z, E+Z] -> MARKET
            bid >  E+Z -> STOP (pending SELL_STOP at E+Z)
      BUY : ask >  E+Z -> NO_VALID_PENDING
            ask in [E-Z, E+Z] -> MARKET
            ask <  E-Z -> STOP (pending BUY_STOP at E-Z)
    Zone boundaries are INCLUSIVE for the market path.
    """
    if esig.direction == "SELL":
        if quote_price < esig.zone_lo:
            return NO_VALID_PENDING
        if quote_price <= esig.zone_hi:
            return MARKET_FILLED
        return "STOP"
    # BUY
    if quote_price > esig.zone_hi:
        return NO_VALID_PENDING
    if quote_price >= esig.zone_lo:
        return MARKET_FILLED
    return "STOP"


def pending_spec(esig: ExecutionSignal) -> Tuple[str, float]:
    """D-3: (pending type, trigger level) for the stop path."""
    if esig.direction == "SELL":
        return ("SELL_STOP", esig.zone_hi)
    return ("BUY_STOP", esig.zone_lo)


def reanchor_levels(esig: ExecutionSignal, fill_price: float) -> Tuple[float, float]:
    """SL/TP re-anchored on the ACTUAL fill, preserving the signal's pip distances.

    Used in `reanchor` entry mode so the trade keeps the signal's intended
    risk/reward geometry regardless of how far the market moved between the H1
    close (signal anchor) and execution. Returns (stop_loss, take_profit).
    """
    sl_dist = abs(esig.entry - esig.stop_loss)
    tp_dist = abs(esig.take_profit - esig.entry)
    if esig.direction == "SELL":
        return fill_price + sl_dist, fill_price - tp_dist
    return fill_price - sl_dist, fill_price + tp_dist


def _triggered(order_type: str, level: float, price: float) -> bool:
    if order_type == "SELL_STOP":
        return price <= level + ROUND_EPS
    if order_type == "BUY_STOP":
        return price >= level - ROUND_EPS
    raise ValueError(f"limit order types are not emittable by EXEC-D1: {order_type}")


@dataclass
class FillInfo:
    """The conservative stop-fill outcome (D-4 corrected)."""
    prior_quote: Optional[float]
    triggering_quote: float
    fill_quote: float
    trigger_level: float
    gap_flag: bool
    adverse_gap_pips: float
    tf: datetime
    order_type: str = ""


def fill_from_quote(esig: ExecutionSignal, order_type: str, level: float,
                    price: float, prior_quote: Optional[float],
                    quote_ts: datetime) -> FillInfo:
    """Build the conservative stop-fill record for one triggering quote (D-4)."""
    gap = False
    adverse = 0.0
    if order_type == "SELL_STOP" and price < level - ROUND_EPS:
        gap = True
        adverse = (level - price) * esig.pip_mult
    elif order_type == "BUY_STOP" and price > level + ROUND_EPS:
        gap = True
        adverse = (price - level) * esig.pip_mult
    return FillInfo(
        prior_quote=prior_quote,
        triggering_quote=price,
        fill_quote=price,               # D-4: fill = triggering quote
        trigger_level=level,
        gap_flag=gap,
        adverse_gap_pips=round(adverse, 4),
        tf=quote_ts,
        order_type=order_type,
    )


def find_trigger(esig: ExecutionSignal, order_type: str, level: float,
                 quotes: List[Quote], tp: datetime,
                 quote_at_tp: Optional[float]) -> Tuple[Optional[FillInfo], bool]:
    """Scan executable quotes in (tp, texp] for the first trigger (D-1/D-4).

    - The trigger time window is t_exp = t0 + 10 min (INCLUSIVE on the boundary:
      a quote with ts == t_exp qualifies; a quote after t_exp never fills).
    - The fill quote is the FIRST observable executable-side quote satisfying the
      trigger condition (conservative; adverse gaps fill at the worse quote).
    - gap_flag is True only when the triggering quote is strictly on the adverse
      side of the level (SELL_STOP: below L; BUY_STOP: above L).

    Returns (FillInfo, stream_complete_when_no_trigger):
      - FillInfo when a trigger is observed;
      - (None, True)  when the provided stream extends to/through t_exp and no
        trigger occurred (the pending has legitimately EXPIRED);
      - (None, False) when the stream ends before t_exp — the entry window is
        still OPEN (the pending remains alive for advance_pending to feed).
    """
    if quotes is None:
        return None, False
    last_ts = quotes[-1].ts if quotes else tp
    complete = last_ts >= esig.texp
    prev: Optional[float] = quote_at_tp
    for q in quotes:
        if q.ts <= tp:
            prev = q.price
            continue
        if q.ts > esig.texp:
            break
        if not _triggered(order_type, level, q.price):
            prev = q.price
            continue
        return fill_from_quote(esig, order_type, level, q.price, prev, q.ts), True
    return None, complete


# ──────────────────────────────────────────────────────────────────────────────
# Fill/position math (all anchored on the ACTUAL fill price, D-6)
# ──────────────────────────────────────────────────────────────────────────────

def position_metrics(esig: ExecutionSignal, fill_price: float,
                     per_pip_usd: float, stop_loss: Optional[float] = None,
                     take_profit: Optional[float] = None):
    """Compute effective risk / effective R:R / risk USD from the actual fill.

    SL/TP default to the signal's frozen absolute levels (D-6); callers in
    `reanchor` entry mode pass the fill-anchored levels instead. Risk =
    |fill - SL| in pips. Returns (risk_dist_pips, reward_dist_pips, effective_rr, risk_usd).
    """
    sl = esig.stop_loss if stop_loss is None else float(stop_loss)
    tp = esig.take_profit if take_profit is None else float(take_profit)
    risk_dist = abs(fill_price - sl) * esig.pip_mult
    reward_dist = abs(tp - fill_price) * esig.pip_mult
    effective_rr = (reward_dist / risk_dist) if risk_dist > ROUND_EPS else 0.0
    risk_usd = risk_dist * per_pip_usd
    return (round(risk_dist, 4), round(reward_dist, 4), round(effective_rr, 3),
            round(risk_usd, 4))


def close_outcome(esig: ExecutionSignal, fill_price: float, exit_price: float,
                  exit_reason: str) -> Dict[str, float]:
    """Realized PnL / R / pips for a closed position (ledger-compatible math).

    Mirrors demo_ledger.py conventions: SL wins when SL and TP are satisfied by
    the same observed price; realized per-unit notional; R = signed excursion /
    initial risk distance. All values derive from the ACTUAL fill price (D-6).
    """
    s = 1.0 if esig.direction == "BUY" else -1.0
    risk = abs(fill_price - esig.stop_loss)
    realized = s * (exit_price - fill_price)
    r = (realized / risk) if risk > ROUND_EPS else 0.0
    pips = s * (exit_price - fill_price) * esig.pip_mult
    return {
        "exit_reason": exit_reason,
        "exit_price": round(exit_price, 6),
        "entry_used": round(fill_price, 6),
        "realized_usd": round(realized, 6),
        "r": round(r, 6),
        "pips": round(pips, 4),
        "frozen_sl": esig.stop_loss,
        "frozen_tp": esig.take_profit,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Engine — orchestrates one signal through the approved lifecycle
# ──────────────────────────────────────────────────────────────────────────────

class LifecycleEngine:
    """EXEC-D1 execution-lifecycle engine (demo/paper only, fully offline).

    The engine is a pure coordinator: it does not read MT5, does not place
    orders, and does not import the broker SDK. Quotes and the clock are
    injected by the caller (recorded quote stream + wall clock). The intended
    integration point (signal journal -> this engine -> lifecycle store) is NOT
    wired into any running workflow; enabling it requires explicit approval.

    Cross-process safety (C-1): every decision path first acquires exclusive
    claims (per signal + per (symbol,direction) slot) and re-reads the event
    log (`store.refresh()`) before committing. Two simultaneous `--once`
    processes therefore cannot both accept the same signal or both open the
    same slot.
    """

    VERSION = "2.0.0"

    def __init__(self, store, *, now_fn: Optional[Callable[[], datetime]] = None,
                 per_pip_usd: float = 0.10, cost_pips: Optional[float] = None,
                 broker_gate=None, zone_half_width: float = ZONE_HALF_WIDTH_DEFAULT,
                 entry_mode: str = ENTRY_MODE_ZONE):
        self.store = store
        self.now_fn = now_fn or _utcnow
        self.per_pip_usd = float(per_pip_usd)
        self.cost_pips = cost_pips
        self.broker_gate = broker_gate          # Optional[BrokerConstraintGate]
        self.zone_half_width = zone_half_width
        self.entry_mode = entry_mode or ENTRY_MODE_ZONE

    def _record(self, event_type: str, esig: ExecutionSignal,
                payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.append(event_type, esig.signal_id, esig.symbol,
                                 esig.direction, payload)

    def _slot_key(self, esig: ExecutionSignal) -> str:
        return f"{esig.symbol}:{esig.direction}"

    # ── lifecycle driver ──────────────────────────────────────────────────────

    def process(self, signal: Dict[str, Any],
                quotes: Optional[List[Dict[str, Any]]] = None) -> str:
        """Process one FIRED signal against a recorded quote stream.

        `quotes`: list of dicts {ts: ISO-UTC, bid: float, ask: float} in
        chronological order; only the executable-side value is used (D-5).

        Returns the terminal (or entry) event class for the signal:
        MARKET_FILLED / PENDING_TRIGGERED / ENTRY_PENDING / EXPIRED_UNFILLED /
        NO_VALID_PENDING / DUPLICATE_SKIPPED / CONCURRENCY_SKIPPED.

        Idempotency and concurrency are protected by exclusive claims around
        the full read-check-decide-write sequence (C-1).
        """
        esig = from_signal_dict(signal, zone_half_width=self.zone_half_width)
        sid = esig.signal_id

        # Fast path (single-process idempotency): avoid claiming signals this
        # process already knows about.
        if self.store.has_signal(sid):
            self._record(DUPLICATE_SKIPPED, esig, {"detail": "signal already processed"})
            return DUPLICATE_SKIPPED

        with self.store.claimed("signal", sid) as claimed_sig:
            if not claimed_sig:
                self._record(DUPLICATE_SKIPPED, esig, {
                    "detail": "signal claim held by another process"})
                return DUPLICATE_SKIPPED

            # Re-read the event log so a concurrent process's committed appends
            # are visible before any decision is recorded.
            self.store.refresh()
            if self.store.has_signal(sid):
                self._record(DUPLICATE_SKIPPED, esig, {
                    "detail": "signal already processed (post-refresh)"})
                return DUPLICATE_SKIPPED

            # Write-ahead: receipt of the signal is persisted before touching
            # the (symbol, direction) slot.
            self._record(SIGNAL_RECEIVED, esig, {
                "entry": esig.entry, "stop_loss": esig.stop_loss,
                "take_profit": esig.take_profit, "zone_lo": esig.zone_lo,
                "zone_hi": esig.zone_hi, "pip_mult": esig.pip_mult,
                "t0_utc": _iso(esig.t0),
                "horizon_hours": esig.horizon.total_seconds() / 3600.0,
                "entry_validity_seconds": ENTRY_VALIDITY_SECONDS,
            })

            with self.store.claimed("slot", self._slot_key(esig)) as claimed_slot:
                if not claimed_slot:
                    self._record(CONCURRENCY_SKIPPED, esig, {
                        "detail": "slot claim held by another process"})
                    return CONCURRENCY_SKIPPED

                self.store.refresh()
                if not self.store.acquires(esig.symbol, esig.direction):
                    self._record(CONCURRENCY_SKIPPED, esig, {
                        "detail": "active pending/open exists for symbol+direction"})
                    return CONCURRENCY_SKIPPED

                return self._decide(esig, quotes)

    def _decide(self, esig: ExecutionSignal,
                quotes: Optional[List[Dict[str, Any]]]) -> str:
        """Evaluate and commit the entry decision. Caller holds the claims."""
        tp = self.now_fn()
        if tp > esig.texp:
            self._record(EXPIRED_UNFILLED, esig, {
                "reason": "processed_after_expiry",
                "texp_utc": _iso(esig.texp), "expired_at_utc": _iso(tp),
                "last_quote": None,
            })
            return EXPIRED_UNFILLED

        side = esig.executable_side
        sorted_quotes = self._sorted_quotes(quotes, side)
        # Primary path: first executable quote observed at/after the processing
        # instant `tp` and not past expiry.
        q0 = next((q for q in sorted_quotes
                   if q.ts >= tp and q.ts <= esig.texp), None)
        # Fix (2026-09-29 no_quote race): the live runner fetches a single tick
        # BEFORE the decision clock is read, so the just-fetched quote's
        # timestamp necessarily precedes `tp` and the primary filter rejected
        # it — expiring an in-window signal ~5 ms after processing (EURUSD
        # 16:00Z). When no quote is at/after `tp`, the freshest quote inside the
        # signal's own validity window (t0 .. t_exp) IS the current market
        # snapshot and must be evaluated. The window bounds stay hard: a
        # pre-signal or post-expiry quote never fills.
        if q0 is None:
            q0 = next((q for q in reversed(sorted_quotes)
                       if esig.t0 <= q.ts <= esig.texp), None)

        if q0 is None:
            self._record(EXPIRED_UNFILLED, esig, {
                "reason": "no_quote", "texp_utc": _iso(esig.texp),
                "expired_at_utc": _iso(tp), "last_quote": None,
            })
            return EXPIRED_UNFILLED

        if self.entry_mode == ENTRY_MODE_REANCHOR:
            # Re-anchor mode (owner decision 2026-09-29): enter at the first
            # in-window executable quote and set SL/TP on the ACTUAL fill,
            # preserving the signal's pip distances. This removes the latency
            # dependence of the fixed +-2-pip close-anchored zone.
            sl, tpx = reanchor_levels(esig, q0.price)
            self._fill_open(esig, fill_quote=q0.price, tf=q0.ts,
                            filled_via=FILL_VIA_MARKET, quote_ts=q0.ts,
                            prior_quote=q0.price,
                            stop_loss_override=sl, take_profit_override=tpx)
            return MARKET_FILLED

        kind = classify_quote(esig, q0.price)

        if kind == NO_VALID_PENDING:
            self._record(NO_VALID_PENDING, esig, {
                "reason": "crossed_zone_favorable", "quote": q0.price,
                "tp_utc": _iso(tp),
                "zone": [esig.zone_lo, esig.zone_hi],
                "detail": f"executable {side} {q0.price} outside zone "
                          f"[{esig.zone_lo}, {esig.zone_hi}] on the adverse side",
            })
            return NO_VALID_PENDING

        if kind == MARKET_FILLED:
            self._fill_open(esig, fill_quote=q0.price, tf=q0.ts,
                            filled_via=FILL_VIA_MARKET,
                            quote_ts=q0.ts, prior_quote=q0.price)
            return MARKET_FILLED

        # STOP path -----------------------------------------------------------
        order_type, level = pending_spec(esig)

        if self.broker_gate is not None:
            gate_eval = self.broker_gate.evaluate(
                order_type=order_type, trigger_level=level,
                executable_quote=q0.price, symbol=esig.symbol,
            )
            if not gate_eval.ok:
                self._record(EXPIRED_UNFILLED, esig, {
                    "reason": "broker_constraint_blocked",
                    "gate_code": gate_eval.code, "detail": gate_eval.detail,
                    "texp_utc": _iso(esig.texp), "expired_at_utc": _iso(tp),
                    "last_quote": q0.price,
                })
                return EXPIRED_UNFILLED

        # Write-ahead: persist the pending BEFORE touch evaluation. The quote
        # watermark starts at the processing quote so a later re-feed of stale
        # quotes cannot re-trigger (M-2).
        self._record(ENTRY_PENDING, esig, {
            "pending_type": order_type, "trigger_level": level,
            "executable_side": side, "tp_utc": _iso(tp),
            "texp_utc": _iso(esig.texp), "quote_at_tp": q0.price,
            "prior_quote": q0.price,
            "last_quote_ts": _iso(q0.ts),
            "last_quote_price": q0.price,
        })

        trigger, stream_complete = find_trigger(esig, order_type, level,
                                                 sorted_quotes, tp, q0.price)
        if trigger is not None:
            self._fill_open(esig, fill_quote=trigger.fill_quote, tf=trigger.tf,
                            filled_via=FILL_VIA_STOP,
                            order_type=trigger.order_type,
                            trigger_level=trigger.trigger_level,
                            triggering_quote=trigger.triggering_quote,
                            prior_quote=trigger.prior_quote,
                            gap_flag=trigger.gap_flag,
                            adverse_gap_pips=trigger.adverse_gap_pips,
                            quote_ts=trigger.tf)
            return PENDING_TRIGGERED

        if stream_complete:
            self._record(EXPIRED_UNFILLED, esig, {
                "reason": "no_touch", "texp_utc": _iso(esig.texp),
                "expired_at_utc": _iso(esig.texp),
                "last_quote": sorted_quotes[-1].price if sorted_quotes else q0.price,
            })
            return EXPIRED_UNFILLED

        # The entry window is still open: the pending remains alive and must be
        # continued via advance_pending() with newly received quotes (M-2).
        return ENTRY_PENDING

    def advance_pending(self, signal_id: str, quote: Dict[str, Any],
                        now: Optional[datetime] = None) -> str:
        """Continue a persisted pending with a newly received quote (M-2).

        - Only quotes with a fresh timestamp within (last seen, t_exp] can
          trigger a fill; a quote stamped after t_exp never fills (D-1).
        - Re-release of an already-seen quote (stale cache) is ignored.
        - On a non-triggering in-window quote the watermark is advanced via a
          PENDING_UPDATED event so restart cannot re-fill from cached quotes.
        - Returns PENDING_TRIGGERED (filled) | EXPIRED_UNFILLED | "" (no-op).
        """
        with self.store.claimed("signal", signal_id) as claimed:
            if not claimed:
                return _NO_OUTCOME
            self.store.refresh()
            pend = self.store.pending_entry(signal_id)
            esig = self._resolved_signal(signal_id)
            if pend is None or esig is None:
                return _NO_OUTCOME

            now = now or self.now_fn()
            side = esig.executable_side
            price = float(quote[side])
            ts = parse_utc(quote.get("ts", _iso(now)))

            if ts > esig.texp:
                # t_exp already closed (or this quote is the proof it did):
                # record the expiry, never fill (D-1).
                self._record(EXPIRED_UNFILLED, esig, {
                    "reason": "quote_after_texp",
                    "texp_utc": _iso(esig.texp),
                    "expired_at_utc": _iso(ts),
                    "last_quote": price,
                })
                return EXPIRED_UNFILLED

            if ts <= parse_utc(pend["tp_utc"]):
                return _NO_OUTCOME                       # before the pending
            wm = pend.get("last_quote_ts")
            if wm is not None and ts <= parse_utc(wm):
                return _NO_OUTCOME                       # stale/duplicate quote

            order_type = pend["pending_type"]
            level = float(pend["trigger_level"])
            prior = pend.get("last_quote_price", pend.get("prior_quote"))

            if not _triggered(order_type, level, price):
                self._record(PENDING_UPDATED, esig, {
                    **pend, "last_quote_ts": _iso(ts), "last_quote_price": price,
                })
                return _NO_OUTCOME

            fi = fill_from_quote(esig, order_type, level, price, prior, ts)
            self._fill_open(esig, fill_quote=fi.fill_quote, tf=fi.tf,
                            filled_via=FILL_VIA_STOP, order_type=fi.order_type,
                            trigger_level=fi.trigger_level,
                            triggering_quote=fi.triggering_quote,
                            prior_quote=fi.prior_quote,
                            gap_flag=fi.gap_flag,
                            adverse_gap_pips=fi.adverse_gap_pips,
                            quote_ts=ts)
            return PENDING_TRIGGERED

    def _sorted_quotes(self, quotes, side: str) -> List[Quote]:
        if not quotes:
            return []
        out = []
        for item in quotes:
            if not isinstance(item, dict):
                continue
            ts = parse_utc(item.get("ts"))
            price = float(item.get(side))
            out.append(Quote(ts=ts, price=price))
        out.sort(key=lambda q: q.ts)
        return out

    def _fill_open(self, esig: ExecutionSignal, *, fill_quote: float, tf: datetime,
                   filled_via: str, quote_ts: datetime,
                   order_type: str = "", trigger_level: Optional[float] = None,
                   triggering_quote: Optional[float] = None,
                   prior_quote: Optional[float] = None,
                   gap_flag: bool = False,
                   adverse_gap_pips: float = 0.0,
                   stop_loss_override: Optional[float] = None,
                   take_profit_override: Optional[float] = None) -> None:
        """Append the SINGLE authoritative fill+open event (M-1).

        VIRTUAL_OPEN carries everything needed to reconstruct the open position
        from replay alone: the actual fill quote, gap diagnostics, frozen SL/TP,
        effective R:R and risk. Replay derives the open position from
        exactly this event; there is no second write that a crash could split.
        In `reanchor` entry mode the SL/TP carried here are the fill-anchored
        levels, and they are the single source of truth for later SL/TP hits.
        """
        sl = esig.stop_loss if stop_loss_override is None else float(stop_loss_override)
        tpx = esig.take_profit if take_profit_override is None else float(take_profit_override)
        risk_pips, reward_pips, eff_rr, risk_usd = position_metrics(
            esig, fill_quote, self.per_pip_usd, stop_loss=sl, take_profit=tpx)
        ticket = f"D1-{esig.signal_id}"
        payload = {
            "ticket": ticket,
            "entry_used": round(fill_quote, 6),
            "fill_quote": round(fill_quote, 6),
            "stop_loss": sl,
            "take_profit": tpx,
            "filled_via": filled_via,
            "quote_ts_utc": _iso(quote_ts),
            "fill_ts_utc": _iso(tf),
            "effective_rr": eff_rr,
            "effective_risk_pips": risk_pips,
            "effective_reward_pips": reward_pips,
            "risk_usd": risk_usd,
            "cost_pips": self.cost_pips,
        }
        if filled_via == FILL_VIA_STOP:
            payload.update({
                "pending_type": order_type,
                "trigger_level": trigger_level,
                "triggering_quote": triggering_quote,
                "prior_quote": prior_quote,
                "gap_flag": gap_flag,
                "adverse_gap_pips": adverse_gap_pips,
            })
        self._record(VIRTUAL_OPEN, esig, payload)

    # ── position life: close against observed prices / horizon ───────────────

    def _resolved_signal(self, signal_id: str):
        """Rebuild the ExecutionSignal from persisted state (restart-safe)."""
        meta = self.store.signal_meta(signal_id)
        if meta is None:
            return None
        esig = signal_from_received_payload(
            signal_id, meta["symbol"], meta["direction"], meta["payload"])
        # The authoritative SL/TP live in the VIRTUAL_OPEN record (single source
        # of truth). In zone mode they equal the signal's frozen levels; in
        # reanchor mode they carry the fill-anchored levels — so later SL/TP hits
        # must use these, not the original signal levels.
        pos = self.store.open_position(signal_id)
        if pos is not None:
            if pos.get("stop_loss") is not None:
                esig.stop_loss = float(pos["stop_loss"])
            if pos.get("take_profit") is not None:
                esig.take_profit = float(pos["take_profit"])
        return esig

    def advance(self, signal_id: str, quote: Dict[str, Any],
                now: Optional[datetime] = None) -> str:
        """Advance one open position against an observed quote (SL-first).

        Returns the close event type, or "" while the position stays OPEN.
        Mirrors demo_ledger.py manage_open semantics on the same quote.
        """
        esig = self._resolved_signal(signal_id)
        if esig is None or self.store.open_position(signal_id) is None:
            return ""
        now = now or self.now_fn()
        side = esig.executable_side
        price = float(quote[side])
        ts = parse_utc(quote.get("ts", _iso(now)))

        if esig.direction == "SELL":
            sl_hit = price >= esig.stop_loss
            tp_hit = price <= esig.take_profit
        else:
            sl_hit = price <= esig.stop_loss
            tp_hit = price >= esig.take_profit

        if sl_hit:                 # SL first (conservative, ledger convention)
            return self._close(signal_id, esig, esig.stop_loss, CLOSED_SL, ts)
        if tp_hit:
            return self._close(signal_id, esig, esig.take_profit, CLOSED_TP, ts)
        self.store.note_last_quote(signal_id, price)
        return ""

    def close_timeout(self, signal_id: str,
                      now: Optional[datetime] = None) -> str:
        """Close an open position once the 6-bar horizon passed (CLOSED_TIMEOUT).

        Exit price = last quoted price if observed, else the fill price (flat).
        """
        esig = self._resolved_signal(signal_id)
        pos = self.store.open_position(signal_id)
        if esig is None or pos is None:
            return ""
        now = now or self.now_fn()
        if now < esig.t_horizon:
            return ""
        exit_price = self.store.last_quote(signal_id)
        if exit_price is None:
            exit_price = float(pos["entry_used"])
        return self._close(signal_id, esig, exit_price, CLOSED_TIMEOUT, now)

    def _close(self, signal_id: str, esig: ExecutionSignal,
               exit_price: float, event_type: str, ts: datetime) -> str:
        fill_price = float(self.store.open_position(signal_id)["entry_used"])
        payload = close_outcome(esig, fill_price, exit_price,
                                event_type.removeprefix("CLOSED_"))
        payload["exit_ts_utc"] = _iso(ts)
        payload["cost_pips"] = self.cost_pips
        self._record(event_type, esig, payload)
        return event_type

    def mark_execution_failed(self, signal_id: str, *, reason: str,
                              detail: str = "",
                              execution: Optional[Dict[str, Any]] = None) -> str:
        """Retract a VIRTUAL_OPEN whose real order was not successfully sent."""
        meta = self.store.signal_meta(signal_id)
        if meta is None:
            return ""
        esig = signal_from_received_payload(
            signal_id, meta["symbol"], meta["direction"], meta["payload"])
        self._record(EXECUTION_FAILED, esig, {
            "reason": reason,
            "detail": detail,
            "execution": dict(execution) if execution else {},
            "ts_utc": _iso(self.now_fn()),
        })
        return EXECUTION_FAILED

    def reconcile_executions(self, executed_signal_ids,
                             broker_symbols) -> List[str]:
        """Roll back open virtual positions that have no real order behind them.

        Startup safety net: for every open position whose signal id has NO
        successful real execution AND whose symbol has NO live broker position,
        append EXECUTION_FAILED. Positions with a real execution, or whose
        symbol is held at the broker, are left untouched.
        """
        executed = set(executed_signal_ids or ())
        held = set(broker_symbols or ())
        reconciled: List[str] = []
        for sid in list(self.store.open_positions()):
            meta = self.store.signal_meta(sid)
            symbol = meta["symbol"] if meta else ""
            if sid in executed or symbol in held:
                continue
            if self.mark_execution_failed(
                    sid, reason="no_real_position_on_startup",
                    detail=(f"no EXECUTED record for {sid} and no broker "
                            f"position for {symbol}")):
                reconciled.append(sid)
        return reconciled

    def record_external_conflict(self, signal_id: str, detail: str) -> str:
        """Record an observed external/manual closure (never CLOSED_MANUAL)."""
        meta = self.store.signal_meta(signal_id)
        if meta is None:
            return ""
        esig = signal_from_received_payload(
            signal_id, meta["symbol"], meta["direction"], meta["payload"])
        self._record(EXTERNAL_STATE_CONFLICT, esig, {
            "detail": detail, "ts_utc": _iso(self.now_fn()),
        })
        return EXTERNAL_STATE_CONFLICT