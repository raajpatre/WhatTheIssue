"""
Base LLM Provider interface.
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: str) -> str:
        """
        Generate raw text response from prompt.
        Must return raw text (JSON mode where provider supports it).
        Timeout should be enforced at 20 seconds.
        """
        pass
