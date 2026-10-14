"""Per-cycle data-quality gate instrumentation (MEASUREMENT ONLY).

Records, for each symbol, which data-quality gate (if any) blocked an entry at
this cycle, appending a row to data/quality_gates.csv. It places NO orders and
changes NO trading behaviour - it exists so we can tell "FX had no setups" apart
from "FX was blocked by the spread gate" over days, before deciding whether to
add a bounded FX exploration quota.

Gates (from the desk brief), evaluated in this priority order:
  1. ROLLOVER  - server clock in the daily close window 00:00-01:00
  2. STALE     - tick age > 300s
  3. SPREAD    - spread > 50% of clean ATR(M5)
  4. FROZEN    - clean ATR(M5) < 1.0   (gold-scaled; XAUUSD only)
  5. THIN      - last completed M15 range > 2.0x clean ATR(M5)
A symbol with none of these is PASS. Structural-void / no-level is an agent
judgement and is deliberately NOT auto-scored here.

Usage:
  python quality_gate.py log     # compute now, append a row per symbol
  python quality_gate.py stats   # block-rate summary from the CSV
"""
import sys
import csv
import datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SYMBOLS = ("XAUUSD", "EURUSD", "USDJPY")
CSV_PATH = HERE / "data" / "quality_gates.csv"
COLUMNS = [
    "ts_utc", "ts_server", "symbol", "bid", "ask", "spread", "atr5",
    "spread_pct_atr", "m15_range", "m15_ratio", "tick_age_s",
    "verdict", "blocked_by", "spread_only",
]


def _log(rows):
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    new = not CSV_PATH.exists()
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def cmd_log():
    import MetaTrader5 as mt5
    import pandas as pd
    from mt5_path import resolve_terminal_path

    if not mt5.initialize(path=resolve_terminal_path(HERE)):
        print("init failed", mt5.last_error())
        return 1
    now_utc = dt.datetime.now(dt.timezone.utc)
    server_now = now_utc + dt.timedelta(hours=3)
    server_hm = server_now.hour * 60 + server_now.minute
    rows = []
    try:
        for sym in SYMBOLS:
            mt5.symbol_select(sym, True)
            tick = mt5.symbol_info_tick(sym)
            m5 = pd.DataFrame(mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 220))
            m15 = pd.DataFrame(mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M15, 0, 60))
            d = m5.tail(200).copy()
            med = d["tick_volume"].median()
            mask = (d["high"] != d["low"]) & (d["tick_volume"] >= 0.30 * med)
            c = d[mask]
            pc = c["close"].shift(1)
            tr = pd.concat([c["high"] - c["low"], (c["high"] - pc).abs(),
                            (c["low"] - pc).abs()], axis=1).max(axis=1)
            atr5 = float(tr.tail(14).mean())
            spread = float(tick.ask - tick.bid)
            age = server_now.timestamp() - tick.time
            # last *completed* M15 bar
            m15r = float(m15["high"].iloc[-2] - m15["low"].iloc[-2])
            spread_pct = (spread / atr5 * 100.0) if atr5 else 0.0
            m15_ratio = (m15r / atr5) if atr5 else 0.0

            blocked = ""
            if 0 <= server_hm < 60:
                blocked = "ROLLOVER"
            elif age > 300:
                blocked = "STALE"
            elif spread_pct > 50.0:
                blocked = "SPREAD"
            elif sym == "XAUUSD" and atr5 < 1.0:
                blocked = "FROZEN"
            elif m15_ratio > 2.0:
                blocked = "THIN"
            verdict = "PASS" if blocked == "" else "BLOCK"
            # spread_only: this symbol would be fine if not for the spread gate
            spread_only = "YES" if (blocked == "SPREAD") else ""
            rows.append({
                "ts_utc": now_utc.strftime("%Y-%m-%d %H:%M:%S"),
                "ts_server": server_now.strftime("%Y-%m-%d %H:%M:%S"),
                "symbol": sym,
                "bid": f"{tick.bid:.5f}", "ask": f"{tick.ask:.5f}",
                "spread": f"{spread:.5f}", "atr5": f"{atr5:.5f}",
                "spread_pct_atr": f"{spread_pct:.1f}",
                "m15_range": f"{m15r:.5f}", "m15_ratio": f"{m15_ratio:.2f}",
                "tick_age_s": f"{age:.0f}",
                "verdict": verdict, "blocked_by": blocked, "spread_only": spread_only,
            })
    finally:
        mt5.shutdown()
    _log(rows)
    for r in rows:
        print(f"{r['symbol']:7s} {r['verdict']:6s} {r['blocked_by']:9s} "
              f"spread={r['spread_pct_atr']}%atr  m15={r['m15_ratio']}xatr  age={r['tick_age_s']}s")
    return 0


def cmd_stats():
    if not CSV_PATH.exists():
        print("no data yet")
        return 0
    from collections import defaultdict, Counter
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    bysym = defaultdict(Counter)
    for r in rows:
        bysym[r["symbol"]][r["blocked_by"] or "PASS"] += 1
    print(f"quality_gates rows: {len(rows)}")
    for sym in SYMBOLS:
        c = bysym.get(sym)
        if not c:
            continue
        tot = sum(c.values())
        print(f"  {sym}: n={tot}  " + "  ".join(f"{k}={c[k]}" for k in
              ("PASS", "SPREAD", "THIN", "STALE", "ROLLOVER", "FROZEN") if c.get(k)))
        sp = c.get("SPREAD", 0)
        print(f"    spread-blocked {sp}/{tot} = {sp / tot * 100:.0f}%  "
              f"(the gate a bounded FX exploration would relax)")
    return 0


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "log"
    if mode == "log":
        return cmd_log()
    if mode == "stats":
        return cmd_stats()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
