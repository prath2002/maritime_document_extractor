from importlib import reload

from fastapi.testclient import TestClient

from app import main as main_module


def test_health_endpoint_returns_ok_with_live_dependencies(env_override, migrated_database):
    env_override({"DATABASE_URL": migrated_database})
    reloaded = reload(main_module)
    app = reloaded.create_app()

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "OK"
    assert payload["version"] == "0.1.0"
    assert payload["uptime"] >= 0
    assert payload["dependencies"]["database"]["status"] == "OK"
    assert payload["dependencies"]["queue"]["status"] == "OK"
    assert payload["dependencies"]["llmProvider"]["status"] == "OK"
    assert payload["timestamp"]
