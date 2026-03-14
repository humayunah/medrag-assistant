"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider."""

    content: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


class LLMProvider(ABC):
    """Base contract every LLM provider must fulfil."""

    name: str

    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate a completion from a list of messages.

        Args:
            messages: OpenAI-style message dicts (role / content).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            A populated ``LLMResponse``.
        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Return *True* when the provider API is reachable and operational."""

    def is_configured(self) -> bool:
        """Return *True* when the required API key / token is set."""
        return False
