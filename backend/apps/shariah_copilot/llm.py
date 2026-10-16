"""
One place that talks to the language model (BRD 9: private gateway, kill switch, safe fallback). Plain HTTPS calls, so no
vendor SDK is needed. Provider is chosen by COPILOT_LLM_PROVIDER:

  anthropic - hosted, needs ANTHROPIC_API_KEY
  gemini    - hosted, needs GEMINI_API_KEY
  ollama    - a model on your own network, no key; nothing leaves the bank (use this when data residency demands it)
"""

import requests
from django.conf import settings


class LLMUnavailable(Exception):
    """The model cannot be reached or is not configured: the caller degrades safely, nothing is invented."""


class LLMError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(f"LLM returned {status_code}: {detail}")


def _post(url, *, headers=None, json=None):
    try:
        response = requests.post(url, headers=headers, json=json, timeout=settings.COPILOT_LLM_TIMEOUT_SECONDS)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
        raise LLMUnavailable(str(exc)) from exc
    if response.status_code in (429, 500, 502, 503, 504):
        # Rate limit or a provider outage: temporary, so the platform answers "unavailable" (503), never a guess.
        raise LLMUnavailable(f"The language model is temporarily unavailable (HTTP {response.status_code}): {response.text[:300]}")
    if not response.ok:
        raise LLMError(response.status_code, response.text[:500])
    return response.json()


def generate(system, user_prompt, *, max_tokens=2000):
    provider = settings.COPILOT_LLM_PROVIDER
    if provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not set.")
        data = _post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01"},
            json={"model": settings.ANTHROPIC_MODEL, "max_tokens": max_tokens, "system": system,
                  "messages": [{"role": "user", "content": user_prompt}]},
        )
        return "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise LLMUnavailable("GEMINI_API_KEY is not set.")
        data = _post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent",
            headers={"x-goog-api-key": settings.GEMINI_API_KEY},
            json={"systemInstruction": {"parts": [{"text": system}]}, "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                  "generationConfig": {"responseMimeType": "application/json"}},
        )
        parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts")) or []
        return "".join(p.get("text", "") for p in parts)
    if provider == "ollama":
        data = _post(
            f"{settings.OLLAMA_HOST.rstrip('/')}/api/chat",
            json={"model": settings.OLLAMA_MODEL, "stream": False, "format": "json",
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_prompt}]},
        )
        return (data.get("message") or {}).get("content", "")
    raise LLMUnavailable(f"Unknown COPILOT_LLM_PROVIDER '{provider}'.")
