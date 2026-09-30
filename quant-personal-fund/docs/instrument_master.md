# Instrument Master

## Purpose

The instrument master is the single source of truth for every instrument in the research universe. It defines each instrument's specifications, trading characteristics, and metadata. All modules (`core`, `signals`, `portfolio`, `risk`, `backtest`) reference the instrument master rather than hardcoding instrument properties.

## Machine-Readable Source

The canonical machine-readable instrument master is `data/reference/instrument_master.csv`.

## Human-Readable Reference

The universe configuration is defined in `config/universe.yaml` and loaded by `core/instruments.py`.

### Asset Classes Included (Phase 1 target: ~16 instruments)

| Asset Class | Instruments | Role in Portfolio |
|---|---|---|
| **G10 FX** | EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, USDCHF, NZDUSD, EURJPY | Macro, rates, carry, global risk exposure |
| **Equity Indices** | S&P 500 (SPX), Nasdaq 100 (NDX), Euro Stoxx 50 (SX5E), Nikkei 225 (NKY) | Global growth and risk-cycle exposure |
| **Government Bonds** | US 10Y Treasury, German Bund, Japanese Government Bond | Policy, inflation, defensive diversification |
| **Commodities** | Gold (XAU), Crude Oil (WTI), Copper | Inflation, supply shocks, demand cycles |

### Instrument Record Fields

| Field | Description | Example |
|---|---|---|
| `ticker` | Standardized ticker symbol | `EURUSD` |
| `asset_class` | One of: `fx`, `equity_index`, `govt_bond`, `commodity` | `fx` |
| `base_currency` | ISO 4217 base currency | `EUR` |
| `quote_currency` | ISO 4217 quote currency | `USD` |
| `pip_value` | Value of one pip in quote currency (FX) or tick value | `0.0001` |
| `lot_size` | Standard lot size in base currency | `100000` |
| `tick_size` | Minimum price increment | `0.00001` |
| `session_hours` | Primary trading session (UTC) | `00:00-23:59` (FX is 24/5) |
| `holiday_calendar` | Reference to holiday calendar | `FX_global` |
| `data_source` | Primary data vendor | `yahoo` |
| `yahoo_ticker` | Yahoo Finance symbol | `EURUSD=X` |
| `is_active` | Whether the instrument is currently in the research universe | `true` |

### Instrument Substitutions

Where direct instruments are unavailable through free data sources, proxies may be used:

| Target Instrument | Yahoo Finance Proxy | Notes |
|---|---|---|
| US 10Y Treasury | `^TNX` | 10-year Treasury yield (need to convert to price/bond proxy) |
| German Bund | `^GDBR10` (or `BUND.DE` if ETF proxy preferred) | May need ETF proxy |
| Japanese Government Bond | ETF proxy (`JGBS`, `JGBL`) | Direct JGB futures data limited on free sources |
| WTI Crude Oil | `CL=F` | Front-month futures |
| Copper | `HG=F` | Front-month futures |

### Addition and Removal

- Instruments are added to the universe by updating `config/universe.yaml` and `data/reference/instrument_master.csv`.
- Instruments are removed (but not deleted) by setting `is_active: false` in the master.
- Historical data for inactive instruments is preserved — they may be reactivated.
- An instrument is only eligible for strategy allocation if it has ≥3 years of continuous daily data and its cost model is populated.