from __future__ import annotations

import asyncio
import json
import uuid
from importlib import reload

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import main as main_module
from app.db.models import Extraction
from app.db.repos.session_repo import SessionRepo
from app.llm.base import LLMProvider, ProviderTimeoutError
from app.llm.types import PreparedDocument


class StubProvider(LLMProvider):
    provider_name = "stub"
    model_name = "stub-model"

    def __init__(self, *, document_responses=None, text_responses=None):
        self._document_responses = list(document_responses or [])
        self._text_responses = list(text_responses or [])
        self.extract_calls = 0

    async def extract_document(self, *, document: PreparedDocument, prompt: str, timeout_seconds: int = 30) -> str:
        self.extract_calls += 1
        response = self._document_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def generate_text(self, *, prompt: str, timeout_seconds: int = 15) -> str:
        response = self._text_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def health_check(self) -> tuple[str, str | None]:
        return "OK", None

    async def close(self) -> None:
        return None



def _payload(*, confidence: str = "HIGH") -> dict[str, object]:
    return {
        "detection": {
            "documentType": "PEME",
            "documentName": "Pre-Employment Medical Examination",
            "category": "MEDICAL",
            "applicableRole": "BOTH",
            "isRequired": True,
            "confidence": confidence,
            "detectionReason": "The form title references PEME.",
        },
        "holder": {
            "fullName": "Samuel P. Samoya",
            "dateOfBirth": "12/03/1988",
            "nationality": "Filipino",
            "passportNumber": None,
            "sirbNumber": "C0869326",
            "rank": "Engine Cadet",
            "photo": "PRESENT",
        },
        "fields": [
            {
                "key": "certificate_number",
                "label": "Certificate Number",
                "value": "PEME-123",
                "importance": "HIGH",
                "status": "OK",
            }
        ],
        "validity": {
            "dateOfIssue": "06/01/2025",
            "dateOfExpiry": "06/01/2027",
            "isExpired": False,
            "daysUntilExpiry": 660,
            "revalidationRequired": False,
        },
        "compliance": {
            "issuingAuthority": "Maritime Health Center",
            "regulationReference": None,
            "imoModelCourse": None,
            "recognizedAuthority": True,
            "limitations": None,
        },
        "medicalData": {
            "fitnessResult": "FIT",
            "drugTestResult": "NEGATIVE",
            "restrictions": None,
            "specialNotes": "Cleared by physician.",
            "expiryDate": "06/01/2027",
        },
        "flags": [{"severity": "LOW", "message": "No material concerns."}],
        "summary": "The holder is medically fit for deployment.",
    }



def _build_app(env_override, migrated_database: str, monkeypatch, provider: StubProvider):
    env_override({"DATABASE_URL": migrated_database})
    reloaded = reload(main_module)
    monkeypatch.setattr(reloaded, "build_llm_provider", lambda settings: provider)
    return reloaded.create_app()



def _upload(
    client: TestClient,
    *,
    file_name: str = "sample.pdf",
    content: bytes = b"sample-pdf-bytes",
    content_type: str = "application/pdf",
    session_id: uuid.UUID | None = None,
):
    data = {}
    if session_id is not None:
        data["sessionId"] = str(session_id)

    return client.post(
        "/api/v1/extract?mode=sync",
        files={"document": (file_name, content, content_type)},
        data=data,
    )


async def _create_session(database_url: str) -> uuid.UUID:
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        repo = SessionRepo(session)
        record = await repo.create()
        await session.commit()
        session_id = record.id

    await engine.dispose()
    return session_id


async def _get_extraction(database_url: str, extraction_id: uuid.UUID) -> Extraction | None:
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(select(Extraction).where(Extraction.id == extraction_id))
        record = result.scalar_one_or_none()

    await engine.dispose()
    return record


