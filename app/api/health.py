from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.health import DependencyHealth, HealthDependencies, HealthResponse

router = APIRouter(tags=["health"])


async def _check_database(request: Request) -> DependencyHealth:
    checker = request.app.state.db_health_checker
    try:
        await checker()
    except Exception as exc:
        return DependencyHealth(status="DEGRADED", detail=f"Database health check failed: {exc}")
    return DependencyHealth(status="OK", detail="Database connection is healthy.")


async def _check_queue(request: Request) -> DependencyHealth:
    status, detail = await request.app.state.queue_manager.health_check()
    return DependencyHealth(status=status, detail=detail)


async def _check_llm_provider(request: Request) -> DependencyHealth:
    provider_error = getattr(request.app.state, "llm_provider_error", None)
    if provider_error:
        return DependencyHealth(status="DEGRADED", detail=provider_error)

    provider = getattr(request.app.state, "llm_provider", None)
    if provider is None:
        return DependencyHealth(status="DEGRADED", detail="No LLM provider was initialized.")

    status, detail = await provider.health_check()
    return DependencyHealth(status=status, detail=detail)


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> JSONResponse:
    database = await _check_database(request)
    queue = await _check_queue(request)
    llm_provider = await _check_llm_provider(request)

    dependencies = HealthDependencies(
        database=database,
        queue=queue,
        llmProvider=llm_provider,
    )
    overall_status = "OK"
    if any(check.status != "OK" for check in (database, queue, llm_provider)):
        overall_status = "DEGRADED"

    started_at = request.app.state.started_at
    payload = HealthResponse(
        status=overall_status,
        version=request.app.version,
        uptime=max(0, int((datetime.now(UTC) - started_at).total_seconds())),
        dependencies=dependencies,
        timestamp=datetime.now(UTC).isoformat(),
    )
    status_code = 200 if overall_status == "OK" else 503
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json", by_alias=True))
