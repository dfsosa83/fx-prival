"""Inspect engine_v36 current state."""
from pathlib import Path

p = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/engine/engine_v36.py")
txt = p.read_text(encoding="utf-8")

print("=== short-stop condition lines ===")
for i, line in enumerate(txt.splitlines(), 1):
    s = line.strip()
    if ('bar["low"]' in s or 'bar["high"]' in s) and "if" in s:
        print(f"{i}: {s}")
    if "short_stop" in s and "if" in s:
        print(f"{i}: {s}")

print()
print("=== v35/v36 refs and def name ===")
print("v35 refs:", txt.count("v35"))
print("v36 refs:", txt.count("v36"))
print("def run_engine_v35 present:", "def run_engine_v35" in txt)
print("def run_engine_v36 present:", "def run_engine_v36" in txt)
print("class EpisodeV35:", "EpisodeV35" in txt)
print("class EpisodeV36:", "EpisodeV36" in txt)