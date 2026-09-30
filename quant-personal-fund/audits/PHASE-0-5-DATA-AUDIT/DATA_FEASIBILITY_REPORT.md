# DATA FEASIBILITY REPORT — PHASE-0-5-DATA-AUDIT

**Date:** 2026-09-24  
**Status:** COMPLETE — MT5 query executed (read-only, demo terminal 7409623)  
**Scope:** 9 instruments × M5/M15/M30/H1 = 36 cells. Data availability/quality only.

---

## 1. Executive Statement

The data-feasibility audit was executed against the **FP Markets demo terminal** (account **7409623 / FPMarketsSC-Demo, USD**). The safety pre-check passed (demo account confirmed; **0 open positions; 0 pending orders**; `login()` never called; no settings/account/order operations). No workflow pause was required — no `run_daily.bat`/`run_gold_rules.bat`/python processes were running.

**Result: 36/36 instrument×timeframe cells probed successfully.** All 9 instruments return OHLCV data at M5/M15/M30/H1. **No strategy, no backtest, no profitability analysis, no timeframe ranking was performed.**

---

## 2. Safety Pre-Check (verified)

| Check | Result |
|---|---|
| Connected account | **Demo 7409623 / FPMarketsSC-Demo, USD**, balance $5,000.05, equity $5,000.05 |
| Open positions | **0** |
| Pending orders | **0** |
| `login()` called | **No** (inherited active terminal session read-only) |
| Active workflows | None running (no python `run_daily`/`run_gold_rules`; no startup scheduler) |
| Terminal disturbed | No |

---

## 3. MT5 Query Findings

### 3.1 Envelope (earliest retrievable via current terminal)

| Instrument | M5 envelope first | Envelope last (probe) |
|---|---|---|
| XAUUSD | **2020-02-28** | 2026-01-30* |
| EURUSD, GBPUSD, AUDUSD, USDCAD, USDCHF, USDJPY, EURJPY | **2016-01-04** | 2026-01-30* |
| NZDUSD | 2016-01-04 (01:00) | 2026-01-30* |

*The "2026-01-30" last is a **probe artifact**: my bracket list's final origin was 2026-01-01. The recent-window query (2026-08-09) returned data for all cells, so the true envelope extends to present. The 2015 probe returned **empty** — a retention/maxbars limit, not a query bug.

**Max-bars finding:** the setting's exact value was **not read** (reading it requires terminal inspection, which would disturb the session — prohibited). Behaviorally, `copy_rates_range` returned data from 2016 (FX) / 2020 (XAUUSD) and **empty for 2015** — consistent with a retention/TERMINAL_MAXBARS limit, but the exact value remains unknown. Requests beyond the envelope fail/return empty; this is a **request-range limitation**, distinct from (and not proof of) broker-server retention.

### 3.2 Per-cell evidence (all 36 cells)

| Metric | Finding |
|---|---|
| **Fields** | `time, open, high, low, close, tick_volume, spread, real_volume` — all 36 cells |
| **Bar spread field** | **Present in all 36** (bar-level spread) — reported separately from historical bid/ask |
| **Duplicates** | **0** in recent window, all cells |
| **Gaps >1.5× interval** | **7 per FX cell** (consistent with weekends); XAUUSD same order — expected closed-market gaps, not unexplained |
| **Repeated-query stability** | **Stable (identical) in all 36 cells** (two identical queries) |
| **Tick data** | **0 rows in 7-day window, all cells** — MT5 error `(-2, 'Invalid arguments')` |
| **Historical bid/ask** | **UNAVAILABLE via tick API** |
| **Source origin** | All cells: `repeated query — stable` (two identical terminal queries) |
| **Server retention** | **Not independently verified** (`server_retention_verified: false`) |

### 3.3 Current symbol specs (demo terminal, current)

