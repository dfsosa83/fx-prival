# FRED Economic Indicators — Recommendations for EURUSD H1 Model

*Research date: July 14, 2026 · FRED API: available and tested*

---

## Key finding: FRED has zero hourly-frequency data

Every series on FRED is daily at best. The vast majority are monthly or quarterly. This means FRED data cannot be aligned hour-by-hour with our H1 bars. However, it can serve as **daily context features** — merged at the date level and carried forward as D1 attributes, similar to how our existing `d1_trend`, `d1_rsi`, and `d1_close_vs_ema20` features work.

**No FRED series will ever provide a new hourly feature.** The value is in enriching the daily context that the model already consumes through D1 resampling.

---

## Recommended FRED series (Tier 1 — high signal, daily frequency)

These series update daily and span 1999–present, covering our full training window.

### 1. Interest rate spread: US 10Y – German 10Y bund proxy

| Series | ID | Frequency | Description |
|---|---|---|---|
| US 10Y Treasury | `DGS10` | Daily | Benchmark US risk-free rate |
| US 2Y Treasury | `DGS2` | Daily | Short-end US rate |
| 10Y–2Y spread | `T10Y2Y` | Daily | Yield curve slope (recession signal) |
| **ECB Deposit Facility Rate** | **`ECBDFR`** | **Daily** | Eurozone policy rate — key for EURUSD |
| German 10Y bund | `IRLTLT01DEM156N` | **Monthly only** | FRED limitation — German bund at daily freq not available |

**Relevance to EURUSD:** The US-EU interest rate differential is the single most important driver of EURUSD on medium-term horizons. A widening spread (US rates rising faster than EU) → USD strengthens → EURUSD falls. Our model currently has no explicit rate differential feature. Adding this as a D1 context feature is the highest-ROI FRED integration.

**Workaround for German bund:** Since FRED only has monthly German yields, we would need an alternative source (see Section 3 below).

### 2. Dollar strength index

| Series | ID | Frequency | Description |
|---|---|---|---|
| **Broad Dollar Index** | **`DTWEXBGS`** | **Daily** | Trade-weighted USD vs broad basket |
| Advanced Foreign Economies Index | `DTWEXAFEGS` | Daily | USD vs EUR, GBP, JPY, CAD, etc. |

**Relevance:** The broad dollar index captures overall USD strength independent of any single pair. EURUSD-specific moves that diverge from the broad index suggest pair-specific catalysts (ECB news, EU data). Our model currently has no cross-pair context.

### 3. Volatility and risk appetite

| Series | ID | Frequency | Description |
|---|---|---|---|
| **VIX** | **`VIXCLS`** | **Daily close** | Equity market fear gauge |
| St. Louis Fed Financial Stress | `STLFSI4` | Weekly | Composite stress index (rates, spreads, credit) |

**Relevance:** VIX is inversely correlated with EURUSD during risk-off periods. High VIX → flight to USD safety → EURUSD drops. Our model captures this partially through `atr_regime` and `rolling_std` but has no external risk sentiment indicator.

### 4. Inflation expectations

| Series | ID | Frequency | Description |
|---|---|---|---|
| **5Y5Y Forward Inflation** | **`T5YIFR`** | **Daily** | Market-implied long-term US inflation expectations |
| Fed Funds Rate | `DFF` | Daily | Policy rate — combines with ECBDFR for spread |

**Relevance:** Inflation expectations directly impact Fed policy pricing. Rising T5YIFR → market prices more Fed hikes → USD strengthens. This is forward-looking, unlike backward-looking CPI releases.

### 5. Credit stress

| Series | ID | Frequency | Description |
|---|---|---|---|
| SOFR | `SOFR` | Daily | LIBOR replacement — overnight funding rate |

**Relevance:** SOFR spikes signal funding market stress, which historically preceded EURUSD volatility events. Our model has no credit market awareness.

---

## Series NOT recommended (Tier 2 — lower signal or wrong frequency)

| Series | Reason |
|---|---|
| Initial Claims (`ICSA`) | Weekly frequency, backward-looking, minimal EURUSD impact |
| VIX sub-indices (GVZCLS, OVXCLS) | Commodity/gold volatility — indirect EURUSD link at best |
| Trade balance / GDP | Quarterly frequency — too sparse to add signal at H1 |
| CPI / PCE | Monthly frequency, priced in within minutes of release |
| TED Spread (`TEDRATE`) | Discontinued in 2022 — LIBOR retired |

---

## Implementation approach for daily FRED data in H1 model

Since FRED data is daily, the integration path is:

```
FRED daily series (updated ~16:00 UTC)
    → Merge into feature pipeline as daily attributes
    → Forward-fill across all H1 bars within the same calendar day
    → Model sees the latest known FRED value at every H1 bar
```

This is analogous to our existing D1 context features (`d1_trend`, `d1_rsi`, `d1_close_vs_ema20`) which are computed from daily OHLC and then carried forward. The FRED values would be additional columns in the D1 merge step.

**Training impact:** Minimal. Daily features add context but won't change the hour-to-hour signal behavior. The model already learns from price-embedded rate expectations. Adding explicit rate/spread data primarily benefits medium-horizon regime awareness.

**Agent pipeline impact:** Higher. The Perplexity and GPT agents in our planned multi-agent architecture can reason about explicit rate spreads, VIX levels, and inflation expectations in a way the LightGBM cannot. These are natural-language-amenable indicators.

