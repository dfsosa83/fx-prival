# Run Log — QPF-RV-2027-09-A1-OFFLINE-REPLAY-REPRODUCIBILITY-V2

Append-only. Do not edit or delete prior entries.

---

## 2026-09-30 — A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK_V2

- **date:** 2026-09-30
- **stage:** `A1_CONTROLLED_OFFLINE_REPLAY_REPRODUCIBILITY_CHECK_V2`
- **status:** `preregistered`
- **scope:** A1 Gold Rules Engine only; unchanged pure modules; existing local XAUUSD fixtures only;
  isolated fixture-only runner `quant-personal-fund/tools/a1_offline_runner/a1_offline_runner.py`.
- **hashes:** runner `36E80FC2…79FA3`; engine `9653AE90…2357E8`; bias `10699993…F8362F`;
  levels `63442EBB…E0E49D5`; fixtures M15 `574A38DC…D28FBB`, M30 `9345E3D3…0A55566F`,
  H1 `81E51BBF…170B7521`.
- **offline boundary:** OFFLINE_REPLAY / orders disabled / no broker connection / no MT5 / no network /
  no environment or credentials / no orders / no virtual fills / no PnL.
- **two-run comparison:** run 1 = 807 records / 0 errors; run 2 = 807 records / 0 errors; required fields
  complete; no prohibited fields; ordered normalized records equal; canonical SHA256 equal
  (`DC11FF41…A0DBBF81`); temp dirs cleaned.
- **decision:** `REPLAY_REPRODUCIBILITY_PASS`.
- **no broker/MT5/network/PnL/trading activity:** confirmed.
- **continuity:** updated (PASS) — next action set to `A1_ORDERS_DISABLED_FORWARD_OBSERVATION_SETUP`.
- **next authorization consequence:**
  ```text
  A separate authorization may design and set up A1 orders-disabled forward
  observation only. No broker connection, demo order, virtual fill, PnL analysis
  or trading is authorized.
  ```
- **artifacts created:**
  - `quant-personal-fund/experiments/QPF-RV-2027-09-A1-OFFLINE-REPLAY-REPRODUCIBILITY-V2/A1_REPLAY_V2_REPORT.md`
  - `.../A1_REPLAY_V2_RESULTS.json`
  - `.../A1_REPLAY_V2_DECISION.md`
  - `.../RUN_LOG.md`
