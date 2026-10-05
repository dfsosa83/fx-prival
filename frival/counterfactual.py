#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Counterfactual recorder — the missing selection-bias leg.

WHY THIS EXISTS
---------------
The trade log records what the agent DID. That measures setup quality but
cannot answer "is the filter better than doing nothing?" A system taking
3 trades per quarter and winning 2 shows a 100% win rate with zero edge.
Proving skill requires the outcome of the setups that were NOT taken.

This module logs every considered-but-rejected setup with the same
structure as a real signal, then resolves its counterfactual: given the
recorded entry, SL and TP, what would the path have done?

The counterfactual is computed the same way the ML notebooks build their
path-dependent labels — TP touched before SL over a forward window — so
live outcomes and model targets are directly comparable.

IT NEVER PLACES ORDERS. Read-only against MT5.

Usage:
    python counterfactual.py consider --id C001 --symbol XAUUSD --side SELL \
        --order-type LIMIT --volume 0.02 --entry 4179.50 --sl 4187.00 \
        --tp1 4163.30 --trigger "M15 rejection at 4179.83" \
        --reject-reason SPREAD_HIGH

    python counterfactual.py resolve --id C001      # force an early resolve
    python counterfactual.py sweep                 # resolve all past horizon
    python counterfactual.py show [--id C001]
    python counterfactual.py stats                 # selectivity + hit rate
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "counterfactuals.csv"
from mt5_path import resolve_terminal_path

TERMINAL_PATH = resolve_terminal_path(HERE)

FORWARD_BARS_DEFAULT = 30          # ~2.5h on M5, matches notebook horizon scale
RESOLVE_GRACE_BARS = 2             # don't resolve on the same bar as the signal

COLUMNS = [
    "cf_id", "logged_at_local", "logged_at_server", "symbol", "side", "order_type",
    "volume", "entry_price", "stop_loss", "tp1", "sl_distance", "rr_tp1",
    "signal_bar_time_server", "signal_close", "signal_atr_m5", "spread_at_signal",
    "reject_reason", "trigger_condition", "horizon_bars", "resolved_bar_time_server",
    "outcome", "bars_held", "tp_touched", "sl_touched", "first_touch",
    "mfe", "mae", "adverse_first", "would_be_r_usd", "notes",
]

PIP = {"XAUUSD": 0.01, "EURUSD": 0.0001, "USDJPY": 0.01}


def _mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        print("[ERROR] MetaTrader5 package missing. Use anaconda3 python.")
        sys.exit(1)
    if not mt5.initialize(path=TERMINAL_PATH):
        print(f"[ERROR] mt5.initialize failed: {mt5.last_error()}")
        sys.exit(1)
    return mt5


def _now():
    utc = dt.datetime.utcnow()
    return ((utc + dt.timedelta(hours=-5)).strftime('%Y-%m-%d %H:%M:%S'),
            (utc + dt.timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S'))


def _load():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def _save(rows):
    with CSV_PATH.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in COLUMNS})


def _next_id(rows):
    n = 0
    for r in rows:
        v = r.get('cf_id', '')
        if v.startswith('C') and v[1:].isdigit():
            n = max(n, int(v[1:]))
    return f'C{n + 1:03d}'


