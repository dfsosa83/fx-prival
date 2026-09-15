# -*- coding: utf-8 -*-
"""Real-data sanity walk: run the state machine over cached live XAUUSD bars.

LOG-ONLY validation (design doc §3.1 / Step 5 gate): feeds the engine the real
M15 fixture bars one at a time and prints the decision journal. No MT5 calls,
no orders. Proves the engine is decision-sane on genuine FPMarkets data before
the launcher is built.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

GOLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GOLD))

import engine as eng  # noqa: E402
from engine import EngineState  # noqa: E402
from tests import fetch_data  # noqa: E402


def last_n(df: pd.DataFrame, n: int) -> pd.DataFrame:
    return df.tail(n).reset_index(drop=True)


def main():
    m15_all, m30_all, h1_all = fetch_data.ensure_fixtures(days=14)
    m15 = last_n(m15_all, 900)
    m30 = last_n(m30_all, 200)
    h1 = last_n(h1_all, 80)

    e = eng.default_engine()
    state = EngineState()
    actions = Counter()
    entries = 0
    print(f"[sanity] walking {len(m15)} real XAUUSD M15 bars "
          f"({m15['datetime'].iloc[0]} .. {m15['datetime'].iloc[-1]})\n")

    for i in range(len(m15)):
        frame = m15.iloc[: i + 1]
        last = frame.iloc[-1]
        s = eng.Snapshot(
            m15_df=frame,
            m30_df=m30 if i >= 0 else m30,
            h1_df=h1,
            utc_now=last["datetime"] + pd.Timedelta(minutes=16),
            bid=float(last["close"]),
            ask=float(last["close"]) + 0.2,
            open_positions=0,
            today_realized_pnl=0.0,
        )
        new_state, dec = e.evaluate(s, state)
        state = new_state
        actions[dec.action] += 1
        if dec.action == eng.ENTRY:
            entries += 1
            print(f"\n>>> ENTRY candidate at {last['datetime']} "
                  f"price={last['close']:.2f}")
            print(f"    reason: {dec.reason}")
            print(f"    gates: { {k: v for k, v in dec.gate_results.items() if k != 'pass'} }")
            if dec.order:
                print(f"    order: {dec.order}")
            state = EngineState()  # prevent repeated entries on same setup

    print(f"\n[sanity] action histogram over {len(m15)} bars:")
    for k, v in sorted(actions.items(), key=lambda x: -x[1]):
        print(f"    {k:>10}: {v}")
    print(f"[sanity] final state: {state.state}")

    if entries == 0:
        print("\n[sanity] NO entries on this window — expected if no confirmed "
              "setup completed. Engine ran cleanly (no ERROR) or entries would "
              "have shown. Check histogram for anomalies.")
    assert actions[eng.ERROR] == 0, f"engine produced ERROR actions: {actions[eng.ERROR]}"
    print("[sanity] PASS: no ERROR actions; engine is decision-sane on live data.")


if __name__ == "__main__":
    main()