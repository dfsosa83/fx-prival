# Erratum — V35_RECONSTRUCTION_REPORT.md

**Date:** 2026-09-24  
**Scope:** DOCUMENTATION-ONLY. No changes to the v3.5 CSV, engine, manifests, reason codes, classifications, or data.

This erratum corrects transcription errors in the human-written `V35_RECONSTRUCTION_REPORT.md`. The authoritative sources — `episode_ledger_v35.csv` and `LEDGER_V35_SUMMARY.json` — are unchanged and reconcile exactly.

## Corrections

| Item | Report (incorrect) | Correct value |
|---|---|---|
| Development `no_c1` | 1,446 | **1,462** |
| Development `missing_bar` | 23 | **17** |
| v3.5 OOS total | (implied 2,579 by cross-reference) | **2,575** |
| v3.5 combined total | (implied 5,229 by cross-reference) | **5,225** |

## Explicit statement

- **Development `no_c1` is 1,462**, not 1,446.
- **Development `missing_bar` is 17**, not 23.
- **v3.5 OOS total is 2,575** and **v3.5 combined total is 5,225**.
- Earlier references to **OOS 2,579 and total 5,229 belong to v3.4** and must not be used for v3.5.
- The **v3.5 CSV and `LEDGER_V35_SUMMARY.json` are authoritative and reconcile exactly** (verified: dev 2,650 = 359+1,462+42+446+324+17; OOS 2,575 = 382+1,270+40+562+281+19+21; total 5,225).

## Verification reference

Independent reconciliation (`reconcile_v35.py`, `compare_sources.py`): CSV rows 5,225 = unique idx 5,225; 0 duplicates; 0 null/unclassified reasons; sum of reason counts per window = window rows; summary JSON == CSV (0 differences). The four mismatches originally reported were two report transcription errors (dev `no_c1`, dev `missing_bar`) and two cross-version references (OOS 2,579 and total 5,229 being v3.4 figures).

*End of erratum.*