def cmd_consider(a):
    import pandas as pd
    rows = _load()
    cf_id = a.id or _next_id(rows)
    local_ts, server_ts = _now()

    mt5 = _mt5()
    try:
        info = mt5.symbol_info(a.symbol)
        tick = mt5.symbol_info_tick(a.symbol)
        d = pd.DataFrame(mt5.copy_rates_from_pos(a.symbol, mt5.TIMEFRAME_M5, 0, 80))
        pc = d['close'].shift(1)
        tr = pd.concat([d['high'] - d['low'], (d['high'] - pc).abs(),
                        (d['low'] - pc).abs()], axis=1).max(axis=1)
        vol_med = d['tick_volume'].median()
        clean = d[~((d['high'] == d['low']) | (d['tick_volume'] < vol_med * 0.30))]
        atr = round((pd.concat([clean['high'] - clean['low'],
                                (clean['high'] - clean['close'].shift(1)).abs(),
                                (clean['low'] - clean['close'].shift(1)).abs()],
                               axis=1).max(axis=1)).tail(14).mean(), 4)
        last_bar = int(d['time'].iloc[-1])
        sig_close = float(d['close'].iloc[-1])
    finally:
        mt5.shutdown()

    entry = float(a.entry)
    sl = float(a.sl)
    tp1 = float(a.tp1)
    sl_dist = abs(entry - sl)
    rr = abs(tp1 - entry) / sl_dist if sl_dist else 0.0
    ps = PIP.get(a.symbol, 0.0001)
    spread_pips = (info.spread * info.trade_tick_size / ps) if info else ''

    row = {c: '' for c in COLUMNS}
    row.update({
        'cf_id': cf_id, 'logged_at_local': local_ts, 'logged_at_server': server_ts,
        'symbol': a.symbol, 'side': a.side.upper(), 'order_type': a.order_type.upper(),
        'volume': a.volume, 'entry_price': entry, 'stop_loss': sl, 'tp1': tp1,
        'sl_distance': f'{sl_dist:.5f}', 'rr_tp1': f'{rr:.2f}',
        'signal_bar_time_server': str(last_bar), 'signal_close': f'{sig_close:.5f}',
        'signal_atr_m5': atr, 'spread_at_signal': f'{spread_pips:.1f}',
        'reject_reason': a.reject_reason, 'trigger_condition': a.trigger,
        'horizon_bars': a.horizon, 'outcome': 'PENDING', 'notes': a.notes,
    })
    rows.append(row)
    _save(rows)
    print(f'[{cf_id}] logged {a.side.upper()} {a.symbol} @ {entry} '
          f'SL {sl} TP {tp1} R:R {rr:.2f}')
    print(f'   reject_reason: {a.reject_reason}')
    print(f'   ATR(M5) {atr}  spread {spread_pips:.1f} pips  horizon {a.horizon} M5 bars')
    print(f'   will resolve after {a.horizon} bars (~{a.horizon * 5} min)')


def cmd_resolve(a):
    import pandas as pd
    rows = _load()
    mt5 = _mt5()
    try:
        targets = [r for r in rows if r.get('outcome') == 'PENDING']
        if getattr(a, 'id', None):
            targets = [r for r in targets if r['cf_id'] == a.id]
        if not targets:
            print('[INFO] nothing pending')
            return
        for r in targets:
            sym = r['symbol']
            sig_ts = int(r['signal_bar_time_server'])
            d = pd.DataFrame(mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M5, 0, 400))
            d = d[d['time'] > sig_ts].reset_index(drop=True)
            horizon = int(r['horizon_bars'])
            if len(d) < horizon:
                continue
            win = d.head(horizon)
            entry = float(r['entry_price'])
            sl = float(r['stop_loss'])
            tp = float(r['tp1'])
            is_buy = r['side'].upper() == 'BUY'

            tp_hit = (win['high'] >= tp).any() if is_buy else (win['low'] <= tp).any()
            sl_hit = (win['low'] <= sl).any() if is_buy else (win['high'] >= sl).any()

            first_touch = 'NONE'
            outcome = 'EXPIRED'
            tp_i = win.index[win['high'] >= tp].tolist() if is_buy else win.index[win['low'] <= tp].tolist()
            sl_i = win.index[win['low'] <= sl].tolist() if is_buy else win.index[win['high'] >= sl].tolist()
            if tp_i and sl_i:
                if tp_i[0] < sl_i[0]:
                    first_touch, outcome = 'TP', 'TP_FIRST'
                else:
                    first_touch, outcome = 'SL', 'SL_FIRST'
            elif tp_i:
                first_touch, outcome = 'TP', 'TP_ONLY'
            elif sl_i:
                first_touch, outcome = 'SL', 'SL_ONLY'

            if is_buy:
                mfe = round(float(win['high'].max()) - entry, 5)
                mae = round(entry - float(win['low'].min()), 5)
            else:
                mfe = round(entry - float(win['low'].min()), 5)
                mae = round(float(win['high'].max()) - entry, 5)

            r['resolved_bar_time_server'] = str(int(win['time'].iloc[-1]))
            r['outcome'] = outcome
            r['bars_held'] = horizon
            r['tp_touched'] = int(bool(tp_hit))
            r['sl_touched'] = int(bool(sl_hit))
            r['first_touch'] = first_touch
            r['mfe'] = mfe
            r['mae'] = mae
            r['adverse_first'] = int(outcome == 'SL_FIRST')
            if outcome.startswith('TP'):
                r['would_be_r_usd'] = f'{float(r["rr_tp1"]):.3f}'
            elif outcome.startswith('SL'):
                r['would_be_r_usd'] = '-1.000'
            print(f'[{r["cf_id"]}] {sym} {r["side"]} -> {outcome} '
                  f'(TP {int(bool(tp_hit))} SL {int(bool(sl_hit))} '
                  f'MFE {mfe} MAE {mae})')
        _save(rows)
        print(f'[OK] {CSV_PATH.name} updated')
    finally:
        mt5.shutdown()


