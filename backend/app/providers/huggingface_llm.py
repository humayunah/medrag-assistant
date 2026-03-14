"""HuggingFace Inference API provider using ``httpx``."""

from __future__ import annotations

import time

import httpx
import structlog

from app.core.config import settings
from app.providers.base import LLMProvider, LLMResponse

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
_HF_INFERENCE_URL = "https://api-inference.huggingface.co/models"
_REQUEST_TIMEOUT = 120.0  # HF models may cold-start


def _messages_to_prompt(messages: list[dict]) -> str:
    """Flatten OpenAI-style messages into a single prompt string.

    Uses Mistral-Instruct chat template conventions:
      [INST] user text [/INST] assistant text
    """
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"<s>[INST] {content} [/INST]</s>")
        elif role == "user":
            parts.append(f"[INST] {content} [/INST]")
        elif role == "assistant":
            parts.append(content)
    return "\n".join(parts)


class HuggingFaceProvider(LLMProvider):
    """HuggingFace Inference API provider (serverless)."""

    name: str = "huggingface"

    def __init__(self, model: str = _DEFAULT_MODEL) -> None:
        self._model_name = model
        self._url = f"{_HF_INFERENCE_URL}/{model}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.HF_API_TOKEN}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return bool(settings.HF_API_TOKEN)

    async def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        log = logger.bind(provider=self.name, model=self._model_name)
        log.debug(
            "huggingface.complete.start", temperature=temperature, max_tokens=max_tokens
        )

        prompt = _messages_to_prompt(messages)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
            },
        }

        start = time.monotonic()
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
            response = await client.post(
                self._url, json=payload, headers=self._headers()
            )
        latency_ms = (time.monotonic() - start) * 1_000

        response.raise_for_status()
        data = response.json()

        # HF returns either a list of generated texts or a single dict.
        if isinstance(data, list) and len(data) > 0:
            content = data[0].get("generated_text", "")
        elif isinstance(data, dict):
            content = data.get("generated_text", "")
        else:
            content = ""

        # HF Inference API does not reliably return token counts.
        # Estimate from character length as a rough proxy.
        prompt_tokens = len(prompt) // 4
        completion_tokens = len(content) // 4

        log.info(
            "huggingface.complete.done",
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(self._url, headers=self._headers())
            # A 200 or a 503 (model loading) both mean the endpoint exists.
            return resp.status_code in {200, 503}
        except Exception:
            logger.warning("huggingface.health_check.failed", exc_info=True)
            return False
