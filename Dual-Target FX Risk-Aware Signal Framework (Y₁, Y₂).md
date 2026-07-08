## Dual-Target FX Risk-Aware Signal Framework (Y₁, Y₂)

*Draft concept note – clean version for Typora*

## 1. Introduction

This project proposes a **dual-target machine learning framework** for FX trading signals suitable for a bank’s trading desk. The goal is to move from pure directional forecasting to **risk-aware, portfolio-level decisions** by introducing two coordinated targets:

- **Y₁**: main trading signal (BUY/SELL) on a specific FX pair.
- **Y₂**: hedge / risk adjustment decision, determining whether the main position should be accompanied by a second position that improves the overall risk profile of the FX book.tiomarkets+1

Since the desk is not highly active in FX, signals must be **selective, well‑supported and aligned with broader risk management**, using H1 and D1 horizons instead of very short intraday scalping.[Memory](https://www.perplexity.ai/search/8faabaa0-1478-409e-80e1-c98204d92ad2)

------

## 2. Conceptual overview

The framework explicitly separates **alpha generation** from **risk shaping**:

- The **Y₁ model** focuses on detecting technically and statistically robust opportunities to enter positions in single FX pairs (e.g. EURUSD) over horizons such as **10 hours (H1)** or **5 business days (D1)**.
- The **Y₂ model** focuses on deciding whether, when a Y₁ signal is triggered, the desk should **apply a complementary hedge or portfolio adjustment**, for example via another pair such as USDJPY, to reduce or redistribute key currency risk (e.g. USD factor exposure).lhfx+2

In production, both decisions are evaluated in sequence:

1. Y₁ suggests a **main position** (e.g. BUY EURUSD).
2. Conditional on Y₁ firing, Y₂ evaluates the **current risk context** (volatility, correlations, exposures) and decides whether to add a **companion position** (e.g. in USDJPY) or leave the main trade unhedged.

------

## 3. Definition of Y₁: primary FX trading signal

## 3.1 Time horizons

We focus on two operational horizons, aligned with the desk’s style:

- **H1 horizon (10 hours)**
  Each bar represents 1 hour. Y₁ predicts the movement over the next 10 bars (10 hours).
- **D1 horizon (5 business days)**
  Each bar represents 1 day. Y₁ predicts the movement over the next 5 daily bars (roughly one trading week).oreilly+1

## 3.2 Future return definition

For a given pair (e.g. EURUSD), we define the future return over horizon $h$ as a simple percentage change:
\[
r_{t \to t+h} = \frac{Close_{t+h} - Close_{t}}{Close_{t}}
\]
This can be computed for any horizon $h$, such as 10 hours or 5 days.

## 3.3 Label construction for Y₁

Using this future return, we define a **three‑state label** based on return thresholds:

- **BUY signal** when the future return is sufficiently positive:

\[
r_{t \to t+h} \ge \theta^{+}
\]

* **SELL signal** when the future return is sufficiently negative:
  \[
  r_{t \to t+h} \le \theta^{-}
  \]

* **NEUTRAL / NO TRADE** when the future return is in between:
  \[
  \theta^{-} < r_{t \to t+h} < \theta^{+}
  \]

The thresholds $\theta^{+}$ and $\theta^{-}$ are chosen in terms of **pips, ATR or R‑units**, so that any trade implied by Y₁ is economically meaningful: large enough to justify transaction costs, risk and capital usage.risklab+1

## 3.4 Separate models for BUY and SELL

To keep the architecture simple and robust:

- A **BUY model** is trained to classify **“BUY vs NO‑BUY”**, using only examples where the future return is non‑negative, and labeling BUY when $r_{t \to t+h} \ge \theta^{+}$.
- A **SELL model** is trained to classify **“SELL vs NO‑SELL”**, using only examples where the future return is non‑positive, and labeling SELL when $r_{t \to t+h} \le \theta^{-}$.mql5+1

This preserves interpretability: Y₁ learns patterns in OHLC and derived features that precede **sufficiently large moves in the desired direction** over 10 hours or 5 days.

------

## 4. Definition of Y₂: hedge / risk adjustment decision

## 4.1 Motivation

While Y₁ focuses on whether to trade a given pair, a bank’s desk also cares about:

- **Exposure to individual currencies** (EUR, USD, JPY, etc.) across the whole book.
- **Volatility and regime shifts** that may increase the risk associated with specific currency factors (e.g. USD).
- **Dynamic correlations** between FX pairs, which can be used to partially hedge or rebalance risk.myfxbook+2

Y₂ is designed to capture this second layer: whether to complement a main position with an additional trade that **improves the risk‑return profile at portfolio level**, rather than simply adding more directional exposure.

## 4.2 Stylized example: EURUSD main position with USDJPY hedge

Consider a simplified example:

- Y₁ issues a **BUY signal on EURUSD**, leading to a long EURUSD position.
- The desk’s exposure now includes being long EUR and short USD.
- A second pair, such as **USDJPY**, can be used to adjust the **net USD and JPY exposure** in the book, depending on current correlations and volatility.rankia+1

In this setting, Y₂ is defined as a **binary label**:

- **Y₂ = 1:** apply a hedge / portfolio adjustment (e.g. open a position in USDJPY with a size calibrated to reduce or redistribute USD risk).
- **Y₂ = 0:** do not apply hedge; keep only the main EURUSD position.

This hedge is not necessarily a simple “opposite position” on the same pair. It is a **controlled adjustment of currency factor exposures** using another FX pair, based on empirical evidence of risk reduction (for example, lower portfolio volatility, smaller drawdowns, better risk‑adjusted returns).oikonomicon.udc+1

## 4.3 Features and criteria for constructing Y₂

To build and train Y₂, the framework uses features such as:

- **Net currency exposures**
  Aggregation of current positions by currency (EUR, USD, JPY, etc.), before and after the main trade suggested by Y₁. This allows us to quantify how much USD, EUR, JPY risk is being taken.
- **Rolling correlations between pairs**
  For example, correlation between EURUSD and USDJPY returns over rolling windows (e.g. 60, 120, 250 days), to identify regimes where adding the hedge historically helped to smooth portfolio behavior.myfxbook+1
- **Volatility measures**
  ATR or standard deviation of returns for each pair and for currency factors, to detect high‑risk regimes that may justify hedging.litefinance+1
- **Event / regime indicators**
  Proximity to major macro events, or regime flags that historically coincide with elevated risk.

Initial historical labels for Y₂ can be constructed via simple rule‑based criteria, for example:

- Set **Y₂ = 1** (apply hedge) when:
  - Net exposure to a key currency (e.g. USD) exceeds a predefined risk threshold, **and**
  - Volatility of USD‑related pairs is above a certain level, **and**
  - The correlation structure suggests that adding a position in the hedge pair historically reduces portfolio variance or drawdown.traders-trust+2
- Set **Y₂ = 0** (no hedge) in other cases.

A machine learning model is then trained to **replicate and refine** this rule‑based behavior, learning from data when a hedge is beneficial and when it is unnecessary.

------

## 5. Operational interaction between Y₁ and Y₂

In live operation, the interaction is:

1. **Signal generation (Y₁)**
   - The Y₁ models (BUY and SELL) evaluate the current state of the market for each pair and, if thresholds are met, trigger a trading alert (for example, “BUY EURUSD with a 10‑hour / 5‑day horizon”).
2. **Risk assessment and hedge decision (Y₂)**
   - Conditional on a Y₁ alert, the Y₂ model is evaluated using the current exposures, correlations, volatility and regime indicators.
   - If **Y₂ = 1**, the system issues a **hedge alert**, recommending the addition of a predefined hedge position (e.g. in USDJPY) sized according to the desk’s risk constraints.
   - If **Y₂ = 0**, the desk operates only the main signal.

This dual‑target approach allows the desk to move from **single‑pair trading** to **risk‑aware portfolio decisions**, while keeping the logic **simple, transparent and compatible** with institutional risk management practices.

