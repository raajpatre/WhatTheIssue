"""
Gemini Provider implementation using REST API.
"""

import os
import httpx
from app.ai.providers.base import LLMProvider

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
TIMEOUT_SECONDS = 20.0


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider via direct REST API.
    Uses response_mime_type: "application/json" for structured output.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        # VERIFY: gemini-1.5-flash or gemini-2.5-flash per current free tier
        self.model = model or os.getenv("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }

        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned from Gemini API")
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise ValueError("No content parts returned from Gemini API")
            return parts[0].get("text", "")
