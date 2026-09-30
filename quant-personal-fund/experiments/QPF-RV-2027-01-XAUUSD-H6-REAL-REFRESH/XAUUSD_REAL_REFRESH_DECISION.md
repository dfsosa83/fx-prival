# XAUUSD Real Refresh — Decision

**Stage:** `XAUUSD_H6_REAL_HISTORY_REFRESH_AND_CANONICAL_REBUILD`
**Date:** 2026-09-30

```text
decision: XAUUSD_REAL_REFRESH_COMPLETE_PENDING_H6_DATA_REAUDIT
```

---

- XAUUSD raw H1 history was refreshed (read-only retrieval) and canonically rebuilt.
- **Original preserved** in immutable backup:
  `ml-signal-service/data/raw/mt5/H1/XAUUSD_H1.pre_h6_refresh_20260930.csv`
  (SHA256 `A36F2E2331B38E72A6D2874B625DB981AED92220499204D18E8CE58D71332CFA`).
- New canonical `XAUUSD_H1.csv`: schema `datetime,open,high,low,close,volume`, **45,809 rows**,
  `2019-01-02 01:00:00` → `2026-09-30 14:00:00`,
  SHA256 `6DB76DE379FCF0EF65E60597B1A14AC3DD5E3466E01216D7386702CB14FB7F36`.
- Completeness threshold `2026-09-24 18:00:00`: **MET**.
- XAUUSD remains a **separate stratum** (never pooled with FX).
- **No H6 snapshot and no H6 screen ran.**
- A **separate authorization** is still required to re-audit H6 availability, then freeze XAUUSD
  independently before its H6 screen.
