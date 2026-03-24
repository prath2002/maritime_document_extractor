from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from app.api import health_router
from app.config import Settings, get_settings
from app.db.base import dispose_engine
from app.db.health import ping_database
from app.llm import LLMProviderError, build_llm_provider
from app.queue import QueueManager


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings = get_settings()
        app.state.settings = settings
        app.state.started_at = datetime.now(UTC)
        app.state.queue_manager = QueueManager(max_depth=settings.queue_max_depth)
        app.state.db_health_checker = ping_database
        app.state.llm_provider_error = None

        try:
            app.state.llm_provider = build_llm_provider(settings)
        except LLMProviderError as exc:
            app.state.llm_provider = None
            app.state.llm_provider_error = str(exc)

        try:
            yield
        finally:
            llm_provider = getattr(app.state, "llm_provider", None)
            if llm_provider is not None:
                await llm_provider.close()

            queue_manager = getattr(app.state, "queue_manager", None)
            if queue_manager is not None:
                await queue_manager.close()

            await dispose_engine()

    app = FastAPI(
        title="Smart Maritime Document Extractor",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health_router, prefix=get_settings().api_prefix)

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        settings: Settings = get_settings()
        return {
            "name": settings.app_name,
            "environment": settings.app_env,
            "version": app.version,
        }

    return app


app = create_app()