async def _count_extractions_for_session(database_url: str, session_id: uuid.UUID) -> int:
    engine = create_async_engine(database_url, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        result = await session.execute(
            select(func.count()).select_from(Extraction).where(Extraction.session_id == session_id)
        )
        count = int(result.scalar_one())

    await engine.dispose()
    return count



def test_sync_extract_success_auto_creates_session_and_persists_record(
    env_override, migrated_database, monkeypatch
):
    provider = StubProvider(document_responses=[json.dumps(_payload())])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = _upload(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["documentType"] == "PEME"
    assert payload["sessionId"]
    assert payload["fileName"] == "sample.pdf"
    assert payload["confidence"] == "HIGH"
    assert provider.extract_calls == 1

    record = asyncio.run(_get_extraction(migrated_database, uuid.UUID(payload["id"])))
    assert record is not None
    assert record.status == "COMPLETE"
    assert record.file_name == "sample.pdf"
    assert record.document_type == "PEME"



def test_sync_extract_uses_existing_session_when_session_id_is_provided(
    env_override, migrated_database, monkeypatch
):
    provider = StubProvider(document_responses=[json.dumps(_payload())])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)
    session_id = asyncio.run(_create_session(migrated_database))

    with TestClient(app) as client:
        response = _upload(client, session_id=session_id)

    assert response.status_code == 200
    assert response.json()["sessionId"] == str(session_id)



def test_sync_extract_deduplicates_same_file_within_session(
    env_override, migrated_database, monkeypatch
):
    provider = StubProvider(document_responses=[json.dumps(_payload())])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)
    session_id = asyncio.run(_create_session(migrated_database))

    with TestClient(app) as client:
        first = _upload(client, session_id=session_id)
        second = _upload(client, session_id=session_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers["X-Deduplicated"] == "true"
    assert first.json()["id"] == second.json()["id"]
    assert provider.extract_calls == 1



def test_sync_extract_treats_same_file_in_different_sessions_as_new_work(
    env_override, migrated_database, monkeypatch
):
    provider = StubProvider(
        document_responses=[json.dumps(_payload()), json.dumps(_payload(confidence="MEDIUM"))]
    )
    app = _build_app(env_override, migrated_database, monkeypatch, provider)
    first_session = asyncio.run(_create_session(migrated_database))
    second_session = asyncio.run(_create_session(migrated_database))

    with TestClient(app) as client:
        first = _upload(client, session_id=first_session)
        second = _upload(client, session_id=second_session)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert provider.extract_calls == 2



def test_sync_extract_rejects_unsupported_mime_type(env_override, migrated_database, monkeypatch):
    provider = StubProvider(document_responses=[])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = _upload(client, file_name="sample.txt", content_type="text/plain")

    assert response.status_code == 400
    assert response.json()["error"] == "UNSUPPORTED_FORMAT"
    assert provider.extract_calls == 0



def test_sync_extract_rejects_empty_file(env_override, migrated_database, monkeypatch):
    provider = StubProvider(document_responses=[])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = _upload(client, content=b"")

    assert response.status_code == 400
    assert response.json()["error"] == "EMPTY_FILE"
    assert provider.extract_calls == 0



def test_sync_extract_rejects_file_too_large(env_override, migrated_database, monkeypatch):
    provider = StubProvider(document_responses=[])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = _upload(client, content=b"x" * ((10 * 1024 * 1024) + 1))

    assert response.status_code == 413
    assert response.json()["error"] == "FILE_TOO_LARGE"
    assert provider.extract_calls == 0



def test_sync_extract_rejects_missing_file(env_override, migrated_database, monkeypatch):
    provider = StubProvider(document_responses=[])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = client.post("/api/v1/extract?mode=sync")

    assert response.status_code == 400
    assert response.json()["error"] == "MISSING_FILE"
    assert provider.extract_calls == 0



def test_sync_extract_rejects_invalid_session_id(env_override, migrated_database, monkeypatch):
    provider = StubProvider(document_responses=[])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/extract?mode=sync",
            files={"document": ("sample.pdf", b"sample-pdf-bytes", "application/pdf")},
            data={"sessionId": "not-a-uuid"},
        )

    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_SESSION_ID"



def test_sync_extract_returns_not_found_for_unknown_session(env_override, migrated_database, monkeypatch):
    provider = StubProvider(document_responses=[])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = _upload(client, session_id=uuid.uuid4())

    assert response.status_code == 404
    assert response.json()["error"] == "SESSION_NOT_FOUND"



def test_sync_extract_returns_parse_failure_and_persists_failed_record(
    env_override, migrated_database, monkeypatch
):
    provider = StubProvider(document_responses=["not-json-at-all"], text_responses=["still not json"])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = _upload(client)

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"] == "LLM_JSON_PARSE_FAIL"
    assert payload["extractionId"]

    record = asyncio.run(_get_extraction(migrated_database, uuid.UUID(payload["extractionId"])))
    assert record is not None
    assert record.status == "FAILED"
    assert record.raw_llm_response == "still not json"



def test_sync_extract_returns_timeout_failure_and_persists_failed_record(
    env_override, migrated_database, monkeypatch
):
    provider = StubProvider(document_responses=[ProviderTimeoutError()])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)

    with TestClient(app) as client:
        response = _upload(client)

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"] == "LLM_TIMEOUT"
    assert payload["extractionId"]

    record = asyncio.run(_get_extraction(migrated_database, uuid.UUID(payload["extractionId"])))
    assert record is not None
    assert record.status == "FAILED"
    assert "timed out" in record.raw_llm_response.lower()



def test_sync_extract_persists_one_record_for_deduplicated_uploads(
    env_override, migrated_database, monkeypatch
):
    provider = StubProvider(document_responses=[json.dumps(_payload())])
    app = _build_app(env_override, migrated_database, monkeypatch, provider)
    session_id = asyncio.run(_create_session(migrated_database))

    with TestClient(app) as client:
        _upload(client, session_id=session_id)
        _upload(client, session_id=session_id)

    count = asyncio.run(_count_extractions_for_session(migrated_database, session_id))
    assert count == 1
