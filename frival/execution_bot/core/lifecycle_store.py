# -*- coding: utf-8 -*-
"""EXEC-D1 append-only lifecycle event store (execution data durability).

EXEC-D1 spec §3 — State durability:
  - Persist every pending order BEFORE execution (write-ahead).
  - Persist every fill immediately (single authoritative VIRTUAL_OPEN event).
  - Persist open virtual positions across `--once` process exits.
  - Reconcile pending and open virtual orders on startup (automatic).
  - Ensure idempotency: a signal cannot create duplicate pending or virtual
    positions — INCLUDING across concurrent processes (review C-1).

Review fixes implemented (2026-09-28 follow-up):
  C-1  Cross-process claims: an O_EXCL claim file per claim key protects the
       full read-check-decide-write sequence. Stale claims (crashed process)
       are reclaimed via a TTL. `refresh()` re-reads the append-only event log
       inside the claim so a concurrent writer's committed state is visible
       before any new decision is appended.
  M-1  VIRTUAL_OPEN is the single authoritative fill+open event (it carries the
       triggering/fill quotes, frozen SL/TP, risk and effective R:R). Open
       positions are derived ONLY from VIRTUAL_OPEN during replay; the former
       MARKET_FILLED/PENDING_TRIGGERED+VIRTUAL_OPEN two-append crash window is
       gone. Legacy rows remain readable and never create duplicate opens.
  M-2  Pending orders persist a quote watermark (`last_quote_ts`) updated by
       PENDING_UPDATED events; `advance_pending()` in the engine fills a pending
       from a later quote and rejects stale/duplicate/post-expiry quotes.
  M-3  LifecycleStore.__init__ automatically replays state and reconciles
       expired pendings at startup (no integrator-remembered reconcile() call).

Design
------
- `lifecycle_events.jsonl` is the append-only SOURCE OF TRUTH. Every state
  transition is appended with fsync before any dependent action is taken.
- `claims/` holds short-lived O_EXCL claim files used for cross-process
  decision rights (signal claim + (symbol,direction) slot claim).
- `pending_entries.jsonl` and `open_positions.jsonl` are derived convenience
  snapshots, rewritten atomically (temp file + os.replace) whenever the active
  set changes. They are regenerated from the event log on startup; the event
  log is always authoritative.

Only demo/paper data is stored here. No MT5, no orders, no broker state.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

try:
    # Normal package layout (execution_bot on sys.path). The `core` package
    # __init__ imports mt5_connector (pytz, MetaTrader5) which may be absent in
    # offline/minimal environments; when the package cannot be imported we fall
    # back to a flat sibling import (core/ on sys.path) so the EXEC-D1 store
    # remains usable without the broker SDK stack (tests/reports only, no MT5).
    from core.lifecycle import (  # noqa: F401
        CLOSED_TP, CLOSED_SL, CLOSED_TIMEOUT, CLOSED_STATES,
        CONCURRENCY_SKIPPED, DUPLICATE_SKIPPED, ENTRY_PENDING, EXCLUDED_STATES,
        EXECUTION_FAILED, EXECUTION_TERMINAL, EXPIRED_UNFILLED,
        EXTERNAL_STATE_CONFLICT, MARKET_FILLED,
        NO_TRADE_TERMINAL, NO_VALID_PENDING, PENDING_TRIGGERED,
        PENDING_UPDATED, SIGNAL_RECEIVED, VIRTUAL_OPEN, parse_utc,
    )
except ImportError:
    from lifecycle import (  # noqa: F401
        CLOSED_TP, CLOSED_SL, CLOSED_TIMEOUT, CLOSED_STATES,
        CONCURRENCY_SKIPPED, DUPLICATE_SKIPPED, ENTRY_PENDING, EXCLUDED_STATES,
        EXECUTION_FAILED, EXECUTION_TERMINAL, EXPIRED_UNFILLED,
        EXTERNAL_STATE_CONFLICT, MARKET_FILLED,
        NO_TRADE_TERMINAL, NO_VALID_PENDING, PENDING_TRIGGERED,
        PENDING_UPDATED, SIGNAL_RECEIVED, VIRTUAL_OPEN, parse_utc,
    )

EVENTS_FILENAME = "lifecycle_events.jsonl"
PENDING_SNAPSHOT = "pending_entries.jsonl"
OPEN_SNAPSHOT = "open_positions.jsonl"
CLAIMS_DIRNAME = "claims"
SCHEMA_VERSION = 2
DEFAULT_CLAIM_TTL_SECONDS = 60.0

# Derived-snapshot writes are BEST-EFFORT: the append-only event log is the
# source of truth (see module docstring) and snapshots are rebuilt from it on
# startup. On Windows a destination file held by another handle (e.g. OneDrive
# sync or antivirus) makes os.replace fail with WinError 5; we retry briefly and
# then swallow the failure, so a snapshot write can NEVER abort the decision
# path or prevent order routing.
SNAPSHOT_WRITE_ATTEMPTS = 3
SNAPSHOT_WRITE_BACKOFF_SECONDS = 0.05


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _epoch_utc(dt: Optional[datetime]) -> float:
    return dt.astimezone(timezone.utc).timestamp() if dt else time.time()


class LifecycleStore:
    """Append-only event store with derived state and cross-process claims."""

    def __init__(self, data_dir, *, now_fn: Optional[Callable[[], datetime]] = None,
                 claim_ttl_seconds: float = DEFAULT_CLAIM_TTL_SECONDS):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.data_dir / EVENTS_FILENAME
        self.pending_snapshot = self.data_dir / PENDING_SNAPSHOT
        self.open_snapshot = self.data_dir / OPEN_SNAPSHOT
        self.claims_dir = self.data_dir / CLAIMS_DIRNAME
        self.claims_dir.mkdir(parents=True, exist_ok=True)
        self.claim_ttl = float(claim_ttl_seconds)
        self.now_fn = now_fn or _utcnow

        self._prune_stale_claims()
        self._reset_indexes()
        self.snapshot_write_failures = 0
        self.last_snapshot_error: Optional[str] = None
        self._replay()
        # M-3: automatic startup reconciliation (idempotent; no-op when there
        # is nothing to expire).
        self.reconcile(self.now_fn())

    # ── indexes ---------------------------------------------------------------

    def _reset_indexes(self) -> None:
        self._seq = 0
        self._signals: Dict[str, Dict[str, Any]] = {}
        self._sig_meta: Dict[str, Dict[str, Any]] = {}
        self._pending: Dict[str, Dict[str, Any]] = {}
        self._open: Dict[str, Dict[str, Any]] = {}
        self._last_quote: Dict[str, float] = {}
        self._active: Dict[Tuple[str, str], str] = {}
        self._closed: List[Dict[str, Any]] = []
        self._exec_failed: List[Dict[str, Any]] = []
        self._excluded: set = set()
        self._events: List[Dict[str, Any]] = []
        self.corrupt_tail = 0
        self.corrupt_mid = 0
        self.duplicate_event_ids = 0

    def refresh(self) -> None:
        """Re-read the event log and rebuild all derived indexes.

        Called INSIDE a claim right before a decision is committed so that a
        concurrent process's already-fsynced appends are visible (C-1). Claims
        themselves are untouched by a refresh.
        """
        self._reset_indexes()
        self._replay()

    # ── append (write-ahead, fsynced) ────────────────────────────────────────

    def append(self, event_type: str, signal_id: str, symbol: str,
               direction: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Append one event atomically (O_APPEND + fsync; header guarded) and
        apply to indexes."""
        self._seq += 1
        event = {
            "event_id": uuid.uuid4().hex,
            "seq": self._seq,
            "ts_utc": self.now_fn().astimezone(timezone.utc).isoformat(),
            "signal_id": signal_id,
            "symbol": symbol,
            "direction": direction,
            "event_type": event_type,
            "payload": payload,
        }
        self._write_line(event)
        self._apply(event, replay=False)
        return dict(event)

    def _write_line(self, event: Dict[str, Any]) -> None:
        # Header creation is guarded by a claim so two concurrent processes
        # cannot interleave partial initial writes (C-1). A duplicate header
        # line would be harmless (replay skips '#') but is prevented anyway.
        if not self.events_path.exists():
            with self.claimed("log-init", "header") as ok:
                if ok and not self.events_path.exists():
                    with open(self.events_path, "a", encoding="utf-8") as f:
                        f.write(f"# schema v{SCHEMA_VERSION}\n")
        fd = os.open(self.events_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            os.write(fd, (json.dumps(event) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

    # ── cross-process claims (C-1) ───────────────────────────────────────────

    def _claim_path(self, kind: str, key: str) -> Path:
        safe = str(key).replace("/", "_").replace("\\", "_").replace(":", "_")
        return self.claims_dir / f"{kind}-{safe}.claim"

    def _claim_stale_age(self) -> float:
        """A claim is stale (crashed holder) after 2x the TTL."""
        return 2.0 * max(self.claim_ttl, 1.0)

    def _prune_stale_claims(self) -> None:
        if not self.claims_dir.exists():
            return
        cutoff = time.time() - self._claim_stale_age()
        for p in self.claims_dir.glob("*.claim"):
            try:
                if p.stat().st_mtime < cutoff:
                    p.unlink()
            except OSError:
                pass

    def _try_claim(self, path: Path, claim_id: str) -> bool:
        for _ in range(3):
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                # Stale-claim recovery: only reclaim when the owner has clearly
                # crashed (older than the TTL). Never delete a live claim.
                try:
                    stale = (time.time() - path.stat().st_mtime) > self._claim_stale_age()
                except OSError:
                    return False
                if stale:
                    try:
                        path.unlink()
                    except OSError:
                        return False
                    continue
                return False
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "claimant": claim_id, "kind": "exclusive",
                    "created_epoch": time.time(),
                }))
                f.flush()
                os.fsync(f.fileno())
            return True
        return False

    @contextlib.contextmanager
    def claimed(self, kind: str, key: str,
                ttl: Optional[float] = None) -> Iterator[bool]:
        """Atomically acquire an exclusive claim; yields True on success.

        The claim is released on normal exit (finally). A crashed holder leaves
        a stale claim file which is reclaimed by TTL on a later attempt/startup.
        `ttl` overrides the store TTL for this claim only.
        """
        old_ttl = None
        if ttl is not None:
            old_ttl = self.claim_ttl
            self.claim_ttl = float(ttl)
        path = self._claim_path(kind, key)
        claim_id = uuid.uuid4().hex
        try:
            ok = self._try_claim(path, claim_id)
            yield ok
        finally:
            if old_ttl is not None:
                self.claim_ttl = old_ttl
            if ok:
                try:
                    path.unlink()
                except OSError:
                    pass

    # ── replay / recovery ────────────────────────────────────────────────────

    def _replay(self) -> None:
        if not self.events_path.exists():
            return
        lines = self.events_path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if idx == len(lines) - 1:
                    self.corrupt_tail += 1          # crashed mid-append
                else:
                    self.corrupt_mid += 1
                continue
            if event.get("event_id") in self._seen_event_ids():
                self.duplicate_event_ids += 1
                continue
            self._apply(event, replay=True)
        # Derived snapshots are written ONCE here, not per replayed event (the
        # previous code rewrote both files for every event in the log).
        self._write_snapshots()

    def _seen_event_ids(self) -> set:
        return {e["event_id"] for e in self._events}

    # ── index application (shared by live append and replay) ─────────────────

    def _apply(self, event: Dict[str, Any], replay: bool) -> None:
        et = event["event_type"]
        sid = event["signal_id"]
        self._events.append(event)
        self._seq = max(self._seq, int(event.get("seq", 0)) + 1)
        self._signals.setdefault(sid, {"status": "SEEN", "terminal": False})
        key = (str(event.get("symbol", "")), str(event.get("direction", "")))

        if et == ENTRY_PENDING:
            self._pending[sid] = dict(event["payload"])
            self._active[key] = sid
            self._signals[sid] = {"status": ENTRY_PENDING, "terminal": False}
        elif et == PENDING_UPDATED:
            # Quote watermark update (M-2); pending set is otherwise unchanged.
            self._pending[sid] = dict(event["payload"])
        elif et in (MARKET_FILLED, PENDING_TRIGGERED):
            # Legacy transactional rows: kept readable for compat. They do NOT
            # create an open position; only VIRTUAL_OPEN does (M-1).
            if sid in self._pending:
                del self._pending[sid]
        elif et == VIRTUAL_OPEN:
            # Single authoritative fill+open event (M-1).
            self._pending.pop(sid, None)
            self._open[sid] = dict(event["payload"])
            self._active[key] = sid
            self._signals[sid] = {"status": VIRTUAL_OPEN, "terminal": False}
        elif et in NO_TRADE_TERMINAL:
            if sid in self._pending and self._active.get(key) == sid:
                del self._active[key]
            self._pending.pop(sid, None)
            self._signals[sid] = {"status": et, "terminal": True}
        elif et in CLOSED_STATES:
            self._open.pop(sid, None)
            if self._active.get(key) == sid:
                del self._active[key]
            self._signals[sid] = {"status": et, "terminal": True}
            self._closed.append(dict(event))
        elif et in EXECUTION_TERMINAL:
            # The real order behind the VIRTUAL_OPEN was not placed: retract the
            # phantom open and release the slot. Never counted as a trade/close.
            self._open.pop(sid, None)
            if self._active.get(key) == sid:
                del self._active[key]
            self._signals[sid] = {"status": et, "terminal": True}
            self._exec_failed.append(dict(event))
        elif et == EXTERNAL_STATE_CONFLICT:
            self._open.pop(sid, None)
            if self._active.get(key) == sid:
                del self._active[key]
            self._excluded.add(sid)
            self._signals[sid] = {"status": et, "terminal": True}
        elif et in (DUPLICATE_SKIPPED, CONCURRENCY_SKIPPED):
            self._signals[sid] = {"status": et, "terminal": False}
        elif et == SIGNAL_RECEIVED:
            self._signals[sid] = {"status": SIGNAL_RECEIVED, "terminal": False}
            self._sig_meta[sid] = {
                "symbol": event.get("symbol", ""),
                "direction": event.get("direction", ""),
                "payload": dict(event["payload"]),
            }

        # Snapshots mirror the ACTIVE SET (pending / open). PENDING_UPDATED only
        # advances a quote watermark within an unchanged set, so it does not need
        # a rewrite (the watermark lives in the authoritative event log and is
        # rebuilt on replay). Replay writes nothing per event (see _replay).
        if not replay and et in (ENTRY_PENDING, VIRTUAL_OPEN,
                                 NO_TRADE_TERMINAL, MARKET_FILLED,
                                 PENDING_TRIGGERED, *CLOSED_STATES,
                                 EXECUTION_FAILED,
                                 EXTERNAL_STATE_CONFLICT):
            self._write_snapshots()

    # ── atomic snapshot rewrite ──────────────────────────────────────────────

    def _write_snapshots(self) -> None:
        """Refresh the derived snapshots. Best-effort; never fatal.

        The append-only event log is authoritative and these files are rebuilt
        from it on startup, so a snapshot write failure must never abort the
        decision path or block order routing. Failures are counted and stored.
        """
        for path, rows in ((self.pending_snapshot, self._pending),
                           (self.open_snapshot, self._open)):
            try:
                self._atomic_rewrite(path, rows)
            except OSError as exc:
                self.snapshot_write_failures += 1
                self.last_snapshot_error = f"{path.name}: {type(exc).__name__}: {exc}"

    def _atomic_rewrite(self, path: Path, rows: Dict[str, Dict[str, Any]]) -> None:
        last_exc: Optional[BaseException] = None
        for attempt in range(SNAPSHOT_WRITE_ATTEMPTS):
            fd, tmp = tempfile.mkstemp(dir=str(self.data_dir), suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    for sid, row in rows.items():
                        f.write(json.dumps({"signal_id": sid, **row}) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, path)
                return
            except OSError as exc:
                last_exc = exc
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                if attempt + 1 < SNAPSHOT_WRITE_ATTEMPTS:
                    time.sleep(SNAPSHOT_WRITE_BACKOFF_SECONDS * (attempt + 1))
            except Exception:
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                raise
        if last_exc is not None:
            raise last_exc

    # ── queries / guards (idempotency + concurrency) ─────────────────────────

    def has_signal(self, signal_id: str) -> bool:
        """True if a REAL lifecycle record exists for the signal.

        Keyed off the SIGNAL_RECEIVED reconstruction record (`_sig_meta`):
        audit-only rows (DUPLICATE_SKIPPED / CONCURRENCY_SKIPPED) do NOT count
        as "processed" — otherwise the loser of a concurrent race could write a
        DUPLICATE_SKIPPED row that makes the winner's post-claim refresh see
        the signal as already handled (review C-1 regression).
        """
        return signal_id in self._sig_meta

    def is_terminal(self, signal_id: str) -> bool:
        return bool(self._signals.get(signal_id, {}).get("terminal"))

    def acquires(self, symbol: str, direction: str) -> bool:
        """True if (symbol, direction) is free of an active pending/open (D-7)."""
        return (symbol, direction) not in self._active

    def signals(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._signals)

    def pending(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._pending)

    def pending_entry(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return self._pending.get(signal_id)

    def open_positions(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._open)

    def open_position(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return self._open.get(signal_id)

    def get_signal(self, signal_id: str):
        """Return the stored ExecutionSignal parameters for a signal id."""
        return {k: v for k, v in (self._signals.get(signal_id, {}) or {}).items()}

    def signal_meta(self, signal_id: str) -> Optional[Dict[str, Any]]:
        """Restart-safe reconstruction record: {symbol, direction, payload} as
        captured by SIGNAL_RECEIVED. None when the signal was never received."""
        return self._sig_meta.get(signal_id)

    def note_last_quote(self, signal_id: str, price: float) -> None:
        self._last_quote[signal_id] = price

    def last_quote(self, signal_id: str) -> Optional[float]:
        return self._last_quote.get(signal_id)

    def closed_records(self) -> List[Dict[str, Any]]:
        """All closed lifecycle records (CLOSED_*) — metrics contract: apply
        `core.invalid_fills.partition` before counting performance."""
        return [dict(e) for e in self._closed]

    def execution_failures(self) -> List[Dict[str, Any]]:
        """EXECUTION_FAILED records: virtual opens whose real order was never
        placed. NOT trades — must be excluded from every performance metric."""
        return [dict(e) for e in self._exec_failed]

    def excluded_signal_ids(self) -> set:
        return set(self._excluded)

    def event_count(self) -> int:
        return len(self._events)

    def events(self) -> List[Dict[str, Any]]:
        """Immutable snapshot of the replayed event log (test/report use)."""
        return [dict(e) for e in self._events]

    # ── startup reconciliation (automatic, M-3) ──────────────────────────────

    def reconcile(self, now: Optional[datetime] = None) -> List[Dict[str, str]]:
        """Expire any pending whose validity window (t0 + 10 min) has lapsed.

        Appends EXPIRED_UNFILLED records for expired pendings. Open positions
        are NOT auto-closed here: closing requires observed quotes via
        LifecycleEngine.advance/close_timeout. Idempotent: no-op when nothing
        is pending. Called automatically at startup (LifecycleStore.__init__);
        the public method remains available for explicit use.
        """
        now = now or self.now_fn()
        expirations: List[Dict[str, str]] = []
        for sid, pend in list(self._pending.items()):
            texp = parse_utc(pend["texp_utc"]) if pend.get("texp_utc") else None
            if texp is not None and now > texp:
                self.append(EXPIRED_UNFILLED, sid, pend.get("symbol", ""),
                            pend.get("direction", ""), {
                                "reason": "reconciled_expired",
                                "texp_utc": pend["texp_utc"],
                                "expired_at_utc": now.astimezone(timezone.utc).isoformat(),
                                "last_quote": self.last_quote(sid),
                            })
                expirations.append({"signal_id": sid, "reason": "reconciled_expired"})
        return expirations

    def integrity_summary(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "events": self.event_count(),
            "pending_active": len(self._pending),
            "open_active": len(self._open),
            "closed": len(self._closed),
            "execution_failed": len(self._exec_failed),
            "excluded_state_conflicts": sorted(self._excluded),
            "corrupt_tail": self.corrupt_tail,
            "corrupt_mid": self.corrupt_mid,
            "duplicate_event_ids": self.duplicate_event_ids,
        }