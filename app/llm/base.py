from abc import ABC, abstractmethod


class LLMProviderError(RuntimeError):
    """Base error for provider bootstrap and health issues."""


class UnsupportedProviderError(LLMProviderError):
    """Raised when the configured provider is known but not yet implemented."""


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    async def health_check(self) -> tuple[str, str | None]:
        """Return provider status and a human-readable detail."""

    async def close(self) -> None:
        """Allow providers to release shared resources on shutdown."""
