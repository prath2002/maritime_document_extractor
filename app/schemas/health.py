from pydantic import BaseModel, ConfigDict, Field


class DependencyHealth(BaseModel):
    status: str
    detail: str | None = None


class HealthDependencies(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    database: DependencyHealth
    queue: DependencyHealth
    llm_provider: DependencyHealth = Field(alias="llmProvider")


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: int
    dependencies: HealthDependencies
    timestamp: str
