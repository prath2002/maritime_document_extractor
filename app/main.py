from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = get_settings()
        yield

    app = FastAPI(
        title="Smart Maritime Document Extractor",
        version="0.1.0",
        lifespan=lifespan,
    )

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
