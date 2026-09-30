# Data Requirements and Venue Checklist

**Status:** CHECKLIST — no data downloaded, no venue selected.

---

## Purpose

Enumerates the data required to build Benchmark v3 and the venue/broker confirmations required before any instrument is execution-ready. **Nothing here is selected or sourced in Phase 5.6.**

## 1. FX (per candidate vehicle — UNDECIDED)

| Vehicle candidate | Required data | Source class needed |
|---|---|---|
| B1 Multi-currency cash account | O/N deposit/borrow rates per currency (SOFR, ESTR, TONA, SONIA, SARON, …) | broker/venue-confirmed |
| B2 Rolling forwards | forward points / outrights per pair/tenor | forward desk |
| B3 Spot + tom/next swap | tom/next swap points per pair/day | venue swap table |
| B4 FX futures | front/quarterly contract prices + roll calendar | exchange + broker |
| B5 Broker CFD | broker swap table + margin terms | broker |

**Pending:** FX vehicle selection, broker venue, carry/funding data. NOT inferred.

## 2. Equities (ETF direction — tickers NOT selected)

| Data | Purpose | Source |
|---|---|---|
| ETF ticker → index mapping | vehicle definition | user/venue decision |
| ETF TER | cost ledger | prospectus/factsheet |
| ETF distribution yield | return construction | factsheet |
| Broker commission/spread | cost ledger | broker |

**Pending:** specific ETF tickers, venue.

## 3. Commodities (futures, contract-by-contract)

| Data | Purpose | Source |
|---|---|---|
| Front-month + next-month contract price series | S2 PnL, S1 signal | exchange data |
| Contract calendar (first/last tradable, first notice) | roll boundaries | venue |
| Broker fee table (commission, bid-ask, slippage at roll) | S3 roll txn cost | broker |
| Negative-price registry | price floor | derived + audit |

**Pending:** contract calendar, broker fee table, venue.

## 4. Rates/Bonds

**Excluded (ADR-003 Option 4).** Revisit trigger: licensed sovereign-futures data costed and acceptable.

## 5. Cost Confirmations Required Before Execution-Readiness

| Item | Confirmation |
|---|---|
| FX spread (per pair, per session) | venue quote table |
| ETF TER + distribution | prospectus/factsheet |
| Commodity commission + roll fee | broker schedule |
| Commodity roll schedule | venue calendar |
| USD O/N funding rate | for opportunity cost tracking (if adopted) |

## 6. Broker/Venue Checklist (none selected)

- [ ] Venue identified and data confirmed
- [ ] FX vehicle selected (B1–B5) with data
- [ ] ETF tickers selected with TER/distribution
- [ ] Commodity contract calendar + fee table confirmed
- [ ] USD funding rate source confirmed (if adopted)

**All items above remain pending user/venue decisions. No item is inferred in Phase 5.6.**