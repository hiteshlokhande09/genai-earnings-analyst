"""
generation.py
================
Llama 3 Integration (Pipeline Step 8 - LLM layer).

Calls Meta Llama 3 through an OpenAI-compatible chat-completions endpoint
(default: Groq free tier). Used ONLY for language tasks:
    * Executive summary generation
    * Top-5 risk factor extraction (category + severity)
    * Forward guidance extraction

Financial numbers are NEVER asked of the LLM -- those come from XBRL.

Cost-control measures (SRS constraints):
    * Only RAG-retrieved chunks are sent (not the whole filing).
    * max_tokens capped at 500.
    * Responses cached in SQLite to avoid re-calling for the same filing.
    * Retry with exponential backoff for transient failures.
"""

from __future__ import annotations

import json
import re
import time
from typing import List, Optional

import requests

from genai_analyst.core import config
from genai_analyst.core import database
# --------------------------------------------------------------------------- #
# Core API call
# --------------------------------------------------------------------------- #
def _chat(system_prompt: str, user_prompt: str) -> Optional[str]:
    """Single chat-completion call with retry/backoff. Returns text or None."""
    if not config.LLAMA3_API_KEY:
        print("[generation] LLAMA3_API_KEY not set; returning None.")
        return None

    headers = {
        "Authorization": f"Bearer {config.LLAMA3_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.LLAMA3_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": config.LLAMA3_MAX_TOKENS,
        "temperature": config.LLAMA3_TEMPERATURE,
    }

    last_err: Optional[Exception] = None
    for attempt in range(config.MAX_RETRIES):
        try:
            resp = requests.post(
                config.LLAMA3_BASE_URL,
                headers=headers,
                json=payload,
                timeout=config.REQUEST_TIMEOUT,
            )
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"Transient status {resp.status_code}")
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(config.BACKOFF_BASE ** attempt)
    print(f"[generation] chat failed after retries: {last_err}")
    return None


def _cached_chat(cache_key: str, system_prompt: str, user_prompt: str) -> Optional[str]:
    """Wrap _chat with a SQLite cache keyed by (filing+task)."""
    cached = database.get_llm_cache(cache_key)
    if cached is not None:
        return cached
    result = _chat(system_prompt, user_prompt)
    if result is not None:
        database.set_llm_cache(cache_key, result)
    return result


# --------------------------------------------------------------------------- #
# Task-specific helpers
# --------------------------------------------------------------------------- #
_SUMMARY_SYS = (
    "You are a meticulous financial analyst. Summarise the provided excerpt "
    "from an SEC filing into a concise, factual executive summary (max 6 "
    "sentences). Do NOT invent numbers; only use figures present in the text."
)

_RISK_SYS = (
    "You are a risk analyst. From the provided risk-factor excerpt, extract the "
    "TOP 5 risk factors. Respond ONLY with a JSON array; each item must have "
    "keys: 'risk' (short phrase), 'category' (one of: Market, Operational, "
    "Financial, Regulatory, Strategic, Technology), and 'severity' (High, "
    "Medium, or Low). No prose, no markdown, JSON only."
)

_GUIDANCE_SYS = (
    "You are a financial analyst. From the provided excerpt, extract management's "
    "forward-looking guidance and outlook in 3-4 concise bullet sentences. If no "
    "explicit guidance is present, state that no formal guidance was provided."
)


def generate_executive_summary(context: str, cache_key: str) -> str:
    """Generate an executive summary from retrieved context."""
    out = _cached_chat(f"{cache_key}:summary", _SUMMARY_SYS, context[:8000])
    return out or "Executive summary unavailable (LLM not configured or no context)."


def extract_risk_factors(context: str, cache_key: str) -> List[dict]:
    """Extract top-5 structured risk factors. Always returns a list."""
    out = _cached_chat(f"{cache_key}:risks", _RISK_SYS, context[:8000])
    if not out:
        return []
    return _safe_parse_json_array(out)


def extract_guidance(context: str, cache_key: str) -> str:
    """Extract forward guidance summary."""
    out = _cached_chat(f"{cache_key}:guidance", _GUIDANCE_SYS, context[:8000])
    return out or "Forward guidance unavailable (LLM not configured or no context)."


def _safe_parse_json_array(text: str) -> List[dict]:
    """Best-effort extraction of a JSON array from an LLM response."""
    # Strip code fences if present.
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


if __name__ == "__main__":
    print("Llama3 configured:", bool(config.LLAMA3_API_KEY))
    print("Model:", config.LLAMA3_MODEL)
