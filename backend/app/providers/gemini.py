"""Google Gemini provider using the ``google-genai`` SDK."""

from __future__ import annotations

import time

import structlog
from google import genai
from google.genai import types

from app.core.config import settings
from app.providers.base import LLMProvider, LLMResponse

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_DEFAULT_MODEL = "gemini-2.0-flash"


class GeminiProvider(LLMProvider):
    """Google Gemini (free-tier) provider."""

    name: str = "gemini"

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model_name = model
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._client

    def is_configured(self) -> bool:
        return bool(settings.GEMINI_API_KEY)

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        log = logger.bind(provider=self.name, model=self._model_name)
        log.debug(
            "gemini.complete.start", temperature=temperature, max_tokens=max_tokens
        )

        system_instruction, contents = _convert_messages(messages)

        client = self._get_client()

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_instruction,
        )

        start = time.monotonic()
        response = await client.aio.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=config,
        )
        latency_ms = (time.monotonic() - start) * 1_000

        prompt_tokens = 0
        completion_tokens = 0
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0

        content = response.text or ""

        log.info(
            "gemini.complete.done",
            latency_ms=round(latency_ms, 1),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return LLMResponse(
            content=content,
            provider=self.name,
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency_ms, 1),
        )

    async def health_check(self) -> bool:
        try:
            client = self._get_client()
            response = await client.aio.models.generate_content(
                model=self._model_name,
                contents="ping",
            )
            return bool(response.text)
        except Exception:
            logger.warning("gemini.health_check.failed", exc_info=True)
            return False


def _convert_messages(messages: list[dict]) -> tuple[str | None, list[types.Content]]:
    """Convert OpenAI-style messages to Gemini contents format."""
    system_instruction: str | None = None
    contents: list[types.Content] = []

    for msg in messages:
        role = msg.get("role", "user")
        text = msg.get("content", "")

        if role == "system":
            system_instruction = text
            continue

        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part(text=text)],
            )
        )

    return system_instruction, contents
