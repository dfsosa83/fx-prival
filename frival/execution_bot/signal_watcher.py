"""
Signal Watcher — Monitors Frival JSONL output for new FIRED signals.

Polls the signals directory every second, reads new entries since the
last processed signal_id, validates trade levels, and queues them for
order execution.

State persisted in frival/execution_bot/data/watcher_state.json to
survive restarts.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List


SIGNALS_DIR = Path(__file__).resolve().parents[1] / "output" / "signals"
STATE_FILE = Path(__file__).resolve().parent / "data" / "watcher_state.json"


def load_state() -> Dict[str, Any]:
    """Load watcher state from disk. Returns empty state on first run."""
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_signal_id": None, "signals_processed": 0}


def save_state(state: Dict[str, Any]):
    """Persist watcher state to disk."""
    os.makedirs(STATE_FILE.parent, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)


def read_new_signals(last_signal_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Read all FIRED signals that appeared after last_signal_id.

    Scans signal JSONL files sorted by date, reads only new entries.
    Returns signals in chronological order (oldest first).
    """
    if not SIGNALS_DIR.exists():
        return []

    signals = []
    signal_files = sorted(SIGNALS_DIR.glob("**/*.jsonl"))

    for filepath in signal_files:
        with open(filepath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sig = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Skip non-FIRED signals
                if sig.get("final_decision") != "FIRED":
                    continue

                # Skip already-processed signals
                signal_id = sig.get("signal_id", "")
                if last_signal_id and signal_id == last_signal_id:
                    continue

                # Skip if we've already passed this signal in the file
                if last_signal_id and signal_id <= last_signal_id:
                    continue

                # Skip signals older than 24 hours or with unparseable timestamps
                ts = sig.get("timestamp_utc", "")
                try:
                    sig_dt = datetime.fromisoformat(ts)
                    if sig_dt.tzinfo is None:
                        sig_dt = sig_dt.replace(tzinfo=timezone.utc)
                    age = (datetime.now(timezone.utc) - sig_dt).total_seconds()
                    if age > 86400:  # 24 hours
                        continue
                except (ValueError, TypeError):
                    if ts:  # has timestamp but couldn't parse → skip
                        continue

                # Skip signals with zero trade levels (old format)
                trade = sig.get("trade", {})
                if trade.get("entry", 0) == 0 or trade.get("stop_loss", 0) == 0:
                    continue

                signals.append(sig)

    return signals


def validate_signal(sig: Dict[str, Any]) -> Optional[str]:
    """
    Validate that a signal has all required fields for order execution.
    Returns None if valid, or an error string if invalid.
    """
    trade = sig.get("trade", {})
    if not trade:
        return "missing trade block"

    required = ["entry", "stop_loss", "take_profit"]
    for field in required:
        val = trade.get(field)
        if val is None or val == 0:
            return f"missing or zero trade.{field}"

    if "symbol" not in sig or not sig["symbol"]:
        return "missing symbol"

    if "direction" not in sig or not sig["direction"]:
        return "missing direction"

    # Check expiry
    expires = trade.get("expires_at_utc", "")
    if expires:
        try:
            expiry_dt = datetime.fromisoformat(expires)
            if expiry_dt.tzinfo is None:
                expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expiry_dt:
                return f"expired at {expires}"
        except (ValueError, TypeError):
            pass

    return None


def watch_loop(callback, poll_seconds: float = 1.0):
    """
    Main polling loop. Calls `callback(signal_dict)` for each new FIRED signal.

    Parameters
    ----------
    callback : callable
        Function to call with each new signal. Should return True if the
        signal was handled (even if rejected), False on critical failure.
    poll_seconds : float
        Seconds between directory scans.
    """
    state = load_state()
    last_id = state.get("last_signal_id")
    count = state.get("signals_processed", 0)

    print(f"[Watcher] Starting — {count} signals processed so far.")
    print(f"[Watcher] Monitoring: {SIGNALS_DIR}")

    while True:
        try:
            new_signals = read_new_signals(last_id)
        except Exception as e:
            print(f"[Watcher] Error reading signals: {e}")
            time.sleep(poll_seconds)
            continue

        for sig in new_signals:
            sig_id = sig["signal_id"]
            pair = sig.get("symbol", "?")
            direction = sig.get("direction", "?")
            prob = sig.get("model", {}).get("probability", 0)

            error = validate_signal(sig)
            if error:
                print(f"[Watcher] SKIP {sig_id}: {error}")
                last_id = sig_id
                continue

            print(f"\n[Watcher] NEW SIGNAL: {pair} {direction} p={prob:.4f}")
            print(f"  Entry: {sig['trade']['entry']:.5f}  SL: {sig['trade']['stop_loss']:.5f}  TP: {sig['trade']['take_profit']:.5f}")

            try:
                success = callback(sig)
            except Exception as e:
                print(f"[Watcher] Callback error: {e}")
                success = False

            if not success:
                print(f"[Watcher] Signal {sig_id} NOT handled — will retry on next poll")

            last_id = sig_id
            count += 1
            state["last_signal_id"] = last_id
            state["signals_processed"] = count
            save_state(state)

        time.sleep(poll_seconds)