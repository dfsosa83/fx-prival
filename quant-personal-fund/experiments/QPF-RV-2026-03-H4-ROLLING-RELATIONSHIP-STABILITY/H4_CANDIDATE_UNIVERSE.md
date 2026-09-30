# H4 — Candidate Universe

**Stage:** `H4_ROLLING_RELATIONSHIP_STABILITY_DESIGN`

---

| Candidate | Pair | Role |
|---|---|---|
| C2 | EURUSD / USDCHF | First H4 candidate |
| C3 | AUDUSD / USDCAD | Second |
| C4 | EURGBP / EURUSD | Third |
| C5 | NZDUSD / USDCAD | Fourth |

## Rules

- H4 evaluates candidates **one at a time** in this order.
- All four are **data-eligible** according to the prior availability audit
  (`QPF-RV-2026-01-FOREX-PAIR-UNIVERSE-AUDIT/PAIR_UNIVERSE_DATA_AUDIT.md`).
- Eligibility is **not** evidence of mean reversion or profitability.
- **No price or result statistic is computed during this design stage.**
- **EURUSD/GBPUSD and AUDUSD/NZDUSD** are historical fixed-beta rejections; they are **not**
  re-tested and are **not** used to calibrate H4.
- Fixed orientations (do not reverse based on results):
  - C2: `log(EURUSD)` on `log(USDCHF)`
  - C3: `log(AUDUSD)` on `log(USDCAD)`
  - C4: `log(EURGBP)` on `log(EURUSD)`
  - C5: `log(NZDUSD)` on `log(USDCAD)`
