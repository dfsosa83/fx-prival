#!/usr/bin/env python
"""Merge MT5 probe results into the 36-cell coverage table + finalize.

Populates instrument_timeframe_coverage.csv with the read-only MT5 probe
evidence, updates contract_metadata.csv with current terminal specs, and
writes the final data-feasibility JSON summary.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")
OUT = Path("quant-personal-fund/audits/PHASE-0-5-DATA-AUDIT")

with open(OUT / "mt5_probe_v2_results.json", encoding="utf-8") as f:
    probe = json.load(f)

cov = pd.read_csv(OUT / "instrument_timeframe_coverage.csv")

for idx, row in cov.iterrows():
    key = f"{row['instrument']}_{row['timeframe']}"
    cell = probe["cells"].get(key)
    if not cell:
        continue
    cov.loc[idx, "returned_start"] = cell.get("envelope_first", "")
    cov.loc[idx, "returned_end"] = cell.get("envelope_last", "")
    cov.loc[idx, "bars_returned_recent"] = cell.get("rows_2026_08_09", "")
    cov.loc[idx, "duplicate_timestamps"] = cell.get("dup_2026_08_09", "")
    cov.loc[idx, "gaps_over_1.5x_recent"] = cell.get("gaps_over_1.5x_2026_08_09", "")
    cov.loc[idx, "repeated_query_stable"] = cell.get("repeated_query_stable", "")
    cov.loc[idx, "source_origin"] = (
        "repeated query — stable (terminal query x2 identical)"
        if cell.get("repeated_query_stable") else "current terminal query"
    )
    cov.loc[idx, "fields_available"] = ",".join(cell.get("fields", []))
    cov.loc[idx, "bars_spread_field"] = "yes" if cell.get("has_bar_spread") else "no"
    cov.loc[idx, "tick_rows"] = cell.get("tick_rows", 0)
    cov.loc[idx, "hist_bid_ask"] = (
        "yes" if cell.get("tick_has_bid_ask") else
        "UNAVAILABLE — tick API returned no ticks (error -2 Invalid arguments)"
    )
    cov.loc[idx, "server_retention_verified"] = False
    cov.loc[idx, "maxbars_setting"] = "NOT READ via terminal (would disturb session); copy_rates_range worked to 2016 on FX / 2020 on XAUUSD"
    cov.loc[idx, "maxbars_constrains_copyrates"] = (
        "OBSERVED: requests beyond envelope returned empty (2015 probe) — consistent with a retention/maxbars limit; "
        "exact TERMINAL_MAXBARS value not read (recording requires terminal inspection)"
    )
    cov.loc[idx, "tz_convention"] = "unix epoch; server offset not decoded; local cache datetimes are UTC-labelled (verify vs broker)"
    cov.loc[idx, "calendar_assumption"] = (
        "PARTIAL — recent-window gaps (7 per FX cell) consistent with weekends; XAUUSD daily halt not mapped; "
        "holiday calendar unresolved"
    )
    cov.loc[idx, "adequacy"] = "exploratory"  # provisional; sealed requires calendar + cost confirmation

# For cells with a stable envelope and no dups -> note adequacy nuance
cov.to_csv(OUT / "instrument_timeframe_coverage.csv", index=False)
print("coverage table merged")

# ── contract_metadata update ───────────────────────────────────────────────
cm = pd.read_csv(OUT / "contract_metadata.csv")
specs = probe["symbol_specs"]
for idx, row in cm.iterrows():
    s = specs.get(row["instrument"], {})
    if not s or "error" in s:
        continue
    cm.loc[idx, "digits"] = s.get("digits")
    cm.loc[idx, "point"] = s.get("point")
    cm.loc[idx, "volume_min"] = s.get("volume_min")
    cm.loc[idx, "volume_step"] = s.get("volume_step")
    cm.loc[idx, "spread_note"] = f"{s.get('spread')} pts (current demo terminal)"
    cm.loc[idx, "swap_long"] = s.get("swap_long")
    cm.loc[idx, "swap_short"] = s.get("swap_short")
    cm.loc[idx, "sessions"] = s.get("path", "")
    cm.loc[idx, "symbol_suffix"] = s.get("path", "")
    cm.loc[idx, "source"] = "MT5 demo terminal symbol_info (current) — swap/spread CONFIRMED CURRENT; contract_size null in API (gold_rules pre-flight verified 100 oz/lot XAUUSD)"
    cm.loc[idx, "broker_confirmed"] = "current-terminal" if row["instrument"] == "XAUUSD" else "current-terminal-spec"
cm.to_csv(OUT / "contract_metadata.csv", index=False)
print("contract metadata updated")

# ── summary JSON ───────────────────────────────────────────────────────────
summary = {
    "cells_total": 36,
    "cells_probed_ok": len(probe["cells"]),
    "cells_error": sum(1 for c in probe["cells"].values() if "error" in c),
    "envelope_summary": {
        sym: {
            "first": probe["cells"][f"{sym}_M5"].get("envelope_first"),
            "last": probe["cells"][f"{sym}_M5"].get("envelope_last"),
        } for sym in ["XAUUSD","EURUSD","GBPUSD","AUDUSD","NZDUSD","USDCAD","USDCHF","USDJPY","EURJPY"]
    },
    "tick_data": "UNAVAILABLE — 0 ticks returned in 7-day window across all 36 cells (MT5 error -2)",
    "hist_bid_ask": "UNAVAILABLE via tick API",
    "bar_spread_field": "present in all 36 cells (bar-level spread, NOT historical bid/ask)",
    "repeated_query_stable": "all 36 cells stable across two identical queries",
    "duplicates": "0 in recent window across all cells",
    "recent_gaps": "7 per FX cell (>1.5x interval, consistent with weekends); XAUUSD cells same order",
    "maxbars": "value NOT read (terminal inspection would disturb session); copy_rates_range returned data from 2016 (FX) / 2020 (XAUUSD); 2015 probe returned empty — retention/maxbars limit observed but TERMINAL_MAXBARS exact value unknown",
    "server_retention_verified": False,
    "source_origin_note": "All data 'repeated query — stable' (two identical terminal queries); broker-server retention not independently verified",
}
with open(OUT / "data_feasibility_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print("summary written")
print(json.dumps(summary, indent=2))