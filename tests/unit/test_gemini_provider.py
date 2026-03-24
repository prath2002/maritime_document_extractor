import time

import pytest

from app.llm.base import ProviderTimeoutError
from app.llm.providers.gemini import GeminiProvider
from app.llm.types import PreparedDocument


async def test_gemini_provider_returns_generated_document_text_when_sync_call_succeeds(monkeypatch):
    provider = GeminiProvider(model_name="gemini-2.5-flash-lite", api_key="test-key")
    document = PreparedDocument(
        file_name="sample.pdf",
        mime_type="application/pdf",
        content_bytes=b"pdf-bytes",
    )

    monkeypatch.setattr(provider, "_generate_document_sync", lambda *, document, prompt: '{"ok":true}')

    result = await provider.extract_document(document=document, prompt="prompt", timeout_seconds=1)

    assert result == '{"ok":true}'


async def test_gemini_provider_wraps_timeout(monkeypatch):
    provider = GeminiProvider(model_name="gemini-2.5-flash-lite", api_key="test-key")

    def slow_generate(*, prompt: str):
        time.sleep(0.05)
        return "{}"

    monkeypatch.setattr(provider, "_generate_text_sync", slow_generate)

    with pytest.raises(ProviderTimeoutError):
        await provider.generate_text(prompt="repair", timeout_seconds=0.01)
