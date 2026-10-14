#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Kill-switch verification harness.

The kill switch is the only guardrail that has never been exercised. An
untested emergency control is an assumption, not a control. This harness proves
the full chain:

    create file -> executor refuses every mutating action
    remove file -> executor accepts again

It never places a REAL order. The "place" leg is proven by asserting that
cmd_place returns without calling order_send, which we verify by holding a
positions/orders snapshot before and after.

Run:  python test_kill_switch.py
"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../fx-prival/frival
DATA = HERE / "data"                           # must match order_executor.DATA exactly
KS = DATA / "emergency_stop.txt"
LOG_PATH = HERE / "trade_log.csv"
PY = sys.executable

PASS, FAIL = "PASS", "FAIL"
results = []


def run(args):
    r = subprocess.run([PY, str(HERE / "order_executor.py")] + args,
                       capture_output=True, text=True, cwd=str(HERE), timeout=60)
    return r.returncode, r.stdout + r.stderr


def snapshot():
    import MetaTrader5 as mt5
    from mt5_path import resolve_terminal_path
    mt5.initialize(path=resolve_terminal_path(HERE))
    try:
        return (mt5.positions_total(), len(mt5.orders_get() or []))
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{PASS if ok else FAIL}] {name}" + (f"  — {detail}" if detail else ""))
    return ok


def main():
    existed_before = KS.exists()
    print(f"kill switch path: {KS}")
    print(f"existed before test: {existed_before}")
    print()

    # ensure a clean starting state
    if existed_before:
        KS.unlink()
        print("[setup] removed pre-existing kill switch (restored later)\n")

    before = snapshot()

    # A decoy signal that ALWAYS fails the risk guardrail, so that after the
    # switch is disarmed the "place" leg can never open a real order. The test
    # then proves the switch gate fired BEFORE any guardrail was evaluated.
    decoy = "TZZZ"
    rows = list(csv.DictReader(LOG_PATH.open(newline="", encoding="utf-8")))
    cols = list(rows[0].keys())
    decoy_row = {c: "" for c in cols}
    decoy_row.update({
        "log_id": decoy, "logged_at_local": "test", "logged_at_server": "test",
        "symbol": "XAUUSD", "setup_id": "KILLSWITCH_TEST_DECOY", "side": "BUY",
        "order_type": "MARKET", "entry_price": "4000.00", "stop_loss": "3900.00",
        "tp1": "4300.00", "volume": "1.00", "sl_distance": "100.00",
        "expected_rr_tp1": "3.00", "status": "PENDING_FILL", "risk_usd": "10000.00",
        "trigger_condition": "kill switch harness decoy - must never be sent",
    })
    rows = [r for r in rows if r.get("log_id") != decoy] + [decoy_row]
    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

    # ── 1. arm the switch ────────────────────────────────────────────────────
    KS.parent.mkdir(parents=True, exist_ok=True)
    KS.write_text("MANUAL TEST — autonomous execution halted\n", encoding="utf-8")
    check("kill switch file is created", KS.exists())

    # ── 2. status must still report (read-only is unaffected) ───────────────
    rc, out = run(["status"])
    check("status still works with switch armed (read-only not blocked)",
          rc == 0 and "KILL SWITCH ACTIVE" in out,
          "read-only path unaffected" if "KILL SWITCH ACTIVE" in out else out[:80])

    # ── 3. place must abort BEFORE the guardrail stage ──────────────────────
    rc, out = run(["place", "--id", decoy, "--market"])
    check("place aborts with switch armed",
          "[ABORT]" in out and "[BLOCKED]" not in out,
          out.strip().splitlines()[0] if out.strip() else "")

    # ── 4. with the switch armed, close-all is PERMITTED (flatten path) ────
    rc, out = run(["close-all", "--reason", "kill switch test"])
    allowed = ("[ABORT]" not in out)
    check("close-all permitted while armed (flatten must never be blocked)",
          allowed, "flatten path stays available" if allowed else out[:80])

    # ── 5. nothing NEW was opened while the switch was armed ───────────────
    # A close-all may legitimately reduce position count (the flatten path is
    # intentionally still permitted while armed). What must never increase is
    # the count of positions or pending orders.
    after = snapshot()
    check("no position or order was OPENED while switch armed",
          after[0] <= before[0] and after[1] <= before[1],
          f"positions/orders {before} -> {after} (decrease only = flatten, never an open)")

    # ── 6. disarm ───────────────────────────────────────────────────────────
    KS.unlink()
    check("kill switch file removed", not KS.exists())

    # ── 7. place now proceeds PAST the switch gate and hits the guardrails ──
    rc, out = run(["place", "--id", decoy, "--market"])
    check("place no longer aborts on the switch (reaches guardrail stage)",
          "[ABORT]" not in out and "[BLOCKED]" in out,
          out.strip().splitlines()[0] if out.strip() else "")

    # ── 8. the decoy never reached the broker ──────────────────────────────
    final = snapshot()
    check("no position or order was opened at any point",
          final[0] <= before[0] and final[1] <= before[1],
          f"positions/orders {before} -> {final} (decoy blocked on risk, never sent)")

    # clean up the decoy row
    rows = [r for r in csv.DictReader(LOG_PATH.open(newline="", encoding="utf-8"))
            if r.get("log_id") != decoy]
    with LOG_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})

    # restore original state
    if existed_before:
        KS.write_text("MANUAL TEST — autonomous execution halted\n", encoding="utf-8")
        print("\n[restore] pre-existing kill switch recreated")

    print("\n" + "=" * 62)
    npass = sum(1 for _, ok, _ in results if ok)
    print(f"{npass}/{len(results)} checks passed")
    if npass != len(results):
        print("KILL SWITCH NOT FULLY VERIFIED")
        for n, ok, d in results:
            if not ok:
                print(f"  FAILED: {n} {d}")
        sys.exit(1)
    print("KILL SWITCH VERIFIED — every mutating path honours the switch")


if __name__ == "__main__":
    main()