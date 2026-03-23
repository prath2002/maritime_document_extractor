import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    return get_settings().database_url


def normalize_database_url(database_url: str) -> tuple[str, dict[str, object]]:
    parsed = make_url(database_url)
    connect_args: dict[str, object] = {}

    sslmode = parsed.query.get("sslmode")
    if sslmode is not None:
        parsed = parsed.difference_update_query(["sslmode"])
        connect_args["ssl"] = build_ssl_connect_arg(sslmode)

    if should_disable_statement_cache(parsed):
        connect_args["statement_cache_size"] = 0

    return parsed.render_as_string(hide_password=False), connect_args


def build_ssl_connect_arg(sslmode: str) -> bool | ssl.SSLContext:
    normalized = sslmode.lower()
    if normalized == "disable":
        return False

    context = ssl.create_default_context()
    if normalized in {"allow", "prefer", "require"}:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def should_disable_statement_cache(parsed_url) -> bool:
    host = parsed_url.host or ""
    port = parsed_url.port

    return host.endswith("pooler.supabase.com") or port in {6432, 6543}


def get_engine() -> AsyncEngine:
    global _engine

    if _engine is None:
        database_url, connect_args = normalize_database_url(get_database_url())
        _engine = create_async_engine(
            database_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            autoflush=False,
            expire_on_commit=False,
        )

    return _session_factory


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        yield session


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    session = get_session_factory()()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()

    _engine = None
    _session_factory = None
