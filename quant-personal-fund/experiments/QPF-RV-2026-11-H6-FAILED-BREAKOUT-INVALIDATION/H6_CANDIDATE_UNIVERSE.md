# H6 — Candidate Universe

**Stage:** `H6_FAILED_BREAKOUT_INVALIDATION_DESIGN`

---

## FX targets

```text
EURUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD
```

- FX targets are evaluated **individually**; their outcomes are **never pooled** into one unlabeled
  result.

## Separate XAUUSD target

```text
XAUUSD
```

- XAUUSD is evaluated **individually** and remains a **separate market-structure stratum**: it must
  **not** be pooled with FX, used as a confirmation feature, or used to rank FX candidates.
- **Do not assume or verify in this stage that XAUUSD H1 data exists.**

## Timeframe

- H6-v1 begins on **H1 only**.
- **M15 and D1 may be proposed only** as separately documented replication designs after H6-v1 is
  completed; they cannot be added to the initial H6-v1 screen.
- An instrument may enter later screening only after a **separately authorized** data-availability/
  quality audit and immutable-snapshot freeze.

## Directional event classes (symmetric, pre-registered)

```text
FAILED_UPWARD_BREAKOUT
FAILED_DOWNWARD_BREAKOUT
```

- A candidate configuration must pass in **both** classes; do **not** select only the favorable
  direction.
- A result for one instrument does **not** approve another instrument.
