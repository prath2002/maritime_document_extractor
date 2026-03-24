from __future__ import annotations

import asyncio
from typing import Any, Callable

from app.llm.base import (
    LLMProvider,
    ProviderClientUnavailableError,
    ProviderRequestError,
    ProviderTimeoutError,
)
from app.llm.types import PreparedDocument


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, *, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        self._client: Any | None = None
        self._sdk_types: Any | None = None

    async def extract_document(
        self,
        *,
        document: PreparedDocument,
        prompt: str,
        timeout_seconds: int = 30,
    ) -> str:
        return await self._run_with_timeout(
            lambda: self._generate_document_sync(document=document, prompt=prompt),
            timeout_seconds=timeout_seconds,
        )

    async def generate_text(self, *, prompt: str, timeout_seconds: int = 15) -> str:
        return await self._run_with_timeout(
            lambda: self._generate_text_sync(prompt=prompt),
            timeout_seconds=timeout_seconds,
        )

    async def health_check(self) -> tuple[str, str | None]:
        if not self.api_key or self.api_key == "replace_me":
            return "DEGRADED", "Gemini API key is missing or still set to a placeholder."
        if not self.model_name:
            return "DEGRADED", "Gemini model name is not configured."
        return "OK", f"Gemini provider configured for model '{self.model_name}'."

    async def _run_with_timeout(self, operation: Callable[[], str], *, timeout_seconds: int) -> str:
        try:
            return await asyncio.wait_for(asyncio.to_thread(operation), timeout=timeout_seconds)
        except TimeoutError as exc:
            raise ProviderTimeoutError() from exc
        except (ProviderRequestError, ProviderClientUnavailableError):
            raise
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ProviderRequestError(f"Gemini request failed: {exc}") from exc

    def _generate_document_sync(self, *, document: PreparedDocument, prompt: str) -> str:
        _, sdk_types = self._get_sdk_modules()
        contents = [
            prompt,
            sdk_types.Part.from_bytes(data=document.content_bytes, mime_type=document.mime_type),
        ]
        return self._generate_content_sync(contents)

    def _generate_text_sync(self, *, prompt: str) -> str:
        return self._generate_content_sync(prompt)

    def _generate_content_sync(self, contents: Any) -> str:
        client, _ = self._get_sdk_modules()
        response = client.models.generate_content(model=self.model_name, contents=contents)
        text = getattr(response, "text", None)
        if not text:
            raise ProviderRequestError("Gemini returned an empty text response.")
        return text

    def _get_sdk_modules(self) -> tuple[Any, Any]:
        if self._client is not None and self._sdk_types is not None:
            return self._client, self._sdk_types

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - exercised only when dependency is absent
            raise ProviderClientUnavailableError(
                "The Gemini SDK is not installed. Install the 'google-genai' package to enable extraction."
            ) from exc

        self._client = genai.Client(api_key=self.api_key)
        self._sdk_types = types
        return self._client, self._sdk_types
