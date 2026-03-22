# SMDE

Smart Maritime Document Extractor backend scaffold.

## Component 1 Status

This repository currently contains the Component 1 foundation:

- `uv`-managed Python project
- FastAPI app bootstrap
- typed environment settings
- initial unit tests

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

3. Run the app:

```powershell
uv run uvicorn app.main:app --reload
```

## Run Tests

```powershell
uv run pytest
```

## Notes

- The app validates required environment variables during startup.
- Database connectivity and health checks are added in later components.
