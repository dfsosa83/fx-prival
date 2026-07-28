import sys
sys.path.insert(0, 'frival')
from evaluate_precision import evaluate_signals

result = evaluate_signals(run_id_filter='20260728_151336')

print('=== SEALED TEST PRECISION ===')
print('Signals evaluated:', result['signals_evaluated'])
print('Wins:', result['wins'])
print('Losses:', result['losses'])
print('No data:', result['no_data'])
print('Precision:', result['precision'])
print('Wilson CI 95%:', result['wilson_ci_95'])
print('EV per trade (R):', result['ev_per_trade_r'])
print('Total R:', result['total_r'])

print()
print('=== Monthly ===')
for m, v in result['monthly'].items():
    wr = v['win_rate']
    r_val = v['total_r']
    print('  {}: {} signals | {} wins | WR={:.3f} | R={:.1f}'.format(
        m, v['signals'], v['wins'], wr, r_val))

print()
print('=== First 10 signals ===')
for r in result['results'][:10]:
    w = 'WIN ' if r['win'] else 'LOSS'
    entry = r.get('entry', 0)
    trade_r = r['trade_r']
    print('  {} | {} | entry={:.5f} | R={:.1f}'.format(r['timestamp_utc'], w, entry, trade_r))
