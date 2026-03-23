import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from importlib import reload

import asyncpg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import config as config_module
from app.db.base import dispose_engine


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


TEST_DATABASE_NAME = "smde_component2_test"


def _as_driver_url(url: str, *, drivername: str, database: str | None = None) -> str:
    parsed = make_url(url)
    if database is not None:
        parsed = parsed.set(database=database)
    return str(parsed.set(drivername=drivername))


def build_test_database_url() -> str:
    return _as_driver_url(
        VALID_ENV["DATABASE_URL"],
        drivername="postgresql+asyncpg",
        database=TEST_DATABASE_NAME,
    )


def build_admin_database_url() -> str:
    return _as_driver_url(VALID_ENV["DATABASE_URL"], drivername="postgresql", database="postgres")


async def recreate_database(admin_dsn: str, database_name: str) -> None:
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            database_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        await conn.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await conn.close()


async def drop_database(admin_dsn: str, database_name: str) -> None:
    conn = await asyncpg.connect(admin_dsn)
    try:
        await conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = $1 AND pid <> pg_backend_pid()",
            database_name,
        )
        await conn.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
    finally:
        await conn.close()


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


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return build_test_database_url()


@pytest.fixture(scope="session")
def alembic_config(test_database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", test_database_url)
    return config


@pytest.fixture(scope="session")
def migrated_database(test_database_url: str, alembic_config: Config) -> str:
    admin_dsn = build_admin_database_url()
    previous_values = {key: os.environ.get(key) for key in VALID_ENV}
    previous_env_file = os.environ.get("SMDE_ENV_FILE")

    try:
        asyncio.run(recreate_database(admin_dsn, TEST_DATABASE_NAME))
    except Exception as exc:
        pytest.skip(f"PostgreSQL is unavailable for integration tests: {exc}")

    migration_env = VALID_ENV.copy()
    migration_env["DATABASE_URL"] = test_database_url
    for key, value in migration_env.items():
        os.environ[key] = value
    os.environ["SMDE_ENV_FILE"] = "__tests__.env"

    config_module.get_settings.cache_clear()
    command.upgrade(alembic_config, "head")

    yield test_database_url

    asyncio.run(drop_database(admin_dsn, TEST_DATABASE_NAME))

    for key, value in previous_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value

    if previous_env_file is None:
        os.environ.pop("SMDE_ENV_FILE", None)
    else:
        os.environ["SMDE_ENV_FILE"] = previous_env_file

    config_module.get_settings.cache_clear()


@pytest.fixture
def db_env_override(monkeypatch: pytest.MonkeyPatch, migrated_database: str) -> dict[str, str]:
    values = VALID_ENV.copy()
    values["DATABASE_URL"] = migrated_database

    keys = set(VALID_ENV)
    for key in keys:
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("SMDE_ENV_FILE", "__tests__.env")
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    config_module.get_settings.cache_clear()
    asyncio.run(dispose_engine())
    return values


@pytest_asyncio.fixture
async def db_session(db_env_override, migrated_database: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(migrated_database, future=True)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(bind=connection, autoflush=False, expire_on_commit=False)

        async with session_factory() as session:
            yield session

        if transaction.is_active:
            await transaction.rollback()

    await engine.dispose()
