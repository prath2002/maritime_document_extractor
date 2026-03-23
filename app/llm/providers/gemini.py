from app.llm.base import LLMProvider


class GeminiProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, *, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key

    async def health_check(self) -> tuple[str, str | None]:
        if not self.api_key or self.api_key == "replace_me":
            return "DEGRADED", "Gemini API key is missing or still set to a placeholder."
        if not self.model_name:
            return "DEGRADED", "Gemini model name is not configured."
        return "OK", f"Gemini provider configured for model '{self.model_name}'."
