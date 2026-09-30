"""Verify v3.6 engine imports and fix presence."""
import sys
from pathlib import Path

sys.path.insert(0, "quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B")
from engine.engine_v36 import EpisodeV36, REASON_CODES_V35, run_engine_v36  # noqa

print("v3.6 engine imports OK")
print("run_engine_v36:", run_engine_v36.__name__)
print("EpisodeV36:", EpisodeV36.__name__)

txt = Path("quant-personal-fund/experiments/EXP-2026-05-INVALIDATION-REVERSAL/audits/PHASE-1B/engine/engine_v36.py").read_text(encoding="utf-8")
print("has high>=stop fix:", 'if bar["high"] >= short_stop:' in txt)
print("no low<=stop bug:", 'if bar["low"] <= short_stop:' not in txt)
print("gap open>=stop handling:", 'float(bar["open"]) >= short_stop' in txt)