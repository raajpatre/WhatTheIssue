"""
Ollama Provider implementation using local REST API.
"""

import os
import httpx
from app.ai.providers.base import LLMProvider

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"
TIMEOUT_SECONDS = 20.0


class OllamaProvider(LLMProvider):
    """
    Ollama provider calling POST {OLLAMA_URL}/api/generate
    with format: "json" and stream: false.
    """

    def __init__(self, url: str | None = None, model: str | None = None):
        self.url = (url or os.getenv("OLLAMA_URL") or DEFAULT_OLLAMA_URL).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL

    def generate(self, prompt: str) -> str:
        endpoint = f"{self.url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
