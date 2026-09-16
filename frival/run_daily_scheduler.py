# -*- coding: utf-8 -*-
"""Frival Daily Pipeline Scheduler — UTC-calibrated session window.

Double-click run_daily.bat → this script runs the 5-pair pipeline at every
hourly :01 target within the FULL legitimate FX session window, every day,
rolling over at midnight Panama.

Calibration (verified live 2026-09-16):
    The session gate in main.py / signal_gate.py tests
    `latest["datetime"].hour` where the H1 bar datetime comes from
    `pd.to_datetime(mt5_epoch, unit="s")` — which is a clean UTC clock
    (a live probe at 13:39 UTC returned stored hour == real UTC hour == 13).
    The gate accepts evaluated-bar hours in [7,16) U [13,22) = 07..21 UTC.

    A :01 run at UTC hour X evaluates the bar that opened at X:00 (it closed
    at :00, so the run at :01 sees exactly that completed bar). Panama = UTC-5,
    so valid PANAMA run hours are X-5 for X in 07..21  =>  02..16.

    => Window: 02:01 .. 16:01 Panama local (15 hourly runs/day), the exact
       London/NY window the models were calibrated on. No wasted predawn runs
       outside the gate.

Rollover: after the last target, waits until Panama midnight, recomputes the
next day's targets, and continues — click once, leave the window open.

No cron, no Task Scheduler. Just keep the terminal window open.
"""
import os
import sys
import time
from datetime import datetime, timedelta

# ── Session config ─────────────────────────────────────────────────────────────
# Run at :01 (let the H1 bar close first).
TARGET_MINUTE = 1
# Valid PANAMA run hours: gate allows evaluated-bar UTC hours 07..21,
# Panama = UTC-5  =>  run hours 02..16.
TARGET_HOURS = list(range(2, 17))        # 02..16 inclusive
UTC_OFFSET = -5                           # America/Panama (no DST)
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


def build_targets(run_hours: list, day=None):
    """:01 targets (Panama local) for the given hours on `day` (default today)."""
    day = day or now_local().date()
    targets = []
    for h in run_hours:
        targets.append(datetime(day.year, day.month, day.day, h, TARGET_MINUTE, 0))
    return targets


def seconds_until(target):
    """Seconds from now (UTC) to the given Panama-local datetime."""
    target_utc = target - timedelta(hours=UTC_OFFSET)
    return max(0.0, (target_utc - datetime.utcnow()).total_seconds())


def countdown_loop(secs, target):
    """Sleep until target, printing countdown updates."""
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
        remaining = int(seconds_until(target))  # drift correction


def _fmt(dt):
    return dt.strftime("%I:%M %p")


def run_pipeline():
    """Execute the full 5-pair pipeline + execution bot."""
    from main import run_live, execute_pending

    t0 = time.time()
    for pair in PAIRS:
        run_live(borderline=True, pair=pair)
    execute_pending()
    elapsed = time.time() - t0
    sys.stdout.write(f"\r{' ':80}\r")
    print(f"[LIVE] Pipeline completed in {elapsed:.0f}s  ({_fmt(now_local())})\n")


def _sleep_until_next_midnight():
    """Wait until Panama local midnight (00:00), printing a countdown."""
    while True:
        now = now_local()
        tomorrow = now.date() + timedelta(days=1)
        midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
        wait = (midnight - now).total_seconds()
        if wait <= 0:
            break
        sys.stdout.write(f"\r[WAITING] Next day starts in {int(wait)//60:>3d} min "
                         f"(at 12:00 AM local)   ")
        sys.stdout.flush()
        time.sleep(min(wait, 300))      # wake every 5 min to re-check alignment


# ── Main loop (ROLLING — stays alive across days) ──────────────────────────────
if __name__ == "__main__":
    print(f"[START] Scheduler started at {_fmt(now_local())} local  (UTC{UTC_OFFSET:+d})")
    print(f"[START] Stays alive 24/7: runs every hourly :01 in the valid session "
          f"window (Panama {_fmt(build_targets(TARGET_HOURS)[0])} - "
          f"{_fmt(build_targets(TARGET_HOURS)[-1])}) and rolls over at midnight.\n")

    run_count_total = 0

    while True:
        targets = build_targets(TARGET_HOURS)   # today's targets
        last_target = targets[-1]

        now = now_local()
        print(f"[DAY] {now.strftime('%Y-%m-%d')} — valid run hours: "
              f"{', '.join(f'{h:02d}:01' for h in TARGET_HOURS)}")

        # Immediate run if we're inside today's window (before last target)
        if now < last_target:
            print(f"[LIVE] Running initial pipeline... ({_fmt(now)})")
            run_pipeline()
            run_count_total += 1

        # Fire every remaining :01 target, then roll to the next day
        while True:
            pending = [t for t in targets if t > now_local()]
            if not pending:
                print(f"[DONE] Today's session complete after {run_count_total} "
                      f"run(s). Waiting for tomorrow at 02:01 local.\n")
                _sleep_until_next_midnight()
                break       # roll over for the new day

            next_run = pending[0]
            wait = seconds_until(next_run)
            if wait < 1.0:
                print(f"[LIVE] Running pipeline... ({_fmt(now_local())})")
                run_pipeline()
                run_count_total += 1
                continue

            print(f"[WAITING] Next run at {_fmt(next_run)} local  ({wait:.0f}s from now)")
            countdown_loop(wait, next_run)

            print(f"[LIVE] Running pipeline... ({_fmt(now_local())})")
            run_pipeline()
            run_count_total += 1