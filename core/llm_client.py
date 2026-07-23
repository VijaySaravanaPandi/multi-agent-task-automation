"""
Thin wrapper around Groq's OpenAI-compatible chat completions endpoint.

Kept deliberately simple (raw requests, no SDK) so it's easy to swap
providers later without touching agent code — agents only ever call
LLMClient.complete(), never the HTTP details directly.
"""

import json
import requests
from config.settings import settings


class LLMClient:
    def __init__(self, api_key: str | None = None):
        # Falls back to key 1 if no specific key given — lets different
        # agents optionally use different Groq accounts/keys later.
        self.api_key = api_key or settings.GROQ_API_KEY_1

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }

        response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Asks the model for JSON only, parses it, raises if invalid.
        Callers (agents) decide how to handle parse failures — this
        method just does the LLM call + parse, nothing more."""
        raw = self.complete(system_prompt, user_prompt, temperature=0.2)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)