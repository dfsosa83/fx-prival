# G0 Decision — Execution Isolation Verification

**Experiment ID:** `QPF-RV-2026-01-EURUSD-GBPUSD-COINTEGRATION`
**Program scope:** `FUTURE_QPF` — family `RV`
**Date:** 2026-09-29
**Stage:** `G0_EXECUTION_ISOLATION`
**Result:** `G0_PASS`

---

## Exact test command

```text
pytest -q tests/system/test_execution_isolation.py tests/system/test_no_lookahead.py
```

Run from the `quant-personal-fund/` repository root.

## Exact test result

```text
8 passed in 0.83s
```

## Nature of the verification

The tests used **static inspection only**. Both guards:

- import no project modules (stdlib only: `ast`, `io`, `tokenize`, `pathlib`);
- read only Python **source** files under the research-library directories
  (`core/`, `data/pipelines/`, `signals/`, `portfolio/`, `risk/`, `backtest/`, `llm_tools/`,
  `monitoring/`);
- do not access market data, MT5, brokers, credentials, `.env`, network, APIs, or execution code;
- do not write files.

## No-access statement

No data, MT5, credentials, network, broker, execution, model, backtest, signal, or market
computation occurred during G0.

## Authorization consequence

`G0_PASS` authorizes only a separately approved G1 data-audit execution.

`G0_PASS` does not authorize G2, G3, G4, G5, G6, source selection, data acquisition, statistical
testing, cost work, backtesting, shadow, demo, or live trading.

## Evidence paths

- `tests/system/test_execution_isolation.py`
- `tests/system/test_no_lookahead.py`
- `G0_G1_DESIGN_SPEC.md`
- `RUN_LOG.md`
