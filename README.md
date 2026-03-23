# SMDE

Smart Maritime Document Extractor backend.

## Current Status

This repository currently contains the completed foundation for:

- Component 1: project bootstrap
- Component 2: database and persistence layer
- Component 3: app bootstrap and `GET /api/health`

Implemented so far:

- `uv`-managed Python project
- FastAPI app bootstrap with startup and shutdown lifecycle wiring
- typed environment settings
- async SQLAlchemy database layer
- Alembic migration setup
- initial PostgreSQL schema for:
  - `sessions`
  - `extractions`
  - `jobs`
  - `validations`
- repository layer for the core persistence entities
- lightweight queue manager bootstrap
- Gemini-first LLM provider bootstrap for health wiring
- `GET /api/health` with real database, queue, and provider dependency states
- unit and integration tests for config, app bootstrap, migrations, repositories, and health checks

Default provider choice for the first real multimodal implementation path:

- `LLM_PROVIDER=gemini`
- `LLM_MODEL=gemini-2.5-flash-lite`

## Local Setup

1. Create a local env file from the example:

```powershell
Copy-Item .env.example .env
```

2. Install dependencies with `uv`:

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
uv sync --dev --python python
```

3. Start PostgreSQL.

Option A: local Docker database

```powershell
docker compose up -d postgres
```

Option B: external PostgreSQL/Supabase

Set `DATABASE_URL` in `.env` to your remote database connection string.

4. Run migrations:

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
uv run alembic upgrade head
```

5. Run the app:

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
uv run uvicorn app.main:app --reload
```

## Health Check

Call the health endpoint after startup:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

Expected behavior:

- `200 OK` when database, queue, and configured LLM provider are healthy
- `503` when one or more dependencies are degraded

## Run Tests

```powershell
$env:UV_CACHE_DIR = (Join-Path (Get-Location) '.uv-cache')
uv run pytest
```

## What Component 3 Added

- startup and shutdown lifecycle wiring in `app/main.py`
- reusable dependency helpers in `app/dependencies.py`
- database ping helper in `app/db/health.py`
- lightweight queue manager in `app/queue/manager.py`
- Gemini-first provider bootstrap in `app/llm/`
- health response models in `app/schemas/health.py`
- `GET /api/health` route in `app/api/health.py`
- health endpoint tests for healthy and degraded paths

## Planning Docs

- `documents/COMPONENT_PLAN.md`: overall delivery roadmap
- `documents/COMPONENT_2_TASK_LIST.md`: completed database and persistence checklist
- `documents/COMPONENT_3_TASK_LIST.md`: completed app bootstrap and health-endpoint checklist

## Verification

The following are verified:

- `uv run pytest`
- `uv run alembic upgrade head`
- direct local `GET /api/health` call returning `200 OK` with healthy dependencies
- direct local `GET /api/health` call returning `503` for degraded provider configuration

## Notes

- The app validates required environment variables during startup.
- The database schema and health endpoint are now in place for later API/service components.
- Google Gemini is the default planned LLM provider going forward because it offers an official free multimodal tier for image/document input.
- Higher-level extraction, async job, validation, and report flows are added in later components.
