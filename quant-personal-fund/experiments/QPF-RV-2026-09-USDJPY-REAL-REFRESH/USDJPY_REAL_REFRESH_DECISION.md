# USDJPY Real Refresh — Decision

**Stage:** `USDJPY_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD`
**Date:** 2026-09-29

```text
decision: USDJPY_REAL_REFRESH_COMPLETE_PENDING_H5_V2_SNAPSHOT
```

---

- USDJPY raw H1 history was refreshed (read-only retrieval) and canonically rebuilt.
- **Original preserved** in immutable backup:
  `ml-signal-service/data/raw/mt5/H1/USDJPY_H1.pre_h5_refresh_20260929.csv`
  (SHA256 `BF92FF4077425E9DC903A1D9D3DC5F847A8F3FED49958AA4B44CFC1C640A4CBC`).
- New canonical USDJPY_H1.csv: schema `datetime,open,high,low,close,volume`, **48,191 rows**,
  `2019-01-02 00:00:00` → `2026-09-29 21:00:00`,
  SHA256 `810F789A7271E9861010B4A0A21987F96905AB9FF83C3449E625FD90416A5858`.
- Completeness threshold `2026-09-24 18:00:00`: **MET**.
- **No H5 snapshot and no H5 screen ran.**
- A **separate authorization** is required for a new seven-series H5-v2 snapshot freeze, using all
  sources under the unchanged H5 protocol.
