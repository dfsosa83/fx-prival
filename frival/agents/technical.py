"""
Agent A — Technical Context Evaluator.

Takes model prediction + feature context → CONFIRM/REJECT/NEUTRAL.
Evaluates D1 trend, EMA alignment, MACD/RSI momentum, ADX strength,
and ensemble internal agreement.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

from .base import chat


PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "technical.txt"


def _load_prompt(prompt_file: Optional[str] = None) -> str:
    path = Path(prompt_file) if prompt_file else PROMPT_FILE
    with open(path, encoding="utf-8") as f:
        return f.read()


def _build_user_message(
    current_price: float,
    probability: float,
    threshold: float,
    individual_probs: Dict[str, float],
    d1_context: Dict[str, Any],
    top_features: Dict[str, float],
) -> str:
    """Build structured context for the technical agent."""

    model_agreement = sum(
        1 for p in individual_probs.values() if p >= threshold
    )

    lines = [
        f"Current price: {current_price:.5f}",
        f"Ensemble probability (SELL): {probability:.4f}",
        f"Operating threshold: {threshold}",
        f"Model agreement: {model_agreement}/4 sub-models above threshold",
    ]

    lines.append("\nSub-model probabilities:")
    for name, prob in sorted(individual_probs.items()):
        lines.append(f"  {name}: {prob:.4f}")

    lines.append("\nD1 Context (prior day close):")
    for key, value in d1_context.items():
        if isinstance(value, float):
            lines.append(f"  {key}: {value:.4f}")
        else:
            lines.append(f"  {key}: {value}")

    lines.append("\nCurrent bar features (model inputs):")
    for name, value in top_features.items():
        lines.append(f"  {name}: {value:.4f}")

    lines.append("\nEvaluate the SELL signal using the rules provided.")
    lines.append("Return JSON only.")

    return "\n".join(lines)


def _parse_response(raw: str) -> Dict[str, Any]:
    """Extract JSON from agent response. Handles markdown code fences."""

    # Strip code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.replace("```", "").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to find JSON object between { and }
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse JSON from agent response: {raw[:200]}...")


def evaluate(
    current_price: float,
    probability: float,
    threshold: float,
    individual_probs: Dict[str, float],
    d1_context: Dict[str, Any],
    top_features: Dict[str, float],
    *,
    model: str = "openai/gpt-4o",
    prompt_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluate whether the technical picture supports a SELL signal.

    Parameters
    ----------
    current_price : float
        Current bar close price.
    probability : float
        Calibrated ensemble probability (class1 = SELL).
    threshold : float
        Operating threshold (0.306).
    individual_probs : dict
        Per-model probabilities {LogReg: 0.31, RandomForest: 0.34, ...}.
    d1_context : dict
        Daily context: d1_rsi, d1_close_vs_ema20, d1_trend, d1_ema20, d1_ema50.
    top_features : dict
        Current bar feature values for the model's inputs.
    model : str
        OpenRouter model ID.

    Returns
    -------
    dict with keys: decision, confidence, justification, regime_flags.
    """
    system_prompt = _load_prompt(prompt_file)
    user_message = _build_user_message(
        current_price, probability, threshold,
        individual_probs, d1_context, top_features,
    )

    print(f"\n[Agent A - Technical] Evaluating signal (p={probability:.4f})...")
    raw = chat(system_prompt, user_message, model=model)
    result = _parse_response(raw)

    print(f"[Agent A] Decision: {result.get('decision')} ({result.get('confidence')})")
    print(f"[Agent A] {result.get('justification', '')}")

    return result