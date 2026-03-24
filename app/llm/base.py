from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.types import PreparedDocument


class LLMProviderError(RuntimeError):
    """Base error for provider bootstrap and health issues."""


class UnsupportedProviderError(LLMProviderError):
    """Raised when the configured provider is known but not yet implemented."""


class ProviderClientUnavailableError(LLMProviderError):
    """Raised when the configured provider SDK is not installed locally."""


class ProviderRequestError(LLMProviderError):
    """Raised when the provider rejects or cannot complete a request."""

    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class ProviderTimeoutError(ProviderRequestError):
    """Raised when a provider request exceeds the configured timeout."""

    def __init__(self, message: str = "The LLM provider request timed out."):
        super().__init__(message, retryable=True)


class LLMProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    async def extract_document(
        self,
        *,
        document: PreparedDocument,
        prompt: str,
        timeout_seconds: int = 30,
    ) -> str:
        """Run a multimodal document extraction request and return the raw text response."""

    @abstractmethod
    async def generate_text(self, *, prompt: str, timeout_seconds: int = 15) -> str:
        """Run a text-only generation request and return the raw text response."""

    @abstractmethod
    async def health_check(self) -> tuple[str, str | None]:
        """Return provider status and a human-readable detail."""

    async def close(self) -> None:
        """Allow providers to release shared resources on shutdown."""
