"""
Agent B — Fundamental / Macro Evaluator.

Uses Perplexity API with web search to assess macro regime:
ECB/Fed divergence, DXY direction, active news, risk sentiment.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


API_ENDPOINT = "https://api.perplexity.ai/chat/completions"
PROMPT_FILE = Path(__file__).resolve().parent / "prompts" / "fundamental.txt"


def _load_api_key() -> str:
    env_file = Path(__file__).resolve().parents[1] / "config" / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("PERPLEXITY_API_KEY="):
                    return line.partition("=")[2].strip()
    key = os.environ.get("PERPLEXITY_API_KEY", "")
    if not key:
        raise RuntimeError("PERPLEXITY_API_KEY not set in frival/config/.env")
    return key


def _load_prompt() -> str:
    with open(PROMPT_FILE, encoding="utf-8") as f:
        return f.read()


def _build_user_message(
    currency_pair: str,
    current_price: float,
    probability: float,
) -> str:
    return (
        f"Evaluate the macro environment for a SELL signal on {currency_pair}.\n"
        f"Current price: {current_price:.5f}\n"
        f"Model probability (SELL): {probability:.4f}\n\n"
        f"Search the web for recent ECB/Fed news, DXY direction, event risk, and "
        f"risk sentiment. Return your evaluation as JSON."
    )


def _parse_response(raw: str) -> Dict[str, Any]:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"Could not parse JSON from: {raw[:200]}...")


def evaluate(
    current_price: float,
    probability: float,
    currency_pair: str = "EURUSD",
    *,
    max_retries: int = 2,
) -> Dict[str, Any]:
    """
    Evaluate the macro environment for a EURUSD SELL signal via Perplexity.

    Parameters
    ----------
    current_price : float
    probability : float
    currency_pair : str
    max_retries : int

    Returns
    -------
    dict with: decision, confidence, justification, regime_flags, news_sources
    """
    api_key = _load_api_key()
    system_prompt = _load_prompt()
    user_message = _build_user_message(currency_pair, current_price, probability)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "search_recency_filter": "day",
        "return_related_questions": False,
    }

    print(f"\n[Agent B - Fundamental] Searching macro context (p={probability:.4f})...")

    for attempt in range(1 + max_retries):
        try:
            resp = requests.post(
                API_ENDPOINT, headers=headers, json=payload, timeout=45.0, verify=False
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                # Strip problematic Unicode characters
                content = (
                    content.encode("ascii", errors="replace")
                    .decode("ascii")
                    .replace("?", " ")
                )
                result = _parse_response(content)
                break
            else:
                result = {
                    "decision": "NEUTRAL",
                    "confidence": "LOW",
                    "justification": f"API error {resp.status_code}",
                    "regime_flags": {},
                    "news_sources": [],
                }
        except Exception as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"[Agent B] Retry {attempt + 1}/{max_retries} in {wait}s: {e}")
                time.sleep(wait)
            else:
                result = {
                    "decision": "NEUTRAL",
                    "confidence": "LOW",
                    "justification": f"API error after {max_retries} retries: {e}",
                    "regime_flags": {},
                    "news_sources": [],
                }

    print(f"[Agent B] Decision: {result.get('decision')} ({result.get('confidence')})")
    print(f"[Agent B] {result.get('justification', '')}")

    return result