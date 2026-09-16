# -*- coding: utf-8 -*-
"""Frival Daily Pipeline Scheduler — DYNAMIC session window.

Double-click run_daily.bat → this script runs the 5-pair pipeline at every
hourly :01 target within the FULL valid FX session window.

Why dynamic:
    The session gate in main.py/signal_gate.py tests `latest["datetime"].hour`
    where the H1 bar timestamp is BROKER SERVER time (MT5 epoch, not UTC).
    FPMarkets server = UTC+3 (verified live). The gate allows server bar-open
    hours [7,15] U [13,21] (=7..21), so the pipeline may run at :01 for server
    run-hours 8..22 — i.e. ~07:00-19:00 UTC, 00-14:00 Panama.

    Instead of hardcoding a UTC/Panama table (which drifts if the broker
    changes its DST offset), this scheduler queries the live server-UTC offset
    from MT5 at launch and computes today's Panama-local targets from it.

No cron, no Task Scheduler. Just keep the terminal window open.
"""
import os
import sys
import time
from datetime import datetime, timedelta

# ── Session config ─────────────────────────────────────────────────────────────
# Run at :01 (let the H1 bar close first).
TARGET_MINUTE = 1
# Session-gate valid RUN server-hours: bar-open [7,21] => run hour = open+1 => [8,22].
# Within these server hours the pipeline is inside the calibrated London/NY domain.
SESSION_RUN_SERVER_HOURS = list(range(8, 23))     # 8..22 inclusive
UTC_OFFSET = -5                                    # America/Panama (no DST)
PAIRS = ["EURUSD", "GBPUSD", "USDCHF", "USDCAD", "EURUSD_AGNOSTIC"]

# ── Environment ────────────────────────────────────────────────────────────────
os.environ.setdefault("MERG_ENABLED", "true")
os.environ.setdefault("MERG_SHADOW_ONLY", "true")

# Set CWD so frival imports resolve
sys.path.insert(0, ".")
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def query_server_utc_offset() -> float:
    """Live server-UTC offset (h) from MT5; fallback to +3.0 (FPMarkets)."""
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            try:
                t = mt5.symbol_info_tick("EURUSD")
                if t is not None:
                    return (t.time - time.time()) / 3600.0
            finally:
                mt5.shutdown()
    except Exception as e:
        print(f"[WARN] server-offset query failed, using +3.0: {e}")
    return 3.0


def panama_run_hours(server_offset: float) -> list:
    """Map valid server run-hours to Panama-local hours (0..23, sorted).

    server = utc + offset ; panama = utc - 5
    => panama = server - offset - 5  =  server - offset + UTC_OFFSET
    """
    hours = set()
    for sh in SESSION_RUN_SERVER_HOURS:
        ph = sh - server_offset + UTC_OFFSET
        if 0 <= ph <= 23:
            hours.add(int(ph))
    return sorted(hours)


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
    now = now_local()
    tomorrow = now.date() + timedelta(days=1)
    midnight = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 0, 0, 0)
    while True:
        wait = (midnight - now_local()).total_seconds()
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
          f"window each day, rolls over at midnight. Click once; leave the "
          f"window open.\n")

    run_count_total = 0

    while True:
        server_offset = query_server_utc_offset()
        run_hours = panama_run_hours(server_offset)
        targets = build_targets(run_hours)          # today's targets
        last_target = targets[-1] if targets else None

        now = now_local()
        print(f"[DAY] {now.strftime('%Y-%m-%d')} — server UTC+{server_offset:.0f} h; "
              f"valid run hours: {', '.join(f'{h:02d}:01' for h in run_hours)}")

        if last_target is None:
            print("[DAY] No valid session hours today; waiting for tomorrow.")
            _sleep_until_next_midnight()
            continue

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
                      f"run(s). Waiting for tomorrow at 00:01 local.\n")
                _sleep_until_next_midnight()
                break       # roll over: recompute hours/offset for the new day

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