def cmd_stats(a):
    rows = [r for r in _load() if r.get('outcome') != 'PENDING']
    pend = [r for r in _load() if r.get('outcome') == 'PENDING']
    print(f'resolved: {len(rows)}   pending: {len(pend)}')
    if not rows:
        print('no resolved counterfactuals yet')
        return
    tp_first = [r for r in rows if r['outcome'].startswith('TP')]
    sl_first = [r for r in rows if r['outcome'].startswith('SL')]
    expired = [r for r in rows if r['outcome'] == 'EXPIRED']
    n = len(rows)
    rr = [float(r['would_be_r_usd']) for r in rows if r.get('would_be_r_usd')]
    print(f'\nTP-first {len(tp_first)}  SL-first {len(sl_first)}  expired {len(expired)}')
    print(f'naive hit rate {len(tp_first) / n * 100:.1f}%')
    if rr:
        print(f'mean R {statistics.mean(rr):+.3f}  total R {sum(rr):+.3f}')
        if len(rr) >= 20:
            sd = statistics.stdev(rr)
            se = sd / (len(rr) ** 0.5)
            print(f'SD {sd:.3f}  SE {se:.3f}  t-stat {statistics.mean(rr) / se:+.2f}')
            print('(t > 2 needed for significance at n>=20)')
    by = {}
    for r in rows:
        by.setdefault(r['reject_reason'], []).append(r)
    if by:
        print('\nby reject_reason:')
        for k, v in sorted(by.items()):
            t = sum(1 for x in v if x['outcome'].startswith('TP'))
            mrr = [float(x['would_be_r_usd']) for x in v if x.get('would_be_r_usd')]
            print(f'  {k:24s} n={len(v):3d}  TP-first {t:3d} ({t / len(v) * 100:5.1f}%)  '
                  f'meanR {statistics.mean(mrr):+.2f}' if mrr else f'  {k:24s} n={len(v):3d}')


def cmd_show(a):
    import pandas as pd
    rows = _load()
    if a.id:
        rows = [r for r in rows if r['cf_id'] == a.id]
    if not rows:
        print('counterfactual log empty')
        return
    print(pd.DataFrame(rows).to_string(index=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('consider')
    c.add_argument('--id')
    c.add_argument('--symbol', required=True)
    c.add_argument('--side', required=True, choices=['BUY', 'SELL'])
    c.add_argument('--order-type', default='LIMIT')
    c.add_argument('--volume', required=True)
    c.add_argument('--entry', required=True)
    c.add_argument('--sl', required=True)
    c.add_argument('--tp1', required=True)
    c.add_argument('--trigger', required=True)
    c.add_argument('--reject-reason', required=True)
    c.add_argument('--horizon', type=int, default=FORWARD_BARS_DEFAULT)
    c.add_argument('--notes', default='')
    r = sub.add_parser('resolve'); r.add_argument('--id')
    sub.add_parser('sweep')
    s = sub.add_parser('show'); s.add_argument('--id')
    sub.add_parser('stats')
    args = ap.parse_args()
    fn = {'consider': cmd_consider, 'resolve': cmd_resolve,
          'sweep': cmd_resolve, 'show': cmd_show, 'stats': cmd_stats}[args.cmd]
    fn(args)


if __name__ == '__main__':
    main()