"""
Thin wrapper around Groq's OpenAI-compatible chat completions endpoint.

Phase 8 adds latency and token accounting to every call, and exposes a
running tally so the orchestrator can report per-task cost/time totals.
Groq doesn't bill per-token like OpenAI, but token counts are still the
standard proxy for "how much did this cost" — most providers use them,
and tracking them here means swapping providers later doesn't lose this.
"""

import json
import time
import requests
from config.settings import settings


class LLMClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GROQ_API_KEY_1
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_latency_seconds = 0.0
        self.call_count = 0

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

        start = time.time()
        response = requests.post(settings.GROQ_API_URL, headers=headers, json=payload, timeout=30)
        elapsed = time.time() - start
        response.raise_for_status()
        data = response.json()

        usage = data.get("usage", {})
        self.total_input_tokens += usage.get("prompt_tokens", 0)
        self.total_output_tokens += usage.get("completion_tokens", 0)
        self.total_latency_seconds += elapsed
        self.call_count += 1

        return data["choices"][0]["message"]["content"]

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict:
        raw = self.complete(system_prompt, user_prompt, temperature=0.2)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(cleaned)

    def get_usage_summary(self) -> dict:
        return {
            "call_count": self.call_count,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_latency_seconds": round(self.total_latency_seconds, 2),
        }