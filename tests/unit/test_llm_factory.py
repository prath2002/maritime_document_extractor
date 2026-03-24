import pytest

from app.config import get_settings
from app.llm.base import UnsupportedProviderError
from app.llm.factory import build_llm_provider
from app.llm.providers.gemini import GeminiProvider


def test_build_llm_provider_returns_gemini_provider(env_override):
    env_override()

    provider = build_llm_provider(get_settings())

    assert isinstance(provider, GeminiProvider)
    assert provider.model_name == "gemini-2.5-flash-lite"


def test_build_llm_provider_rejects_unimplemented_provider(env_override):
    env_override({"LLM_PROVIDER": "claude", "LLM_MODEL": "claude-haiku-4-5-20251001"})

    with pytest.raises(UnsupportedProviderError):
        build_llm_provider(get_settings())
