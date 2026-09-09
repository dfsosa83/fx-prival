# -*- coding: utf-8 -*-
"""Frival Daily Pipeline Scheduler.

Double-click run_daily.bat → this script runs the 5-pair pipeline at every :01
from 08:01 to 11:01 AM Panama time (UTC-5). First run fires immediately on start,
then the scheduler waits for the next :01 target. Displays countdown between runs
and exits after the final 11:01 execution.

No cron, no Task Scheduler. Just keep the terminal window open.
"""
import os
import sys
import time
from datetime import datetime, timedelta

# ── Session config ─────────────────────────────────────────────────────────────
# Panama = UTC-5, no DST. Target execution hours in Panama local time.
TARGET_HOURS = [8, 9, 10, 11]          # 08:01, 09:01, 10:01, 11:01 AM
TARGET_MINUTE = 1                       # fire at :01 (let the bar close first)
UTC_OFFSET = -5                         # America/Panama
PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "EURUSD_AGNOSTIC"]

# ── Environment ────────────────────────────────────────────────────────────────
os.environ.setdefault("MERG_ENABLED", "true")
os.environ.setdefault("MERG_SHADOW_ONLY", "true")

# Set CWD so frival imports resolve
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def now_local():
    """Current naive datetime in Panama local time (UTC-5)."""
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)


def next_target(local_dt):
    """Return the next :01 target datetime (Panama local), or None if done.

    If all TARGET_HOURS for today have passed, returns None.
    If the current minute is past :01 for a valid hour, skips to the next hour.
    If local_dt is already exactly at or past :01, the NEXT valid hour is found.
    """
    today = local_dt.date()
    for h in TARGET_HOURS:
        target = datetime(today.year, today.month, today.day, h, TARGET_MINUTE, 0)
        if target > local_dt:
            return target
    return None


def seconds_until(target):
    """Seconds from now (UTC) to the given Panama-local target datetime."""
    # target is in Panama-local naive.  Convert to UTC by subtracting UTC_OFFSET.
    target_utc = target - timedelta(hours=UTC_OFFSET)
    now_utc = datetime.utcnow()
    delta = (target_utc - now_utc).total_seconds()
    return max(0.0, delta)


def countdown_loop(secs, target):
    """Sleep until target, printing countdown updates every 60s or 10s."""
    remaining = int(secs)
    while remaining > 0:
        if remaining > 60:
            mins = remaining // 60
            sys.stdout.write(f"\r[WAITING] Next run in {mins:>3d} min  "
                             f"(at {_fmt(target)} local)   ")
        else:
            sys.stdout.write(f"\r[WAITING] Next run in {remaining:>3d} sec "
                             f"(at {_fmt(target)} local)   ")
        sys.stdout.flush()
        snooze = min(remaining, 60) if remaining > 10 else min(remaining, 10)
        time.sleep(snooze)
        remaining = int(seconds_until(target))  # re-compute for drift correction


def _fmt(dt):
    """Format a datetime as HH:MM AM/PM."""
    return dt.strftime("%I:%M %p")


def run_pipeline():
    """Execute the full 5-pair pipeline + execution bot."""
    from main import run_live, execute_pending

    t0 = time.time()
    for pair in PAIRS:
        run_live(borderline=True, pair=pair)
    execute_pending()
    elapsed = time.time() - t0
    sys.stdout.write(f"\r{' ':80}\r")   # clear countdown line
    print(f"[LIVE] Pipeline completed in {elapsed:.0f}s  ({_fmt(now_local())})\n")


# ── Main loop ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    local_now_dt = now_local()
    print(f"[START] Scheduler started at {_fmt(local_now_dt)} local  "
          f"(UTC{UTC_OFFSET:+d})\n")

    # 1) Immediate first run (unless we're already past 11:01)
    if local_now_dt.hour < (TARGET_HOURS[-1] + 1) or (
        local_now_dt.hour == TARGET_HOURS[-1] and local_now_dt.minute < TARGET_MINUTE + 2
    ):
        print(f"[LIVE] Running initial pipeline... ({_fmt(local_now_dt)})\n")
        run_pipeline()
    else:
        print("[DONE] Already past 11:01 AM. No executions remaining.\n")
        sys.exit(0)

    # 2) Loop for remaining :01 targets
    run_count = 1
    while True:
        next_run = next_target(now_local())
        if next_run is None:
            print(f"[DONE] Last execution complete. Session ended after "
                  f"{run_count} run(s).  ({_fmt(now_local())})\n")
            break

        wait = seconds_until(next_run)
        if wait < 1.0:
            # Already at the target — run immediately
            print(f"\n[LIVE] Running pipeline... ({_fmt(now_local())})\n")
            run_pipeline()
            run_count += 1
            continue

        print(f"[WAITING] Next run at {_fmt(next_run)} local  "
              f"({wait:.0f}s from now)")
        countdown_loop(wait, next_run)

        # Arrived — execute
        print(f"\n[LIVE] Running pipeline... ({_fmt(now_local())})\n")
        run_pipeline()
        run_count += 1