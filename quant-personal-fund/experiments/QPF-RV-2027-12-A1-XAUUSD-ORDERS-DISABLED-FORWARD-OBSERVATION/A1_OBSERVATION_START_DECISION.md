# A1 XAUUSD Orders-Disabled Forward-Observation Start Decision

**Stage:** `A1_MT5_OBSERVATION_ONLY_FORWARD_START`
**Date:** 2026-09-30

```text
decision: A1_ORDERS_DISABLED_FORWARD_OBSERVATION_STARTED
```

The observation-only session `a1_xauusd_observ_20260930` is active. Preflight passed (static scan
clean, demo verified, XAUUSD available, 0 positions / 0 orders, H1/M30/M15 + tick read OK) and one
first cycle completed with lifecycle status `NO_SETUP` (1 observation event, 1 heartbeat).

MT5 demo access is read-only data source only. Orders, virtual fills, PnL and trading remain disabled.
The observation window remains **30 calendar days AND 50 completed cycles**
(`OBSERVATION_WINDOW_INCOMPLETE`). A separately authorized monitoring/close stage is required later.
No PnL, cost or trading conclusion exists.
