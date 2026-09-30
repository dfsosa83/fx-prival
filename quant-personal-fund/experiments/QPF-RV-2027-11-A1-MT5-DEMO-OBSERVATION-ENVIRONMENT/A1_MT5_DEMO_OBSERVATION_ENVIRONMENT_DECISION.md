# A1 MT5-Demo Observation-Environment Decision

**Stage:** `A1_MT5_DEMO_OBSERVATION_ENVIRONMENT`
**Date:** 2026-09-30

```text
decision: A1_MT5_DEMO_OBSERVATION_ENVIRONMENT_READY
```

The DEMO-only, orders-disabled observation environment is prepared and validated on the real
FP Markets demo terminal: `demo_verified=true`, XAUUSD available, 0 positions / 0 orders, all three
timeframes (H1/M30/M15) and a tick read OK. Orders are disabled by construction and verified by a
static forbidden-method scan; only a redacted structural attestation is persisted.

A separate explicit authorization is required to begin forward observation. No broker order, demo
order, virtual fill, PnL analysis or trading is authorized by this setup.
