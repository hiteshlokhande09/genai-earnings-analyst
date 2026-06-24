"""
Llama 3 language generation (Sprint 1, Step 8 — summary / risk / guidance).

Calls a Llama 3 model through an OpenAI-compatible chat-completions endpoint
(Groq by default). Three task functions generate the executive summary, a
structured list of risk factors, and the forward-guidance summary.

Cost-control measures (per the SRS non-functional requirements):
* only the RAG-retrieved context is sent to the model, never the full filing;
* responses are capped at ``LLAMA3_MAX_TOKENS``;
* calls retry with exponential backoff on transient failures;
* if no API key is configured, clearly-labelled placeholders are returned so
  the rest of the pipeline still runs.
"""

from __future__ import annotations

import json
import re
import time
from typing import List, Optional

import requests

from genai_analyst.core import config

_PLACEHOLDER = "[LLM not configured — set LLAMA3_API_KEY in your .env file.]"
_EMPTY = "No forward-looking guidance was found in the retrieved sections of this filing."


def _chat(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Send a single chat-completion request, with retries. Returns text/None."""
    if not config.is_llm_configured():
        return None

    headers = {
        "Authorization": f"Bearer {config.LLAMA3_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.LLAMA3_MODEL,
        "max_tokens": config.LLAMA3_MAX_TOKENS,
        "temperature": config.LLAMA3_TEMPERATURE,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    last_error: Optional[Exception] = None
    for attempt in range(config.HTTP_MAX_RETRIES):
        # Exponential backoff (base HTTP_BACKOFF_SECONDS, doubling each retry)
        # to avoid hammering the endpoint during transient outages/rate limits.
        try:
            response = requests.post(
                config.LLAMA3_BASE_URL,
                headers=headers,
                json=payload,
                timeout=config.HTTP_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as error:
            last_error = error
            time.sleep(config.HTTP_BACKOFF_SECONDS * (2 ** attempt))

    print(f"[nlp.generation] Llama 3 request failed: {last_error}")
    return None


def generate_executive_summary(context: str) -> str:
    """Generate a concise executive summary from retrieved context."""
    if not config.is_llm_configured():
        return _PLACEHOLDER
    system = (
        "You are a financial analyst. Write a concise, factual executive "
        "summary of the company's performance using ONLY the provided context. "
        "Do not invent numbers."
    )
    result = _chat(system, f"Context:\n{context}\n\nExecutive summary:")
    return result or _PLACEHOLDER


def extract_risk_factors(context: str) -> List[dict]:
    """Extract the top risk factors as a list of structured dicts."""
    if not config.is_llm_configured():
        return []
    system = (
        "You are a financial analyst. From the provided context, extract the "
        "top 5 risk factors. Respond ONLY with a JSON array of objects, each "
        'with keys "risk", "category" and "severity" (Low/Medium/High). '
        "No prose, no markdown."
    )
    result = _chat(system, f"Context:\n{context}\n\nJSON:")
    if not result:
        return []

    # Be tolerant of code fences or stray text around the JSON.
    match = re.search(r"\[.*\]", result, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def extract_guidance(context: str) -> str:
    """Summarise forward-looking guidance from retrieved context."""
    if not config.is_llm_configured():
        return _PLACEHOLDER
    system = (
        "You are a financial analyst. Summarise the company's forward-looking "
        "guidance and outlook using ONLY the provided context. If no explicit "
        "guidance is given, say so."
    )
    result = _chat(system, f"Context:\n{context}\n\nForward guidance:")
    return result or _EMPTY