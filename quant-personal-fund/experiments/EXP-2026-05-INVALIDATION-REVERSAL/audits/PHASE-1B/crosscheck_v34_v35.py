"""Cross-check v3.4 vs v3.5 totals to identify the 2,579/5,229 reference."""
import json
from pathlib import Path

import pandas as pd

BASE = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/reports")

v34 = json.load(open(BASE / "LEDGER_V34_SUMMARY.json", encoding="utf-8"))
led = pd.read_csv(BASE / "episode_ledger_v35.csv")

print("=== v3.4 summary (prior version) ===")
for w in ["development", "research_grade_oos"]:
    d = v34[w]
    print(f"  {w}: total_original_long_entries = {d['total_original_long_entries']}")
v34_total = v34["development"]["total_original_long_entries"] + v34["research_grade_oos"]["total_original_long_entries"]
print(f"  v3.4 TOTAL: {v34_total}")

print("\n=== v3.5 CSV ===")
dev = (led["assignment_window"] == "development").sum()
oos = (led["assignment_window"] == "research_grade_oos").sum()
print(f"  dev rows: {dev}")
print(f"  oos rows: {oos}")
print(f"  v3.5 TOTAL: {dev + oos}")