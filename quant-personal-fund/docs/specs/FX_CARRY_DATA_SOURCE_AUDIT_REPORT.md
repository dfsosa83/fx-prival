# FX Carry Data-Source Feasibility Audit — Research Report

**Project:** quant-personal-fund  
**Audit type:** Source research and written feasibility only  
**Date:** 2026-09-28  
**Verdict scope:** applies ONLY to the FX carry candidate, not the portfolio platform

---

## 1. Executive Verdict

### `HOLD — SOURCE/TERMS REQUIRED`

**No free or low-cost source of historical FX forward points (or an equivalent defensible forward-return measure) has been identified from public documentation.** The forward-data gap is structural: FX forward points are an OTC-broker product with no free historical archive, and the free sources (ECB, FRED, central banks) publish **spot or interest rates only** — which the minimum viable carry standard explicitly excludes as carry data.

A HOLD (rather than STOP) is issued because **paid vendor coverage exists in principle** (Refinitiv/Bloomberg-class forward points), but its cost, coverage, and licensing are not established from public information, and vendor outreach is outside this audit's scope. The verdict is `HOLD — SOURCE/TERMS REQUIRED`: the candidate is not testable with current free sources, and determining whether a paid source is affordable requires vendor terms that this audit could not obtain.

**This does not pause the broader project.** Only the FX carry candidate is held.

---

## 2. Source-Comparison Table

Prioritized by cost. Classification key: **[F]** documented fact · **[A]** assumption · **[U]** unresolved from public sources this session.

| # | Source | What it supplies | Forward/carry? | Cost | Depth/freq | Verdict |
|---|---|---|---|---|---|---|
| 1 | **Yahoo Finance daily FX** (already local) | Spot FX prices | Spot only — **no forwards** | Free (held locally) | Daily, 2015+ | **Confirmed available** (Stage 1A); insufficient alone |
| 2 | **ECB euro reference rates** (verified live this session) | **Spot** EUR rates; explicitly "for information only; transaction use discouraged" | **Spot only — no forwards** | Free | Daily, 1999+ | **Confirmed spot-only** — not carry |
| 3 | **FRED / policy + OIS-class rates** | US (DGS3MO etc.) + some non-US policy rates | Interest rates only — **no forwards** | Free | Daily/monthly | **Confirmed not carry** (explicitly excluded by standard) |
| 4 | **Central banks (BoE, Riksbank, Norges, BoJ, SNB)** | Spot + some money-market rates | Largely spot/rates; **forward points not consistently archived** | Free | Daily/monthly | **[A]** some publish daily spot; **no free forward-point archive confirmed** |
| 5 | **BIS statistics** (Triennial FX survey, locational banking) | Aggregate turnover/positions, some forward components | **Aggregate survey, not tradeable daily forward points** | Free | Triennial/quarterly | **[A]** not a daily forward-point series; **[U]** exact forward series unverified (page 404 this session) |
| 6 | **CME / Eurex / SGX FX futures** | Exchange-traded FX futures: settlement prices, volume/OI, contracts, rolls | **Futures** (separate route — not spot carry) | Settlement data free; depth varies | Daily, futures contracts | **[U]** exact free-settlement endpoint unverified (403 this session); futures are a **separate** research path, not a spot-carry substitute |
| 7 | **Paid vendors: Refinitiv (WM/Refinitiv), Bloomberg (BFIX), FactSet, LSEG** | Historical forward points/outrights, bid/ask, tenor, timestamp | **Actual forward data** | **Paid; quote required** | Daily intraday | **[A]/[U]** coverage exists in principle; cost/licensing not publicly priced; **no vendor contact made** |
| 8 | **Broker (FP Markets) historical swap/financing archive** | Broker-specific overnight swap history | Broker swap series — **not OTC forward points** | Unknown; not publicly documented | Unknown | **[U]** no public archive documented; not found in local repo; requires broker confirmation |

---

## 3. Cheapest Source Combination That Could Meet the Minimum Standard

**No free combination meets the minimum viable carry-data standard.** The binding missing component is **FX forward points or an equivalent defensible forward-return measure**. Every free source supplies either spot (Yahoo/ECB) or interest rates (FRED/central banks), neither of which is a forward return.

**The cheapest *theoretically viable* combination would be:**

1. **Spot FX** (Yahoo daily — already held, free) for the spot-return leg.
2. **Forward points or outright forwards** — **unavailable free**; would require either:
   - A paid vendor (Refinitiv/Bloomberg-class) — cost unknown; **HOLD on terms**, or
   - A broker forward-desk historical quote — requires broker confirmation, or
   - A defensible forward construction from OIS/policy-rate differentials **only if** a date-consistent, timestamped forward-implied series can be justified — **but this is explicitly NOT allowed** by the minimum standard unless the construction itself is defensible as a forward-return measure, which a rate differential alone is not.
3. **Financing/roll conventions + contract costs** — partially available (current swap, contract specs pending broker confirmation); historical series unavailable.

**Conclusion:** the cheapest viable combination is **not available at free cost**. The minimum standard cannot be met without either a paid vendor (terms unknown) or a broker forward archive (not publicly confirmed).

---

## 4. Exchange-Traded FX Futures — Separate Research Path

