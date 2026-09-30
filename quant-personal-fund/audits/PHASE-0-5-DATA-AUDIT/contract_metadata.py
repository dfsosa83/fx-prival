#!/usr/bin/env python
"""Phase 0.5 — contract metadata (CURRENT-SPEC, from verified prior evidence).

Sources:
  - XAUUSD: gold_rules design doc v1.3 pre-flight (verified live 2026-09-15):
    contract 100 oz/lot, digits 2, point 0.01, tick value $1/$1 at 1.0 lot,
    volume_min 0.01, margin ~$8.60/0.01 lot, spread 19 pts, trade_mode full.
  - FX: quant-personal-fund instrument master (config/universe.yaml) +
    cost model (config/cost_model.yaml) — research-spec, NOT broker-confirmed.
  - EURJPY: cross-pair, JPY-quoted, pip 0.01 (instrument master).

All values are CURRENT-SPEC PROVISIONAL unless confirmed by the broker.
Swap values for FX are from the research cost model (0.0 = unmodeled), NOT
broker-confirmed. This is a data-governance artifact, not a cost decision.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
OUT = Path("quant-personal-fund/audits/PHASE-0-5-DATA-AUDIT")

rows = [
    # instrument, contract_size, digits, point, tick_value_note, volume_min,
    # spread_note, swap_long, swap_short, sessions, suffix, source, confirmed
    ("XAUUSD", 100.0, 2, 0.01, "$1 per $1 price move @1.0 lot", 0.01,
     "19 pts (verified live 2026-09-15)", "unmodeled", "unmodeled",
     "~23h/day CFD + daily maintenance halt", "", "gold_rules v1.3 pre-flight", "yes"),
    ("EURUSD", None, 5, 0.00001, "USD per 1 EUR unit", None,
     "1.8 pips research (spread_pips*1.5)", 0.0, 0.0,
     "24/5 FX", "", "quant-personal-fund cost_model (research)", "no"),
    ("GBPUSD", None, 5, 0.00001, "USD per 1 GBP unit", None,
     "2.4 pips research", 0.0, 0.0, "24/5 FX", "", "research cost_model", "no"),
    ("AUDUSD", None, 5, 0.00001, "USD per 1 AUD unit", None,
     "2.3 pips research", 0.0, 0.0, "24/5 FX", "", "research cost_model", "no"),
    ("NZDUSD", None, 5, 0.00001, "USD per 1 NZD unit", None,
     "3.0 pips research", 0.0, 0.0, "24/5 FX", "", "research cost_model", "no"),
    ("USDCAD", None, 5, 0.00001, "CAD per 1 USD unit", None,
     "2.3 pips research", 0.0, 0.0, "24/5 FX", "", "research cost_model", "no"),
    ("USDCHF", None, 5, 0.00001, "CHF per 1 USD unit", None,
     "2.3 pips research", 0.0, 0.0, "24/5 FX", "", "research cost_model", "no"),
    ("USDJPY", None, 3, 0.001, "JPY per 1 USD unit; pip 0.01", None,
     "2.0 pips research", 0.0, 0.0, "24/5 FX", "", "research cost_model", "no"),
    ("EURJPY", None, 3, 0.001, "JPY per 1 EUR unit; pip 0.01 (cross)", None,
     "3.0 pips research", 0.0, 0.0, "24/5 FX (cross)", "", "research cost_model", "no"),
]

df = pd.DataFrame(rows, columns=[
    "instrument", "contract_size", "digits", "point", "tick_value_note",
    "volume_min", "spread_note", "swap_long", "swap_short", "sessions",
    "symbol_suffix", "source", "broker_confirmed",
])
df.to_csv(OUT / "contract_metadata.csv", index=False)
print(f"contract_metadata.csv: {len(df)} rows")

# Reproducibility manifest (local-only portion; no MT5 queries run)
manifest = {
    "audit": "PHASE-0-5-DATA-AUDIT",
    "generated_at": "2026-09-24",
    "mt5_query_status": "STOPPED",
    "mt5_stop_reason": (
        "Active terminal64 (FPMarkets MT5) process detected. MT5 Python API is "
        "single-terminal IPC; cannot guarantee an isolated read-only connection "
        "without risking disturbance of the active session. Per approved "
        "safeguard #2, stopped before any MT5 query."
    ),
    "terminal_maxbars_setting": "NOT READ (MT5 query not run; would require terminal inspection)",
    "local_files_inventoried": 33,
    "source_origin_policy": (
        "No MT5 queries run; all data rows marked 'MT5 QUERY NOT RUN'. "
        "server_retention_verified=False everywhere."
    ),
    "instrument_timeframe_cells": 36,
    "contract_metadata_source": (
        "XAUUSD: verified live pre-flight (gold_rules v1.3). FX: research "
        "instrument master/cost model — PROVISIONAL, not broker-confirmed."
    ),
    "python": sys.version.split()[0],
    "audit_scripts": ["local_inventory.py"],
}

with open(OUT / "REPRODUCIBILITY_MANIFEST.json", "w") as f:
    json.dump(manifest, f, indent=2)
print("REPRODUCIBILITY_MANIFEST.json written")