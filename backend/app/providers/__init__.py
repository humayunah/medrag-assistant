"""LLM provider abstraction layer.

Re-exports every concrete provider, the base types, and the router so that
callers can simply write::

    from app.providers import ProviderRouter, LLMResponse
"""

from app.providers.base import LLMProvider, LLMResponse
from app.providers.claude import ClaudeProvider
from app.providers.gemini import GeminiProvider
from app.providers.groq import GroqProvider
from app.providers.huggingface_llm import HuggingFaceProvider
from app.providers.router import CircuitBreaker, ProviderRouter

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "ClaudeProvider",
    "GeminiProvider",
    "GroqProvider",
    "HuggingFaceProvider",
    "CircuitBreaker",
    "ProviderRouter",
]
