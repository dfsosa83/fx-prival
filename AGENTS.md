# Frival desk — agent operating rules

The desk brief is `ACTIVE MONITOR — Frival desk.md`. Work from `frival/` with
`C:\Users\sosap\anaconda3\envs\frival\python.exe`. These rules supplement the
brief; where they conflict with a one-off instruction, ask.

## Position sizing — MANDATORY: risk-based, never fixed lots

Size every order from the risk budget, per symbol:

    volume = (equity * RISK_PCT) / (sl_distance * money_per_price_unit)

- `money_per_price_unit` is the USD value of a 1.00 PRICE move per 1.00 lot,
  from the broker (`symbol_info.trade_tick_value / trade_tick_size`) or
  `log_trade._money_per_price_unit_per_lot(symbol)`. **Never hardcode.**
  Live values: XAUUSD 100, EURUSD 100000, USDJPY ~632.
- `RISK_PCT` = 5.0 (the executor's `MAX_RISK_PCT_PER_TRADE`).
- Round **down** to the 0.01 lot step, then state the realised `risk_pct`.
- **Use the helper, don't do it by hand:** `log_trade.py size --symbol X
  --entry E --sl S` prints the correct lots, or pass `--risk-pct 5` to
  `log_trade.py signal` instead of `--volume` and it sizes itself.

Because the per-unit value differs ~1000x between gold, EURUSD and USDJPY, the
same "small" lot count means wildly different risk. At ~$700 equity and
SL = 1.5xATR(M5), 5% risk is roughly:

| symbol | correct vol | risk at the 0.01 min lot |
|---|---|---|
| XAUUSD | ~0.045 | ~$7 (1.0%) |
| EURUSD | ~0.5-0.6 | ~$0.06 (0.01%) |
| USDJPY | ~0.6-0.7 | ~$0.5 (0.07%) |

**Tiny USDJPY/EURUSD lots are the recurring error.** USDJPY at 0.01-0.02 lots
risks under $1 — that is ~30-50x undersized and materially under-uses the risk
budget (ledger: T017 0.01 lot = -$0.61, T025 0.02 lot = -$0.71). Always derive
the volume from the formula; never reuse a gold lot count on an FX pair.

## Entry filters

- **Momentum alignment (new).** Do not take an entry against the body of the
  immediately-preceding H1 candle. Buying straight into a rejection/hammer bar
  is the one repeatable loss pattern in the ledger (T032). If the prior H1 bar
  closed strongly against the intended side, WAIT. Every signal records
  `mom_alignment` (ALIGNED/AGAINST) so this filter can be MEASURED before it is
  ever hard-enforced in the executor.
- The four gates still bind: SL beyond a real swing high/low, FVG or OB;
  SL 1.0-4.0x ATR(M5); R:R >= 1.9 to the order TP; risk <= 5% of equity.
- When 1.9:1 is only reached at TP2/TP3, use that as the order TP and say so.

## Operational rules

- `order_executor.py` is the ONLY component authorised to place, modify or
  close orders. Never use `place --force`.
- `reconcile_deals.py` is read-only: never run its `apply` (it mislabels closed
  rows as OPEN and cannot match `FRIVAL_CLOSE`).
- Run `order_executor.py manage` every cycle; log every rejected setup as a
  counterfactual.
- `log_trade.py exit` now resolves the true opening fill from broker history
  when `fill_price` is empty, so realised PnL/R come from the fill, not the
  signal entry.
- `log_trade.py signal` upserts by `log_id` (re-emitting the same id updates
  the row; it no longer appends a duplicate).
