from collections.abc import Iterator
from importlib import reload

import pytest
from fastapi.testclient import TestClient

from app import config as config_module


VALID_ENV = {
    "APP_NAME": "SMDE",
    "APP_ENV": "test",
    "PORT": "8000",
    "DATABASE_URL": "postgresql+asyncpg://smde:smde@localhost:5432/smde",
    "LLM_PROVIDER": "claude",
    "LLM_MODEL": "claude-haiku-4-5-20251001",
    "LLM_API_KEY": "test-key",
    "PROMPT_VERSION": "v1.0",
    "SYNC_MAX_FILE_SIZE_MB": "2",
    "QUEUE_MAX_DEPTH": "50",
    "WORKER_HEARTBEAT_INTERVAL_S": "10",
    "STALE_JOB_TIMEOUT_MINUTES": "5",
}


@pytest.fixture
def env_override(monkeypatch: pytest.MonkeyPatch):
    def apply(overrides: dict[str, str | None] | None = None) -> dict[str, str]:
        values = VALID_ENV.copy()
        if overrides:
            for key, value in overrides.items():
                if value is None:
                    values.pop(key, None)
                else:
                    values[key] = value

        keys = set(VALID_ENV) | set(overrides or {})
        for key in keys:
            monkeypatch.delenv(key, raising=False)

        monkeypatch.setenv("SMDE_ENV_FILE", "__tests__.env")

        for key, value in values.items():
            monkeypatch.setenv(key, value)

        config_module.get_settings.cache_clear()
        return values

    return apply


@pytest.fixture
def app_instance(env_override):
    env_override()
    from app import main as main_module

    reload(main_module)
    return main_module.create_app()


@pytest.fixture
def client(app_instance) -> Iterator[TestClient]:
    with TestClient(app_instance) as test_client:
        yield test_client