**Clearly separated from spot FX carry:**

| Aspect | FX futures |
|---|---|
| What it supplies | Exchange-traded forward prices via futures contracts (CME, Eurex, SGX) — a **genuine, settled, tradable forward-return** |
| Carry vs futures | Futures basis (future vs spot) is a real forward-return measure — **but it is futures-based carry, not OTC spot carry** |
| Data | Settlement prices, volume/open interest, contract specs, roll data — free settlement endpoints exist in principle |
| Depth | Daily, futures contracts (quarterly/other); historical depth varies by contract |
| Limitations | Contract granularity, roll management, contract-size differences, and a different cost/venue structure vs spot/CFD |
| Verdict | **[U]** — a **separate** research path with genuine merit. It is NOT a substitute silently relabeled as spot carry; it would be its own hypothesis (futures-based carry) with its own data/cost/roll machinery. Worth assessing separately if FX carry remains blocked. |

---

## 5. Exact Data Gaps and Validation Tests Still Needed

| Gap | Status |
|---|---|
| Historical forward points (any pair, any tenor) | **Unavailable free**; paid terms unknown |
| Historical broker swap series | **Unavailable**; requires broker confirmation |
| FX contract sizes | **Requires broker confirmation** (terminal returned null) |
| Holiday/early-close calendar + DST | **Requires broker confirmation** |
| Forward-implied construction with revision timestamps | **Not a substitute** without forwards |

**Validation tests (for the data pilot, if one is ever authorized):**
- Spot-return integrity (already validated in Stage 1B).
- Forward-point internal consistency: `forward ≈ spot × (1 + r_dom × t) / (1 + r_for × t)` (covered-interest-parity check) on the vendor/broker data.
- Bid/ask forward spread vs spot spread.
- Timestamp/tenor/fixing-convention alignment across spot, forward, and rates.
- Roll and financing convention reconciliation.
- Point-in-time (revision-free) availability check on any historical forward series.

---

## 6. Conditional Recommendation for Next Step

### If a suitable low-cost source exists (currently not identified):
Propose a **narrowly scoped data pilot** — do not run it:
- **Pilot scope:** acquire a small, dated sample of forward points (or forward-implied construction) for 1–2 G10 pairs, one tenor (e.g., 1M or 3M), with bid/ask, for a ~2-year window; validate CIP consistency and timestamp alignment; estimate round-trip carry cost.
- **Gate:** pilot confirms date-consistent forward data + defensible carry return → proceed to a pre-registered FX carry hypothesis. If not → **STOP the FX carry candidate**.

### If no suitable low-cost source exists (current finding):
**The FX carry claim cannot be tested** — specifically, the claim that *long-higher-yield/short-lower-yield currencies earn the rate differential after costs* cannot be measured without forwards or a broker swap history. **No zero-swap proxy, no rate-differential-as-carry substitute, and no arbitrary approximation will be used.**

**Distinct alternative research path worth assessing:** **Exchange-traded FX futures carry** (§4) — a separate, genuinely distinct route with real forward-return data, requiring its own data/cost/roll assessment. This is the most promising alternative if FX carry remains data-blocked.

---

## 7. Source List (links + access evidence)

| Source | Link | Access/pricing evidence |
|---|---|---|
| ECB euro reference rates | `https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html` | **Verified this session**: spot only; "for information only; transaction use strongly discouraged" |
| FRED | `https://fred.stlouisfed.org` | Documented free; rates only; not carry |
| BIS FX statistics | `https://www.bis.org/statistics/` | **[U]** forward-statistics page returned 404 this session; aggregate survey, not daily tradeable forwards |
| CME FX | `https://www.cmegroup.com/trading/fx/` | **[U]** 403 (blocked automated access this session); settlement data free in principle; futures only |
| Yahoo Finance (local) | local parquet | Confirmed free, held locally |
| Refinitiv / Bloomberg / FactSet | vendor sites | **[U]** forward-point coverage exists in principle; **no public price; no vendor contact made** |

**Access-evidence note:** several vendor/venue pages (CME, BIS forward-statistics) returned 403/404 to automated fetch this session. That is a **web-access limitation of this audit**, not evidence about the data. It is marked `[U]` (unresolved from public sources this session), not `[F]` unavailable.

---

## Labels Summary

| Label | Items |
|---|---|
| **Documented fact** | ECB publishes spot-only; Yahoo spot local; FRED rates not carry; forward points are OTC-broker data |
| **Assumption** | Central banks may publish some daily spot; BIS has some forward components but not tradeable daily forwards |
| **Provider claim** | None relied upon (no vendor outreach) |
| **Unresolved** | CME/BIS exact free endpoints (web-blocked this session); paid vendor pricing/coverage |

**Scope confirmed:** no strategy signal, ranking, hedge ratio, allocation, forecast, backtest, performance metric, or instrument selection. No code/files created. No downloads, API calls, MT5/broker/account access, login, orders, vendor outreach, or `frival/` changes. EXP-2026-05 and closed families untouched. No timeframe imposed.

---

*This is a research and feasibility report only. The FX carry candidate is `HOLD — SOURCE/TERMS REQUIRED`. The portfolio platform and other research paths are unaffected. Awaiting explicit approval before any data pilot or further research.*