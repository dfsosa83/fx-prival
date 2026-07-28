"""
Agent evaluation for SELL signals.

Agent A — Technical (GPT-4o via OpenRouter)
Agent B — Fundamental (Sonar Pro via Perplexity API)
Senior  — Coordination layer (rule engine)
"""

from .technical import evaluate as evaluate_technical
from .fundamental import evaluate as evaluate_fundamental
from .senior import synthesize