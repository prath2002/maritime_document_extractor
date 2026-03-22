import asyncio
from importlib import reload

from fastapi.testclient import TestClient

from app import main as main_module


def test_app_imports_cleanly(env_override):
    env_override()

    reloaded = reload(main_module)

    assert reloaded.app is not None


def test_test_client_starts_cleanly(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["name"] == "SMDE"


def test_app_has_expected_metadata(app_instance):
    assert app_instance.title == "Smart Maritime Document Extractor"
    assert app_instance.version == "0.1.0"


def test_env_override_fixture_works(env_override):
    values = env_override({"APP_ENV": "development"})

    assert values["APP_ENV"] == "development"


async def test_async_test_support_is_configured():
    await asyncio.sleep(0)

    assert True
