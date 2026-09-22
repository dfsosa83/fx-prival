# -*- coding: utf-8 -*-
"""Virtual-fill ledger for DEMO mode — records REALIZED PnL from price action.

ROADMAP-2026-Q4 § 9 / PORTFOLIO-DEMO-SPEC.md §3 (prerequisite C).

Problem verified 2026-09-21/22: in demo mode `OrderManager.execute_order` returns
`order: 0, deal: 0` (simulated). The old code logged "EXECUTED ticket=0, pnl 0"
and never recorded a fill, so the paper account had NO virtual PnL — the demo was
logging decisions, not evidence.

This module gives simulated fills a real lifecycle: open -> (SL/TP/timeout/engine
close) -> realized USD + R, persisted to a per-trade ledger. It is pure/testable
and shared by the FX order bot and the gold rules runner.

Conventions
-----------
- SL/TP hit in the same bar: SL first (conservative).
- Round-trip cost is NOT re-modeled here: callers pass an already-cost-adjusted
  entry (or subtract cost in the close computation) — see the companion cost model
  in `ml-signal-service/experiments/_core/costs.py`.
- R = signed price excursion / initial risk distance (|entry - SL|), per trade.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

VIRTUAL_TICKET_PREFIX = "DEMO-"


@dataclass
class VirtualPosition:
    ticket: str
    symbol: str
    direction: str          # "buy" | "sell"
    volume: float
    entry: float
    sl: float
    tp: float
    opened_at: str
    open_event_ts: str = ""
    status: str = "OPEN"    # OPEN | CLOSED
    exit_price: Optional[float] = None
    exit_reason: str = ""
    realized_usd: float = 0.0
    r: float = 0.0

    def to_row(self) -> Dict:
        return asdict(self)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def open_virtual(pool: List[VirtualPosition], symbol: str, direction: str,
                 volume: float, entry: float, sl: float, tp: float,
                 event_ts: str = "") -> VirtualPosition:
    """Open a virtual position (returns the new row and appends to `pool`)."""
    ticket = f"{VIRTUAL_TICKET_PREFIX}{int(time.time() * 1000)}"
    pos = VirtualPosition(
        ticket=ticket, symbol=symbol, direction=direction.lower(),
        volume=float(volume), entry=float(entry), sl=float(sl), tp=float(tp),
        opened_at=event_ts or _now_iso(), open_event_ts=event_ts or _now_iso(),
    )
    pool.append(pos)
    return pos


def _sign(pos: VirtualPosition) -> float:
    return 1.0 if pos.direction == "buy" else -1.0


def _risk(pos: VirtualPosition) -> float:
    return abs(pos.entry - pos.sl)


def manage_open(pool: List[VirtualPosition], latest_price: float) -> List[VirtualPosition]:
    """Advance open positions against a freshly observed price.

    The latest_price is treated as the *current* bar. A position closes when:
      - SL hit first   -> exit_reason "SL", exit at SL level,
      - TP hit first   -> exit_reason "TP", exit at TP level,
      - else stays OPEN.
    On the same observed price, SL wins (conservative).

    Returns the list of positions that CLOSED in this step. Closed positions
    remain in the pool with status CLOSED and realized fields populated.
    """
    closed = []
    if latest_price is None:
        return closed
    for pos in [p for p in pool if p.status == "OPEN"]:
        # Direction-aware barriers:
        #   LONG: SL below entry (hit when price <= SL), TP above (hit when >= TP)
        #   SELL: SL above entry (hit when price >= SL), TP below (hit when <= TP)
        if pos.direction == "buy":
            sl_hit = latest_price <= pos.sl
            tp_hit = latest_price >= pos.tp
        else:
            sl_hit = latest_price >= pos.sl
            tp_hit = latest_price <= pos.tp
        if sl_hit:
            _do_close(pos, "SL")
            closed.append(pos)
        elif tp_hit:
            _do_close(pos, "TP")
            closed.append(pos)
    return closed


def _do_close(pos: VirtualPosition, reason: str) -> None:
    exit_px = pos.sl if reason == "SL" else pos.tp
    s = _sign(pos)
    pos.exit_price = exit_px
    pos.exit_reason = reason
    pos.realized_usd = s * (exit_px - pos.entry)   # per unit notional (≈$ per 1 lot-ish)
    risk = _risk(pos)
    pos.r = s * (exit_px - pos.entry) / risk if risk > 0 else 0.0
    pos.status = "CLOSED"


def close_pool(pool: List[VirtualPosition], reason: str = "ENGINE") -> List[VirtualPosition]:
    """Force-close every open position (e.g. engine shutdown / session end)."""
    closed = []
    for pos in pool:
        if pos.status == "OPEN":
            _do_close(pos, reason)
            closed.append(pos)
    return closed


# ── persistence ────────────────────────────────────────────────────────────────

def load_ledger(path: Path) -> List[VirtualPosition]:
    """Load a persisted ledger JSONL if present (one JSON trade per line)."""
    if not path.exists():
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                out.append(VirtualPosition(**d))
            except Exception:
                continue
    return out


def append_trade(path: Path, pos: VirtualPosition) -> None:
    """Append a closed trade to the ledger, creating dir/file if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(pos.to_row()) + "\n")


def open_positions(pool: List[VirtualPosition]) -> List[VirtualPosition]:
    return [p for p in pool if p.status == "OPEN"]