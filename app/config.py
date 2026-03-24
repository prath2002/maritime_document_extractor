from functools import lru_cache
from os import getenv
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(alias="APP_NAME")
    app_env: Literal["development", "test", "staging", "production"] = Field(alias="APP_ENV")
    port: int = Field(alias="PORT")

    database_url: str = Field(alias="DATABASE_URL")

    llm_provider: Literal["claude", "gemini", "groq", "mistral", "openai", "ollama"] = Field(
        alias="LLM_PROVIDER"
    )
    llm_model: str = Field(alias="LLM_MODEL")
    llm_api_key: str = Field(alias="LLM_API_KEY")

    prompt_version: str = Field(default="v1.0", alias="PROMPT_VERSION")
    sync_max_file_size_mb: int = Field(default=2, alias="SYNC_MAX_FILE_SIZE_MB")
    queue_max_depth: int = Field(default=50, alias="QUEUE_MAX_DEPTH")
    worker_heartbeat_interval_s: int = Field(default=10, alias="WORKER_HEARTBEAT_INTERVAL_S")
    stale_job_timeout_minutes: int = Field(default=5, alias="STALE_JOB_TIMEOUT_MINUTES")

    @property
    def api_prefix(self) -> str:
        return "/api/v1"


@lru_cache
def get_settings() -> Settings:
    env_file = getenv("SMDE_ENV_FILE", ".env")
    return Settings(_env_file=env_file)
