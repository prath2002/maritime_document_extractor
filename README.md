# SMDE

Smart Maritime Document Extractor backend.

## Current Status

This repository currently contains the completed foundation for:

- Component 1: project bootstrap
- Component 2: database and persistence layer
- Component 3: app bootstrap and `GET /api/v1/health`
- Component 4: LLM reliability core
- Component 5: sync extraction flow with persisted results and deduplication

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
- Gemini-first provider bootstrap for health wiring
- extraction-ready provider abstraction with Gemini SDK-backed transport
- typed extraction and reliability pipeline models
- in-memory document preparation and base64 helpers
- JSON boundary extraction plus repair-prompt flow
- timeout handling and LOW-confidence retry orchestration
- `GET /api/v1/health` with real database, queue, and provider dependency states
- `POST /api/v1/extract?mode=sync` with:
  - multipart upload handling
  - MIME type and 10 MB file-size validation
  - optional session auto-create
  - SHA-256 deduplication within a session
  - persisted success and failed extraction records
  - normalized extraction/error response payloads
- unit and integration tests for config, app bootstrap, migrations, repositories, health checks, the Component 4 LLM reliability pipeline, and the Component 5 sync extraction flow

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
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Expected behavior:

- `200 OK` when database, queue, and configured LLM provider are healthy
- `503` when one or more dependencies are degraded

## Sync Extraction

Call the sync extraction endpoint with a supported document upload:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/extract?mode=sync" ^
  -F "document=@sample.pdf;type=application/pdf"
```

Optional existing-session usage:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v1/extract?mode=sync" ^
  -F "document=@sample.pdf;type=application/pdf" ^
  -F "sessionId=<existing-session-uuid>"
```

Current sync extraction behavior:

- accepts `application/pdf`, `image/jpeg`, and `image/png`
- rejects files larger than 10 MB
- creates a new session when `sessionId` is omitted
- returns a cached result with `X-Deduplicated: true` when the same file is uploaded to the same session again
- persists failed extraction outcomes instead of dropping them

Current limitation:

- only `mode=sync` is implemented in this repository today
- queue-backed `mode=async` and job polling begin in Component 6

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
- `GET /api/v1/health` route in `app/api/health.py`
- health endpoint tests for healthy and degraded paths

## What Component 4 Added

- extraction-ready provider interface in `app/llm/base.py`
- Gemini SDK-backed extraction transport in `app/llm/providers/gemini.py`
- exact assignment extraction prompt plus repair/retry prompt helpers in `app/llm/prompts.py`
- typed extraction payload and pipeline result models in `app/llm/types.py`
- in-memory document preparation helpers in `app/utils/document_preparation.py`
- JSON boundary extraction helpers in `app/utils/json_extractor.py`
- reliability orchestration in `app/services/extraction_core.py`
- unit tests for document preparation, provider factory/provider behavior, JSON extraction, timeout handling, repair flow, and LOW-confidence retry selection

## What Component 5 Added

- `POST /api/v1/extract` route in `app/api/extract.py`
- sync extraction orchestration in `app/services/sync_extraction.py`
- sync extraction success/error response models in `app/schemas/extraction.py`
- SHA-256 hashing helper in `app/utils/hash.py`
- extraction repository update support for persisted retry/failure handling
- integration tests for sync happy path, validation failures, deduplication, parse failure persistence, and timeout persistence

## Planning Docs

- `documents/COMPONENT_PLAN.md`: overall delivery roadmap
- `documents/COMPONENT_2_TASK_LIST.md`: completed database and persistence checklist
- `documents/COMPONENT_3_TASK_LIST.md`: completed app bootstrap and health-endpoint checklist
- `documents/COMPONENT_4_TASK_LIST.md`: completed LLM reliability-core checklist
- `documents/COMPONENT_5_TASK_LIST.md`: completed sync extraction checklist

## Verification

The following are verified:

- `uv run pytest`
- `uv run alembic upgrade head`
- direct local `GET /api/v1/health` call returning `200 OK` with healthy dependencies
- direct local `GET /api/v1/health` call returning `503` for degraded provider configuration
- live Gemini extraction through `ExtractionCoreService` using a non-sensitive generated sample image
- local manual reliability checks for repair, timeout, and LOW-confidence retry behavior using controlled stub responses
- local sync extraction coverage for:
  - successful upload with session auto-create
  - existing-session upload path
  - deduplication with `X-Deduplicated: true`
  - unsupported format handling
  - file-too-large handling
  - parse-failure persistence
  - timeout-failure persistence

## Notes

- The app validates required environment variables during startup.
- Uploaded source documents are kept in memory only for the sync flow; they are not persisted to disk.
- The database schema, health endpoint, LLM reliability core, and sync extraction flow are now in place for later API/service components.
- Google Gemini remains the default planned LLM provider because it offers an official multimodal SDK path and a free-tier-friendly developer workflow.
- The async job flow, polling endpoint, and session-compliance endpoints begin in Component 6.
