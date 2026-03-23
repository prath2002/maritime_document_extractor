from importlib import reload

from fastapi.testclient import TestClient

from app import main as main_module


class HealthyProvider:
    async def health_check(self) -> tuple[str, str | None]:
        return "OK", "Mock provider is healthy."

    async def close(self) -> None:
        return None


def test_health_endpoint_returns_degraded_when_database_check_fails(app_instance):
    with TestClient(app_instance) as client:
        async def failing_db_health() -> None:
            raise RuntimeError("database is unavailable")

        client.app.state.db_health_checker = failing_db_health
        client.app.state.llm_provider = HealthyProvider()
        client.app.state.llm_provider_error = None

        response = client.get("/api/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "DEGRADED"
    assert payload["dependencies"]["database"]["status"] == "DEGRADED"
    assert "database is unavailable" in payload["dependencies"]["database"]["detail"]
    assert payload["dependencies"]["llmProvider"]["status"] == "OK"


def test_health_endpoint_returns_degraded_when_provider_bootstrap_fails(env_override, migrated_database):
    env_override(
        {
            "DATABASE_URL": migrated_database,
            "LLM_PROVIDER": "claude",
            "LLM_MODEL": "claude-haiku-4-5-20251001",
        }
    )

    reloaded = reload(main_module)
    app = reloaded.create_app()

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 503
    payload = response.json()
    assert payload["dependencies"]["database"]["status"] == "OK"
    assert payload["dependencies"]["llmProvider"]["status"] == "DEGRADED"
    assert "not yet implemented" in payload["dependencies"]["llmProvider"]["detail"]


def test_app_startup_and_shutdown_manage_component_3_resources(env_override, monkeypatch):
    env_override()
    reloaded = reload(main_module)
    dispose_calls = {"count": 0}

    async def fake_dispose_engine() -> None:
        dispose_calls["count"] += 1

    monkeypatch.setattr(reloaded, "dispose_engine", fake_dispose_engine)
    app = reloaded.create_app()

    with TestClient(app) as client:
        assert client.app.state.settings.app_name == "SMDE"
        assert client.app.state.started_at is not None
        assert client.app.state.queue_manager is not None
        assert client.app.state.db_health_checker is not None

    assert dispose_calls["count"] == 1
    assert app.state.queue_manager._closed is True
