import pytest
from pydantic import ValidationError

from app.config import get_settings


def test_settings_load_with_valid_env(env_override):
    env_override()

    settings = get_settings()

    assert settings.app_name == "SMDE"
    assert settings.app_env == "test"
    assert settings.api_prefix == "/api/v1"


def test_settings_fail_when_database_url_missing(env_override):
    env_override({"DATABASE_URL": None})

    with pytest.raises(ValidationError):
        get_settings()


def test_settings_fail_when_llm_provider_missing(env_override):
    env_override({"LLM_PROVIDER": None})

    with pytest.raises(ValidationError):
        get_settings()


def test_settings_fail_when_llm_api_key_missing(env_override):
    env_override({"LLM_API_KEY": None})

    with pytest.raises(ValidationError):
        get_settings()
