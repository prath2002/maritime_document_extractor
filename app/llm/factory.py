from app.config import Settings, get_settings
from app.llm.base import LLMProvider, UnsupportedProviderError
from app.llm.providers.gemini import GeminiProvider


SUPPORTED_PROVIDERS: dict[str, type[LLMProvider]] = {
    "gemini": GeminiProvider,
}


def build_llm_provider(settings: Settings | None = None) -> LLMProvider:
    active_settings = settings or get_settings()
    provider_class = SUPPORTED_PROVIDERS.get(active_settings.llm_provider)
    if provider_class is None:
        raise UnsupportedProviderError(
            f"Provider '{active_settings.llm_provider}' is configured but not yet implemented."
        )
    return provider_class(model_name=active_settings.llm_model, api_key=active_settings.llm_api_key)
