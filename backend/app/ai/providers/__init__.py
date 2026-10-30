"""
Provider factory for AI layer.
"""

import os
from app.ai.providers.base import LLMProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.ollama import OllamaProvider


def get_provider() -> LLMProvider:
    """
    Pick provider by LLM_PROVIDER env var ('gemini' | 'ollama').
    Default is 'gemini'.
    Switching providers requires zero code changes.
    """
    provider_name = os.getenv("LLM_PROVIDER", "gemini").lower().strip()
    if provider_name == "ollama":
        return OllamaProvider()
    return GeminiProvider()
