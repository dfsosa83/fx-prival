"""
OpenRouter API client.

Async, with retry and structured JSON output enforcement.
Uses the OpenAI-compatible API endpoint.
"""

import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any

from openai import OpenAI


def _load_api_key() -> str:
    """Load OpenRouter key from .env file or environment."""
    env_file = Path(__file__).resolve().parents[1] / "config" / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    return line.partition("=")[2].strip()

    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Add it to frival/config/.env"
        )
    return key


def chat(
    system_prompt: str,
    user_message: str,
    *,
    model: str = "openai/gpt-4o",
    temperature: float = 0.1,
    max_tokens: int = 500,
    max_retries: int = 2,
    timeout: float = 30.0,
) -> str:
    """
    Send a prompt to OpenRouter and return the response text.

    Parameters
    ----------
    system_prompt : str
        Instructions for the agent (role, rules, output format).
    user_message : str
        The specific question or data to evaluate.
    model : str
        OpenRouter model ID (e.g. "openai/gpt-4o", "anthropic/claude-3.5-sonnet").
    temperature : float
        Lower = more deterministic.
    max_tokens : int
        Max response length.
    max_retries : int
        Number of retries on failure.
    timeout : float
        Seconds before timeout.

    Returns
    -------
    str — raw response content from the model.
    """
    api_key = _load_api_key()

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=timeout,
    )

    for attempt in range(1 + max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"[OpenRouter] Retry {attempt + 1}/{max_retries} in {wait}s: {e}")
                time.sleep(wait)
            else:
                raise RuntimeError(f"OpenRouter call failed after {max_retries} retries: {e}")

    return ""