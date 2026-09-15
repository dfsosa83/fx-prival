# -*- coding: utf-8 -*-
"""Gold engine status summary — answers "is it working / did it trade?"

Prints, from the persisted journal + state:
  - current engine state (WATCH_ZONE / IN_TRADE / ...)
  - today's signal activity (actions histogram per session)
  - any order sent / position closed (ORDER_SENT, CLOSE_POSITION)
  - last N journal lines useful for a quick health check

Run anytime while the engine is running:
    python gold_rules/status.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
STATE_FILE = HERE / "state" / "engine_state.json"
JOURNAL_DIR = HERE / "journal"

ACTION_LABELS = {
    "ENTRY": "ENTRY SENT",
    "ORDER_SENT": "ORDER SENT",
    "CLOSE_POSITION": "POSITION CLOSED",
    "INVALIDATE": "INVALIDATED",
    "BE": "BREAK-EVEN",
    "TRAIL": "TRAIL UPDATED",
    "CONFIRM": "CONFIRMED",
    "DROP": "SETUP DROPPED",
    "WATCH": "WATCHING BREAK",
}


def main():
    print("=" * 60)
    print("Gold Rules Engine — status")
    print("=" * 60)

    if STATE_FILE.exists():
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        print(f"\nState      : {st.get('state')}")
        print(f"H1 bias    : {st.get('h1_bias')}")
        print(f"Direction  : {st.get('direction')}")
        print(f"Watched    : {st.get('watched_level')}")
        print(f"Active trd : {st.get('active_trade')}")
        print(f"Last action: {st.get('last_action')} — {st.get('last_reason')}")
        print(f"Updated    : {st.get('updated_at')}")
    else:
        print("\n[no state file yet — engine has not run]")

    print("\nSession activity (today + existing journals):")
    files = sorted(JOURNAL_DIR.glob("*.jsonl")) if JOURNAL_DIR.exists() else []
    totals = Counter()
    orders = []
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except Exception:
                continue
            act = d.get("action")
            totals[act] += 1
            if act in ("ORDER_SENT", "CLOSE_POSITION", "ENTRY"):
                orders.append((f.stem, d.get("ts"), act, d.get("result", d.get("order", ""))))
    if not files:
        print("  (no journals yet)")
    else:
        for k, v in totals.most_common():
            label = ACTION_LABELS.get(k, k)
            print(f"  {label:<16}: {v}")
    if orders:
        print("\nTrade events:")
        for when, ts, act, detail in orders:
            print(f"  {when} {ts}  {act}  {detail}")
    else:
        print("\nNo trade events yet — engine is still watching for a confirmed setup.")


if __name__ == "__main__":
    main()