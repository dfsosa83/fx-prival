# CLOSURE REPORT — EXP-2026-05-INVALIDATION-REVERSAL

**Version:** v3.6  
**Status:** **STOP — closed.**  
**Date:** 2026-09-25

---

## Final Verdict

> **STOP — historical research-grade OOS did not confirm the development effect; no operational use.**

The reversal strategy variant is closed. It is not deployed, not recommended for demo/live trading, and no forward validation, parameter tuning, or post-hoc optimization is authorized for this variant.

---

## 1. Headline Results (v3.6 corrected scoring, base cost scenario)

| Period | Eligible | mean ΔR | 6h CI | P(>0) | PF (diag) |
|---|---|---|---|---|
| **Development** | 1,863 | **+0.0322 R** | [0.0001, 0.0633] | 0.975 | 1.44 |
| **Research-grade OOS** | 1,692 | **−0.0208 R** | [−0.0499, 0.0074] | 0.083 | 0.77 |

The development effect is **not confirmed** by the research-grade OOS window, which is directionally negative.

## 2. Cost Sensitivity

| Scenario | Development mean ΔR | OOS mean ΔR |
|---|---|---|
| Base | +0.0322 | −0.0208 |
| 2× spread | +0.0295 | −0.0231 |
| 2× slippage | +0.0308 | −0.0220 |
| Combined | +0.0282 | −0.0242 |

**Development remains positive but weak** across all four scenarios (PF 1.38–1.44; 6h CI lower bound ≈ 0 or slightly negative). **OOS remains negative in all four scenarios** (PF 0.74–0.77; CIs straddle 0, upper bound +0.005 to +0.007).

## 3. Block Sensitivity (base scenario)

| Period | 3h CI | 6h CI | 12h CI |
|---|---|---|---|
| Development | [0.0021, 0.0606] | [0.0001, 0.0633] | **[−0.0038, 0.0663]** |
| OOS | [−0.0467, 0.0048] | [−0.0499, 0.0074] | [−0.0514, 0.0095] |

**Development does not robustly exclude zero at the 12h block** (lower bound −0.0038). **OOS remains directionally negative at all block lengths.**

## 4. Status of Historical Evidence

- **Historical OOS is research-grade, not sealed.** No historical period was ever sealed; forward post-freeze validation would be the only GO source.
- **Bar spread remains a historical proxy**, not an executable bid/ask path.
- **Historical bid/ask is unavailable** (tick API returned nothing).
- **Broker calendar / DST behavior remains incompletely confirmed** (maintenance window observed 23:45–01:00 UTC on a limited sample; holidays/early-close unconfirmed).

## 5. Prior Invalid Scoring

The prior scoring run (v3.5-based `SCORING_RESULTS.json`, `SCORING_REPORT.md`, `scored_*.csv`) is **INVALID — short-stop condition defect** and must never be used as evidence for or against any hypothesis. It remains labeled invalid and preserved unchanged.

## 6. Exit-Type Decomposition (corrected v3.6)

| Window | Time exits (12 bars) | Stop/forced (<12) |
|---|---|---|
| Development (359 c1) | 282 | 77 |
| OOS (382 c1) | 297 | 85 |

The defective 1-bar pattern (739/741) is gone; the frozen stop/time/forced exits are exercised.

## 7. Prohibitions (unchanged)

- No strategy deployment, demo/live trading, forward validation, parameter tuning, or post-hoc optimization for this variant.
- No new hypothesis, strategy variant, ML model, or follow-up experiment is created by this closure.
- No MT5/broker/account access, no orders, no `frival/` modifications.

---

*Stopped after closure. Awaiting explicit user direction.*