---

## Alternative sources for hourly-frequency economic data

FRED cannot provide hourly data. The following sources offer higher-frequency economic indicators relevant to EURUSD:

### 1. Market-implied indicators (already in price data)

The most reliable "high-frequency economic data" is embedded in the price bars themselves:

| Indicator | Source | Frequency | Note |
|---|---|---|---|
| EURUSD spot | MT5 data | Tick → H1 | Already used |
| Implied rate differential | EURUSD forward points | Intraday | Available via MT5 if broker provides forwards |
| Options-implied volatility | 1-week ATM EURUSD vol | Intraday | Available via OTC brokers, Bloomberg |
| 25-delta risk reversals | Options market | Intraday | Measures EURUSD sentiment skew |

**Recommendation:** If the MT5 broker provides EURUSD forward points, extract the 1-month forward spread as a proxy for short-term rate differential. This updates tick-by-tick and would be the single best hourly-frequency economic feature.

### 2. News sentiment APIs (text → numeric)

| API | Coverage | Frequency | Cost |
|---|---|---|---|
| **NewsAPI** | 80,000+ sources, real-time | Per-article | Free tier (100 req/day) |
| **GDELT** | Global news monitor, 100+ languages | Every 15 min | Free |
| **ForexLive** | FX-specific economic news | Real-time | Free RSS |
| Bloomberg API | Professional terminal | Real-time | $2,000+/month |

**Recommendation:** GDELT's Global Knowledge Graph provides a numeric "tone" score for news articles mentioning EURUSD, euro, or ECB. Updated every 15 minutes. This is the closest free approximation to an hourly-frequency sentiment indicator. The Perplexity agent already does this ad-hoc; GDELT would automate and quantify it.

### 3. Economic calendars (scheduled event metadata)

| Source | What it provides | Frequency |
|---|---|---|
| **ForexFactory calendar** | Scheduled releases, consensus, previous, actual | As released |
| Investing.com calendar | Same, with importance ratings | As released |
| **FRED release calendar** | When each series updates | Metadata only |

**Recommendation:** An economic calendar feature that marks each H1 bar as "NFP release hour," "ECB decision hour," "CPI release hour," etc. This is a binary/scheduled feature — not a value, but a flag saying "high-impact event happening now." Our model could learn to suppress signals during event risk or lean into directional bias post-release.

### 4. Alternative data providers with sub-daily frequency

| Provider | Data type | Frequency | Cost |
|---|---|---|---|
| **Refinitiv Eikon** | Professional FX data, forward points, vol surfaces | Intraday | $$$$ |
| **Quandl/Nasdaq** | Economic indicators via API | Some daily | Free–$ |
| **OANDA API** | FX rates + order book sentiment | Tick | Free tier |
| **Dukascopy** | Historical tick data + SWFX sentiment | Tick | Free |
| **IG Client Sentiment** | Retail trader positioning (long/short %) | Hourly | Free API |

**Recommendation:** IG Client Sentiment is the most relevant free alternative. It publishes the percentage of retail traders long vs short on major pairs, updated hourly. High retail short interest on EURUSD is often a contrarian bullish signal. This is directly actionable at H1 frequency.

---

## Summary — what to build into the agent pipeline

### Immediate (Iteration 2 — simple daily merges, no cost)

| Feature | Source | Priority | Effort |
|---|---|---|---|
| **US-EU rate spread proxy** | `DGS10` (FRED) minus `ECBDFR` (FRED) | High | Low |
| **VIX level** | `VIXCLS` (FRED) | High | Low |
| **Dollar index** | `DTWEXBGS` (FRED) | Medium | Low |
| **5Y5Y inflation expectation** | `T5YIFR` (FRED) | Medium | Low |
| **Financial stress index** | `STLFSI4` (FRED, weekly) | Low | Low |

All five are daily → merged as D1 context. Add ~20 lines to `compute_features()`. Zero API cost (FRED is free).

### Medium-term (Iteration 3 — external APIs, low cost)

| Feature | Source | Priority | Effort |
|---|---|---|---|
| **Economic calendar event flags** | ForexFactory scraping or Investing.com | High | Medium |
| **IG Client Sentiment** | IG REST API (free) | High | Medium |
| **GDELT news tone** | GDELT 2.0 API (free) | Medium | Medium |

These provide true hourly/sub-hourly signals.

### Premium (if budget allows)

| Feature | Source | Priority | Effort |
|---|---|---|---|
| **EURUSD 1M forward points** | Broker MT5 or OANDA API | Very High | Medium |
| **EURUSD 1W ATM vol** | Refinitiv/Bloomberg | High | High |

---

## Note on the agent architecture

The Perplexity agent in our planned pipeline (see `next_agent_pipeline_design.md`) already queries live web sources for fundamental analysis. Adding FRED features to the LightGBM model's feature set **does not replace** the Perplexity agent — it complements it:

- **LightGBM + FRED features:** Learns stable statistical relationships from historical rate/spread/VIX patterns. Works silently every bar.
- **Perplexity agent:** Reads and interprets the latest ECB statement, FOMC minutes, or breaking EURUSD news that has no historical analog. Runs only when a signal fires.

Both are needed. FRED features improve the base model's precision. The Perplexity agent catches regime breaks and one-off events the model has never seen.