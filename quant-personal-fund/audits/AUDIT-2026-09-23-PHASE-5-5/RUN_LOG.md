# RUN_LOG — AUDIT-2026-09-23-PHASE-5-5

**Audit:** AUDIT-2026-09-23-PHASE-5-5
**Manifest:** audit_manifest.yaml
**Type:** analysis-only, non-invasive, append-only
**Status:** COMPLETE

---

## Run History

| # | Step | Date | Result | Key Finding |
|---|---|---|---|---|
| 1 | a — Test suite + environment | 2026-09-23 | 225 passed, 1 warning | Env: py3.11.11, pandas 2.2.2, lgbm 4.5.0 |
| 2 | b — Base-currency / representation | 2026-09-23 | COMPLETE | **H9 CONFIRMED**: 4 non-USD instruments unconverted |
| 3 | c — Benchmark reconciliation | 2026-09-23 | COMPLETE | Turnover 0 correct; cost/gross = 100% holding cost; benchmark is REBALANCED |
| 4 | d — Financing double-charge | 2026-09-23 | COMPLETE | **H1 CONFIRMED**: double-charge on 7 financed instruments |
| 5 | e — Cost waterfall | 2026-09-23 | COMPLETE | Trend cost/gross 97.9%; carry 703.7%; JPY spreads dominate |
| 6 | f — Data provenance | 2026-09-23 | COMPLETE | adj_close used everywhere; orphan 2644.T file; common-range loss ~100-180 rows |
| 7 | g — Trend/carry trace | 2026-09-23 | COMPLETE | Trend cash residual ~36%; carry signal ~coin flip (45% long/47% short) |
| 8 | h — Stats consistency | 2026-09-23 | COMPLETE | Metrics recompute exactly; **no CI on any verdict**; benchmark Sharpe CI includes zero |
| 9 | i — LOO/LACO + hashes | 2026-09-23 | COMPLETE | Commodity leg drives Sharpe; WTI biggest single asset; 27 hashes captured |
| 10 | j — Final report | 2026-09-23 | COMPLETE | **REMEDIATE** |

---

## Final Recommendation

**REMEDIATE** — confirmed blocking issues (H9 base-currency conversion, H1 financing double-charge, H5 benchmark definition, S1 no CI) require a controlled rerun under new hashes before verdicts are relied upon.

## Notes

- No source code, configuration, raw data, strategy parameters, experiment outputs, historical reports, prior manifests, or sealed verdicts were modified.
- All diagnostic artifacts are under `audits/AUDIT-2026-09-23-PHASE-5-5/`.
- Findings classification: VERIFIED (source/artifact) | REPORTED (docs, unverified) | ASSUMPTION (unresolved).