| Instrument | Digits | Point | Vol min/step | Spread (pts) | Swap long | Swap short | Path |
|---|---|---|---|---|---|---|---|
| XAUUSD | 2 | 0.01 | 0.01 | 21 | −63.88 | +39.45 | Metals Gold\XAUUSD |
| EURUSD | 5 | 1e-5 | 0.01 | 13 | −6.47 | +2.83 | Forex Majors\EURUSD |
| GBPUSD | 5 | 1e-5 | 0.01 | 17 | −2.22 | −2.02 | Forex Majors\GBPUSD |
| AUDUSD | 5 | 1e-5 | 0.01 | 13 | −0.69 | −2.39 | Forex Majors\AUDUSD |
| NZDUSD | 5 | 1e-5 | 0.01 | 14 | −3.97 | +0.43 | Forex Majors\NZDUSD |
| USDCAD | 5 | 1e-5 | 0.01 | 15 | +2.68 | −8.22 | Forex Majors\USDCAD |
| USDCHF | 5 | 1e-5 | 0.01 | 15 | +7.18 | −10.02 | Forex Majors\USDCHF |
| USDJPY | 3 | 0.001 | 0.01 | 14 | +9.37 | −14.84 | Forex Majors\USDJPY |
| EURJPY | 3 | 0.001 | 0.01 | 16 | +3.51 | −9.94 | Forex Minors\EURJPY |

**Notes:**
- `contract_size` returned **null** from `symbol_info` on this API build. The gold_rules pre-flight (v1.3, live) verified **XAUUSD contract size 100 oz/lot** via `trade_contract_size` — this is the authoritative XAUUSD value. FX contract sizes must be confirmed by the broker; **not** inferred from the null field.
- **FX swaps are now populated and non-zero** (e.g., EURUSD −6.47/+2.83) — this is a material correction to the research cost model's `swap = 0` assumption and must be reflected in any future cost model (outside this audit).

---

## 4. Local Data Inventory (context)

| Source | Count | Coverage |
|---|---|---|
| MT5 H1 cache | 12 CSV | 7 of 9 instruments, 2019–2026 (AUDUSD/NZDUSD absent locally) |
| Gold M5 | 1 CSV | XAUUSD M5, 2026-08-25 → 09-18 |
| Yahoo daily | 19 parquet | daily only |

Local H1 is consistent with the MT5 envelope (2019+ ⊂ 2016+ server envelope). Full hashes in `data_inventory.csv`.

---

## 5. Adequacy Classification (36 cells)

| Class | Cells | Basis |
|---|---|---|
| **Exploratory** | 36/36 | OHLCV + bar spread + stable repeated query + 0 dups + expected weekend gaps |
| **Development** | 30/36 (all FX; XAUUSD provisional) | Requires confirmed calendar/holiday mapping + timezone decode + confirmed contract specs |
| **Sealed** | **0** | Requires: calendar/holiday resolution, timezone decode, broker-confirmed contract specs incl. contract size, and a cost convention (historical bid/ask UNAVAILABLE → sealed tests cannot model execution-grade spreads) |

**Key adequacy blocker:** **historical bid/ask is unavailable** (tick API returns nothing). Bar-level `spread` is present but is not an execution-grade bid/ask path. A sealed reversal study can use bar-close OHLCV with modeled costs, but **cannot claim execution-grade spread realism**.

---

## 6. Unresolved Broker Questions

1. Exact "Max. bars in chart" value and whether `copy_rates_range` is capped by it (behaviorally: 2016+ FX, 2020+ XAUUSD, 2015 empty).
2. Contract size per FX symbol (API returned null; XAUUSD verified 100 oz/lot by prior pre-flight).
3. Timezone convention of the returned timestamps (server-local vs UTC; local H1 cache uses UTC-labelled datetimes).
4. Trading calendars (holidays, gold daily halt) per instrument.
5. Whether tick/bid-ask history exists at any depth (none retrievable via this terminal).
6. Confirmation that 2016→present intraday history is the broker's actual retention (not merely terminal cache).

---

## 7. Data-Feasibility Recommendation

### **GO — data feasibility for research (exploratory/development-grade) is established.**

- All 36 cells return stable, duplicate-free OHLCV + bar spread with multi-year envelopes (2016+ FX, 2020+ XAUUSD).
- This is **sufficient to design a development sample** for the invalidation-and-reversal study at M15/M30/H1 on FX and XAUUSD.
- **Sealed-test readiness is NOT yet established** because: (a) historical bid/ask is unavailable (cost realism limited), (b) contract size for FX is unconfirmed, (c) timezone/calendar are unresolved.

**This is a data-feasibility GO only. It is not a strategy verdict and authorizes nothing beyond data use.**

---

*No strategy defined; no backtest; no profitability/timeframe ranking; no sealed-test inspection. `server_retention_verified=false`.*