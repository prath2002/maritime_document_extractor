from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Extraction
from app.db.repos.extraction_repo import ExtractionRepo
from app.db.repos.session_repo import SessionRepo
from app.llm import (
    EXTRACTION_PROMPT,
    ExtractionFailureCode,
    ExtractionPipelineFailure,
    ExtractionPipelineSuccess,
    LLMProvider,
)
from app.services.extraction_core import ExtractionCoreService
from app.utils.document_preparation import prepare_document
from app.utils.hash import sha256_hexdigest


class UnknownSessionError(RuntimeError):
    """Raised when a requested session does not exist."""


@dataclass(slots=True)
class SyncExtractionOutcome:
    extraction: Extraction
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None


class SyncExtractionService:
    def __init__(
        self,
        *,
        db_session: AsyncSession,
        provider: LLMProvider | None,
        prompt_version: str,
        provider_error_message: str | None = None,
    ):
        self.db_session = db_session
        self.provider = provider
        self.prompt_version = prompt_version
        self.provider_error_message = provider_error_message
        self.session_repo = SessionRepo(db_session)
        self.extraction_repo = ExtractionRepo(db_session)

    async def run(
        self,
        *,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
        session_id: UUID | None,
    ) -> SyncExtractionOutcome:
        session = await self._resolve_session(session_id)
        file_hash = sha256_hexdigest(content_bytes)
        existing = await self.extraction_repo.find_by_session_and_hash(session.id, file_hash)

        if existing is not None and existing.status == "COMPLETE":
            return SyncExtractionOutcome(
                extraction=existing,
                status_code=200,
                headers={"X-Deduplicated": "true"},
            )

        if self.provider is None:
            record = await self._persist_failure_without_provider(
                existing=existing,
                session_id=session.id,
                file_name=file_name,
                mime_type=mime_type,
                content_bytes=content_bytes,
                file_hash=file_hash,
            )
            return SyncExtractionOutcome(
                extraction=record,
                status_code=503,
                error_code="LLM_PROVIDER_UNAVAILABLE",
                message=self.provider_error_message or "No LLM provider is currently configured.",
            )

        prepared_document = prepare_document(
            file_name=file_name,
            mime_type=mime_type,
            content_bytes=content_bytes,
        )
        extraction_core = ExtractionCoreService(
            provider=self.provider,
            prompt_version=self.prompt_version,
        )
        pipeline_result = await extraction_core.run(
            document=prepared_document,
            prompt=EXTRACTION_PROMPT,
        )

        if isinstance(pipeline_result, ExtractionPipelineSuccess):
            data = self._build_success_data(
                session_id=session.id,
                file_name=file_name,
                mime_type=mime_type,
                content_bytes=content_bytes,
                file_hash=file_hash,
                result=pipeline_result,
            )
            record, headers = await self._persist_record(
                existing=existing,
                data=data,
                prefer_existing_complete=True,
            )
            return SyncExtractionOutcome(extraction=record, status_code=200, headers=headers)

        data = self._build_failure_data(
            session_id=session.id,
            file_name=file_name,
            mime_type=mime_type,
            content_bytes=content_bytes,
            file_hash=file_hash,
            result=pipeline_result,
        )
        record, headers = await self._persist_record(
            existing=existing,
            data=data,
            prefer_existing_complete=False,
        )

        if record.status == "COMPLETE":
            return SyncExtractionOutcome(extraction=record, status_code=200, headers=headers)

        status_code = 422 if pipeline_result.error_code == ExtractionFailureCode.LLM_JSON_PARSE_FAIL else 500
        return SyncExtractionOutcome(
            extraction=record,
            status_code=status_code,
            headers=headers,
            error_code=pipeline_result.error_code.value,
            message=pipeline_result.message,
        )

    async def _resolve_session(self, session_id: UUID | None):
        if session_id is None:
            return await self.session_repo.create()

        session = await self.session_repo.get_by_id(session_id)
        if session is None:
            raise UnknownSessionError(f"Session '{session_id}' was not found.")
        return session

    async def _persist_failure_without_provider(
        self,
        *,
        existing: Extraction | None,
        session_id: UUID,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
        file_hash: str,
    ) -> Extraction:
        data = self._blank_failure_data(
            session_id=session_id,
            file_name=file_name,
            mime_type=mime_type,
            content_bytes=content_bytes,
            file_hash=file_hash,
            message=self.provider_error_message or "No LLM provider is currently configured.",
            processing_time_ms=0,
        )
        record, _ = await self._persist_record(
            existing=existing,
            data=data,
            prefer_existing_complete=False,
        )
        return record

    async def _persist_record(
        self,
        *,
        existing: Extraction | None,
        data: dict[str, Any],
        prefer_existing_complete: bool,
    ) -> tuple[Extraction, dict[str, str]]:
        headers: dict[str, str] = {}

        if existing is not None:
            record = await self.extraction_repo.update(existing, **data)
            await self.db_session.commit()
            return record, headers

        record, created = await self.extraction_repo.create_or_get_existing(**data)
        if created:
            await self.db_session.commit()
            return record, headers

        if prefer_existing_complete and record.status == "COMPLETE":
            headers["X-Deduplicated"] = "true"
            await self.db_session.commit()
            return record, headers

        record = await self.extraction_repo.update(record, **data)
        await self.db_session.commit()
        return record, headers

    def _build_success_data(
        self,
        *,
        session_id: UUID,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
        file_hash: str,
        result: ExtractionPipelineSuccess,
    ) -> dict[str, Any]:
        extraction = result.extraction
        validity_payload = extraction.validity.model_dump(mode="json", by_alias=True)
        compliance_payload = extraction.compliance.model_dump(mode="json", by_alias=True)
        medical_payload = extraction.medical_data.model_dump(mode="json", by_alias=True)

        return {
            "session_id": session_id,
            "file_name": file_name,
            "file_hash": file_hash,
            "file_size_bytes": len(content_bytes),
            "mime_type": mime_type,
            "status": "COMPLETE",
            "document_type": extraction.detection.document_type,
            "document_name": extraction.detection.document_name,
            "category": extraction.detection.category.value,
            "applicable_role": extraction.detection.applicable_role.value,
            "confidence": extraction.detection.confidence.value,
            "is_required": extraction.detection.is_required,
            "holder_name": extraction.holder.full_name,
            "date_of_birth": extraction.holder.date_of_birth,
            "nationality": extraction.holder.nationality,
            "sirb_number": extraction.holder.sirb_number,
            "passport_number": extraction.holder.passport_number,
            "rank": extraction.holder.rank,
            "date_of_issue": _parse_date_or_none(extraction.validity.date_of_issue),
            "date_of_expiry": _parse_date_or_none(extraction.validity.date_of_expiry),
            "is_expired": extraction.validity.is_expired,
            "days_until_expiry": extraction.validity.days_until_expiry,
            "issuing_authority": extraction.compliance.issuing_authority,
            "fitness_result": extraction.medical_data.fitness_result.value,
            "drug_test_result": extraction.medical_data.drug_test_result.value,
            "fields_json": [field.model_dump(mode="json") for field in extraction.fields],
            "validity_json": validity_payload,
            "medical_data_json": medical_payload,
            "compliance_json": compliance_payload,
            "flags_json": [flag.model_dump(mode="json") for flag in extraction.flags],
            "raw_llm_response": result.raw_llm_response,
            "summary": extraction.summary,
            "prompt_version": result.prompt_version,
            "processing_time_ms": result.processing_time_ms,
        }

    def _build_failure_data(
        self,
        *,
        session_id: UUID,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
        file_hash: str,
        result: ExtractionPipelineFailure,
    ) -> dict[str, Any]:
        raw_response = result.raw_llm_response or result.message
        return self._blank_failure_data(
            session_id=session_id,
            file_name=file_name,
            mime_type=mime_type,
            content_bytes=content_bytes,
            file_hash=file_hash,
            message=raw_response,
            processing_time_ms=result.processing_time_ms,
        )

    def _blank_failure_data(
        self,
        *,
        session_id: UUID,
        file_name: str,
        mime_type: str,
        content_bytes: bytes,
        file_hash: str,
        message: str,
        processing_time_ms: int,
    ) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "file_name": file_name,
            "file_hash": file_hash,
            "file_size_bytes": len(content_bytes),
            "mime_type": mime_type,
            "status": "FAILED",
            "document_type": None,
            "document_name": None,
            "category": None,
            "applicable_role": None,
            "confidence": None,
            "is_required": False,
            "holder_name": None,
            "date_of_birth": None,
            "nationality": None,
            "sirb_number": None,
            "passport_number": None,
            "rank": None,
            "date_of_issue": None,
            "date_of_expiry": None,
            "is_expired": False,
            "days_until_expiry": None,
            "issuing_authority": None,
            "fitness_result": None,
            "drug_test_result": None,
            "fields_json": None,
            "validity_json": None,
            "medical_data_json": None,
            "compliance_json": None,
            "flags_json": None,
            "raw_llm_response": message,
            "summary": None,
            "prompt_version": self.prompt_version,
            "processing_time_ms": processing_time_ms,
        }


def _parse_date_or_none(raw_value: str | None):
    if raw_value in {None, "", "No Expiry", "Lifetime"}:
        return None

    try:
        return datetime.strptime(raw_value, "%d/%m/%Y").date()
    except ValueError:
        return None
